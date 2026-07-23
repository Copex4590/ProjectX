from __future__ import annotations

import logging

from engines.base_engine import BaseEngine

logger = logging.getLogger(__name__)


class CameraEngine(BaseEngine):

    def __init__(self):

        super().__init__("Camera")

    def on_start(self):

        logger.info("Camera Engine started")

    def on_stop(self):

        logger.info("Camera Engine stopped")
