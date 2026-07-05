# ============================================================================
# Project X
# Alert Manager
# ============================================================================

import math
from datetime import datetime

from alerts.alert_event import AlertEvent, EvaluationEvent
from alerts.alert_registry import AlertRegistry, alert_registry
from alerts.alert_rule import (
    RULE_TYPE_CAMERA_LOST,
    RULE_TYPE_CAMERA_VISIBLE,
    RULE_TYPE_ENTER_REGION,
    RULE_TYPE_EXIT_REGION,
    RULE_TYPE_SPEED_OVER,
    SUPPORTED_RULE_TYPES,
    AlertRule,
)


def _normalize_mmsi(mmsi: int | str | None) -> int | None:

    if mmsi is None:
        return None

    try:
        normalized = int(mmsi)
    except (TypeError, ValueError):
        return None

    if normalized <= 0:
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


def _matches_mmsi_filter(mmsi: int, conditions: dict) -> bool:

    filter_mmsi = conditions.get("mmsi")

    if filter_mmsi is None:
        return True

    return int(filter_mmsi) == int(mmsi)


class AlertManager:

    def __init__(self, registry: AlertRegistry | None = None):

        self._registry = registry or alert_registry

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

    def evaluate(self, event) -> list[AlertEvent]:

        evaluation = EvaluationEvent.from_payload(event)

        if evaluation is None:
            return []

        matched_events: list[AlertEvent] = []

        for rule in self._registry.rules():
            if not self._rule_matches(rule, evaluation):
                continue

            alert_event = self._build_alert_event(rule, evaluation)
            saved = self._registry.append_event(alert_event)
            matched_events.append(saved)

        return matched_events

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

        if rule.event_type == RULE_TYPE_ENTER_REGION:
            return _point_in_region(
                event.latitude,
                event.longitude,
                rule.conditions,
            )

        if rule.event_type == RULE_TYPE_EXIT_REGION:
            return not _point_in_region(
                event.latitude,
                event.longitude,
                rule.conditions,
            )

        if rule.event_type == RULE_TYPE_CAMERA_VISIBLE:
            return event.camera_visible is True

        if rule.event_type == RULE_TYPE_CAMERA_LOST:
            return event.camera_visible is False

        return True

    def _build_alert_event(
        self,
        rule: AlertRule,
        event: EvaluationEvent,
    ) -> AlertEvent:

        message = rule.safe_text(rule.conditions.get("message"))

        if not message:
            message = (
                f"Rule '{rule.name}' matched for MMSI {event.mmsi} "
                f"({event.event_type})"
            )

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
        )


alert_manager = AlertManager()
