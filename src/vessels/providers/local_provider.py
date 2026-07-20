# ============================================================================
# Project X
# Local Vessel Photo Provider
# ============================================================================

from pathlib import Path

from vessels.photo_record import PhotoRecord
from vessels.photo_registry import PhotoRegistry, get_photo_registry, vessel_photos_dir
from vessels.providers.base_provider import VesselPhotoProvider


def _normalize_mmsi(mmsi: int | str | None) -> int | None:

    if mmsi is None:
        return None

    try:
        normalized = int(mmsi)
    except (TypeError, ValueError):
        return None

    if normalized <= 0:
        return None

    return normalized


class LocalProvider(VesselPhotoProvider):

    def __init__(
        self,
        registry: PhotoRegistry | None = None,
        storage_dir: Path | str | None = None,
    ):

        self._registry = registry or get_photo_registry()
        self._storage_dir = Path(storage_dir or vessel_photos_dir())

    def name(self) -> str:

        return "local"

    def supports(self, record: PhotoRecord) -> bool:

        return _normalize_mmsi(record.mmsi) is not None

    def has_photo(self, record: PhotoRecord) -> bool:

        stored = self._resolve_record(record)

        if stored is None:
            return False

        if stored.local_file:
            return self._resolve_storage_path(stored.local_file) is not None

        if stored.thumbnail:
            return self._resolve_storage_path(stored.thumbnail) is not None

        return True

    def get_photo(self, record: PhotoRecord) -> PhotoRecord | None:

        if not self.has_photo(record):
            return None

        return self._resolve_record(record)

    def metadata(self, record: PhotoRecord) -> dict:

        stored = self._resolve_record(record)
        local_path = ""
        thumbnail_path = ""

        if stored is not None:
            local_path = self._storage_path_text(stored.local_file)
            thumbnail_path = self._storage_path_text(stored.thumbnail)

        return {
            "provider": self.name(),
            "ready": True,
            "network": False,
            "has_photo": self.has_photo(record),
            "storage_dir": str(self._storage_dir),
            "local_file": local_path,
            "thumbnail": thumbnail_path,
            "source": stored.source if stored is not None else "",
        }

    def _resolve_record(self, record: PhotoRecord) -> PhotoRecord | None:

        normalized_mmsi = _normalize_mmsi(record.mmsi)

        if normalized_mmsi is None:
            return None

        return self._registry.get(normalized_mmsi)

    def _resolve_storage_path(self, value: str | None) -> Path | None:

        text = str(value or "").strip()

        if not text:
            return None

        path = Path(text)

        if not path.is_absolute():
            path = self._storage_dir / path

        if path.exists() and path.is_file():
            return path

        return None

    def _storage_path_text(self, value: str | None) -> str:

        path = self._resolve_storage_path(value)

        if path is None:
            return ""

        return str(path)
