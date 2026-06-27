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
