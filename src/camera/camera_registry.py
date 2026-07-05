# ============================================================================
# Project X
# Camera Registry
# ============================================================================

from __future__ import annotations

from copy import deepcopy
from threading import Lock

from camera.camera import Camera


class CameraRegistry:

    def __init__(self):

        self._lock = Lock()
        self._cameras: dict[str, Camera] = {}
        self._by_observation: dict[str, set[str]] = {}

    def add(self, camera: Camera) -> Camera:

        with self._lock:
            previous = self._cameras.get(camera.id)

            if previous is not None:
                self._detach(previous)

            stored = deepcopy(camera)
            self._cameras[stored.id] = stored
            self._attach(stored)
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

            self._detach(camera)

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

    def by_observation(self, observation_point_id: str) -> list[Camera]:

        normalized = str(observation_point_id).strip()

        with self._lock:
            camera_ids = self._by_observation.get(normalized, set())
            return deepcopy([
                self._cameras[camera_id]
                for camera_id in camera_ids
                if camera_id in self._cameras
            ])

    def replace_all(self, cameras: list[Camera]) -> None:

        with self._lock:
            self._cameras.clear()
            self._by_observation.clear()

            for camera in cameras:
                stored = deepcopy(camera)
                self._cameras[stored.id] = stored
                self._attach(stored)

    def _attach(self, camera: Camera) -> None:

        point_id = str(camera.observation_point_id).strip()

        if not point_id:
            return

        self._by_observation.setdefault(point_id, set()).add(camera.id)

    def _detach(self, camera: Camera) -> None:

        point_id = str(camera.observation_point_id).strip()
        point_set = self._by_observation.get(point_id)

        if point_set is None:
            return

        point_set.discard(camera.id)

        if not point_set:
            del self._by_observation[point_id]
