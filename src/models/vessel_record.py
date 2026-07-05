# ============================================================================
# Project X
# Vessel Record Model
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VesselRecord:

    mmsi: int

    imo: str = ""
    name: str = ""
    callsign: str = ""
    ship_type: str = ""
    flag: str = ""

    length: float | None = None
    width: float | None = None
    draft: float | None = None

    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def normalized_mmsi(self) -> int:

        return int(self.mmsi)

    def safe_text(self, value: str | None) -> str:

        if value is None:
            return ""

        return str(value).strip()

    @classmethod
    def from_row(cls, row) -> "VesselRecord":

        return cls(
            mmsi=int(row["mmsi"]),
            imo=str(row["imo"] or ""),
            name=str(row["name"] or ""),
            callsign=str(row["callsign"] or ""),
            ship_type=str(row["ship_type"] or ""),
            flag=str(row["flag"] or ""),
            length=row["length"],
            width=row["width"],
            draft=row["draft"],
            first_seen=datetime.fromisoformat(row["first_seen"]),
            last_seen=datetime.fromisoformat(row["last_seen"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
