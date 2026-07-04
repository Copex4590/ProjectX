# ============================================================================
# Project X
# AIS-catcher configuration
# ============================================================================

import os
from pathlib import Path

_DEFAULT_AIS_CATCHER_EXECUTABLE = (
    "/home/zoli/AIS-catcher/build/AIS-catcher"
)

_DEFAULT_AIS_CATCHER_ARGS = "-d:0 -o 5 -S 10110"

AIS_CATCHER_EXECUTABLE = Path(
    os.environ.get(
        "PROJECTX_AIS_CATCHER_EXECUTABLE",
        _DEFAULT_AIS_CATCHER_EXECUTABLE,
    )
)

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
