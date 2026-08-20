"""Catalog playback validation statuses and records.

A camera is VALIDATED only when Hunter found a live source AND Project X
playback actually started (HlsPlayer.has_video). Finding an .m3u8 or HTTP 200
is not enough.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


class ValidationStatus(str, Enum):
    VALIDATED = "VALIDATED"
    FAILED = "FAILED"
    NO_STREAM_FOUND = "NO_STREAM_FOUND"
    PLAYBACK_FAILED = "PLAYBACK_FAILED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


def _utc_now() -> str:

    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProbeOutcome:
    """Result of one Hunter discover + playback attempt. No network here."""

    discovered: bool = False
    playback_ok: bool = False
    timed_out: bool = False
    error: str = ""
    stream_url: str = ""
    source_type: str = ""
    source_page: str = ""


_NO_STREAM_HINTS = (
    "without a live camera",
    "no stream",
    "empty",
    "üres",
    "not found",
)


def classify_outcome(outcome: ProbeOutcome) -> ValidationStatus:
    """Map a probe into a terminal status. VALIDATED requires playback proof."""

    if outcome.timed_out:
        return ValidationStatus.TIMEOUT
    if outcome.discovered:
        if outcome.playback_ok:
            return ValidationStatus.VALIDATED
        return ValidationStatus.PLAYBACK_FAILED
    err = (outcome.error or "").strip()
    if not err:
        return ValidationStatus.NO_STREAM_FOUND
    lower = err.lower()
    if "timeout" in lower or "időtúllépés" in lower:
        return ValidationStatus.TIMEOUT
    if any(hint in lower for hint in _NO_STREAM_HINTS):
        return ValidationStatus.NO_STREAM_FOUND
    return ValidationStatus.ERROR


@dataclass
class ValidationRecord:
    camera_id: str
    name: str = ""
    lat: float = 0.0
    lon: float = 0.0
    source: str = ""
    web_url: str = ""
    country: str = ""
    location: str = ""
    city: str = ""
    status: ValidationStatus = ValidationStatus.ERROR
    discovery_result: str = ""
    stream_url: str = ""
    source_type: str = ""
    playback_ok: bool = False
    error: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:

        return {
            "camera_id": self.camera_id,
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "source": self.source,
            "web_url": self.web_url,
            "country": self.country,
            "location": self.location,
            "city": self.city,
            "status": self.status.value,
            "discovery_result": self.discovery_result,
            "stream_url": self.stream_url,
            "source_type": self.source_type,
            "playback_ok": self.playback_ok,
            "error": self.error,
            "timestamp": self.timestamp or _utc_now(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ValidationRecord:

        status_raw = str(data.get("status") or ValidationStatus.ERROR.value)
        try:
            status = ValidationStatus(status_raw)
        except ValueError:
            status = ValidationStatus.ERROR
        return cls(
            camera_id=str(data.get("camera_id") or ""),
            name=str(data.get("name") or ""),
            lat=float(data.get("lat") or 0.0),
            lon=float(data.get("lon") or 0.0),
            source=str(data.get("source") or ""),
            web_url=str(data.get("web_url") or ""),
            country=str(data.get("country") or ""),
            location=str(data.get("location") or ""),
            city=str(data.get("city") or ""),
            status=status,
            discovery_result=str(data.get("discovery_result") or ""),
            stream_url=str(data.get("stream_url") or ""),
            source_type=str(data.get("source_type") or ""),
            playback_ok=bool(data.get("playback_ok")),
            error=str(data.get("error") or ""),
            timestamp=str(data.get("timestamp") or ""),
        )


def record_from_camera(camera: object, outcome: ProbeOutcome) -> ValidationRecord:
    """Build a persisted record from a listing camera + probe outcome."""

    status = classify_outcome(outcome)
    camera_id = str(
        getattr(camera, "key", None) or getattr(camera, "id", "") or ""
    ).strip()
    web_url = str(getattr(camera, "web_url", "") or "").strip()
    return ValidationRecord(
        camera_id=camera_id,
        name=str(getattr(camera, "name", "") or "").strip(),
        lat=float(getattr(camera, "lat", 0.0) or 0.0),
        lon=float(getattr(camera, "lon", 0.0) or 0.0),
        source=str(getattr(camera, "source", "") or "").strip(),
        web_url=web_url,
        country=str(getattr(camera, "country", "") or "").strip(),
        location=str(getattr(camera, "location", "") or "").strip(),
        city=str(getattr(camera, "city", "") or "").strip(),
        status=status,
        discovery_result="found" if outcome.discovered else "none",
        stream_url=outcome.stream_url,
        source_type=outcome.source_type,
        playback_ok=bool(outcome.playback_ok),
        error=outcome.error,
        timestamp=_utc_now(),
    )


@dataclass
class ValidationSummary:
    total: int = 0
    processed: int = 0
    validated: int = 0
    failed: int = 0
    no_stream_found: int = 0
    playback_failed: int = 0
    timeout: int = 0
    error: int = 0
    pending: int = 0
    counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:

        return {
            "total": self.total,
            "processed": self.processed,
            "validated": self.validated,
            "failed": self.failed,
            "no_stream_found": self.no_stream_found,
            "playback_failed": self.playback_failed,
            "timeout": self.timeout,
            "error": self.error,
            "pending": self.pending,
            "counts": dict(self.counts),
        }
