# ============================================================================
# Project X
# AISStream Engine
# ============================================================================

from threading import Thread
import traceback

from database import registry
from engines.ais.ais_client import AISClient
from engines.ais.ais_parser import AISParser
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

        print("[AIS] Engine starting...")

        try:
            preferences = preferences_manager.get()
            print("[AIS] Preferences loaded.")

            api_key = preferences.aisstream_api_key.strip()
            print(f"[AIS] API key length: {len(api_key)}")

            if not api_key:
                print("[AIS] No API key.")

                eventbus.publish(
                    "ais.status",
                    status="offline"
                )
                return

            print("[AIS] Connecting...")

            self.client.connect(api_key)

            print("[AIS] Connected.")

            eventbus.publish(
                "ais.status",
                status="connected"
            )

            self.thread = Thread(
                target=self.worker,
                daemon=True
            )

            self.thread.start()

            print("[AIS] Worker thread started.")

        except Exception as error:

            print("[AIS] START FAILED")
            print(error)
            traceback.print_exc()

            eventbus.publish(
                "ais.status",
                status="offline"
            )

    def worker(self):

        print("[AIS] Worker running.")

        while self.running:

            try:

                message = self.client.receive()

                ship = self.parser.parse(message)

                if ship is None:
                    continue

                registry.add(ship)

                eventbus.publish(
                    "ship.updated",
                    ship=ship
                )

            except Exception as error:

                print("[AIS] WORKER FAILED")
                print(error)
                traceback.print_exc()
                break

    def on_stop(self):

        print("[AIS] Engine stopping.")

        self.client.disconnect()

        eventbus.publish(
            "ais.status",
            status="offline"
        )
