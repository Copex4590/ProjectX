# ============================================================================
# Project X
# Vessel Photo Manager
# ============================================================================

from pathlib import Path

from vessels.photo_provider import (
    PhotoProvider,
    PhotoProviderRegistry,
    photo_provider_registry,
)
from vessels.photo_record import PhotoRecord
from vessels.photo_registry import PhotoRegistry, get_photo_registry, vessel_photos_dir


class PhotoManager:

    def __init__(
        self,
        registry: PhotoRegistry | None = None,
        provider_registry: PhotoProviderRegistry | None = None,
        storage_dir: Path | str | None = None,
    ):

        self._registry = registry or get_photo_registry()
        self._provider_registry = provider_registry or photo_provider_registry
        self._storage_dir = Path(storage_dir or vessel_photos_dir())

    @property
    def storage_dir(self) -> Path:

        return self._storage_dir

    def get_photo(self, mmsi: int | str) -> PhotoRecord | None:

        return self._registry.get(mmsi)

    def has_photo(self, mmsi: int | str) -> bool:

        return self._registry.has(mmsi)

    def get_photo_file(self, mmsi: int | str) -> Path | None:

        if not self.has_photo(mmsi):
            return None

        record = self.get_photo(mmsi)

        if record is None:
            return None

        for field in (record.local_file, record.thumbnail):
            path = self._resolve_storage_path(field)

            if path is not None and path.exists() and path.is_file():
                return path

        return None

    def register_photo(self, record: PhotoRecord) -> PhotoRecord:

        self._ensure_storage_dirs()

        payload = PhotoRecord(
            mmsi=record.mmsi,
            imo=record.safe_text(record.imo),
            source=record.safe_text(record.source),
            local_file=self._normalize_storage_path(record.local_file),
            remote_url=record.safe_text(record.remote_url),
            thumbnail=self._normalize_storage_path(record.thumbnail),
            copyright=record.safe_text(record.copyright),
            photographer=record.safe_text(record.photographer),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

        return self._registry.register(payload)

    def remove_photo(self, mmsi: int | str) -> bool:

        removed = self._registry.remove(mmsi)

        if removed is None:
            return False

        self._delete_storage_file(removed.local_file)
        self._delete_storage_file(removed.thumbnail)

        return True

    def register_provider(
        self,
        provider: PhotoProvider,
        *,
        priority: int = 0,
    ) -> None:

        self._provider_registry.register(provider, priority=priority)

    def unregister_provider(self, provider: PhotoProvider) -> bool:

        return self._provider_registry.unregister(provider)

    def list_providers(self) -> list[PhotoProvider]:

        return self._provider_registry.list_providers()

    def find_provider(
        self,
        mmsi: int,
        imo: str = "",
    ) -> PhotoProvider | None:

        return self._provider_registry.find_provider(mmsi, imo)

    def _ensure_storage_dirs(self) -> None:

        self._storage_dir.mkdir(parents=True, exist_ok=True)
        (self._storage_dir / "images").mkdir(parents=True, exist_ok=True)
        (self._storage_dir / "thumbnails").mkdir(parents=True, exist_ok=True)

    def _normalize_storage_path(self, value: str | None) -> str:

        text = str(value or "").strip()

        if not text:
            return ""

        path = Path(text)

        if path.is_absolute():
            try:
                path.relative_to(self._storage_dir)
            except ValueError:
                return text
            return str(path.relative_to(self._storage_dir))

        return str(Path(text))

    def _resolve_storage_path(self, value: str | None) -> Path | None:

        text = str(value or "").strip()

        if not text:
            return None

        path = Path(text)

        if path.is_absolute():
            return path

        return self._storage_dir / path

    def _delete_storage_file(self, value: str | None) -> None:

        path = self._resolve_storage_path(value)

        if path is None or not path.exists() or not path.is_file():
            return

        try:
            path.relative_to(self._storage_dir)
        except ValueError:
            return

        path.unlink(missing_ok=True)


from storage.lazy_singleton import LazySingleton, lazy_module_getattr


get_photo_manager = LazySingleton(PhotoManager)


def __getattr__(name: str):
    return lazy_module_getattr(
        name,
        module_name=__name__,
        export_name="photo_manager",
        getter=get_photo_manager,
    )
