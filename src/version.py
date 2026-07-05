# ============================================================================
# Project X
# Version & Build Metadata
# ============================================================================

from __future__ import annotations

import os

PROJECT_NAME = "Project X"
PROJECT_VERSION = "0.3.0-alpha"
PROJECT_BUILD = os.environ.get("PROJECTX_BUILD", "dev")
GITHUB_URL = os.environ.get("PROJECTX_GITHUB_URL", "")
LICENSE_NAME = "MIT License"
