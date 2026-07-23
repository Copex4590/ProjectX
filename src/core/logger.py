# ============================================================================
# Project X
# Legacy logger facade (SAVE-202 — delegates to centralized config)
# ============================================================================

from __future__ import annotations

import logging

from app.logging_config import configure_logging

configure_logging()

APP_NAME = "Project X"
logger = logging.getLogger(APP_NAME)
