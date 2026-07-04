# ============================================================================
# Project X
# AIS RTL Client (AIS-catcher TCP)
# ============================================================================

import socket


class AISRtlClient:

    def __init__(self):

        self._socket = None
        self._buffer = ""

    def connect(self, host="localhost", port=10110):

        self._socket = socket.socket()
        self._socket.connect((host, port))

    def receive(self):

        if not self._socket:
            return None

        if "\n" not in self._buffer:
            data = self._socket.recv(4096).decode("utf-8", errors="ignore")
            if not data:
                return None
            self._buffer += data

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
                self._socket.close()
            except OSError:
                pass
            self._socket = None

        self._buffer = ""
