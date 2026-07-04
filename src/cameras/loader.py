# ============================================================================
# Project X
# Camera Loader
# ============================================================================

import json
from pathlib import Path

from config.cameras import CAMERAS_CONFIG_DIR, CAMERAS_INDEX_FILE
from database.camera_registry import CameraRegistry
from models.camera import Camera


class CameraLoadError(Exception):

    pass


class CameraLoader:

    def __init__(self, config_dir: Path | None = None):

        self.config_dir = Path(config_dir or CAMERAS_CONFIG_DIR)
        self.index_file = self.config_dir / "index.json"

    def load_into(self, registry: CameraRegistry) -> int:

        index = self._load_index()
        cameras = []

        for country_entry in index.get("countries", []):
            cameras.extend(self._load_country_file(country_entry))

        registry.replace_all(cameras)
        return len(cameras)

    def load_country(self, country_code: str) -> list[Camera]:

        index = self._load_index()

        for country_entry in index.get("countries", []):
            if country_entry.get("code", "").upper() == country_code.upper():
                return self._load_country_file(country_entry)

        raise CameraLoadError(
            f"Country not found in camera index: {country_code}"
        )

    def _load_index(self) -> dict:

        if not self.index_file.exists():
            raise CameraLoadError(
                f"Camera index file not found: {self.index_file}"
            )

        with self.index_file.open(encoding="utf-8") as handle:
            data = json.load(handle)

        if not isinstance(data, dict):
            raise CameraLoadError("Camera index must be a JSON object")

        return data

    def _load_country_file(self, country_entry: dict) -> list[Camera]:

        country_code = country_entry.get("code", "").strip().upper()
        filename = country_entry.get("file", "").strip()

        if not country_code:
            raise CameraLoadError("Country entry is missing 'code'")

        if not filename:
            raise CameraLoadError(
                f"Country entry '{country_code}' is missing 'file'"
            )

        country_path = self.config_dir / filename

        if not country_path.exists():
            raise CameraLoadError(
                f"Camera config file not found for {country_code}: {country_path}"
            )

        with country_path.open(encoding="utf-8") as handle:
            data = json.load(handle)

        if not isinstance(data, dict):
            raise CameraLoadError(
                f"Camera config must be a JSON object: {country_path}"
            )

        file_country = data.get("country", country_code).strip().upper()
        cameras = []

        for index, entry in enumerate(data.get("cameras", []), start=1):
            cameras.append(
                self._parse_camera(
                    entry,
                    country_code=file_country,
                    source=f"{country_path}:{index}",
                )
            )

        return cameras

    def _parse_camera(
        self,
        entry: dict,
        *,
        country_code: str,
        source: str,
    ) -> Camera:

        if not isinstance(entry, dict):
            raise CameraLoadError(
                f"Camera entry must be an object ({source})"
            )

        camera_id = str(entry.get("id", "")).strip()

        if not camera_id:
            raise CameraLoadError(f"Camera id is required ({source})")

        name = str(entry.get("name", "")).strip()

        if not name:
            raise CameraLoadError(
                f"Camera name is required for '{camera_id}' ({source})"
            )

        lat = self._require_float(entry, "lat", camera_id, source)
        lon = self._require_float(entry, "lon", camera_id, source)

        direction_deg = self._optional_float(
            entry,
            "direction_deg",
            fallback_keys=("direction",),
            default=0.0,
        )

        visibility_radius_km = self._optional_float(
            entry,
            "visibility_radius_km",
            fallback_keys=("visibility_radius", "radius_km"),
            default=0.0,
        )

        fov_deg = self._optional_float(
            entry,
            "fov_deg",
            fallback_keys=("fov",),
            default=90.0,
        )

        enabled = bool(entry.get("enabled", True))
        description = str(entry.get("description", "")).strip()

        return Camera(
            id=camera_id,
            name=name,
            country=country_code,
            lat=lat,
            lon=lon,
            direction_deg=direction_deg,
            visibility_radius_km=visibility_radius_km,
            fov_deg=fov_deg,
            enabled=enabled,
            description=description,
        )

    def _require_float(
        self,
        entry: dict,
        key: str,
        camera_id: str,
        source: str,
    ) -> float:

        if key not in entry:
            raise CameraLoadError(
                f"Camera '{camera_id}' is missing '{key}' ({source})"
            )

        try:
            return float(entry[key])
        except (TypeError, ValueError) as error:
            raise CameraLoadError(
                f"Camera '{camera_id}' has invalid '{key}' ({source})"
            ) from error

    def _optional_float(
        self,
        entry: dict,
        key: str,
        *,
        fallback_keys: tuple[str, ...] = (),
        default: float = 0.0,
    ) -> float:

        value = entry.get(key)

        if value is None:
            for fallback_key in fallback_keys:
                value = entry.get(fallback_key)
                if value is not None:
                    break

        if value is None:
            return default

        try:
            return float(value)
        except (TypeError, ValueError) as error:
            raise CameraLoadError(
                f"Invalid numeric value for '{key}'"
            ) from error
