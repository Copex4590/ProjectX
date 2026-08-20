"""Chromium/WebEngine process flags. Import before QApplication."""

from __future__ import annotations

import os
import socket


def _free_port() -> int:
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def configure_remote_debugging() -> int:
    """Enable Chromium DevTools so the engine can read network responses.

    Must run before QApplication / first QWebEngine object.
    """
    existing = os.environ.get("QTWEBENGINE_REMOTE_DEBUGGING", "").strip()
    if existing:
        port = int(existing.split(":")[-1])
    else:
        port = _free_port()
        os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = str(port)
    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    if "--remote-allow-origins" not in flags:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
            f"{flags} --remote-allow-origins=*".strip()
        )
    return port


def debugging_port() -> int | None:
    raw = os.environ.get("QTWEBENGINE_REMOTE_DEBUGGING", "").strip()
    if not raw:
        return None
    try:
        return int(raw.split(":")[-1])
    except ValueError:
        return None
