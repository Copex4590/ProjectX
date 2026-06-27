# ============================================================================
# Project X
# Ship Registry
# ============================================================================

from models.ship import Ship


class ShipRegistry:

    def __init__(self):

        self._ships = {}

    def add(self, ship: Ship):

        self._ships[ship.mmsi] = ship

    def get(self, mmsi: int):

        return self._ships.get(mmsi)

    def remove(self, mmsi: int):

        self._ships.pop(mmsi, None)

    def all(self):

        return list(self._ships.values())

    def count(self):

        return len(self._ships)

    def clear(self):

        self._ships.clear()


registry = ShipRegistry()
