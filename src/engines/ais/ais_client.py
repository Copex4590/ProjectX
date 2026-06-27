# ============================================================================
# Project X
# AIS Client
# ============================================================================

import json
import websocket

from .ais_protocol import AISProtocol


class AISClient:

    def __init__(self):

        self.ws = None

    def connect(self, api_key: str):

        self.ws = websocket.create_connection(
            f"wss://stream.aisstream.io/v0/stream?apiKey={api_key}"
        )

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
