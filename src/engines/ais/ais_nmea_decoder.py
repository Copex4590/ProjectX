# ============================================================================
# Project X
# AIS NMEA Decoder (RTL / AIS-catcher)
# ============================================================================

from .ais_nmea_parser import AisNmeaParser


class AISNmeaDecoder:

    def __init__(self):

        self._parser = AisNmeaParser()

    def feed(self, line: str):

        self._parser.feed(line)

    def decode(self):

        return self._parser.pop_decoded()
