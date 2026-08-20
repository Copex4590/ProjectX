# ============================================================================
# Project X
# Unified Camera Manager (SAVE-231)
# ============================================================================
"""Single CameraManager for catalog packs, Hunter listing catalog, and user cameras.

Catalog + enabled packs + Hunter listing-catalog cameras load via ``load()``.
User cameras persist to ``cameras.json``. The EarthCam mapsearch inventory is
produced by the Hunter listing scanner, not fetched here.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from debug.obs_freeze_trace import trace_enter, trace_exit
from PySide6.QtCore import QObject, Signal

from app.paths import runtime_config_path
from cameras.hunter_catalog import load_listing_cameras
from cameras.loader import CameraLoader
from cameras.pack_manager import CameraPackManager, camera_pack_manager
from database.camera_registry import CameraRegistry, camera_registry
from models.camera import (
    SOURCE_EARTHCAM,
    SOURCE_USER,
    Camera,
    normalize_camera_type,
)

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

CAMERAS_FILE = Path(
    os.environ.get(
        "PROJECTX_CAMERAS_FILE",
        str(runtime_config_path("cameras.json")),
    )
)


def _utc_now() -> datetime:

    return datetime.now(timezone.utc)


class CameraManager(QObject):
    """Process-wide camera façade (catalog + packs + Hunter listing + user CRUD)."""

    changed = Signal()

    def __init__(
        self,
        registry: CameraRegistry | None = None,
        config_dir: Path | None = None,
        user_path: Path | None = None,
        pack_manager: CameraPackManager | None = None,
        hunter_catalog_loader=None,
    ):

        super().__init__()

        self.registry = registry or camera_registry
        self.loader = CameraLoader(config_dir)
        self._pack_manager = pack_manager or camera_pack_manager
        self._hunter_catalog_loader = hunter_catalog_loader or load_listing_cameras
        self._user_path = Path(user_path or CAMERAS_FILE)
        self._lock = Lock()
        self._catalog_loaded = False

        # User cameras available immediately for Dashboard/Wizard.
        self._merge_into_registry(user_cameras=self._read_user_cameras())

    def load(self) -> int:
        """Load catalog + packs + Hunter listing catalog + user cameras."""

        with self._lock:
            catalog = self.loader.load_cameras()
            try:
                packs = self._pack_manager.load_enabled_cameras(self.loader)
            except Exception:
                logger.exception("Failed loading enabled camera packs")
                packs = []
            hunter = self._load_hunter_listing_unlocked()
            users = self._read_user_cameras_unlocked()
            merged = self._merge_lists(catalog, packs, hunter, users)
            self.registry.replace_all(merged)
            self._catalog_loaded = True
            return len(merged)

    def reload(self) -> int:

        self.registry.clear()
        self._catalog_loaded = False
        return self.load()

    def reload_hunter_catalog(self) -> int:
        """Reload Hunter listing cameras from disk without dropping other sources."""

        with self._lock:
            hunter = self._load_hunter_listing_unlocked()
            others = [
                camera
                for camera in self.registry.all()
                if camera.source != SOURCE_EARTHCAM
            ]
            users = [
                camera for camera in others if camera.source == SOURCE_USER
            ]
            rest = [
                camera for camera in others if camera.source != SOURCE_USER
            ]
            merged = self._merge_lists(rest, hunter, users)
            self.registry.replace_all(merged)
            count = len(hunter)

        self.changed.emit()
        return count

    def ensure_loaded(self) -> int:

        if self._catalog_loaded and self.registry.count() > 0:
            return self.registry.count()
        return self.load()

    def get(self, camera_id: str) -> Camera | None:

        return self.registry.get(camera_id)

    def all(self) -> list[Camera]:

        return self.registry.all()

    def enabled(self) -> list[Camera]:

        return self.registry.enabled()

    def by_country(self, country: str) -> list[Camera]:

        return self.registry.by_country(country)

    def by_observation(self, observation_point_id: str) -> list[Camera]:

        trace_enter(
            "CameraManager.by_observation "
            f"observation_point_id={observation_point_id}"
        )
        try:
            return self.registry.by_observation(observation_point_id)
        finally:
            trace_exit(
                "CameraManager.by_observation "
                f"observation_point_id={observation_point_id}"
            )

    def countries(self) -> list[str]:

        return self.registry.countries()

    def count(self) -> int:

        return self.registry.count()

    def observing(self, lat: float, lon: float) -> list[Camera]:

        return [
            camera
            for camera in self.registry.enabled()
            if camera.can_observe(lat, lon)
        ]

    def within_radius(self, lat: float, lon: float) -> list[Camera]:

        return [
            camera
            for camera in self.registry.enabled()
            if camera.is_within_radius(lat, lon)
        ]

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
            raise KeyError(f"Unknown observation point: {observation_point_id}")

        resolved_lat = point.latitude if latitude is None else float(latitude)
        resolved_lon = (
            point.longitude if longitude is None else float(longitude)
        )

        camera = Camera.new_user_camera(
            name=name,
            observation_point_id=point.id,
            enabled=enabled,
            camera_type=camera_type,
            stream_url=stream_url,
            latitude=resolved_lat,
            longitude=resolved_lon,
            heading=heading,
            field_of_view=field_of_view,
            max_distance=max_distance,
            description=description,
        )

        with self._lock:
            result = self.registry.add(camera)
            self._write_user_cameras_unlocked()

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
            camera = self._require_user_camera(camera_id)

            if name is not None:
                camera.name = str(name).strip() or camera.name
            if enabled is not None:
                camera.enabled = bool(enabled)
            if camera_type is not None:
                camera.provider_type = normalize_camera_type(camera_type)
            if stream_url is not None:
                camera.stream_url = str(stream_url).strip()
            if latitude is not None:
                camera.lat = float(latitude)
            if longitude is not None:
                camera.lon = float(longitude)
            if heading is not None:
                camera.direction_deg = float(heading)
            if field_of_view is not None:
                camera.fov_deg = float(field_of_view)
            if max_distance is not None:
                camera.visibility_radius_km = float(max_distance)
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

            camera.source = SOURCE_USER
            camera.updated_at = _utc_now()
            result = self.registry.add(camera)
            self._write_user_cameras_unlocked()

        self.changed.emit()
        return result

    def remove(self, camera_id: str) -> None:

        with self._lock:
            camera = self.registry.get(camera_id)
            if camera is None:
                raise KeyError(f"Unknown camera: {camera_id}")
            if camera.source != SOURCE_USER and not camera.observation_point_id:
                raise KeyError(f"Cannot remove catalog camera: {camera_id}")
            self.registry.remove(camera_id)
            self._write_user_cameras_unlocked()

        self.changed.emit()

    def _require_user_camera(self, camera_id: str) -> Camera:

        camera = self.registry.get(camera_id)
        if camera is None:
            raise KeyError(f"Unknown camera: {camera_id}")
        if camera.source != SOURCE_USER and not camera.observation_point_id:
            raise KeyError(f"Not a user camera: {camera_id}")
        return camera

    def _load_hunter_listing_unlocked(self) -> list[Camera]:

        try:
            return list(self._hunter_catalog_loader() or [])
        except Exception:
            logger.exception("Failed loading Hunter listing catalog")
            return []

    def _merge_into_registry(self, *, user_cameras: list[Camera]) -> None:

        existing = {
            camera.id: camera
            for camera in self.registry.all()
            if camera.source != SOURCE_USER
        }
        for camera in user_cameras:
            existing[camera.id] = camera
        self.registry.replace_all(list(existing.values()))

    @staticmethod
    def _merge_lists(*groups: list[Camera]) -> list[Camera]:

        merged: dict[str, Camera] = {}
        for group in groups:
            for camera in group:
                merged[camera.id] = camera
        return list(merged.values())

    def _read_user_cameras(self) -> list[Camera]:

        with self._lock:
            return self._read_user_cameras_unlocked()

    def _read_user_cameras_unlocked(self) -> list[Camera]:

        if not self._user_path.exists():
            return []

        try:
            with self._user_path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed reading user cameras from %s", self._user_path)
            return []

        migrated = self._migrate(data)
        cameras = [
            Camera.from_user_dict(item)
            for item in migrated.get("cameras", [])
            if isinstance(item, dict)
        ]

        if data != migrated:
            self._write_user_payload_unlocked(migrated)

        return cameras

    def _write_user_cameras_unlocked(self) -> None:

        cameras = [
            camera
            for camera in self.registry.all()
            if camera.source == SOURCE_USER or camera.observation_point_id
        ]
        # Ensure source tag for OP-bound entries.
        payload_cameras = []
        for camera in cameras:
            camera.source = SOURCE_USER
            payload_cameras.append(camera.to_user_dict())

        self._write_user_payload_unlocked(
            {
                "version": SCHEMA_VERSION,
                "cameras": payload_cameras,
            }
        )

    def _write_user_payload_unlocked(self, payload: dict) -> None:

        self._user_path.parent.mkdir(parents=True, exist_ok=True)
        with self._user_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")

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
            record["type"] = normalize_camera_type(
                record.get("provider_type") or record.get("type") or "hls"
            )
            record["provider_type"] = record["type"]
            cameras.append(record)

        payload["cameras"] = cameras
        return payload


camera_manager = CameraManager()
