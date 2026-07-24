# ============================================================================
# Project X
# Session Recording models (SAVE-219)
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


SESSION_FILE_EXTENSION = ".pxsession"
SESSION_MANIFEST_NAME = "manifest.json"
SESSION_EVENTS_NAME = "events.jsonl"
SESSION_FORMAT_VERSION = 1

EVENT_SESSION_STATE = "session.state"
EVENT_SESSION_REPLAY_FRAME = "session.replay.frame"
EVENT_SESSION_REPLAY_ALERTS = "session.replay.alerts"


class SessionState(str, Enum):

    IDLE = "idle"
    RECORDING = "recording"
    REPLAYING = "replaying"
    PAUSED = "paused"


RECORDABLE_EVENTS = (
    "ship.updated",
    "ais.status",
    "rtl.status",
    "alerts.fired",
    "alerts.acknowledged",
    "alerts.cleared",
    "camera.link.changed",
    "camera.link.mode",
    "camera.coverage.toggled",
    "vessel.playback.mode",
    "vessel.playback.position",
    "timeline.arrival",
    "timeline.departure",
)

PLAYBACK_RATES = (1, 2, 5, 10)


@dataclass
class RecordedEvent:
    """One timestamped EventBus capture."""

    timestamp: datetime
    name: str
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:

        return {
            "ts": self.timestamp.isoformat(timespec="milliseconds"),
            "name": self.name,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RecordedEvent":

        raw_ts = str(data.get("ts") or "")
        try:
            timestamp = datetime.fromisoformat(raw_ts)
        except ValueError:
            timestamp = datetime.now()
        return cls(
            timestamp=timestamp,
            name=str(data.get("name") or ""),
            payload=dict(data.get("payload") or {}),
        )


@dataclass
class SessionManifest:
    """Metadata stored inside a .pxsession archive."""

    session_id: str
    created_at: datetime
    started_at: datetime
    ended_at: datetime | None = None
    event_count: int = 0
    format_version: int = SESSION_FORMAT_VERSION
    app_version: str = ""
    label: str = ""

    @property
    def duration_seconds(self) -> float:

        end = self.ended_at or self.started_at
        return max(0.0, (end - self.started_at).total_seconds())

    def to_dict(self) -> dict:

        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(timespec="seconds"),
            "started_at": self.started_at.isoformat(timespec="seconds"),
            "ended_at": (
                self.ended_at.isoformat(timespec="seconds")
                if self.ended_at
                else None
            ),
            "duration_seconds": round(self.duration_seconds, 3),
            "event_count": self.event_count,
            "format_version": self.format_version,
            "app_version": self.app_version,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionManifest":

        def _parse(value: object) -> datetime | None:
            text = str(value or "").strip()
            if not text:
                return None
            try:
                return datetime.fromisoformat(text)
            except ValueError:
                return None

        created = _parse(data.get("created_at")) or datetime.now()
        started = _parse(data.get("started_at")) or created
        ended = _parse(data.get("ended_at"))
        return cls(
            session_id=str(data.get("session_id") or ""),
            created_at=created,
            started_at=started,
            ended_at=ended,
            event_count=int(data.get("event_count") or 0),
            format_version=int(
                data.get("format_version") or SESSION_FORMAT_VERSION
            ),
            app_version=str(data.get("app_version") or ""),
            label=str(data.get("label") or ""),
        )


@dataclass(frozen=True)
class SessionEntry:
    """Listed session file on disk."""

    path: Path
    manifest: SessionManifest
    size_bytes: int

    @property
    def session_id(self) -> str:

        return self.manifest.session_id

    @property
    def label(self) -> str:

        return self.manifest.label or self.path.stem
