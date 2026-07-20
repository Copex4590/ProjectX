from vessels.photo_manager import PhotoManager
from vessels.photo_provider import (
    PhotoProvider,
    PhotoProviderRegistry,
    PhotoProviderStatus,
    photo_provider_registry,
)
from vessels.photo_record import PhotoRecord
from vessels.photo_registry import PhotoRegistry
from storage.lazy_singleton import lazy_submodule_export

__all__ = [
    "PhotoManager",
    "PhotoProvider",
    "PhotoProviderRegistry",
    "PhotoProviderStatus",
    "PhotoRecord",
    "PhotoRegistry",
    "VESSEL_PHOTOS_DIR",
    "photo_manager",
    "photo_provider_registry",
    "photo_registry",
]


def __getattr__(name: str):
    if name == "photo_registry":
        return lazy_submodule_export(__name__, name)
    if name == "photo_manager":
        return lazy_submodule_export(__name__, name)
    if name == "VESSEL_PHOTOS_DIR":
        from vessels.photo_registry import vessel_photos_dir

        return vessel_photos_dir()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
