# ============================================================================
# Project X
# AISStream Engine
# ============================================================================

from pathlib import Path
from threading import Thread

from database import registry
from engines.ais.ais_client import AISClient
from engines.ais.ais_parser import AISParser
from engines.base_engine import BaseEngine
from events import eventbus


class AISStreamEngine(BaseEngine):

    def __init__(self):

        super().__init__("AISStream")

        self.client = AISClient()
        self.parser = AISParser()

        self.thread = None

    def on_start(self):

        api_file = Path.home() / "duna-monitor" / "api_key.txt"

        api_key = api_file.read_text().strip()

        self.client.connect(api_key)

        eventbus.publish(
            "ais.status",
            status="connected"
        )

        self.thread = Thread(
            target=self.worker,
            daemon=True
        )

        self.thread.start()

    def worker(self):

        while self.running:

            message = self.client.receive()

            ship = self.parser.parse(message)

            if ship is None:
                continue

            registry.add(ship)

            eventbus.publish(
                "ship.updated",
                ship=ship
            )

    def on_stop(self):

        self.client.disconnect()

        eventbus.publish(
            "ais.status",
            status="offline"
        )
