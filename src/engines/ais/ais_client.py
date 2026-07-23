# ============================================================================
# Project X
# AIS Client
# ============================================================================

from __future__ import annotations

import json
import logging

import websocket

from .ais_protocol import AISProtocol

logger = logging.getLogger(__name__)

DEFAULT_CONNECT_TIMEOUT_S = 10.0
DEFAULT_RECV_TIMEOUT_S = 1.0


class AISClient:

    def __init__(self):

        self.ws = None

    def connect(self, api_key: str):

        self.disconnect()
        self.ws = websocket.create_connection(
            f"wss://stream.aisstream.io/v0/stream?apiKey={api_key}",
            timeout=DEFAULT_CONNECT_TIMEOUT_S,
        )
        self.ws.settimeout(DEFAULT_RECV_TIMEOUT_S)

        self.ws.send(
            json.dumps(
                AISProtocol.subscribe_message(api_key)
            )
        )

    def receive(self):

        if self.ws is None:
            return None

        message = self.ws.recv()

        if isinstance(message, bytes):
            message = message.decode("utf-8")

        return json.loads(message)

    def disconnect(self):

        if self.ws:
            try:
                self.ws.close()
            except Exception:
                logger.debug("AISStream websocket close failed", exc_info=True)
            self.ws = None
