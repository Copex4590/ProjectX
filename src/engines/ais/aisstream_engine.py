# ============================================================================
# Project X
# AISStream Engine
# ============================================================================

from threading import Thread

from core.logger import logger
from engines.ais.ais_client import AISClient
from engines.ais.ais_parser import AISParser
from engines.ais.hybrid_ais_engine import hybrid_ais_engine
from engines.base_engine import BaseEngine
from events import eventbus
from preferences import preferences_manager


class AISStreamEngine(BaseEngine):

    def __init__(self):

        super().__init__("AISStream")

        self.client = AISClient()
        self.parser = AISParser()

        self.thread = None

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

            logger.info("Connecting to AISStream")

            self.client.connect(api_key)

            logger.info("AISStream connected")

            eventbus.publish(
                "ais.status",
                status="connected"
            )

            self.thread = Thread(
                target=self.worker,
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

    def worker(self):

        logger.info("AIS worker running")

        while self.running:

            try:

                message = self.client.receive()

                ship = self.parser.parse(message)

                if ship is None:
                    continue

                hybrid_ais_engine.publish_ship(ship)

            except Exception:

                logger.exception("AIS worker crashed")
                break

    def on_stop(self):

        logger.info("AIS Engine stopping")

        self.client.disconnect()

        eventbus.publish(
            "ais.status",
            status="offline"
        )
