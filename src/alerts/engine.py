# ============================================================================
# Project X
# Professional Alerts Engine (SAVE-215)
# ============================================================================

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime
from threading import Event, Lock, Thread
from typing import Any

from alerts.alert_event import EvaluationEvent
from alerts.alert_manager import alert_manager
from alerts.alert_rule import (
    RULE_TYPE_AIS_LOST,
    RULE_TYPE_ANCHORED,
    RULE_TYPE_ARRIVAL,
    RULE_TYPE_CAMERA_OFFLINE,
    RULE_TYPE_DB_SYNC_FAILED,
    RULE_TYPE_DEPARTURE,
    RULE_TYPE_ENTER_REGION,
    RULE_TYPE_EXIT_REGION,
    RULE_TYPE_SPEED_OVER,
    RULE_TYPE_SPEED_UNDER,
)
from alerts.notify_hooks import install_default_notification_sinks
from database.vessel_database_manager import EVENT_SYNC_FAILED
from events import eventbus
from observation.geo_context import geo_context

logger = logging.getLogger(__name__)

EVENT_TIMELINE_ARRIVAL = "timeline.arrival"
EVENT_TIMELINE_DEPARTURE = "timeline.departure"

_QUEUE_IDLE_TIMEOUT_S = 0.5
_ANCHORED_DWELL_S = 120.0


