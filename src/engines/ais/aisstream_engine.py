# ============================================================================
# Project X
# AISStream Engine
# ============================================================================

from __future__ import annotations

import logging
import time
from threading import Thread

from core.logger import logger
from engines.ais.ais_client import AISClient
from engines.ais.ais_parser import AISParser
from engines.ais.hybrid_ais_engine import hybrid_ais_engine
from engines.base_engine import BaseEngine
from events import eventbus
from preferences import preferences_manager

_log = logging.getLogger(__name__)

AIS_RECONNECT_MIN_S = 1.0
AIS_RECONNECT_MAX_S = 60.0


class AISStreamEngine(BaseEngine):

    def __init__(self):

        super().__init__("AISStream")

        self.client = AISClient()
        self.parser = AISParser()

        self.thread = None
        self._reconnect_backoff_s = AIS_RECONNECT_MIN_S

    def on_start(self):

        logger.info("AIS Engine starting")

        try:

            preferences = preferences_manager.get()

            logger.info("Preferences loaded")

            api_key = preferences.aisstream_api_key.strip()

            logger.info(
                "AIS API key loaded (length=%d)",
                len(api_key)
            )

            if not api_key:

                logger.warning("No AIS API key configured")

                eventbus.publish(
                    "ais.status",
                    status="offline"
                )

                return

            self.thread = Thread(
                target=self.worker,
                args=(api_key,),
                daemon=True
            )

            self.thread.start()

            logger.info("AIS worker started")

        except Exception:

            logger.exception("AIS engine failed during startup")

            eventbus.publish(
                "ais.status",
                status="offline"
            )

    def worker(self, api_key: str):

        logger.info("AIS worker running")

        while self.running:

            try:
                logger.info("Connecting to AISStream")
                self.client.connect(api_key)
                self._reconnect_backoff_s = AIS_RECONNECT_MIN_S
                eventbus.publish("ais.status", status="connected")
                logger.info("AISStream connected")

                while self.running:
                    try:
                        message = self.client.receive()
                    except Exception:
                        # timeout or transient recv error — retry read
                        continue

                    if message is None:
                        continue

                    ship = self.parser.parse(message)

                    if ship is None:
                        continue

                    hybrid_ais_engine.publish_ship(ship)

            except Exception:
                logger.exception("AIS worker connection error")
                eventbus.publish("ais.status", status="offline")
                self.client.disconnect()
                if not self.running:
                    break
                delay = self._reconnect_backoff_s
                time.sleep(delay)
                self._reconnect_backoff_s = min(
                    AIS_RECONNECT_MAX_S,
                    max(AIS_RECONNECT_MIN_S, delay * 2.0),
                )

        self.client.disconnect()

    def on_stop(self):

        logger.info("AIS Engine stopping")

        self.client.disconnect()

        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=5.0)
            if self.thread.is_alive():
                logger.warning("AISStreamEngine worker did not stop within 5s")

        eventbus.publish(
            "ais.status",
            status="offline"
        )
