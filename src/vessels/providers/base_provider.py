# ============================================================================
# Project X
# Vessel Photo Provider Base
# ============================================================================

from abc import ABC, abstractmethod

from vessels.photo_record import PhotoRecord


class VesselPhotoProvider(ABC):

    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def supports(self, record: PhotoRecord) -> bool:
        ...

    @abstractmethod
    def has_photo(self, record: PhotoRecord) -> bool:
        ...

    @abstractmethod
    def get_photo(self, record: PhotoRecord) -> PhotoRecord | None:
        ...

    @abstractmethod
    def metadata(self, record: PhotoRecord) -> dict:
        ...
