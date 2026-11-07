"""Hardware / software detection for Afterlife.

Everything here is split into two layers:

* **pure parsers** -- ``parse_nvidia_smi``, ``parse_rocminfo``, ``parse_lspci``,
  ``parse_nvcc``, ``parse_version_string``. They take a raw string (the stdout
  of a tool) and return structured data. They never touch the system, so tests
  feed them synthetic fixtures.
* **thin runners** -- ``run_tool`` and ``detect_environment``. They shell out /
  import, wrap *everything* in try/except, and feed whatever they captured into
  the pure parsers. A missing tool yields ``None``; nothing raises.

An "arch" is ``sm_XX`` for NVIDIA (compute capability 7.0 -> ``sm_70``) or
``gfxXXX`` for AMD (``gfx906``).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class GPU:
    """A detected GPU."""

    vendor: str  # "nvidia" | "amd" | "unknown"
    name: str
    arch: str | None  # "sm_70" / "gfx906" / None if we could not resolve it
    source: str  # which tool told us: "nvidia-smi" | "rocminfo" | "lspci"
    pci_id: str | None = None


@dataclass
class Environment:
    """Everything doctor needs to compare against the cliff database."""

    gpus: list[GPU] = field(default_factory=list)
    nvidia_driver: str | None = None
    cuda_toolkit: str | None = None
    rocm: str | None = None
    frameworks: dict[str, str | None] = field(default_factory=dict)
    # tools we tried to run and whether they were present (for honesty in output)
    tools_present: dict[str, bool] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Static lookup tables (fallbacks when a tool can't give us the arch directly)
# ---------------------------------------------------------------------------

# Map a lowercase substring of a GPU marketing name -> compute capability arch.
# Used only as a fallback; nvidia-smi compute_cap is preferred when present.
_NVIDIA_NAME_TO_SM: list[tuple[str, str]] = [
    ("h100", "sm_90"),
    ("h800", "sm_90"),
    ("l40", "sm_89"),
    ("l4", "sm_89"),
    ("rtx 40", "sm_89"),
    ("rtx 50", "sm_120"),
    ("a100", "sm_80"),
    ("a40", "sm_86"),
    ("a10", "sm_86"),
    ("a6000", "sm_86"),
    ("rtx 30", "sm_86"),
    ("rtx a", "sm_86"),
    ("a16", "sm_86"),
    ("a2", "sm_86"),
    ("rtx 20", "sm_75"),
    ("gtx 16", "sm_75"),
    ("titan rtx", "sm_75"),
    ("t4", "sm_75"),
    ("quadro rtx", "sm_75"),
    ("v100", "sm_70"),
    ("titan v", "sm_70"),
    ("gv100", "sm_70"),
    ("p100", "sm_60"),
    ("p40", "sm_61"),
    ("p4", "sm_61"),
    ("gtx 10", "sm_61"),
    ("titan xp", "sm_61"),
    ("titan x (pascal)", "sm_61"),
    ("quadro p", "sm_61"),
    ("m40", "sm_52"),
    ("m60", "sm_52"),
    ("gtx 9", "sm_52"),
    ("titan x", "sm_52"),
]

# Map an AMD marketing name substring -> gfx arch (lspci fallback only).
_AMD_NAME_TO_GFX: list[tuple[str, str]] = [
    ("mi50", "gfx906"),
    ("mi60", "gfx906"),
    ("radeon vii", "gfx906"),
    ("radeon pro vii", "gfx906"),
    ("vega 20", "gfx906"),
    ("mi25", "gfx900"),
    ("vega 10", "gfx900"),
    ("vega 56", "gfx900"),
    ("vega 64", "gfx900"),
    ("mi100", "gfx908"),
    ("mi210", "gfx90a"),
    ("mi250", "gfx90a"),
    ("mi300", "gfx942"),
]


def cc_to_sm(compute_cap: str) -> str | None:
    """'7.0' -> 'sm_70', '8.6' -> 'sm_86'. Returns None if unparseable."""
    compute_cap = compute_cap.strip()
    m = re.fullmatch(r"(\d+)\.(\d+)", compute_cap)
    if not m:
        return None
    return f"sm_{m.group(1)}{m.group(2)}"


def _nvidia_name_to_sm(name: str) -> str | None:
    low = name.lower()
    for sub, sm in _NVIDIA_NAME_TO_SM:
        if sub in low:
            return sm
    return None


def _amd_name_to_gfx(name: str) -> str | None:
    low = name.lower()
    for sub, gfx in _AMD_NAME_TO_GFX:
        if sub in low:
            return gfx
    return None


# ---------------------------------------------------------------------------
# Pure parsers
# ---------------------------------------------------------------------------


def parse_nvidia_smi(text: str) -> tuple[list[GPU], str | None]:
    """Parse ``nvidia-smi --query-gpu=name,driver_version,compute_cap --format=csv``.

    Returns (gpus, driver_version). Tolerates the ``[Not Supported]``
    compute_cap that old drivers emit by falling back to the name map.
    """
    gpus: list[GPU] = []
    driver: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.lower().startswith("name"):
            continue  # header or blank
        parts = [p.strip() for p in line.split(",")]
        if not parts or not parts[0]:
            continue
        name = parts[0]
        if len(parts) >= 2 and parts[1]:
            driver = parts[1]
        arch: str | None = None
        if len(parts) >= 3 and parts[2]:
            arch = cc_to_sm(parts[2])
        if arch is None:
            arch = _nvidia_name_to_sm(name)
        gpus.append(GPU(vendor="nvidia", name=name, arch=arch, source="nvidia-smi"))
    return gpus, driver


def parse_rocminfo(text: str) -> list[GPU]:
    """Parse ``rocminfo`` output, pulling GPU-agent gfx names.

    rocminfo prints one ``Name: gfxNNN`` (and often ``Marketing Name:``) per
    agent. CPU agents have no gfx name, so we only keep ``gfx*`` entries.
    """
    gpus: list[GPU] = []
    pending_gfx: str | None = None
    pending_market: str | None = None

    def flush() -> None:
        nonlocal pending_gfx, pending_market
        if pending_gfx:
            gpus.append(
                GPU(
                    vendor="amd",
                    name=pending_market or pending_gfx,
                    arch=pending_gfx,
                    source="rocminfo",
                )
            )
        pending_gfx = None
        pending_market = None

    for raw in text.splitlines():
        line = raw.strip()
        m = re.match(r"Name:\s*(gfx[0-9a-fA-F]+)", line)
        if m:
            flush()  # new agent block begins
            pending_gfx = m.group(1).lower()
            continue
        mm = re.match(r"Marketing Name:\s*(.+)", line)
        if mm and pending_gfx:
            pending_market = mm.group(1).strip()
    flush()
    return gpus


def parse_lspci(text: str) -> list[GPU]:
    """Parse ``lspci`` output for VGA / 3D / display controllers.

    Fallback path when neither nvidia-smi nor rocminfo is available (e.g. driver
    not installed). Resolves arch by marketing-name substring only.
    """
    gpus: list[GPU] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not re.search(r"(VGA compatible controller|3D controller|Display controller)", line):
            continue
        # strip the "bus addr CLASS:" prefix to get the device description
        desc = re.sub(r"^\S+\s+(VGA compatible controller|3D controller|Display controller):\s*",
                      "", line)
        low = desc.lower()
        if "nvidia" in low:
            gpus.append(
                GPU(vendor="nvidia", name=desc, arch=_nvidia_name_to_sm(desc), source="lspci")
            )
        elif "amd" in low or "advanced micro devices" in low or "ati" in low:
            gpus.append(
                GPU(vendor="amd", name=desc, arch=_amd_name_to_gfx(desc), source="lspci")
            )
    return gpus


def parse_nvcc(text: str) -> str | None:
    """Extract the CUDA toolkit version from ``nvcc --version``."""
    m = re.search(r"release\s+(\d+\.\d+)", text)
    if m:
        return m.group(1)
    m = re.search(r"V(\d+\.\d+\.\d+)", text)
    return m.group(1) if m else None


def parse_version_string(text: str) -> str | None:
    """Pull the first ``X.Y`` / ``X.Y.Z`` token from arbitrary --version output."""
    m = re.search(r"(\d+\.\d+(?:\.\d+)?)", text)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Thin runners (everything wrapped; never raises)
# ---------------------------------------------------------------------------

# A "runner" takes an argv list and returns stdout, or None if the tool is
# absent / failed. Injectable so tests can supply fixtures.
Runner = Callable[[list[str]], str | None]


def real_runner(argv: list[str]) -> str | None:
    """Run a command, returning combined stdout or None on any failure."""
    exe = argv[0]
    if shutil.which(exe) is None:
        return None
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    out = proc.stdout or ""
    # nvcc prints version to stdout; some tools use stderr -- include both.
    if proc.stderr:
        out = out + "\n" + proc.stderr
    return out


def _import_version(module: str) -> str | None:
    """Return ``module.__version__`` if importable, else None. Never raises."""
    try:
        import importlib

        mod = importlib.import_module(module)
    except Exception:  # noqa: BLE001 - importing a framework can raise anything (CUDA init, OSError, etc.)
        return None
    ver = getattr(mod, "__version__", None)
    if isinstance(ver, str):
        # torch reports e.g. "2.14.0+cu126" -- keep the leading version token
        return parse_version_string(ver)
    return None


def detect_environment(runner: Runner = real_runner) -> Environment:
    """Detect the full environment, wrapping every probe.

    ``runner`` is injectable for tests. Framework versions come from import
    first (torch, vllm), then a ``--version`` subprocess (ollama, llama.cpp).
    """
    env = Environment()

    # --- NVIDIA GPUs + driver ------------------------------------------------
    smi = runner(
        ["nvidia-smi", "--query-gpu=name,driver_version,compute_cap", "--format=csv,noheader"]
    )
    env.tools_present["nvidia-smi"] = smi is not None
    nv_gpus: list[GPU] = []
    if smi:
        nv_gpus, env.nvidia_driver = parse_nvidia_smi(smi)
        env.gpus.extend(nv_gpus)

    # --- AMD GPUs ------------------------------------------------------------
    rocm_info = runner(["rocminfo"])
    env.tools_present["rocminfo"] = rocm_info is not None
    amd_gpus: list[GPU] = []
    if rocm_info:
        amd_gpus = parse_rocminfo(rocm_info)
        env.gpus.extend(amd_gpus)

    # --- lspci fallback ------------------------------------------------------
    # Only consult lspci if a driver tool gave us nothing, so we don't
    # double-count the same card from two sources.
    if not nv_gpus and not amd_gpus:
        lspci = runner(["lspci"])
        env.tools_present["lspci"] = lspci is not None
        if lspci:
            env.gpus.extend(parse_lspci(lspci))
    else:
        env.tools_present["lspci"] = shutil.which("lspci") is not None

    # --- CUDA toolkit --------------------------------------------------------
    nvcc = runner(["nvcc", "--version"])
    env.tools_present["nvcc"] = nvcc is not None
    if nvcc:
        env.cuda_toolkit = parse_nvcc(nvcc)

    # --- ROCm version --------------------------------------------------------
    rocm_ver = runner(["hipconfig", "--version"])
    if rocm_ver:
        env.rocm = parse_version_string(rocm_ver)

    # --- frameworks ----------------------------------------------------------
    env.frameworks["torch"] = _import_version("torch")
    env.frameworks["vllm"] = _import_version("vllm")
    env.frameworks["flash_attn"] = _import_version("flash_attn")

    ollama_v = runner(["ollama", "--version"])
    env.tools_present["ollama"] = ollama_v is not None
    if ollama_v:
        env.frameworks["ollama"] = parse_version_string(ollama_v)

    llama_v = runner(["llama-cli", "--version"])
    env.tools_present["llama.cpp"] = llama_v is not None
    if llama_v:
        env.frameworks["llama_cpp"] = parse_version_string(llama_v)

    return env
