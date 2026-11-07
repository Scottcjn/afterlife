"""Synthetic tool-output fixtures and an injectable fake runner for tests."""

from __future__ import annotations

from afterlife.detect import Runner

# --- nvidia-smi --query-gpu=name,driver_version,compute_cap --format=csv,noheader

# V100 on a driver branch PAST 580 (breaks everything).
NVIDIA_SMI_V100_NEW_DRIVER = "Tesla V100-PCIE-16GB, 590.00, 7.0\n"

# V100 on the last-good R580 branch (works now, must not upgrade).
NVIDIA_SMI_V100_R580 = "Tesla V100-SXM2-32GB, 580.173.02, 7.0\n"

# GTX 1060 (Pascal, sm_61) -- the P40/Pascal proxy.
NVIDIA_SMI_GTX1060 = "NVIDIA GeForce GTX 1060 6GB, 590.00, 6.1\n"

# RTX 3060 (Ampere, sm_86) -- the supported control.
NVIDIA_SMI_RTX3060 = "NVIDIA GeForce RTX 3060, 590.00, 8.6\n"

# Old driver that reports compute_cap as "[Not Supported]" -> name-map fallback.
NVIDIA_SMI_V100_NOCC = "Tesla V100-PCIE-16GB, 470.00, [Not Supported]\n"

# --- rocminfo (trimmed to the fields the parser reads) ---------------------

ROCMINFO_MI50 = """\
*******
Agent 1
*******
  Name:                    AMD Ryzen 9 5950X
  Device Type:             CPU
*******
Agent 2
*******
  Name:                    gfx906
  Marketing Name:          AMD Instinct MI50/MI60
  Device Type:             GPU
  Compute Unit:            60
"""

# --- lspci -----------------------------------------------------------------

# An unrecognised / brand-new NVIDIA card: name does not resolve to an arch.
LSPCI_UNKNOWN_NVIDIA = (
    "00:02.0 Host bridge: Intel Corporation Device 9b00\n"
    "01:00.0 VGA compatible controller: NVIDIA Corporation Device 9999 (rev a1)\n"
)

# --- nvcc --version --------------------------------------------------------

NVCC_13 = (
    "nvcc: NVIDIA (R) Cuda compiler driver\n"
    "Cuda compilation tools, release 13.0, V13.0.48\n"
)
NVCC_129 = (
    "nvcc: NVIDIA (R) Cuda compiler driver\n"
    "Cuda compilation tools, release 12.9, V12.9.41\n"
)

# --- ollama / llama-cli --version ------------------------------------------

OLLAMA_STOCK = "ollama version is 0.40.15\n"
OLLAMA_OLD = "ollama version is 0.12.3\n"


def make_runner(outputs: dict[str, str | None]) -> Runner:
    """Build a fake Runner keyed by the executable name (argv[0]).

    A key present with a string value returns that text; a key present with
    ``None`` (or an absent key) simulates the tool being missing.
    """

    def runner(argv: list[str]) -> str | None:
        return outputs.get(argv[0])

    return runner
