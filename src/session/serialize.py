# ============================================================================
# Project X
# Session payload serialization (SAVE-219)
# ============================================================================

from __future__ import annotations

from datetime import datetime
from typing import Any


def _iso(value: datetime | None) -> str | None:

    if value is None:
        return None
    return value.isoformat(timespec="milliseconds")


def serialize_ship(ship: Any) -> dict:
    """Slim ship snapshot suitable for JSON."""

    if ship is None:
        return {}
    return {
        "mmsi": int(getattr(ship, "mmsi", 0) or 0),
        "name": str(getattr(ship, "name", "") or ""),
        "callsign": str(getattr(ship, "callsign", "") or ""),
        "ship_type": str(getattr(ship, "ship_type", "") or ""),
        "lat": float(getattr(ship, "lat", 0.0) or 0.0),
        "lon": float(getattr(ship, "lon", 0.0) or 0.0),
        "speed": float(getattr(ship, "speed", 0.0) or 0.0),
        "course": float(getattr(ship, "course", 0.0) or 0.0),
        "heading": float(getattr(ship, "heading", 0.0) or 0.0),
        "destination": str(getattr(ship, "destination", "") or ""),
        "eta": str(getattr(ship, "eta", "") or ""),
        "source": str(getattr(ship, "source", "") or ""),
        "distance_km": float(getattr(ship, "distance_km", 0.0) or 0.0),
        "direction": str(getattr(ship, "direction", "") or ""),
        "text_heading": str(getattr(ship, "text_heading", "") or ""),
        "ais_visible": bool(getattr(ship, "ais_visible", False)),
        "rtl_visible": bool(getattr(ship, "rtl_visible", False)),
        "camera_visible": bool(getattr(ship, "camera_visible", False)),
        "last_seen": _iso(getattr(ship, "last_seen", None)),
    }


def serialize_alert_event(event: Any) -> dict:

    if event is None:
        return {}
    return {
        "id": getattr(event, "id", None),
        "rule_id": int(getattr(event, "rule_id", 0) or 0),
        "mmsi": int(getattr(event, "mmsi", 0) or 0),
        "event_type": str(getattr(event, "event_type", "") or ""),
        "timestamp": _iso(getattr(event, "timestamp", None)),
        "severity": str(getattr(event, "severity", "info") or "info"),
        "message": str(getattr(event, "message", "") or ""),
        "metadata": dict(getattr(event, "metadata", {}) or {}),
        "acknowledged": bool(getattr(event, "acknowledged", False)),
        "acknowledged_at": _iso(getattr(event, "acknowledged_at", None)),
    }


def serialize_camera_link_snapshot(snapshot: Any) -> dict:

    if snapshot is None:
        return {}

    def _scored(item: Any) -> dict | None:
        if item is None:
            return None
        camera = getattr(getattr(item, "match", None), "camera", None) or getattr(
            item, "camera", None
        )
        return {
            "camera_id": str(getattr(camera, "id", "") or ""),
            "camera_name": str(getattr(camera, "name", "") or ""),
            "camera_lat": float(getattr(camera, "lat", 0.0) or 0.0),
            "camera_lon": float(getattr(camera, "lon", 0.0) or 0.0),
            "score": float(getattr(item, "score", 0.0) or 0.0),
            "state": str(getattr(getattr(item, "state", None), "value", getattr(item, "state", ""))),
            "in_fov": bool(getattr(item, "in_fov", False)),
            "distance_km": float(
                getattr(getattr(item, "match", None), "distance_km", 0.0) or 0.0
            ),
            "explanation": "",
        }

    active = _scored(getattr(snapshot, "active", None))
    if active is not None:
        active["explanation"] = str(getattr(snapshot, "explanation", "") or "")

    alternatives = []
    for item in list(getattr(snapshot, "alternatives", []) or []):
        scored = _scored(item)
        if scored is not None:
            alternatives.append(scored)

    mode = getattr(snapshot, "mode", None)
    mode_value = getattr(mode, "value", mode)
    return {
        "mmsi": getattr(snapshot, "mmsi", None),
        "mode": str(mode_value or "Auto"),
        "active": active,
        "alternatives": alternatives,
        "explanation": str(getattr(snapshot, "explanation", "") or ""),
        "coverage_visible": bool(getattr(snapshot, "coverage_visible", False)),
        "switched": bool(getattr(snapshot, "switched", False)),
        "reason": str(getattr(snapshot, "reason", "") or ""),
    }


def serialize_event_payload(event_name: str, args: tuple, kwargs: dict) -> dict:
    """Convert EventBus args/kwargs into a JSON-safe payload."""

    payload: dict[str, Any] = {}
    name = str(event_name)

    if name == "ship.updated":
        ship = kwargs.get("ship")
        if ship is None and args:
            ship = args[0]
        if ship is not None:
            payload["ship"] = serialize_ship(ship)
        else:
            # No ship in kwargs — capture full registry snapshot marker.
            payload["registry_hint"] = True
        return payload

    if name in ("alerts.fired", "alerts.acknowledged"):
        event = kwargs.get("event")
        if event is None and args:
            event = args[0]
        payload["event"] = serialize_alert_event(event)
        return payload

    if name == "alerts.cleared":
        payload["count"] = int(kwargs.get("count") or 0)
        payload["acknowledged_only"] = bool(kwargs.get("acknowledged_only", False))
        return payload

    if name == "camera.link.changed":
        snapshot = kwargs.get("snapshot")
        if snapshot is None and args:
            snapshot = args[0]
        payload["snapshot"] = serialize_camera_link_snapshot(snapshot)
        return payload

    if name in ("camera.link.mode", "camera.coverage.toggled"):
        for key, value in kwargs.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                payload[key] = value
            else:
                payload[key] = str(value)
        return payload

    if name in ("ais.status", "rtl.status"):
        payload["status"] = str(kwargs.get("status") or (args[0] if args else "offline"))
        return payload

    if name in ("timeline.arrival", "timeline.departure"):
        for key in ("mmsi", "latitude", "longitude", "speed"):
            if key in kwargs:
                payload[key] = kwargs[key]
        if "timestamp" in kwargs:
            ts = kwargs["timestamp"]
            payload["timestamp"] = _iso(ts) if isinstance(ts, datetime) else str(ts)
        return payload

    if name in ("vessel.playback.mode", "vessel.playback.position"):
        for key, value in kwargs.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                payload[key] = value
            elif isinstance(value, datetime):
                payload[key] = _iso(value)
            else:
                payload[key] = str(value)
        return payload

    # Generic fallback
    for key, value in kwargs.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            payload[key] = value
        elif isinstance(value, datetime):
            payload[key] = _iso(value)
        else:
            payload[key] = str(value)
    return payload
