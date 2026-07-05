# ============================================================================
# Project X
# Camera configuration paths
# ============================================================================

import os
from pathlib import Path

from app.paths import bundled_config_dir

CAMERAS_CONFIG_DIR = Path(
    os.environ.get(
        "PROJECTX_CAMERAS_CONFIG_DIR",
        str(bundled_config_dir() / "cameras"),
    )
)

CAMERAS_INDEX_FILE = CAMERAS_CONFIG_DIR / "index.json"
