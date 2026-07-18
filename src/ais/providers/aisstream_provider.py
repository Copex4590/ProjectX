# ============================================================================
# Project X
# AISStream Provider
# ============================================================================

from __future__ import annotations

import json
import socket

import websocket

from ais.providers.provider import AISProvider, AISProviderType, AISTestResult
from engines.ais.ais_client import AISClient
from engines.ais.ais_protocol import AISProtocol

AISSTREAM_REGISTER_URL = "https://aisstream.io/authenticate"

# Minimal bbox used only for connection tests when no observation point exists yet.
_TEST_BOUNDING_BOXES = [[[0.0, 0.0], [1.0, 1.0]]]


class AISStreamProvider(AISProvider):

    provider_type = AISProviderType.AISSTREAM

    @property
    def display_name(self) -> str:

        return "AISStream"

    def test(self, *, api_key: str = "", **_kwargs) -> AISTestResult:

        key = str(api_key or "").strip()

        if not key:
            return AISTestResult(
                success=False,
                message="Please paste your API key.",
            )

        if not self._has_internet():
            return AISTestResult(
                success=False,
                message="No Internet connection.",
            )

        client = AISClient()

        try:
            client.ws = websocket.create_connection(
                f"wss://stream.aisstream.io/v0/stream?apiKey={key}",
                timeout=10,
            )

            client.ws.send(
                json.dumps(
                    AISProtocol.subscribe_message(
                        key,
                        bounding_boxes=_TEST_BOUNDING_BOXES,
                    )
                )
            )

            client.ws.settimeout(8)

            response = client.receive()

            if isinstance(response, dict):
                return AISTestResult(
                    success=True,
                    message="Connection successful",
                )

            return AISTestResult(
                success=False,
                message="Unexpected AISStream response.",
            )

        except websocket.WebSocketBadStatusException as error:
            if getattr(error, "status_code", None) in (401, 403):
                return AISTestResult(
                    success=False,
                    message="Invalid API key.",
                )

            return AISTestResult(
                success=False,
                message="AISStream unavailable.",
            )

        except (TimeoutError, socket.timeout, OSError):
            if not self._has_internet():
                return AISTestResult(
                    success=False,
                    message="No Internet connection.",
                )

            return AISTestResult(
                success=False,
                message="AISStream unavailable.",
            )

        except Exception as e:
            return AISTestResult(
                success=False,
                message=f"{type(e).__name__}: {e}",
            )

        finally:
            client.disconnect()

    def _has_internet(self) -> bool:

        try:
            socket.create_connection(("1.1.1.1", 53), timeout=3)
            return True
        except OSError:
            return False
