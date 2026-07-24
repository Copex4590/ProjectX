# ============================================================================
# Project X
# Version & Build Metadata
# ============================================================================

from __future__ import annotations

import os
from pathlib import Path


PROJECT_NAME = "Project X"
PROJECT_VERSION = "0.3.1-beta"
__version__ = PROJECT_VERSION
GITHUB_URL = os.environ.get(
    "PROJECTX_GITHUB_URL",
    "https://github.com/Copex4590/ProjectX",
)
LICENSE_NAME = "MIT License"


def _read_packaged_build_stamp() -> str | None:
    """Read stamp written by release build scripts into bundled resources."""
    candidates: list[Path] = []
    try:
        # Avoid importing app.paths here (version is imported very early).
        import sys

        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            candidates.append(Path(sys._MEIPASS) / "resources" / "build_stamp")
        here = Path(__file__).resolve().parent
        candidates.append(here / "resources" / "build_stamp")
    except Exception:
        return None

    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            return text
    return None


def _resolve_project_build() -> str:
    env = os.environ.get("PROJECTX_BUILD", "").strip()
    if env:
        return env
    stamped = _read_packaged_build_stamp()
    if stamped:
        return stamped
    return "dev"


PROJECT_BUILD = _resolve_project_build()
