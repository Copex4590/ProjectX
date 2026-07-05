# ============================================================================
# Project X
# Alert Event Model
# ============================================================================

import json
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AlertEvent:

    rule_id: int
    mmsi: int
    event_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    severity: str = "info"
    message: str = ""
    metadata: dict = field(default_factory=dict)
    id: int | None = None

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
    def from_row(cls, row) -> "AlertEvent":

        return cls(
            id=int(row["id"]),
            rule_id=int(row["rule_id"]),
            mmsi=int(row["mmsi"]),
            event_type=str(row["event_type"] or ""),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            severity=str(row["severity"] or "info"),
            message=str(row["message"] or ""),
            metadata=cls.metadata_from_row(row["metadata"]),
        )


@dataclass
class EvaluationEvent:

    mmsi: int
    event_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    speed: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    camera_visible: bool | None = None
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload) -> "EvaluationEvent | None":

        if isinstance(payload, EvaluationEvent):
            return payload

        if not isinstance(payload, dict):
            return None

        mmsi = payload.get("mmsi")

        try:
            normalized_mmsi = int(mmsi)
        except (TypeError, ValueError):
            return None

        if normalized_mmsi <= 0:
            return None

        event_type = str(payload.get("event_type") or "").strip().upper()

        if not event_type:
            return None

        timestamp = payload.get("timestamp")

        if isinstance(timestamp, datetime):
            parsed_timestamp = timestamp
        elif timestamp:
            try:
                parsed_timestamp = datetime.fromisoformat(str(timestamp))
            except ValueError:
                parsed_timestamp = datetime.now()
        else:
            parsed_timestamp = datetime.now()

        speed = payload.get("speed")
        latitude = payload.get("latitude", payload.get("lat"))
        longitude = payload.get("longitude", payload.get("lon"))
        camera_visible = payload.get("camera_visible")
        metadata = payload.get("metadata") or {}

        if not isinstance(metadata, dict):
            metadata = {}

        return cls(
            mmsi=normalized_mmsi,
            event_type=event_type,
            timestamp=parsed_timestamp.replace(microsecond=0),
            speed=float(speed) if speed is not None else None,
            latitude=float(latitude) if latitude is not None else None,
            longitude=float(longitude) if longitude is not None else None,
            camera_visible=(
                bool(camera_visible)
                if camera_visible is not None
                else None
            ),
            metadata=metadata,
        )
