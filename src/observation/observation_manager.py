# ============================================================================
# Project X
# Observation Manager
# ============================================================================

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from PySide6.QtCore import QObject, Signal

from observation.observation_point import ObservationPoint

SCHEMA_VERSION = 1

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

OBSERVATION_POINTS_FILE = Path(
    os.environ.get(
        "PROJECTX_OBSERVATION_POINTS_FILE",
        str(_CONFIG_DIR / "observation_points.json"),
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
        self._points: list[ObservationPoint] = []
        self._active_id: str | None = None
        self._load()

    def active(self) -> ObservationPoint | None:

        with self._lock:
            return deepcopy(self._find_active())

    def all(self) -> list[ObservationPoint]:

        with self._lock:
            return deepcopy(self._points)

    def get(self, point_id: str) -> ObservationPoint | None:

        with self._lock:
            point = self._find_by_id(point_id)
            return deepcopy(point) if point else None

    def set_active(self, point_id: str) -> ObservationPoint:

        with self._lock:
            target = self._require_point(point_id)

            for point in self._points:
                point.active = point.id == target.id

            self._active_id = target.id
            self._write_unlocked()
            result = deepcopy(target)

        self.changed.emit()
        return result

    def create(
        self,
        name: str,
        latitude: float,
        longitude: float,
        *,
        elevation: float | None = None,
        description: str = "",
        set_active: bool = True,
    ) -> ObservationPoint:

        point = ObservationPoint(
            name=str(name).strip() or "Observation Point",
            latitude=float(latitude),
            longitude=float(longitude),
            elevation=elevation,
            description=str(description).strip(),
            active=set_active,
        )

        with self._lock:
            if set_active or not self._points:
                for existing in self._points:
                    existing.active = False
                point.active = True
                self._active_id = point.id

            self._points.append(point)
            self._write_unlocked()
            result = deepcopy(point)

        self.changed.emit()
        return result

    def move(
        self,
        point_id: str,
        latitude: float,
        longitude: float,
    ) -> ObservationPoint:

        with self._lock:
            point = self._require_point(point_id)
            point.latitude = float(latitude)
            point.longitude = float(longitude)
            point.updated_at = _utc_now()
            self._write_unlocked()
            result = deepcopy(point)

        self.changed.emit()
        return result

    def rename(self, point_id: str, name: str) -> ObservationPoint:

        with self._lock:
            point = self._require_point(point_id)
            point.name = str(name).strip() or point.name
            point.updated_at = _utc_now()
            self._write_unlocked()
            result = deepcopy(point)

        self.changed.emit()
        return result

    def delete(self, point_id: str) -> None:

        with self._lock:
            point = self._require_point(point_id)
            self._points = [
                item for item in self._points if item.id != point.id
            ]

            if self._active_id == point.id:
                self._active_id = None

                if self._points:
                    self._points[0].active = True
                    self._active_id = self._points[0].id

            for item in self._points:
                item.active = item.id == self._active_id

            self._write_unlocked()

        self.changed.emit()

    def coordinates(self) -> tuple[float, float] | None:

        point = self.active()

        if point is None:
            return None

        return point.latitude, point.longitude

    def _find_by_id(self, point_id: str) -> ObservationPoint | None:

        normalized = str(point_id).strip()

        for point in self._points:
            if point.id == normalized:
                return point

        return None

    def _find_active(self) -> ObservationPoint | None:

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

    def _require_point(self, point_id: str) -> ObservationPoint:

        point = self._find_by_id(point_id)

        if point is None:
            raise KeyError(f"Unknown observation point: {point_id}")

        return point

    def _load(self) -> None:

        with self._lock:
            if not self._path.exists():
                self._points = []
                self._active_id = None
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

            active = self._find_active()

            if active is not None:
                self._active_id = active.id

            if data != migrated:
                self._write_unlocked()

    def _migrate(self, data: dict | None) -> dict:

        payload = dict(data or {})
        payload.setdefault("version", SCHEMA_VERSION)
        payload.setdefault("active_id", None)
        payload.setdefault("points", [])
        payload["version"] = SCHEMA_VERSION
        return payload

    def _write_unlocked(self) -> None:

        active = self._find_active()
        payload = {
            "version": SCHEMA_VERSION,
            "active_id": active.id if active else None,
            "points": [point.to_dict() for point in self._points],
        }

        self._path.parent.mkdir(parents=True, exist_ok=True)

        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")


observation_manager = ObservationManager()
