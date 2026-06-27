# ============================================================================
# Project X
# AISStream Engine
# ============================================================================

from pathlib import Path

from engines.base_engine import BaseEngine
from engines.ais.ais_client import AISClient
from events import eventbus


class AISStreamEngine(BaseEngine):

    def __init__(self):

        super().__init__("AISStream")

        self.client = AISClient()

    def on_start(self):

        eventbus.publish(
            "ais.status",
            status="connecting"
        )

        api_file = Path.home() / "duna-monitor" / "api_key.txt"

        if not api_file.exists():

            print("❌ api_key.txt nem található.")
            return

        api_key = api_file.read_text().strip()

        print("📡 Kapcsolódás AISStream...")

        self.client.connect(api_key)

        print("✅ AISStream kapcsolódva")

        eventbus.publish(
            "ais.status",
            status="connected"
        )

    def on_stop(self):

        self.client.disconnect()

        eventbus.publish(
            "ais.status",
            status="offline"
        )
