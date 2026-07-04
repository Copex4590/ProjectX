# ============================================================================
# Project X
# Camera Registry
# ============================================================================

from threading import Lock

from models.camera import Camera


class CameraRegistry:

    def __init__(self):

        self._cameras: dict[str, Camera] = {}
        self._by_country: dict[str, set[str]] = {}
        self._lock = Lock()

    def add(self, camera: Camera):

        with self._lock:

            camera_id = camera.id
            previous = self._cameras.get(camera_id)

            if previous is not None:
                self._by_country[previous.country].discard(camera_id)

                if not self._by_country[previous.country]:
                    del self._by_country[previous.country]

            self._cameras[camera_id] = camera
            self._by_country.setdefault(camera.country, set()).add(camera_id)

    def get(self, camera_id: str):

        with self._lock:
            return self._cameras.get(camera_id)

    def remove(self, camera_id: str):

        with self._lock:

            camera = self._cameras.pop(camera_id, None)

            if camera is None:
                return

            country_set = self._by_country.get(camera.country)

            if country_set is not None:
                country_set.discard(camera_id)

                if not country_set:
                    del self._by_country[camera.country]

    def all(self):

        with self._lock:
            return list(self._cameras.values())

    def enabled(self):

        with self._lock:
            return [
                camera
                for camera in self._cameras.values()
                if camera.enabled
            ]

    def by_country(self, country: str):

        with self._lock:

            camera_ids = self._by_country.get(country.upper(), set())

            return [
                self._cameras[camera_id]
                for camera_id in camera_ids
                if camera_id in self._cameras
            ]

    def countries(self):

        with self._lock:
            return sorted(self._by_country.keys())

    def count(self):

        with self._lock:
            return len(self._cameras)

    def count_by_country(self, country: str):

        with self._lock:
            return len(self._by_country.get(country.upper(), set()))

    def exists(self, camera_id: str):

        with self._lock:
            return camera_id in self._cameras

    def clear(self):

        with self._lock:
            self._cameras.clear()
            self._by_country.clear()

    def replace_all(self, cameras: list[Camera]):

        with self._lock:

            self._cameras.clear()
            self._by_country.clear()

            for camera in cameras:
                self._cameras[camera.id] = camera
                self._by_country.setdefault(camera.country, set()).add(camera.id)


camera_registry = CameraRegistry()
