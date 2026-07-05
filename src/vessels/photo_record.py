# ============================================================================
# Project X
# Vessel Photo Record
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PhotoRecord:

    mmsi: int

    imo: str = ""
    source: str = ""
    local_file: str = ""
    remote_url: str = ""
    thumbnail: str = ""
    copyright: str = ""
    photographer: str = ""

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def normalized_mmsi(self) -> int:

        return int(self.mmsi)

    def safe_text(self, value: str | None) -> str:

        if value is None:
            return ""

        return str(value).strip()

    @classmethod
    def from_row(cls, row) -> "PhotoRecord":

        return cls(
            mmsi=int(row["mmsi"]),
            imo=str(row["imo"] or ""),
            source=str(row["source"] or ""),
            local_file=str(row["local_file"] or ""),
            remote_url=str(row["remote_url"] or ""),
            thumbnail=str(row["thumbnail"] or ""),
            copyright=str(row["copyright"] or ""),
            photographer=str(row["photographer"] or ""),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
