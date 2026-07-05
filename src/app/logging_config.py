# ============================================================================
# Project X
# Logging Configuration
# ============================================================================

from __future__ import annotations

import logging
import os


def configure_logging() -> None:

    level_name = os.environ.get("PROJECTX_LOG_LEVEL", "").strip().upper()

    if level_name:
        level = getattr(logging, level_name, logging.WARNING)
    elif os.environ.get("PROJECTX_DEBUG"):
        level = logging.DEBUG
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
    )
