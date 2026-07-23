# ============================================================================
# Project X
# Camera Coverage Model (SAVE-217)
# ============================================================================

from __future__ import annotations

import math
from dataclasses import dataclass

from engines.camera.link_states import CameraLinkState
from models.camera import Camera


@dataclass(frozen=True)
class CoverageSector:
    """Map-ready FOV coverage sector for one camera."""

    camera_id: str
    name: str
    lat: float
    lon: float
    direction_deg: float
    fov_deg: float
    radius_km: float
    state: str
    polygon: list[list[float]]  # [[lat, lon], ...]

    def to_map_dict(self) -> dict:

        return {
            "id": self.camera_id,
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "direction_deg": self.direction_deg,
            "fov_deg": self.fov_deg,
            "radius_km": self.radius_km,
            "state": self.state,
            "polygon": self.polygon,
        }


def _destination_point(
    lat: float,
    lon: float,
    bearing_deg: float,
    distance_km: float,
) -> tuple[float, float]:
    """Forward geodesic approximation (spherical Earth)."""

    radius = 6371.0
    angular = distance_km / radius
    bearing = math.radians(bearing_deg)
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)

    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular)
        + math.cos(lat1) * math.sin(angular) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular) * math.cos(lat1),
        math.cos(angular) - math.sin(lat1) * math.sin(lat2),
    )

    return math.degrees(lat2), (math.degrees(lon2) + 540.0) % 360.0 - 180.0


class CameraCoverageModel:
    """Build FOV coverage polygons for map overlays."""

    def __init__(self, *, arc_steps: int = 24):

        self._arc_steps = max(6, int(arc_steps))

    def sector_for_camera(
        self,
        camera: Camera,
        *,
        state: CameraLinkState | str = CameraLinkState.ONLINE,
    ) -> CoverageSector | None:

        radius = float(camera.visibility_radius_km or 0.0)
        fov = float(camera.fov_deg or 0.0)

        if radius <= 0.0 or fov <= 0.0:
            return None

        state_value = state.value if isinstance(state, CameraLinkState) else str(state)
        half = fov / 2.0
        start = (camera.direction_deg - half) % 360.0
        end = (camera.direction_deg + half) % 360.0

        # Sweep clockwise from start → end spanning `fov` degrees.
        polygon: list[list[float]] = [[camera.lat, camera.lon]]
        for step in range(self._arc_steps + 1):
            fraction = step / self._arc_steps
            bearing = (start + fov * fraction) % 360.0
            lat, lon = _destination_point(camera.lat, camera.lon, bearing, radius)
            polygon.append([round(lat, 6), round(lon, 6)])
        polygon.append([camera.lat, camera.lon])

        return CoverageSector(
            camera_id=camera.id,
            name=camera.name,
            lat=camera.lat,
            lon=camera.lon,
            direction_deg=camera.direction_deg,
            fov_deg=fov,
            radius_km=radius,
            state=state_value,
            polygon=polygon,
        )

    def sectors_for_cameras(
        self,
        cameras: list[Camera],
        *,
        states: dict[str, CameraLinkState | str] | None = None,
    ) -> list[CoverageSector]:

        states = states or {}
        sectors: list[CoverageSector] = []
        for camera in cameras:
            if not camera.enabled:
                continue
            sector = self.sector_for_camera(
                camera,
                state=states.get(camera.id, CameraLinkState.ONLINE),
            )
            if sector is not None:
                sectors.append(sector)
        return sectors


camera_coverage_model = CameraCoverageModel()
