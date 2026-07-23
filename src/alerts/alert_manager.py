# ============================================================================
# Project X
# Alert Manager (SAVE-215 Professional Alerts Engine)
# ============================================================================

from __future__ import annotations

import csv
import math
from datetime import datetime
from pathlib import Path

from alerts.alert_event import AlertEvent, EvaluationEvent
from alerts.alert_registry import AlertRegistry, alert_registry
from alerts.alert_rule import (
    ALERT_TYPE_LABELS,
    RULE_TYPE_AIS_LOST,
    RULE_TYPE_ANCHORED,
    RULE_TYPE_ARRIVAL,
    RULE_TYPE_CAMERA_LOST,
    RULE_TYPE_CAMERA_OFFLINE,
    RULE_TYPE_CAMERA_VISIBLE,
    RULE_TYPE_DB_SYNC_FAILED,
    RULE_TYPE_DEPARTURE,
    RULE_TYPE_ENTER_REGION,
    RULE_TYPE_EXIT_REGION,
    RULE_TYPE_SPEED_OVER,
    RULE_TYPE_SPEED_UNDER,
    SUPPORTED_RULE_TYPES,
    AlertRule,
)
from events import eventbus

EVENT_ALERT_FIRED = "alerts.fired"
EVENT_ALERT_ACKNOWLEDGED = "alerts.acknowledged"
EVENT_ALERT_CLEARED = "alerts.cleared"

_SYSTEM_RULE_SPECS = (
    (RULE_TYPE_ENTER_REGION, "Vessel Enter Area", 60, {"radius_km": 1.0}),
    (RULE_TYPE_EXIT_REGION, "Vessel Leave Area", 60, {"radius_km": 1.0}),
    (RULE_TYPE_ARRIVAL, "Vessel Arrived", 50, {}),
    (RULE_TYPE_DEPARTURE, "Vessel Departed", 50, {}),
    (RULE_TYPE_SPEED_OVER, "Speed Above Limit", 70, {"speed_limit": 15.0}),
    (RULE_TYPE_SPEED_UNDER, "Speed Below Limit", 40, {"speed_limit": 0.5}),
    (RULE_TYPE_ANCHORED, "Anchored", 40, {"speed_limit": 0.3}),
    (RULE_TYPE_AIS_LOST, "AIS Lost", 80, {}),
    (RULE_TYPE_CAMERA_OFFLINE, "Camera Offline", 70, {}),
    (RULE_TYPE_DB_SYNC_FAILED, "Database Sync Failed", 80, {}),
)


def _normalize_mmsi(mmsi: int | str | None) -> int | None:

    if mmsi is None:
        return None

    try:
        normalized = int(mmsi)
    except (TypeError, ValueError):
        return None

    if normalized < 0:
        return None

    return normalized


def _severity_from_priority(priority: int) -> str:

    if priority >= 80:
        return "critical"

    if priority >= 50:
        return "warning"

    return "info"


def _distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:

    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )

    return radius_km * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def _point_in_region(
    latitude: float | None,
    longitude: float | None,
    conditions: dict,
) -> bool:

    if latitude is None or longitude is None:
        return False

    center_lat = conditions.get("latitude", conditions.get("lat"))
    center_lon = conditions.get("longitude", conditions.get("lon"))
    radius_km = conditions.get("radius_km", conditions.get("radius"))

    if center_lat is None or center_lon is None or radius_km is None:
        return False

    distance = _distance_km(
        float(latitude),
        float(longitude),
        float(center_lat),
        float(center_lon),
    )

    return distance <= float(radius_km)


def _has_region_center(conditions: dict) -> bool:

    center_lat = conditions.get("latitude", conditions.get("lat"))
    center_lon = conditions.get("longitude", conditions.get("lon"))
    radius_km = conditions.get("radius_km", conditions.get("radius"))
    return center_lat is not None and center_lon is not None and radius_km is not None


def _matches_mmsi_filter(mmsi: int, conditions: dict) -> bool:

    filter_mmsi = conditions.get("mmsi")

    if filter_mmsi is None:
        return True

    return int(filter_mmsi) == int(mmsi)


