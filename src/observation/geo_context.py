# ============================================================================
# Project X
# GeoContext — geographic single source of truth
# ============================================================================

from __future__ import annotations

import math

from observation.observation_point import ObservationPoint

EARTH_RADIUS_KM = 6371.0
_KM_PER_DEGREE_LAT = 111.0


def _observation_manager():
    from observation.observation_manager import get_observation_manager

    return get_observation_manager()


def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )

    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def initial_bearing_deg(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)

    x = math.sin(dlon) * math.cos(lat2_rad)
    y = (
        math.cos(lat1_rad) * math.sin(lat2_rad)
        - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
    )

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360.0) % 360.0


class GeoContext:
    """Single API for geographic values derived from the reference observation point."""

    def reference(self) -> ObservationPoint | None:

        return _observation_manager().reference()

    def coordinates(self) -> tuple[float, float] | None:

        return _observation_manager().reference_coordinates()

    def radius_km(self) -> float | None:

        point = self.reference()

        if point is None:
            return None

        return point.coverage_radius_km

    def has_reference(self) -> bool:

        return self.reference() is not None

    def distance_km(
        self,
        latitude: float,
        longitude: float,
        *,
        origin_lat: float | None = None,
        origin_lon: float | None = None,
    ) -> float | None:

        if origin_lat is None or origin_lon is None:
            coords = self.coordinates()

            if coords is None:
                return None

            origin_lat, origin_lon = coords

        return haversine_distance_km(
            origin_lat,
            origin_lon,
            latitude,
            longitude,
        )

    def bearing_deg(
        self,
        latitude: float,
        longitude: float,
        *,
        origin_lat: float | None = None,
        origin_lon: float | None = None,
    ) -> float | None:

        if origin_lat is None or origin_lon is None:
            coords = self.coordinates()

            if coords is None:
                return None

            origin_lat, origin_lon = coords

        return initial_bearing_deg(
            origin_lat,
            origin_lon,
            latitude,
            longitude,
        )

    def is_within_coverage(
        self,
        latitude: float | None,
        longitude: float | None,
    ) -> bool:

        point = self.reference()

        if point is None or latitude is None or longitude is None:
            return False

        distance_km = self.distance_km(latitude, longitude)

        if distance_km is None:
            return False

        return distance_km <= point.coverage_radius_km

    def coverage_bounding_box(
        self,
        latitude: float,
        longitude: float,
        coverage_radius_km: float,
    ) -> list[list[float]]:

        if coverage_radius_km <= 0:
            raise ValueError("coverage_radius_km must be positive")

        lat_delta = coverage_radius_km / _KM_PER_DEGREE_LAT
        cos_lat = math.cos(math.radians(latitude))

        if abs(cos_lat) < 1e-6:
            cos_lat = 1e-6

        lon_delta = coverage_radius_km / (_KM_PER_DEGREE_LAT * abs(cos_lat))

        lat_min = max(-90.0, latitude - lat_delta)
        lat_max = min(90.0, latitude + lat_delta)
        lon_min = max(-180.0, longitude - lon_delta)
        lon_max = min(180.0, longitude + lon_delta)

        return [[lat_min, lon_min], [lat_max, lon_max]]

    def ais_bounding_box(self) -> list[list[float]] | None:

        point = self.reference()

        if point is None:
            return None

        return self.coverage_bounding_box(
            point.latitude,
            point.longitude,
            point.coverage_radius_km,
        )

    def ais_bounding_boxes(self) -> list[list[list[float]]] | None:

        box = self.ais_bounding_box()

        if box is None:
            return None

        return [box]

    def ship_observation_fields(
        self,
        latitude: float | None,
        longitude: float | None,
    ) -> dict[str, float | None]:

        if latitude is None or longitude is None:
            return {
                "distance_km": None,
                "reference_bearing_deg": None,
            }

        distance = self.distance_km(latitude, longitude)
        bearing = self.bearing_deg(latitude, longitude)

        return {
            "distance_km": round(distance, 2) if distance is not None else None,
            "reference_bearing_deg": bearing,
        }

    @property
    def changed(self):

        return _observation_manager().changed


geo_context = GeoContext()
