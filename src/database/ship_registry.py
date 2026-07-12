# ============================================================================
# Project X
# Ship Registry
# ============================================================================

from threading import Lock

from database.vessel_sync import vessel_sync
from engines.timeline.arrival_departure_engine import arrival_departure_engine
from models.ship import Ship
from timeline.timeline_recorder import timeline_recorder


class ShipRegistry:
    """Runtime in-memory ship store. AIS updates must enter via HybridAisEngine."""

    def __init__(self):

        self._ships = {}
        self._lock = Lock()

    def add(self, ship: Ship):

        with self._lock:

            current = self._ships.get(ship.mmsi)

            if current is None:

                ship.add_history()
                self._ships[ship.mmsi] = ship

            else:

                current.name = ship.name
                current.callsign = ship.callsign
                current.ship_type = ship.ship_type

                current.lat = ship.lat
                current.lon = ship.lon

                current.speed = ship.speed
                current.course = ship.course
                current.heading = ship.heading

                current.destination = ship.destination
                current.eta = ship.eta

                current.source = ship.source
                current.last_seen = ship.last_seen

                current.ais_visible = current.ais_visible or ship.ais_visible
                current.rtl_visible = current.rtl_visible or ship.rtl_visible
                current.camera_visible = ship.camera_visible

                current.distance_km = ship.distance_km
                current.direction = ship.direction
                current.text_heading = ship.text_heading

                current.add_history()

            merged = self._ships.get(ship.mmsi)

        vessel_sync.enqueue(merged)
        timeline_recorder.enqueue(merged)
        arrival_departure_engine.notify(merged)

    def get(self, mmsi: int):

        with self._lock:
            return self._ships.get(mmsi)

    def remove(self, mmsi: int):

        with self._lock:
            self._ships.pop(mmsi, None)

    def all(self):

        with self._lock:
            return list(self._ships.values())

    def count(self):

        with self._lock:
            return len(self._ships)

    def clear(self):

        with self._lock:
            self._ships.clear()

    def names(self):

        with self._lock:
            return sorted(
                ship.name
                for ship in self._ships.values()
                if ship.name
            )

    def exists(self, mmsi: int):

        with self._lock:
            return mmsi in self._ships


registry = ShipRegistry()
