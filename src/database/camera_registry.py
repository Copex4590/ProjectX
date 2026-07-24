# ============================================================================
# Project X
# Unified Camera Registry (SAVE-231)
# ============================================================================

from __future__ import annotations

from copy import deepcopy
from threading import Lock

from models.camera import Camera


class CameraRegistry:

    def __init__(self):

        self._cameras: dict[str, Camera] = {}
        self._by_country: dict[str, set[str]] = {}
        self._by_observation: dict[str, set[str]] = {}
        self._lock = Lock()

    def add(self, camera: Camera) -> Camera:

        with self._lock:
            camera_id = camera.id
            previous = self._cameras.get(camera_id)

            if previous is not None:
                self._detach_locked(previous)

            stored = deepcopy(camera)
            self._cameras[stored.id] = stored
            self._attach_locked(stored)
            return deepcopy(stored)

    def get(self, camera_id: str) -> Camera | None:

        with self._lock:
            camera = self._cameras.get(str(camera_id).strip())
            return deepcopy(camera) if camera else None

    def remove(self, camera_id: str) -> None:

        with self._lock:
            camera = self._cameras.pop(str(camera_id).strip(), None)

            if camera is None:
                return

            self._detach_locked(camera)

    def all(self) -> list[Camera]:

        with self._lock:
            return deepcopy(list(self._cameras.values()))

    def enabled(self) -> list[Camera]:

        with self._lock:
            return deepcopy([
                camera
                for camera in self._cameras.values()
                if camera.enabled
            ])

    def by_country(self, country: str) -> list[Camera]:

        with self._lock:
            camera_ids = self._by_country.get(str(country).strip().upper(), set())
            return deepcopy([
                self._cameras[camera_id]
                for camera_id in camera_ids
                if camera_id in self._cameras
            ])

    def by_observation(self, observation_point_id: str) -> list[Camera]:

        normalized = str(observation_point_id).strip()

        with self._lock:
            camera_ids = self._by_observation.get(normalized, set())
            return deepcopy([
                self._cameras[camera_id]
                for camera_id in camera_ids
                if camera_id in self._cameras
            ])

    def countries(self) -> list[str]:

        with self._lock:
            return sorted(self._by_country.keys())

    def count(self) -> int:

        with self._lock:
            return len(self._cameras)

    def count_by_country(self, country: str) -> int:

        with self._lock:
            return len(self._by_country.get(str(country).strip().upper(), set()))

    def exists(self, camera_id: str) -> bool:

        with self._lock:
            return str(camera_id).strip() in self._cameras

    def clear(self) -> None:

        with self._lock:
            self._cameras.clear()
            self._by_country.clear()
            self._by_observation.clear()

    def replace_all(self, cameras: list[Camera]) -> None:

        with self._lock:
            self._cameras.clear()
            self._by_country.clear()
            self._by_observation.clear()

            for camera in cameras:
                stored = deepcopy(camera)
                self._cameras[stored.id] = stored
                self._attach_locked(stored)

    def _attach_locked(self, camera: Camera) -> None:

        country = str(camera.country or "").strip().upper()
        if country:
            camera.country = country
            self._by_country.setdefault(country, set()).add(camera.id)

        point_id = str(camera.observation_point_id or "").strip()
        if point_id:
            self._by_observation.setdefault(point_id, set()).add(camera.id)

    def _detach_locked(self, camera: Camera) -> None:

        country = str(camera.country or "").strip().upper()
        country_set = self._by_country.get(country)
        if country_set is not None:
            country_set.discard(camera.id)
            if not country_set:
                del self._by_country[country]

        point_id = str(camera.observation_point_id or "").strip()
        point_set = self._by_observation.get(point_id)
        if point_set is not None:
            point_set.discard(camera.id)
            if not point_set:
                del self._by_observation[point_id]


camera_registry = CameraRegistry()
