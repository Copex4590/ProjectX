# ============================================================================
# Project X
# AIS RTL Client (AIS-catcher TCP)
# ============================================================================

from __future__ import annotations

import logging
import socket

logger = logging.getLogger(__name__)

DEFAULT_RECV_TIMEOUT_S = 1.0


class AISRtlClient:

    def __init__(self, recv_timeout_s: float = DEFAULT_RECV_TIMEOUT_S):

        self._socket = None
        self._buffer = ""
        self._recv_timeout_s = float(recv_timeout_s)

    def connect(self, host="localhost", port=10110):

        self.disconnect()
        self._socket = socket.socket()
        self._socket.settimeout(self._recv_timeout_s)
        self._socket.connect((host, port))
        self._socket.settimeout(self._recv_timeout_s)

    def receive(self):

        if not self._socket:
            return None

        try:
            if "\n" not in self._buffer:
                data = self._socket.recv(4096).decode("utf-8", errors="ignore")
                if not data:
                    return None
                self._buffer += data
        except socket.timeout:
            return None
        except OSError:
            logger.debug("RTL socket receive failed", exc_info=True)
            return None

        if "\n" not in self._buffer:
            return None

        line, self._buffer = self._buffer.split("\n", 1)
        line = line.strip()

        if not line:
            return None

        return line

    def disconnect(self):

        if self._socket:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                logger.debug("RTL socket shutdown failed", exc_info=True)
            try:
                self._socket.close()
            except OSError:
                logger.debug("RTL socket close failed", exc_info=True)
            self._socket = None

        self._buffer = ""
