# ============================================================================
# Project X
# Vessel Timeline Record
# ============================================================================

import json
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TimelineRecord:

    mmsi: int
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: str = ""
    latitude: float | None = None
    longitude: float | None = None
    speed: float | None = None
    course: float | None = None
    heading: float | None = None
    source: str = ""
    metadata: dict = field(default_factory=dict)
    id: int | None = None

    def normalized_mmsi(self) -> int:

        return int(self.mmsi)

    def safe_text(self, value: str | None) -> str:

        if value is None:
            return ""

        return str(value).strip()

    def metadata_json(self) -> str:

        if not self.metadata:
            return "{}"

        return json.dumps(self.metadata, sort_keys=True)

    @classmethod
    def metadata_from_row(cls, value) -> dict:

        text = str(value or "").strip()

        if not text:
            return {}

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return {}

        if isinstance(payload, dict):
            return payload

        return {}

    @classmethod
    def from_row(cls, row) -> "TimelineRecord":

        return cls(
            id=int(row["id"]),
            mmsi=int(row["mmsi"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            event_type=str(row["event_type"] or ""),
            latitude=row["latitude"],
            longitude=row["longitude"],
            speed=row["speed"],
            course=row["course"],
            heading=row["heading"],
            source=str(row["source"] or ""),
            metadata=cls.metadata_from_row(row["metadata"]),
        )
