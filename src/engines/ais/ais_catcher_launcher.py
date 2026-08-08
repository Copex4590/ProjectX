# ============================================================================
# Project X
# AIS-catcher launcher (RTL subsystem)
# ============================================================================

from __future__ import annotations

import logging
import socket
import subprocess
import time
from pathlib import Path

from config.aiscatcher import (
    AIS_CATCHER_ARGS,
    AIS_CATCHER_EXECUTABLE,
    AIS_CATCHER_HOST,
    AIS_CATCHER_POLL_INTERVAL,
    AIS_CATCHER_PORT,
    AIS_CATCHER_STARTUP_TIMEOUT,
)

logger = logging.getLogger(__name__)


def _process_gui_events():

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        return

    app = QApplication.instance()
    if app is not None:
        app.processEvents()


def is_port_open(host=AIS_CATCHER_HOST, port=AIS_CATCHER_PORT, timeout=1.0):

    try:
        with socket.create_connection((str(host), int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_port(
    host=AIS_CATCHER_HOST,
    port=AIS_CATCHER_PORT,
    timeout=AIS_CATCHER_STARTUP_TIMEOUT,
    poll_interval=AIS_CATCHER_POLL_INTERVAL,
):

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if is_port_open(host, port, timeout=poll_interval):
            return True

        _process_gui_events()

        time.sleep(poll_interval)

    return False


def build_ais_catcher_args(*, port: int) -> list[str]:
    """Return AIS-Catcher argv with ``-S <port>`` matching the TCP listen port."""

    resolved = int(port)
    args: list[str] = []
    skip_next = False

    for arg in AIS_CATCHER_ARGS:
        if skip_next:
            skip_next = False
            continue
        if arg == "-S":
            skip_next = True
            continue
        if isinstance(arg, str) and arg.startswith("-S") and arg[2:].isdigit():
            continue
        args.append(arg)

    args.extend(["-S", str(resolved)])
    return args


def resolve_ais_catcher_endpoint(
    host: str | None = None,
    port: int | None = None,
) -> tuple[str, int]:
    """Resolve host/port with config defaults (same source HybridEngine uses)."""

    resolved_host = str(host if host is not None else AIS_CATCHER_HOST).strip()
    if not resolved_host:
        resolved_host = AIS_CATCHER_HOST
    try:
        resolved_port = int(port if port is not None else AIS_CATCHER_PORT)
    except (TypeError, ValueError):
        resolved_port = int(AIS_CATCHER_PORT)
    return resolved_host, resolved_port


def ensure_ais_catcher_ready(
    host: str | None = None,
    port: int | None = None,
    *,
    executable: Path | None = None,
) -> bool:
    """Start AIS-Catcher if needed on the given host/port (idempotent).

    If the TCP port is already open, returns True without launching again.
    ``host``/``port`` default to ``AIS_CATCHER_HOST`` / ``AIS_CATCHER_PORT``.
    """

    resolved_host, resolved_port = resolve_ais_catcher_endpoint(host, port)

    if is_port_open(resolved_host, resolved_port):
        logger.debug(
            "AIS-Catcher already running on %s:%s",
            resolved_host,
            resolved_port,
        )
        return True

    exe = Path(executable) if executable is not None else Path(AIS_CATCHER_EXECUTABLE)

    if not exe.is_file():
        logger.warning("AIS-Catcher executable not found: %s", exe)
        return False

    command = [str(exe), *build_ais_catcher_args(port=resolved_port)]

    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as error:
        logger.warning("AIS-Catcher failed to start: %s", error)
        return False

    logger.info("Starting AIS-Catcher: %s", " ".join(command))

    if wait_for_port(resolved_host, resolved_port):
        logger.info("AIS-Catcher ready on %s:%s", resolved_host, resolved_port)
        return True

    logger.warning(
        "AIS-Catcher did not respond within %ss on %s:%s",
        AIS_CATCHER_STARTUP_TIMEOUT,
        resolved_host,
        resolved_port,
    )
    return False
