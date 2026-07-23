# ============================================================================
# Project X
# AIS-catcher configuration
# ============================================================================

from __future__ import annotations

import os
import shutil
from pathlib import Path


_DEFAULT_AIS_CATCHER_ARGS = "-d:0 -o 5 -S 10110"


def _find_default_executable() -> Path:
    """
    Megpróbálja automatikusan megtalálni az AIS-catcher binárist.
    """

    env = os.environ.get("PROJECTX_AIS_CATCHER_EXECUTABLE")
    if env:
        return Path(env)

    exe = shutil.which("AIS-catcher")
    if exe:
        return Path(exe)

    candidates = [
        Path.home() / "AIS-catcher" / "build" / "AIS-catcher",
        Path("/usr/local/bin/AIS-catcher"),
        Path("/usr/bin/AIS-catcher"),
    ]

    if os.name == "nt":
        program_files = Path(
            os.environ.get("ProgramFiles")
            or os.environ.get("PROGRAMFILES")
            or Path.home()
        )
        candidates = [
            Path.home() / "AIS-catcher" / "AIS-catcher.exe",
            program_files / "AIS-catcher" / "AIS-catcher.exe",
        ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return Path("AIS-catcher")


AIS_CATCHER_EXECUTABLE = _find_default_executable()

AIS_CATCHER_ARGS = os.environ.get(
    "PROJECTX_AIS_CATCHER_ARGS",
    _DEFAULT_AIS_CATCHER_ARGS,
).split()

AIS_CATCHER_HOST = os.environ.get(
    "PROJECTX_AIS_CATCHER_HOST",
    "localhost",
)

AIS_CATCHER_PORT = int(
    os.environ.get(
        "PROJECTX_AIS_CATCHER_PORT",
        "10110",
    )
)

AIS_CATCHER_STARTUP_TIMEOUT = float(
    os.environ.get(
        "PROJECTX_AIS_CATCHER_STARTUP_TIMEOUT",
        "30",
    )
)

AIS_CATCHER_POLL_INTERVAL = float(
    os.environ.get(
        "PROJECTX_AIS_CATCHER_POLL_INTERVAL",
        "0.5",
    )
)
