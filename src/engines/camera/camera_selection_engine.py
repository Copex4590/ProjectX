# ============================================================================
# Project X
# Camera Selection Engine
# ============================================================================

from cameras.manager import CameraManager, camera_manager
from engines.camera.camera_match import CameraMatch, build_camera_match
from models.ship import Ship


class CameraSelectionEngine:

    def __init__(self, manager: CameraManager | None = None):

        self._manager = manager or camera_manager

    def get_matching_cameras(self, ship: Ship) -> list[CameraMatch]:

        matches = []
        seen_ids: set[str] = set()

        for camera in self._manager.enabled():

            if camera.id in seen_ids:
                continue

            if not camera.can_observe(ship.lat, ship.lon):
                continue

            seen_ids.add(camera.id)
            matches.append(build_camera_match(camera, ship.lat, ship.lon))

        matches.sort(
            key=lambda match: (
                -match.confidence,
                match.distance_km,
                match.bearing_difference_deg,
                match.camera.id,
            )
        )

        return matches

    def get_best_camera(self, ship: Ship) -> CameraMatch | None:

        matches = self.get_matching_cameras(ship)

        if not matches:
            return None

        return matches[0]


camera_selection_engine = CameraSelectionEngine()
