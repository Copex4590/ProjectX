# ============================================================================
# Project X
# RTL Reception Monitor
# ============================================================================

from __future__ import annotations

import socket
import time
from dataclasses import dataclass

from config.aiscatcher import AIS_CATCHER_HOST, AIS_CATCHER_PORT
from database import registry
from engines.ais.ais_rtl_client import AISRtlClient


@dataclass(frozen=True)
class ReceptionTestResult:

    success: bool
    message: str = ""
    message_count: int = 0
    ships_detected: int = 0
    signal_quality: str = "none"
    last_message: str = ""
    duration_seconds: float = 0.0


def _signal_quality_from_rate(rate: float) -> str:

    if rate <= 0:
        return "none"

    if rate < 1.0:
        return "weak"

    if rate < 5.0:
        return "fair"

    return "good"


def count_rtl_ships() -> int:

    count = 0

    for ship in registry.all():
        if getattr(ship, "rtl_visible", False):
            count += 1
            continue

        if str(getattr(ship, "source", "")).upper() == "RTL":
            count += 1

    return count


def run_reception_test(
    *,
    host: str | None = None,
    port: int | None = None,
    duration_seconds: float = 10.0,
) -> ReceptionTestResult:

    resolved_host = host or AIS_CATCHER_HOST
    resolved_port = int(port or AIS_CATCHER_PORT)
    client = AISRtlClient()
    message_count = 0
    last_message = ""
    start = time.monotonic()
    deadline = start + max(duration_seconds, 1.0)

    try:
        client.connect(resolved_host, resolved_port)
    except OSError:
        return ReceptionTestResult(
            success=False,
            message="TCP connection failed.",
            duration_seconds=0.0,
        )

    client._socket.settimeout(0.5)

    try:
        while time.monotonic() < deadline:
            line = client.receive()

            if not line:
                continue

            if "AIVDM" in line or "AIVDO" in line:
                message_count += 1
                last_message = line[:120]
    except (OSError, socket.timeout):
        pass
    finally:
        client.disconnect()

    elapsed = max(time.monotonic() - start, 0.1)
    rate = message_count / elapsed
    ships_detected = count_rtl_ships()

    return ReceptionTestResult(
        success=message_count > 0 or ships_detected > 0,
        message_count=message_count,
        ships_detected=ships_detected,
        signal_quality=_signal_quality_from_rate(rate),
        last_message=last_message,
        duration_seconds=elapsed,
    )
