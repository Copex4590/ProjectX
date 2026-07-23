# ============================================================================
# Project X
# Logbook Recorder
# ============================================================================

from __future__ import annotations

import logging
from queue import Empty, Queue
from threading import Lock, Thread

from events import eventbus
from logbook.logbook_manager import logbook_manager

logger = logging.getLogger(__name__)

_STOP = object()


class LogbookRecorder:

    def __init__(self, manager=None):

        self._manager = manager or logbook_manager
        self._lock = Lock()
        self._last_ship_data: dict[int, dict[str, float]] = {}
        self._started = False
        self._queue: Queue = Queue()
        self._worker: Thread | None = None
        self._worker_lock = Lock()
        self._stop_requested = False

    def start(self) -> None:

        if self._started:
            return

        eventbus.subscribe("ship.updated", self._on_ship_updated)
        self._ensure_worker()
        self._started = True

    def stop(self, timeout: float = 5.0) -> None:

        self._stop_requested = True

        if self._started:
            try:
                eventbus.unsubscribe("ship.updated", self._on_ship_updated)
            except Exception:
                logger.exception("Failed to unsubscribe logbook recorder")
            self._started = False

        with self._worker_lock:
            worker = self._worker
            if worker is not None and worker.is_alive():
                self._queue.put(_STOP)

        if worker is not None and worker.is_alive():
            worker.join(timeout=timeout)
            if worker.is_alive():
                logger.warning("Logbook recorder worker did not stop within %.1fs", timeout)

        self._manager.stop(timeout=timeout)

    def _on_ship_updated(self, ship=None, **kwargs) -> None:
        """EventBus hot path: enqueue only — never touch XLSX here."""

        if ship is None or self._stop_requested:
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

        self._ensure_worker()
        self._queue.put(ship)

    def _ensure_worker(self) -> None:

        with self._worker_lock:
            if self._worker is not None and self._worker.is_alive():
                return

            self._stop_requested = False
            self._worker = Thread(
                target=self._worker_loop,
                name="LogbookRecorderWorker",
                daemon=True,
            )
            self._worker.start()

    def _worker_loop(self) -> None:

        while True:
            try:
                item = self._queue.get(timeout=0.5)
            except Empty:
                if self._stop_requested:
                    return
                continue

            try:
                if item is _STOP:
                    return

                self._manager.append_observation(item)
            except Exception:
                logger.exception("Logbook append failed")
            finally:
                self._queue.task_done()


logbook_recorder = LogbookRecorder()
