"""Validate Afterlife stack manifests: YAML parses, index references exist, scripts are executable."""

from __future__ import annotations

import sys
from typing import Any
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    files = [root / "index.yaml", *sorted(root.glob("*/stack.yaml"))]
    docs: dict[str, dict[str, Any]] = {}
    for f in files:
        try:
            data = yaml.safe_load(f.read_text())
        except yaml.YAMLError as exc:
            errors.append(f"{f}: {exc}")
            continue
        if not isinstance(data, dict) or data.get("schema") != 1:
            errors.append(f"{f}: missing schema: 1")
            continue
        docs[f.name if f.name == "index.yaml" else f.parent.name] = data
    index = docs.get("index.yaml")
    if index is None:
        return errors
    stacks = index.get("stacks", {})
    for sid, s in stacks.items():
        for key in ("manifest", "dockerfile", "install"):
            if not (root / s[key]).is_file():
                errors.append(f"index stack {sid}: missing {s[key]}")
        if sid not in docs:
            errors.append(f"index stack {sid}: manifest did not load")
        elif docs[sid].get("id") != sid:
            errors.append(f"{sid}: manifest id mismatch")
        if not (root / s["install"]).stat().st_mode & 0o111:
            errors.append(f"{sid}: install script not executable")
    for arch, a in index.get("arches", {}).items():
        for sid in [a["recommended"], *a.get("alternatives", [])]:
            if sid not in stacks:
                errors.append(f"arch {arch}: unknown stack {sid}")
    return errors


if __name__ == "__main__":
    errs = validate()
    for e in errs:
        print("ERROR", e)
    print("OK" if not errs else f"{len(errs)} error(s)")
    sys.exit(1 if errs else 0)
