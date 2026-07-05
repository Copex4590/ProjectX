# ============================================================================
# Project X
# AIS-catcher launcher (RTL subsystem)
# ============================================================================

import logging
import socket
import subprocess
import time

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
        with socket.create_connection((host, port), timeout=timeout):
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


def ensure_ais_catcher_ready():

    host = AIS_CATCHER_HOST
    port = AIS_CATCHER_PORT

    if is_port_open(host, port):
        logger.debug("AIS-Catcher already running on %s:%s", host, port)
        return True

    executable = AIS_CATCHER_EXECUTABLE

    if not executable.is_file():
        logger.warning("AIS-Catcher executable not found: %s", executable)
        return False

    command = [str(executable), *AIS_CATCHER_ARGS]

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

    if wait_for_port(host, port):
        logger.info("AIS-Catcher ready on %s:%s", host, port)
        return True

    logger.warning(
        "AIS-Catcher did not respond within %ss on %s:%s",
        AIS_CATCHER_STARTUP_TIMEOUT,
        host,
        port,
    )
    return False
