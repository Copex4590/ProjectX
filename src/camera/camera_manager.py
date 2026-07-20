# ============================================================================
# Project X
# Camera Manager
# ============================================================================

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from debug.obs_freeze_trace import trace_enter, trace_exit
from PySide6.QtCore import QObject, Signal

from camera.camera import Camera, _normalize_camera_type
from camera.camera_registry import CameraRegistry

SCHEMA_VERSION = 1

from storage.deferred_paths import deferred_config_path
from storage.lazy_singleton import LazySingleton, lazy_module_getattr


def cameras_file() -> Path:
    """Return the active cameras configuration file path."""

    return deferred_config_path("PROJECTX_CAMERAS_FILE", "cameras.json")


def _utc_now() -> datetime:

    return datetime.now(timezone.utc)


class CameraManager(QObject):

    changed = Signal()

    def __init__(
        self,
        path: Path | None = None,
        registry: CameraRegistry | None = None,
    ):

        super().__init__()

        self._path = path or cameras_file()
        self._registry = registry or CameraRegistry()
        self._lock = Lock()
        self._load()

    def all(self) -> list[Camera]:

        with self._lock:
            return self._registry.all()

    def enabled(self) -> list[Camera]:

        with self._lock:
            return self._registry.enabled()

    def get(self, camera_id: str) -> Camera | None:

        with self._lock:
            return self._registry.get(camera_id)

    def by_observation(self, observation_point_id: str) -> list[Camera]:

        trace_enter(
            "CameraManager.by_observation "
            f"observation_point_id={observation_point_id}"
        )

        try:
            with self._lock:
                return self._registry.by_observation(observation_point_id)
        finally:
            trace_exit(
                "CameraManager.by_observation "
                f"observation_point_id={observation_point_id}"
            )

    def add(
        self,
        name: str,
        observation_point_id: str,
        *,
        enabled: bool = True,
        camera_type: str = "hls",
        stream_url: str = "",
        latitude: float | None = None,
        longitude: float | None = None,
        heading: float = 0.0,
        field_of_view: float = 90.0,
        max_distance: float = 0.0,
        description: str = "",
    ) -> Camera:

        from observation.observation_manager import observation_manager

        point = observation_manager.get(observation_point_id)

        if point is None:
            raise KeyError(
                f"Unknown observation point: {observation_point_id}"
            )

        resolved_lat = point.latitude if latitude is None else float(latitude)
        resolved_lon = (
            point.longitude if longitude is None else float(longitude)
        )

        normalized_type = _normalize_camera_type(camera_type)

        camera = Camera(
            name=str(name).strip() or "Camera",
            observation_point_id=point.id,
            enabled=bool(enabled),
            type=normalized_type,
            stream_url=str(stream_url).strip(),
            latitude=resolved_lat,
            longitude=resolved_lon,
            heading=float(heading),
            field_of_view=float(field_of_view),
            max_distance=float(max_distance),
            description=str(description).strip(),
        )

        with self._lock:
            result = self._registry.add(camera)
            self._write_unlocked()

        self.changed.emit()
        return result

    def update(
        self,
        camera_id: str,
        *,
        name: str | None = None,
        enabled: bool | None = None,
        camera_type: str | None = None,
        stream_url: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        heading: float | None = None,
        field_of_view: float | None = None,
        max_distance: float | None = None,
        description: str | None = None,
        observation_point_id: str | None = None,
    ) -> Camera:

        with self._lock:
            camera = self._require_camera(camera_id)

            if name is not None:
                camera.name = str(name).strip() or camera.name

            if enabled is not None:
                camera.enabled = bool(enabled)

            if camera_type is not None:
                camera.type = _normalize_camera_type(camera_type)

            if stream_url is not None:
                camera.stream_url = str(stream_url).strip()

            if latitude is not None:
                camera.latitude = float(latitude)

            if longitude is not None:
                camera.longitude = float(longitude)

            if heading is not None:
                camera.heading = float(heading)

            if field_of_view is not None:
                camera.field_of_view = float(field_of_view)

            if max_distance is not None:
                camera.max_distance = float(max_distance)

            if description is not None:
                camera.description = str(description).strip()

            if observation_point_id is not None:
                from observation.observation_manager import observation_manager

                point = observation_manager.get(observation_point_id)

                if point is None:
                    raise KeyError(
                        f"Unknown observation point: {observation_point_id}"
                    )

                camera.observation_point_id = point.id

            camera.updated_at = _utc_now()
            result = self._registry.add(camera)
            self._write_unlocked()

        self.changed.emit()
        return result

    def remove(self, camera_id: str) -> None:

        with self._lock:
            self._registry.remove(camera_id)
            self._write_unlocked()

        self.changed.emit()

    def _require_camera(self, camera_id: str) -> Camera:

        camera = self._registry.get(camera_id)

        if camera is None:
            raise KeyError(f"Unknown camera: {camera_id}")

        return camera

    def _load(self) -> None:

        with self._lock:
            if not self._path.exists():
                self._registry.replace_all([])
                self._write_unlocked()
                return

            with self._path.open(encoding="utf-8") as handle:
                data = json.load(handle)

            migrated = self._migrate(data)
            cameras = [
                Camera.from_dict(item)
                for item in migrated.get("cameras", [])
            ]
            self._registry.replace_all(cameras)

            if data != migrated:
                self._write_unlocked()

    def _migrate(self, data: dict | None) -> dict:

        payload = dict(data or {})
        payload.setdefault("version", SCHEMA_VERSION)
        payload.setdefault("cameras", [])
        payload["version"] = SCHEMA_VERSION

        cameras = []

        for item in payload.get("cameras", []):
            if not isinstance(item, dict):
                continue

            record = dict(item)
            record["type"] = _normalize_camera_type(record.get("type", "hls"))
            cameras.append(record)

        payload["cameras"] = cameras
        return payload

    def _write_unlocked(self) -> None:

        payload = {
            "version": SCHEMA_VERSION,
            "cameras": [
                camera.to_dict()
                for camera in self._registry.all()
            ],
        }

        self._path.parent.mkdir(parents=True, exist_ok=True)

        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")


get_camera_manager = LazySingleton(CameraManager)


def __getattr__(name: str):
    if name == "CAMERAS_FILE":
        return cameras_file()
    return lazy_module_getattr(
        name,
        module_name=__name__,
        export_name="camera_manager",
        getter=get_camera_manager,
    )
