# ============================================================================
# Project X
# Camera Manager
# ============================================================================

from pathlib import Path

from cameras.loader import CameraLoader
from database.camera_registry import CameraRegistry, camera_registry
from models.camera import Camera


class CameraManager:

    def __init__(
        self,
        registry: CameraRegistry | None = None,
        config_dir: Path | None = None,
    ):

        self.registry = registry or camera_registry
        self.loader = CameraLoader(config_dir)

    def load(self) -> int:

        return self.loader.load_into(self.registry)

    def reload(self) -> int:

        self.registry.clear()
        return self.load()

    def get(self, camera_id: str) -> Camera | None:

        return self.registry.get(camera_id)

    def all(self) -> list[Camera]:

        return self.registry.all()

    def enabled(self) -> list[Camera]:

        return self.registry.enabled()

    def by_country(self, country: str) -> list[Camera]:

        return self.registry.by_country(country)

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


camera_manager = CameraManager()
