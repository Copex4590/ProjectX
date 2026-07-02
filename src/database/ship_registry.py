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

            old = self._ships.get(ship.mmsi)

            if old:

                old.name = ship.name
                old.callsign = ship.callsign
                old.ship_type = ship.ship_type
                old.lat = ship.lat
                old.lon = ship.lon
                old.speed = ship.speed
                old.course = ship.course
                old.heading = ship.heading
                old.destination = ship.destination
                old.eta = ship.eta
                old.source = ship.source
                old.last_seen = ship.last_seen
                old.ais_visible = ship.ais_visible
                old.rtl_visible = ship.rtl_visible
                old.camera_visible = ship.camera_visible

                old.add_history()

            else:

                ship.add_history()
                self._ships[ship.mmsi] = ship

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
