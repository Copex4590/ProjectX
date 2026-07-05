# ============================================================================
# Project X
# AIS-Catcher Status
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config.aiscatcher import (
    AIS_CATCHER_EXECUTABLE,
    AIS_CATCHER_HOST,
    AIS_CATCHER_PORT,
)
from engines.ais.ais_catcher_launcher import is_port_open


@dataclass(frozen=True)
class AISCatcherStatus:

    installed: bool
    running: bool
    host: str
    port: int
    executable: str


def get_aiscatcher_status(
    *,
    host: str | None = None,
    port: int | None = None,
) -> AISCatcherStatus:

    resolved_host = host or AIS_CATCHER_HOST
    resolved_port = int(port or AIS_CATCHER_PORT)
    executable = Path(AIS_CATCHER_EXECUTABLE)

    return AISCatcherStatus(
        installed=executable.is_file(),
        running=is_port_open(resolved_host, resolved_port, timeout=1.0),
        host=resolved_host,
        port=resolved_port,
        executable=str(executable),
    )