class ProfessionalAlertsEngine:
    """
    Edge-detecting alert engine.

    Subscribes to EventBus signals and evaluates enabled rules without
    blocking the AIS hot path (queue + worker thread).
    """

    def __init__(self, manager=None):

        self._manager = manager or alert_manager
        self._lock = Lock()
        self._queue: deque[tuple[str, dict[str, Any]]] = deque()
        self._wake = Event()
        self._stop = Event()
        self._thread: Thread | None = None

        self._inside_region: dict[int, bool] = {}
        self._speed_over: dict[int, bool] = {}
        self._speed_under: dict[int, bool] = {}
        self._anchored_since: dict[int, datetime] = {}
        self._anchored_active: dict[int, bool] = {}
        self._camera_visible: dict[int, bool] = {}
        self._ais_online = True

    def start(self) -> None:

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return

            self._stop.clear()
            self._manager.ensure_system_rules()
            install_default_notification_sinks(self._manager)

            eventbus.subscribe("ship.updated", self._on_ship_updated)
            eventbus.subscribe("ais.status", self._on_ais_status)
            eventbus.subscribe(EVENT_SYNC_FAILED, self._on_sync_failed)
            eventbus.subscribe(EVENT_TIMELINE_ARRIVAL, self._on_timeline_arrival)
            eventbus.subscribe(EVENT_TIMELINE_DEPARTURE, self._on_timeline_departure)

            self._thread = Thread(
                target=self._worker_loop,
                name="ProfessionalAlertsEngine",
                daemon=True,
            )
            self._thread.start()
            logger.info("Professional Alerts Engine started")

    def stop(self, timeout: float = 5.0) -> None:

        self._stop.set()
        self._wake.set()

        eventbus.unsubscribe("ship.updated", self._on_ship_updated)
        eventbus.unsubscribe("ais.status", self._on_ais_status)
        eventbus.unsubscribe(EVENT_SYNC_FAILED, self._on_sync_failed)
        eventbus.unsubscribe(EVENT_TIMELINE_ARRIVAL, self._on_timeline_arrival)
        eventbus.unsubscribe(EVENT_TIMELINE_DEPARTURE, self._on_timeline_departure)

        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout)
        self._thread = None
        logger.info("Professional Alerts Engine stopped")

    def _enqueue(self, kind: str, payload: dict[str, Any]) -> None:

        with self._lock:
            self._queue.append((kind, payload))
        self._wake.set()

    def _on_ship_updated(self, *args, **kwargs) -> None:

        ship = kwargs.get("ship")
        if ship is None and args:
            ship = args[0]
        if ship is None:
            return

        try:
            payload = {
                "mmsi": int(ship.mmsi),
                "lat": float(ship.lat),
                "lon": float(ship.lon),
                "speed": float(ship.speed),
                "camera_visible": bool(ship.camera_visible),
                "timestamp": ship.last_seen or datetime.now(),
                "name": str(ship.name or ""),
            }
        except Exception:
            return

        self._enqueue("ship", payload)

    def _on_ais_status(self, *args, **kwargs) -> None:

        status = kwargs.get("status")
        if status is None and args:
            status = args[0]
        self._enqueue("ais_status", {"status": str(status or "").strip().lower()})

    def _on_sync_failed(self, *args, **kwargs) -> None:

        message = str(kwargs.get("error") or kwargs.get("message") or "Database sync failed")
        self._enqueue("db_sync_failed", {"message": message})

    def _on_timeline_arrival(self, *args, **kwargs) -> None:

        self._enqueue("arrival", dict(kwargs))

    def _on_timeline_departure(self, *args, **kwargs) -> None:

        self._enqueue("departure", dict(kwargs))

    def _worker_loop(self) -> None:

        while not self._stop.is_set():
            self._wake.wait(timeout=_QUEUE_IDLE_TIMEOUT_S)
            self._wake.clear()

            while True:
                with self._lock:
                    if not self._queue:
                        break
                    kind, payload = self._queue.popleft()

                try:
                    if kind == "ship":
                        self._process_ship(payload)
                    elif kind == "ais_status":
                        self._process_ais_status(payload)
                    elif kind == "db_sync_failed":
                        self._process_db_sync_failed(payload)
                    elif kind == "arrival":
                        self._fire_simple(
                            RULE_TYPE_ARRIVAL,
                            int(payload.get("mmsi") or 0),
                            payload,
                        )
                    elif kind == "departure":
                        self._fire_simple(
                            RULE_TYPE_DEPARTURE,
                            int(payload.get("mmsi") or 0),
                            payload,
                        )
                except Exception:
                    logger.exception("Alerts engine failed on %s", kind)

    def _process_ship(self, payload: dict[str, Any]) -> None:

        mmsi = int(payload["mmsi"])
        lat = float(payload["lat"])
        lon = float(payload["lon"])
        speed = float(payload["speed"])
        camera_visible = bool(payload["camera_visible"])
        timestamp = payload.get("timestamp") or datetime.now()

        self._process_region(mmsi, lat, lon, timestamp, payload)
        self._process_speed(mmsi, speed, lat, lon, timestamp, payload)
        self._process_anchored(mmsi, speed, lat, lon, timestamp, payload)
        self._process_camera(mmsi, camera_visible, lat, lon, timestamp, payload)

    def _region_conditions(self) -> dict:

        # Prefer first enabled ENTER/EXIT rule conditions; fallback to geo reference.
        for rule in self._manager.rules():
            if not rule.enabled:
                continue
            if rule.event_type in (RULE_TYPE_ENTER_REGION, RULE_TYPE_EXIT_REGION):
                conditions = dict(rule.conditions or {})
                if conditions.get("latitude") or conditions.get("lat"):
                    return conditions

        observation = geo_context.reference()
        if observation is None:
            return {}

        lat = getattr(observation, "latitude", None)
        lon = getattr(observation, "longitude", None)
        if lat is None or lon is None:
            return {}

        return {
            "latitude": float(lat),
            "longitude": float(lon),
            "radius_km": 1.0,
        }

    def _process_region(
        self,
        mmsi: int,
        lat: float,
        lon: float,
        timestamp: datetime,
        payload: dict[str, Any],
    ) -> None:

        conditions = self._region_conditions()
        if not conditions:
            return

        from alerts.alert_manager import _point_in_region

        inside = _point_in_region(lat, lon, conditions)
        previous = self._inside_region.get(mmsi)

        if previous is None:
            self._inside_region[mmsi] = inside
            return

        if inside and not previous:
            self._fire_simple(
                RULE_TYPE_ENTER_REGION,
                mmsi,
                {
                    **payload,
                    "latitude": lat,
                    "longitude": lon,
                    "timestamp": timestamp,
                },
            )
        elif previous and not inside:
            self._fire_simple(
                RULE_TYPE_EXIT_REGION,
                mmsi,
                {
                    **payload,
                    "latitude": lat,
                    "longitude": lon,
                    "timestamp": timestamp,
                },
            )

        self._inside_region[mmsi] = inside

    def _process_speed(
        self,
        mmsi: int,
        speed: float,
        lat: float,
        lon: float,
        timestamp: datetime,
        payload: dict[str, Any],
    ) -> None:

        over_limit = None
        under_limit = None

        for rule in self._manager.rules():
            if not rule.enabled:
                continue
            if rule.event_type == RULE_TYPE_SPEED_OVER:
                over_limit = float(
                    rule.conditions.get("speed_limit", rule.conditions.get("min_speed", 15.0))
                )
            if rule.event_type == RULE_TYPE_SPEED_UNDER:
                under_limit = float(
                    rule.conditions.get("speed_limit", rule.conditions.get("max_speed", 0.5))
                )

        if over_limit is not None:
            active = speed > over_limit
            previous = self._speed_over.get(mmsi, False)
            if active and not previous:
                self._fire_simple(
                    RULE_TYPE_SPEED_OVER,
                    mmsi,
                    {
                        **payload,
                        "speed": speed,
                        "latitude": lat,
                        "longitude": lon,
                        "timestamp": timestamp,
                    },
                )
            self._speed_over[mmsi] = active

        if under_limit is not None:
            active = speed < under_limit
            previous = self._speed_under.get(mmsi, False)
            if active and not previous:
                self._fire_simple(
                    RULE_TYPE_SPEED_UNDER,
                    mmsi,
                    {
                        **payload,
                        "speed": speed,
                        "latitude": lat,
                        "longitude": lon,
                        "timestamp": timestamp,
                    },
                )
            self._speed_under[mmsi] = active

    def _process_anchored(
        self,
        mmsi: int,
        speed: float,
        lat: float,
        lon: float,
        timestamp: datetime,
        payload: dict[str, Any],
    ) -> None:

        limit = 0.3
        for rule in self._manager.rules():
            if rule.enabled and rule.event_type == RULE_TYPE_ANCHORED:
                limit = float(rule.conditions.get("speed_limit", 0.3))
                break

        if speed <= limit:
            since = self._anchored_since.get(mmsi)
            if since is None:
                self._anchored_since[mmsi] = timestamp
                return

            dwell = (timestamp - since).total_seconds()
            if dwell >= _ANCHORED_DWELL_S and not self._anchored_active.get(mmsi, False):
                self._anchored_active[mmsi] = True
                self._fire_simple(
                    RULE_TYPE_ANCHORED,
                    mmsi,
                    {
                        **payload,
                        "speed": speed,
                        "latitude": lat,
                        "longitude": lon,
                        "timestamp": timestamp,
                    },
                )
        else:
            self._anchored_since.pop(mmsi, None)
            self._anchored_active[mmsi] = False

    def _process_camera(
        self,
        mmsi: int,
        camera_visible: bool,
        lat: float,
        lon: float,
        timestamp: datetime,
        payload: dict[str, Any],
    ) -> None:

        previous = self._camera_visible.get(mmsi)
        self._camera_visible[mmsi] = camera_visible

        if previous is None:
            return

        if previous and not camera_visible:
            self._fire_simple(
                RULE_TYPE_CAMERA_OFFLINE,
                mmsi,
                {
                    **payload,
                    "camera_visible": False,
                    "latitude": lat,
                    "longitude": lon,
                    "timestamp": timestamp,
                },
            )

    def _process_ais_status(self, payload: dict[str, Any]) -> None:

        status = str(payload.get("status") or "").strip().lower()
        online = status in {"connected", "online"}

        if self._ais_online and not online and status in {"offline", "waiting", "error"}:
            self._fire_simple(
                RULE_TYPE_AIS_LOST,
                0,
                {"status": status, "timestamp": datetime.now()},
            )

        if status:
            self._ais_online = online

    def _process_db_sync_failed(self, payload: dict[str, Any]) -> None:

        self._fire_simple(
            RULE_TYPE_DB_SYNC_FAILED,
            0,
            {
                "message": payload.get("message") or "Database sync failed",
                "timestamp": datetime.now(),
            },
        )

    def _fire_simple(self, event_type: str, mmsi: int, payload: dict[str, Any]) -> None:

        evaluation = EvaluationEvent(
            mmsi=int(mmsi),
            event_type=event_type,
            timestamp=payload.get("timestamp") or datetime.now(),
            speed=payload.get("speed"),
            latitude=payload.get("latitude", payload.get("lat")),
            longitude=payload.get("longitude", payload.get("lon")),
            camera_visible=payload.get("camera_visible"),
            metadata={
                key: value
                for key, value in payload.items()
                if key
                not in {
                    "mmsi",
                    "event_type",
                    "timestamp",
                    "speed",
                    "latitude",
                    "longitude",
                    "lat",
                    "lon",
                    "camera_visible",
                }
            },
        )
        self._manager.evaluate(evaluation)


professional_alerts_engine = ProfessionalAlertsEngine()
