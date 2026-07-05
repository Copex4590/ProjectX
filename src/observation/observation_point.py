# ============================================================================
# Project X
# Observation Point Model
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


def _utc_now() -> datetime:

    return datetime.now(timezone.utc)


@dataclass
class ObservationPoint:

    name: str
    latitude: float
    longitude: float
    id: str = field(default_factory=lambda: uuid4().hex)
    elevation: float | None = None
    description: str = ""
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    active: bool = False

    def to_dict(self) -> dict:

        return {
            "id": self.id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "elevation": self.elevation,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ObservationPoint:

        created_at = _parse_datetime(data.get("created_at"))
        updated_at = _parse_datetime(data.get("updated_at"))

        elevation = data.get("elevation")
        parsed_elevation = None

        if elevation is not None and str(elevation).strip() != "":
            parsed_elevation = float(elevation)

        return cls(
            id=str(data.get("id") or uuid4().hex),
            name=str(data.get("name") or "").strip() or "Observation Point",
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            elevation=parsed_elevation,
            description=str(data.get("description") or "").strip(),
            created_at=created_at,
            updated_at=updated_at,
            active=bool(data.get("active", False)),
        )


def _parse_datetime(value) -> datetime:

    if isinstance(value, datetime):
        return value

    text = str(value or "").strip()

    if not text:
        return _utc_now()

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return _utc_now()

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed
