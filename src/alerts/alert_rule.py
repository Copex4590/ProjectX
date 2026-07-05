# ============================================================================
# Project X
# Alert Rule Model
# ============================================================================

import json
from dataclasses import dataclass, field
from datetime import datetime

RULE_TYPE_ARRIVAL = "ARRIVAL"
RULE_TYPE_DEPARTURE = "DEPARTURE"
RULE_TYPE_SPEED_OVER = "SPEED_OVER"
RULE_TYPE_ENTER_REGION = "ENTER_REGION"
RULE_TYPE_EXIT_REGION = "EXIT_REGION"
RULE_TYPE_CAMERA_VISIBLE = "CAMERA_VISIBLE"
RULE_TYPE_CAMERA_LOST = "CAMERA_LOST"

SUPPORTED_RULE_TYPES = (
    RULE_TYPE_ARRIVAL,
    RULE_TYPE_DEPARTURE,
    RULE_TYPE_SPEED_OVER,
    RULE_TYPE_ENTER_REGION,
    RULE_TYPE_EXIT_REGION,
    RULE_TYPE_CAMERA_VISIBLE,
    RULE_TYPE_CAMERA_LOST,
)


@dataclass
class AlertRule:

    name: str
    enabled: bool = True
    priority: int = 0
    event_type: str = ""
    conditions: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    id: int | None = None

    def safe_text(self, value: str | None) -> str:

        if value is None:
            return ""

        return str(value).strip()

    def conditions_json(self) -> str:

        if not self.conditions:
            return "{}"

        return json.dumps(self.conditions, sort_keys=True)

    @classmethod
    def conditions_from_row(cls, value) -> dict:

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
    def from_row(cls, row) -> "AlertRule":

        return cls(
            id=int(row["id"]),
            name=str(row["name"] or ""),
            enabled=bool(row["enabled"]),
            priority=int(row["priority"]),
            event_type=str(row["event_type"] or ""),
            conditions=cls.conditions_from_row(row["conditions"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
