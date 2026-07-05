# ============================================================================
# Project X
# MarineTraffic Vessel Photo Provider (Stub)
# ============================================================================

from vessels.photo_record import PhotoRecord
from vessels.providers.base_provider import VesselPhotoProvider


class MarineTrafficProvider(VesselPhotoProvider):

    def name(self) -> str:

        return "marinetraffic"

    def supports(self, record: PhotoRecord) -> bool:

        return bool(record.safe_text(record.imo))

    def has_photo(self, record: PhotoRecord) -> bool:

        return False

    def get_photo(self, record: PhotoRecord) -> PhotoRecord | None:

        return None

    def metadata(self, record: PhotoRecord) -> dict:

        return {
            "provider": self.name(),
            "ready": False,
            "status": "stub",
            "network": False,
            "has_photo": False,
            "imo": record.safe_text(record.imo),
            "message": "MarineTraffic provider is not enabled",
        }
