# ============================================================================
# Project X
# AIS Receiver
# ============================================================================


class AISReceiver:

    def __init__(self, client):

        self.client = client

    def receive(self):

        return self.client.receive()
