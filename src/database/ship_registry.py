# ============================================================================
# Project X
# Ship Registry
# ============================================================================

from threading import Lock

from models.ship import Ship


class ShipRegistry:

    def __init__(self):

        self._ships = {}
        self._lock = Lock()

    def add(self, ship: Ship):

        with self._lock:

            current = self._ships.get(ship.mmsi)

            if current is None:

                ship.add_history()
                self._ships[ship.mmsi] = ship
                return

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

            current.ais_visible = ship.ais_visible
            current.rtl_visible = ship.rtl_visible
            current.camera_visible = ship.camera_visible

            current.add_history()

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
