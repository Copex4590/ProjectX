# ============================================================================
# Project X
# AIS Client
# ============================================================================

import json
import websocket

from .ais_protocol import AISProtocol, AISSTREAM_WS_URL


class AISClient:

    def __init__(self):

        self.ws = None

    def connect(self, api_key: str):

        self.ws = websocket.create_connection(AISSTREAM_WS_URL, timeout=10)

        self.ws.send(
            json.dumps(
                AISProtocol.subscribe_message(api_key)
            )
        )

    def receive(self):

        message = self.ws.recv()

        if isinstance(message, bytes):
            message = message.decode("utf-8")

        return json.loads(message)

    def disconnect(self):

        if self.ws:
            self.ws.close()
