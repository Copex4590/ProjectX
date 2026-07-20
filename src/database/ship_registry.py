# ============================================================================
# Project X
# Ship Registry
# ============================================================================

from threading import Lock

from logbook.duna_format import get_direction, get_heading
from models.ship import Ship
from observation.geo_context import geo_context
from storage.lazy_singleton import LazySingleton


def _apply_observation_distance(ship: Ship) -> None:

    observation = geo_context.ship_observation_fields(ship.lat, ship.lon)
    distance = observation.get("distance_km")

    if distance is None:
        return

    direction = get_direction(ship.lat)
    ship.distance_km = distance
    ship.direction = direction
    ship.text_heading = get_heading(ship.course, ship.speed, direction)


class ShipRegistry:
    """Runtime in-memory ship store. AIS updates must enter via HybridAisEngine."""

    def __init__(self):

        self._ships = {}
        self._lock = Lock()

    def add(self, ship: Ship):

        _apply_observation_distance(ship)

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

        from database.vessel_sync import get_vessel_sync
        from engines.timeline.arrival_departure_engine import get_arrival_departure_engine
        from timeline.timeline_recorder import get_timeline_recorder

        get_vessel_sync().enqueue(merged)
        get_timeline_recorder().enqueue(merged)
        get_arrival_departure_engine().notify(merged)

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

    def purge_ais_only_ships(self) -> int:

        with self._lock:
            stale_mmsis = [
                mmsi
                for mmsi, ship in self._ships.items()
                if ship.ais_visible and not ship.rtl_visible
            ]

            for mmsi in stale_mmsis:
                self._ships.pop(mmsi, None)

            return len(stale_mmsis)

    def purge_rtl_only_ships(self) -> int:

        with self._lock:
            stale_mmsis = [
                mmsi
                for mmsi, ship in self._ships.items()
                if ship.rtl_visible and not ship.ais_visible
            ]

            for mmsi in stale_mmsis:
                self._ships.pop(mmsi, None)

            return len(stale_mmsis)

    def purge_outside_reference_coverage(self) -> int:

        with self._lock:
            stale_mmsis = [
                mmsi
                for mmsi, ship in self._ships.items()
                if not geo_context.is_within_coverage(ship.lat, ship.lon)
            ]

            for mmsi in stale_mmsis:
                self._ships.pop(mmsi, None)

            return len(stale_mmsis)

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


get_ship_registry = LazySingleton(ShipRegistry)


def __getattr__(name: str):
    if name == "registry":
        return get_ship_registry()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
