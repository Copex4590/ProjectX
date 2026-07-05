# ============================================================================
# Project X
# Logbook Recorder
# ============================================================================

from __future__ import annotations

from threading import Lock

from events import eventbus
from logbook.logbook_manager import logbook_manager


class LogbookRecorder:

    def __init__(self, manager=None):

        self._manager = manager or logbook_manager
        self._lock = Lock()
        self._last_ship_data: dict[int, dict[str, float]] = {}
        self._started = False

    def start(self) -> None:

        if self._started:
            return

        eventbus.subscribe("ship.updated", self._on_ship_updated)
        self._started = True

    def _on_ship_updated(self, ship=None, **kwargs) -> None:

        if ship is None:
            return

        lat = getattr(ship, "lat", None)
        lon = getattr(ship, "lon", None)

        if lat is None or lon is None:
            return

        mmsi = int(getattr(ship, "mmsi", 0) or 0)

        if mmsi <= 0:
            return

        speed = float(getattr(ship, "speed", 0.0) or 0.0)
        distance_km = getattr(ship, "distance_km", None)

        if distance_km is None:
            from logbook.duna_format import calc_distance_km

            distance_km = calc_distance_km(float(lat), float(lon))
        else:
            distance_km = float(distance_km)

        current_distance = round(distance_km, 2)

        with self._lock:
            previous = self._last_ship_data.get(mmsi)

            if previous is None:
                should_save = True
            else:
                should_save = (
                    abs(current_distance - previous["distance"]) >= 0.01
                    or speed >= 0.5
                )

            if not should_save:
                return

            self._last_ship_data[mmsi] = {
                "distance": current_distance,
                "speed": speed,
            }

        self._manager.append_observation(ship)


logbook_recorder = LogbookRecorder()
