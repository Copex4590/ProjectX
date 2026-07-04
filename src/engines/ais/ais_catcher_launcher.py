# ============================================================================
# Project X
# AIS-catcher launcher (RTL subsystem)
# ============================================================================

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
        print(f"✅ AIS-catcher már fut ({host}:{port})")
        return True

    executable = AIS_CATCHER_EXECUTABLE

    if not executable.is_file():
        print(f"❌ AIS-catcher nem található: {executable}")
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
        print(f"❌ AIS-catcher indítás sikertelen: {error}")
        return False

    print(f"📡 AIS-catcher indítása: {' '.join(command)}")

    if wait_for_port(host, port):
        print(f"✅ AIS-catcher kész ({host}:{port})")
        return True

    print(
        f"❌ AIS-catcher nem válaszol "
        f"{AIS_CATCHER_STARTUP_TIMEOUT:g}s alatt ({host}:{port})"
    )
    return False
