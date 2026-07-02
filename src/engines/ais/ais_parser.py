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

        lat = report.get("Latitude")
        lon = report.get("Longitude")

        if lat is None or lon is None:
            return None

        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            return None

        ship = Ship(
            mmsi=metadata.get("MMSI", 0),
            name=metadata.get("ShipName", ""),
            lat=lat,
            lon=lon,
            speed=float(report.get("Sog") or 0.0),
            course=float(report.get("Cog") or 0.0),
            heading=float(report.get("TrueHeading") or 0.0),
            source="AISStream",
            ais_visible=True,
            last_seen=datetime.now(),
        )

        return ship
