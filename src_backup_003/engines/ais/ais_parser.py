# ============================================================================
# Project X
# AIS Parser
# ============================================================================

from datetime import datetime

from models import Ship


class AISParser:

    def parse(self, message: dict):

        metadata = message.get("MetaData", {})
        report = message.get("Message", {}).get("PositionReport", {})

        if not report:
            return None

        ship = Ship(
            mmsi=metadata.get("MMSI", 0),
            name=metadata.get("ShipName", ""),
            lat=report.get("Latitude", 0.0),
            lon=report.get("Longitude", 0.0),
            speed=report.get("Sog", 0.0),
            course=report.get("Cog", 0.0),
            heading=report.get("TrueHeading", 0.0),
            source="AISStream",
            ais_visible=True,
            last_seen=datetime.now(),
        )

        return ship
