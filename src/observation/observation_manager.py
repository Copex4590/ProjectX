# ============================================================================
# Project X
# Observation Manager
# ============================================================================

from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from PySide6.QtCore import QObject, Signal

from observation.observation_point import (
    DEFAULT_COVERAGE_RADIUS_KM,
    ObservationPoint,
)

SCHEMA_VERSION = 3

from app.paths import runtime_config_path

from debug.obs_freeze_trace import (
    begin_delete_trace_session,
    reset_trace_log,
    trace_block,
    trace_enter,
    trace_event,
    trace_exit,
)

OBSERVATION_POINTS_FILE = Path(
    os.environ.get(
        "PROJECTX_OBSERVATION_POINTS_FILE",
        str(runtime_config_path("observation_points.json")),
    )
)


def _utc_now() -> datetime:

    return datetime.now(timezone.utc)


class ObservationManager(QObject):

    changed = Signal()

    def __init__(self, path: Path | None = None):

        super().__init__()

        self._path = path or OBSERVATION_POINTS_FILE
        self._lock = Lock()
        self._lock_owner_thread_id: int | None = None
        self._lock_owner_thread_name: str | None = None
        self._lock_owner_caller: str | None = None
        self._points: list[ObservationPoint] = []
        self._active_id: str | None = None
        self._reference_id: str | None = None
        self._multi_op_notice_shown = False
        self._load()

    def _lock_owner_label(self) -> str:

        if self._lock_owner_thread_name is None:
            return "none"

        caller = self._lock_owner_caller or "unknown"
        owner_id = self._lock_owner_thread_id
        return f"{self._lock_owner_thread_name} id={owner_id} caller={caller}"

    @contextmanager
    def _hold_lock(self, caller: str):

        waiting_thr = threading.current_thread().name
        waiting_id = threading.get_ident()
        owner = self._lock_owner_label()

        trace_enter(
            "ObservationManager._lock.acquire "
            f"caller={caller} thr={waiting_thr} id={waiting_id} owner={owner}"
        )

        try:
            self._lock.acquire()
            self._lock_owner_thread_id = waiting_id
            self._lock_owner_thread_name = waiting_thr
            self._lock_owner_caller = caller

            trace_exit(
                "ObservationManager._lock.acquire "
                f"caller={caller} thr={waiting_thr} id={waiting_id} owner=acquired"
            )

            try:
                yield
            finally:
                trace_enter(
                    "ObservationManager._lock.release "
                    f"caller={caller} thr={waiting_thr} id={waiting_id}"
                )

                try:
                    self._lock_owner_thread_id = None
                    self._lock_owner_thread_name = None
                    self._lock_owner_caller = None
                    self._lock.release()
                finally:
                    trace_exit(
                        "ObservationManager._lock.release "
                        f"caller={caller} thr={waiting_thr} id={waiting_id}"
                    )
        except BaseException:
            trace_event(
                "ObservationManager._lock.acquire FAILED "
                f"caller={caller} thr={waiting_thr} id={waiting_id} owner={owner}"
            )
            raise

    def active(self) -> ObservationPoint | None:

        trace_enter("ObservationManager.active")

        try:
            with self._hold_lock("active"):
                return deepcopy(self._find_active())
        finally:
            trace_exit("ObservationManager.active")

    def all(self) -> list[ObservationPoint]:

        trace_enter("ObservationManager.all")

        try:
            with self._hold_lock("all"):
                return deepcopy(self._points)
        finally:
            trace_exit("ObservationManager.all")

    def get(self, point_id: str) -> ObservationPoint | None:

        with self._hold_lock("get"):
            point = self._find_by_id(point_id)
            return deepcopy(point) if point else None

    def active_points(self) -> list[ObservationPoint]:

        trace_enter("ObservationManager.active_points")

        try:
            with self._hold_lock("active_points"):
                return deepcopy(
                    [point for point in self._points if point.active]
                )
        finally:
            trace_exit("ObservationManager.active_points")

    def reference(self) -> ObservationPoint | None:

        trace_enter("ObservationManager.reference")

        try:
            with self._hold_lock("reference"):
                return deepcopy(self._find_reference_unlocked())
        finally:
            trace_exit("ObservationManager.reference")

    def reference_coordinates(self) -> tuple[float, float] | None:

        point = self.reference()

        if point is None:
            return None

        return point.latitude, point.longitude

    def needs_reference_selection(self) -> bool:

        trace_enter("ObservationManager.needs_reference_selection")

        try:
            with self._hold_lock("needs_reference_selection"):
                active_points = [point for point in self._points if point.active]

                if len(active_points) <= 1:
                    return False

                reference = self._find_reference_unlocked()

                if reference is None:
                    return True

                return not any(
                    point.id == reference.id for point in active_points
                )
        finally:
            trace_exit("ObservationManager.needs_reference_selection")

    def set_reference(self, point_id: str) -> ObservationPoint:

        trace_enter(f"ObservationManager.set_reference point_id={point_id}")

        try:
            with self._hold_lock("set_reference"):
                target = self._require_point(point_id)

                if not target.active:
                    raise ValueError(
                        f"Observation point is not active: {point_id}"
                    )

                self._reference_id = target.id
                trace_enter("ObservationManager.set_reference._write_unlocked")
                self._write_unlocked()
                trace_exit("ObservationManager.set_reference._write_unlocked")
                result = deepcopy(target)

            trace_enter("ObservationManager.set_reference.changed.emit")
            self.changed.emit()
            trace_exit("ObservationManager.set_reference.changed.emit")
            return result
        finally:
            trace_exit(f"ObservationManager.set_reference point_id={point_id}")

    def activate_point(self, point_id: str) -> ObservationPoint:

        with self._hold_lock("activate_point"):
            point = self._require_point(point_id)
            point.active = True
            point.updated_at = _utc_now()
            self._active_id = point.id

            active_points = [item for item in self._points if item.active]

            if len(active_points) == 1:
                self._reference_id = point.id

            self._write_unlocked()
            result = deepcopy(point)

        self.changed.emit()
        return result

    def deactivate_point(self, point_id: str) -> ObservationPoint:

        with self._hold_lock("deactivate_point"):
            point = self._require_point(point_id)
            point.active = False
            point.updated_at = _utc_now()

            if self._active_id == point.id:
                self._active_id = None

                for item in self._points:
                    if item.active:
                        self._active_id = item.id
                        break

            if self._reference_id == point.id:
                self._reference_id = None

                active_points = [item for item in self._points if item.active]

                if len(active_points) == 1:
                    self._reference_id = active_points[0].id

            self._write_unlocked()
            result = deepcopy(point)

        self.changed.emit()
        return result

    def set_active(self, point_id: str) -> ObservationPoint:

        trace_enter(f"ObservationManager._set_active point_id={point_id}")

        try:
            with self._hold_lock("_set_active"):
                target = self._require_point(point_id)

                for point in self._points:
                    point.active = point.id == target.id

                self._active_id = target.id
                self._reference_id = target.id
                self._write_unlocked()
                result = deepcopy(target)

            trace_enter("ObservationManager._set_active.changed.emit")
            self.changed.emit()
            trace_exit("ObservationManager._set_active.changed.emit")
            return result
        finally:
            trace_exit(f"ObservationManager._set_active point_id={point_id}")

    def create(
        self,
        name: str,
        latitude: float,
        longitude: float,
        *,
        coverage_radius_km: float,
        elevation: float | None = None,
        description: str = "",
        set_active: bool = True,
    ) -> ObservationPoint:

        reset_trace_log()
        trace_enter("ObservationManager.create")

        point = ObservationPoint(
            name=str(name).strip() or "Observation Point",
            latitude=float(latitude),
            longitude=float(longitude),
            coverage_radius_km=float(coverage_radius_km),
            elevation=elevation,
            description=str(description).strip(),
            active=set_active,
        )

        with self._hold_lock("create"):
            if set_active or not self._points:
                for existing in self._points:
                    existing.active = False
                point.active = True
                self._active_id = point.id
                self._reference_id = point.id

            self._points.append(point)
            trace_enter("ObservationManager.create._write_unlocked")
            self._write_unlocked()
            trace_exit("ObservationManager.create._write_unlocked")
            result = deepcopy(point)

        trace_enter("ObservationManager.changed.emit")
        self.changed.emit()
        trace_exit("ObservationManager.changed.emit")
        trace_exit("ObservationManager.create")
        return result

    def try_consume_multi_op_notice(self) -> bool:

        with self._hold_lock("try_consume_multi_op_notice"):
            if self._multi_op_notice_shown:
                return False

            if len(self._points) != 2:
                return False

            self._multi_op_notice_shown = True
            self._write_unlocked()
            return True

    def move(
        self,
        point_id: str,
        latitude: float,
        longitude: float,
    ) -> ObservationPoint:

        with self._hold_lock("move"):
            point = self._require_point(point_id)
            point.latitude = float(latitude)
            point.longitude = float(longitude)
            point.updated_at = _utc_now()
            self._write_unlocked()
            result = deepcopy(point)

        self.changed.emit()
        return result

    def rename(self, point_id: str, name: str) -> ObservationPoint:

        with self._hold_lock("rename"):
            point = self._require_point(point_id)
            point.name = str(name).strip() or point.name
            point.updated_at = _utc_now()
            self._write_unlocked()
            result = deepcopy(point)

        self.changed.emit()
        return result

    def set_coverage_radius(
        self,
        point_id: str,
        coverage_radius_km: float,
    ) -> ObservationPoint:

        radius = float(coverage_radius_km)

        if radius <= 0:
            raise ValueError("coverage_radius_km must be positive")

        with self._hold_lock("set_coverage_radius"):
            point = self._require_point(point_id)
            point.coverage_radius_km = radius
            point.updated_at = _utc_now()
            self._write_unlocked()
            result = deepcopy(point)

        self.changed.emit()
        return result

    def delete(self, point_id: str) -> None:

        trace_enter(f"ObservationManager.delete_observation point_id={point_id}")

        try:
            with self._hold_lock("delete_observation"):
                point = self._require_point(point_id)
                self._points = [
                    item for item in self._points if item.id != point.id
                ]

                if self._active_id == point.id:
                    self._active_id = None
                    self._reference_id = None

                    if self._points:
                        self._points[0].active = True
                        self._active_id = self._points[0].id
                        self._reference_id = self._points[0].id

                for item in self._points:
                    item.active = item.id == self._active_id

                trace_enter("ObservationManager.delete_observation._write_unlocked")
                self._write_unlocked()
                trace_exit("ObservationManager.delete_observation._write_unlocked")

            trace_enter("ObservationManager.changed.emit")
            self.changed.emit()
            trace_exit("ObservationManager.changed.emit")
        finally:
            trace_exit(f"ObservationManager.delete_observation point_id={point_id}")

    def coordinates(self) -> tuple[float, float] | None:

        return self.reference_coordinates()

    def _find_reference_unlocked(self) -> ObservationPoint | None:

        trace_enter("ObservationManager._find_reference_unlocked")

        try:
            if self._reference_id:
                point = self._find_by_id(self._reference_id)

                if point is not None and point.active:
                    return point

            active_points = [point for point in self._points if point.active]

            if len(active_points) == 1:
                self._reference_id = active_points[0].id
                return active_points[0]

            if len(active_points) == 0:
                return None

            if self._active_id:
                point = self._find_by_id(self._active_id)

                if point is not None and point.active:
                    self._reference_id = point.id
                    return point

            return None
        finally:
            trace_exit("ObservationManager._find_reference_unlocked")

    def _find_reference(self) -> ObservationPoint | None:

        with self._hold_lock("_find_reference"):
            return self._find_reference_unlocked()

    def _find_by_id(self, point_id: str) -> ObservationPoint | None:

        normalized = str(point_id).strip()

        for point in self._points:
            if point.id == normalized:
                return point

        return None

    def _find_active(self) -> ObservationPoint | None:

        trace_enter("ObservationManager._find_active")

        try:
            if self._active_id:
                point = self._find_by_id(self._active_id)

                if point is not None:
                    return point

            for point in self._points:
                if point.active:
                    self._active_id = point.id
                    return point

            if self._points:
                self._points[0].active = True
                self._active_id = self._points[0].id
                return self._points[0]

            return None
        finally:
            trace_exit("ObservationManager._find_active")

    def _require_point(self, point_id: str) -> ObservationPoint:

        point = self._find_by_id(point_id)

        if point is None:
            raise KeyError(f"Unknown observation point: {point_id}")

        return point

    def _load(self) -> None:

        with self._hold_lock("_load"):
            if not self._path.exists():
                self._points = []
                self._active_id = None
                self._reference_id = None
                self._write_unlocked()
                return

            with self._path.open(encoding="utf-8") as handle:
                data = json.load(handle)

            migrated = self._migrate(data)
            self._points = [
                ObservationPoint.from_dict(item)
                for item in migrated.get("points", [])
            ]
            self._active_id = migrated.get("active_id")
            self._reference_id = migrated.get("reference_id")
            self._multi_op_notice_shown = bool(
                migrated.get("multi_op_notice_shown", False)
            )

            active = self._find_active()

            if active is not None:
                self._active_id = active.id

            self._find_reference_unlocked()

            needs_write = data != migrated

            if self._normalize_active_state_unlocked():
                needs_write = True

            if (
                not self._multi_op_notice_shown
                and len(self._points) >= 2
            ):
                self._multi_op_notice_shown = True
                needs_write = True

            if needs_write:
                self._write_unlocked()

    def _normalize_active_state_unlocked(self) -> bool:

        active = self._find_active()

        if active is None:
            return False

        changed = False

        for point in self._points:
            should_active = point.id == active.id

            if point.active != should_active:
                point.active = should_active
                changed = True

        if self._active_id != active.id:
            self._active_id = active.id
            changed = True

        return changed

    def _migrate(self, data: dict | None) -> dict:

        payload = dict(data or {})
        payload.setdefault("version", SCHEMA_VERSION)
        payload.setdefault("active_id", None)
        payload.setdefault("reference_id", None)
        payload.setdefault("points", [])
        payload.setdefault("multi_op_notice_shown", False)

        version = int(payload.get("version") or 1)
        points = payload.get("points", [])
        active_ids = [
            str(item.get("id"))
            for item in points
            if item.get("active")
        ]

        if version < SCHEMA_VERSION:
            if not payload.get("reference_id"):
                if len(active_ids) == 1:
                    payload["reference_id"] = active_ids[0]
                elif payload.get("active_id"):
                    payload["reference_id"] = payload["active_id"]

            for item in points:
                if item.get("coverage_radius_km") in (None, ""):
                    item["coverage_radius_km"] = DEFAULT_COVERAGE_RADIUS_KM

        payload["version"] = SCHEMA_VERSION
        return payload

    def _write_unlocked(self) -> None:

        trace_enter("ObservationManager._write_unlocked")

        try:
            trace_enter("ObservationManager._write_unlocked._find_active")
            active = self._find_active()
            trace_exit("ObservationManager._write_unlocked._find_active")

            trace_enter("ObservationManager._write_unlocked._find_reference_unlocked")
            reference = self._find_reference_unlocked()
            trace_exit("ObservationManager._write_unlocked._find_reference_unlocked")

            payload = {
                "version": SCHEMA_VERSION,
                "active_id": active.id if active else None,
                "reference_id": reference.id if reference else self._reference_id,
                "points": [point.to_dict() for point in self._points],
                "multi_op_notice_shown": self._multi_op_notice_shown,
            }

            trace_enter("ObservationManager._write_unlocked.mkdir")
            self._path.parent.mkdir(parents=True, exist_ok=True)
            trace_exit("ObservationManager._write_unlocked.mkdir")

            trace_enter("ObservationManager._write_unlocked.json.dump")
            with self._path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
            trace_exit("ObservationManager._write_unlocked.json.dump")
        finally:
            trace_exit("ObservationManager._write_unlocked")


observation_manager = ObservationManager()
