# ============================================================================
# Project X
# Version & Build Metadata
# ============================================================================

from __future__ import annotations

import os

PROJECT_NAME = "Project X"
PROJECT_VERSION = "0.3.1-alpha.1"
__version__ = PROJECT_VERSION
PROJECT_BUILD = os.environ.get("PROJECTX_BUILD", "dev")
GITHUB_URL = os.environ.get(
    "PROJECTX_GITHUB_URL",
    "https://github.com/Copex4590/ProjectX",
)
LICENSE_NAME = "MIT License"