class AlertManager:

    def __init__(self, registry: AlertRegistry | None = None):

        self._registry = registry or alert_registry
        self._notification_sinks: list = []

    def register_notification_sink(self, sink) -> None:

        if sink is not None and sink not in self._notification_sinks:
            self._notification_sinks.append(sink)

    def register_rule(self, rule: AlertRule) -> AlertRule:

        event_type = rule.safe_text(rule.event_type).upper()

        if event_type and event_type not in SUPPORTED_RULE_TYPES:
            raise ValueError(f"Unsupported alert rule type: {event_type}")

        return self._registry.register_rule(rule)

    def remove_rule(self, rule_id: int) -> bool:

        return self._registry.remove_rule(rule_id)

    def rules(self) -> list[AlertRule]:

        return self._registry.rules()

    def events(self) -> list[AlertEvent]:

        return self._registry.events()

    def active_events(self) -> list[AlertEvent]:

        return [event for event in self.events() if not event.acknowledged]

    def history_events(self) -> list[AlertEvent]:

        return [event for event in self.events() if event.acknowledged]

    def acknowledge(self, event_id: int) -> AlertEvent | None:

        event = self._registry.acknowledge_event(event_id)
        if event is not None:
            eventbus.publish(EVENT_ALERT_ACKNOWLEDGED, event=event)
        return event

    def clear_history(self) -> int:

        count = self._registry.clear_events(acknowledged_only=True)
        eventbus.publish(EVENT_ALERT_CLEARED, count=count, acknowledged_only=True)
        return count

    def clear_all(self) -> int:

        count = self._registry.clear_events(acknowledged_only=False)
        eventbus.publish(EVENT_ALERT_CLEARED, count=count, acknowledged_only=False)
        return count

    def export_events(self, path: Path | str, *, acknowledged: bool | None = None) -> Path:

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        events = self.events()
        if acknowledged is True:
            events = [event for event in events if event.acknowledged]
        elif acknowledged is False:
            events = [event for event in events if not event.acknowledged]

        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "id",
                    "timestamp",
                    "event_type",
                    "severity",
                    "mmsi",
                    "rule_id",
                    "message",
                    "acknowledged",
                    "acknowledged_at",
                    "priority",
                ]
            )
            for event in events:
                writer.writerow(
                    [
                        event.id,
                        event.timestamp.isoformat(timespec="seconds"),
                        event.event_type,
                        event.severity,
                        event.mmsi,
                        event.rule_id,
                        event.message,
                        int(event.acknowledged),
                        (
                            event.acknowledged_at.isoformat(timespec="seconds")
                            if event.acknowledged_at
                            else ""
                        ),
                        (event.metadata or {}).get("priority", ""),
                    ]
                )

        return target

    def ensure_system_rules(self) -> list[AlertRule]:

        existing = {
            rule.event_type: rule
            for rule in self.rules()
            if (rule.metadata if False else True)
        }
        # Index by event_type for system defaults (first rule wins).
        by_type = {}
        for rule in self.rules():
            by_type.setdefault(rule.event_type, rule)

        created: list[AlertRule] = []

        for event_type, name, priority, conditions in _SYSTEM_RULE_SPECS:
            if event_type in by_type:
                continue

            payload = dict(conditions)
            payload.setdefault("message", ALERT_TYPE_LABELS.get(event_type, name))
            payload["system"] = True

            rule = self.register_rule(
                AlertRule(
                    name=name,
                    enabled=True,
                    priority=priority,
                    event_type=event_type,
                    conditions=payload,
                )
            )
            created.append(rule)

        return created

    def set_rule_enabled(self, rule_id: int, enabled: bool) -> AlertRule | None:

        for rule in self.rules():
            if rule.id == rule_id:
                rule.enabled = bool(enabled)
                return self.register_rule(rule)

        return None

    def evaluate(self, event) -> list[AlertEvent]:

        evaluation = EvaluationEvent.from_payload(event)

        if evaluation is None:
            return []

        matched_events: list[AlertEvent] = []

        for rule in self._registry.rules():
            if not self._rule_matches(rule, evaluation):
                continue

            if rule.id is None:
                continue

            alert_event = self._build_alert_event(rule, evaluation)
            saved = self._registry.append_event(alert_event)
            matched_events.append(saved)
            self._notify_fired(saved)

        return matched_events

    def _notify_fired(self, event: AlertEvent) -> None:

        eventbus.publish(EVENT_ALERT_FIRED, event=event)
        # Notification sinks are invoked on the GUI thread via AlertsGuiBridge.

    def _rule_matches(self, rule: AlertRule, event: EvaluationEvent) -> bool:

        if not rule.enabled:
            return False

        if rule.event_type != event.event_type:
            return False

        if not _matches_mmsi_filter(event.mmsi, rule.conditions):
            return False

        if rule.event_type == RULE_TYPE_SPEED_OVER:
            speed_limit = rule.conditions.get(
                "speed_limit",
                rule.conditions.get("min_speed"),
            )

            if speed_limit is None or event.speed is None:
                return False

            return float(event.speed) > float(speed_limit)

        if rule.event_type == RULE_TYPE_SPEED_UNDER:
            speed_limit = rule.conditions.get(
                "speed_limit",
                rule.conditions.get("max_speed"),
            )

            if speed_limit is None or event.speed is None:
                return False

            return float(event.speed) < float(speed_limit)

        if rule.event_type == RULE_TYPE_ANCHORED:
            speed_limit = float(
                rule.conditions.get("speed_limit", 0.3)
            )
            if event.speed is None:
                return False
            return float(event.speed) <= speed_limit

        if rule.event_type == RULE_TYPE_ENTER_REGION:
            if _has_region_center(rule.conditions):
                return _point_in_region(
                    event.latitude,
                    event.longitude,
                    rule.conditions,
                )
            return True

        if rule.event_type == RULE_TYPE_EXIT_REGION:
            if _has_region_center(rule.conditions):
                return not _point_in_region(
                    event.latitude,
                    event.longitude,
                    rule.conditions,
                )
            return True

        if rule.event_type == RULE_TYPE_CAMERA_VISIBLE:
            return event.camera_visible is True

        if rule.event_type in (RULE_TYPE_CAMERA_LOST, RULE_TYPE_CAMERA_OFFLINE):
            return event.camera_visible is False

        # ARRIVAL, DEPARTURE, AIS_LOST, DB_SYNC_FAILED: type match is enough
        return True

    def _build_alert_event(
        self,
        rule: AlertRule,
        event: EvaluationEvent,
    ) -> AlertEvent:

        message = rule.safe_text(rule.conditions.get("message"))

        if not message:
            label = ALERT_TYPE_LABELS.get(event.event_type, event.event_type)
            if event.mmsi > 0:
                message = f"{label}: MMSI {event.mmsi}"
            else:
                message = label

        metadata = {
            "rule_name": rule.name,
            "priority": rule.priority,
            "evaluation": dict(event.metadata or {}),
        }

        return AlertEvent(
            rule_id=int(rule.id),
            mmsi=event.mmsi,
            event_type=event.event_type,
            timestamp=event.timestamp or datetime.now(),
            severity=_severity_from_priority(rule.priority),
            message=message,
            metadata=metadata,
            acknowledged=False,
        )


alert_manager = AlertManager()
