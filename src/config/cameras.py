# ============================================================================
# Project X
# Camera configuration paths
# ============================================================================

import os
from pathlib import Path

_CONFIG_DIR = Path(__file__).resolve().parent / "cameras"

CAMERAS_CONFIG_DIR = Path(
    os.environ.get(
        "PROJECTX_CAMERAS_CONFIG_DIR",
        str(_CONFIG_DIR),
    )
)

CAMERAS_INDEX_FILE = CAMERAS_CONFIG_DIR / "index.json"
