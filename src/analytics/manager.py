# ============================================================================
# Project X
# Analytics Dashboard manager (SAVE-216)
# ============================================================================

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from threading import Lock

from ais.ais_manager import ais_manager
from ais.provider_manager import provider_manager
from ais.user_provider_service import provider_display_status
from alerts.alert_manager import alert_manager
from alerts.alert_rule import ALERT_TYPE_LABELS
from cameras.manager import camera_manager
from database import registry
from rtl.rtl_manager import rtl_manager
from timeline.timeline_manager import timeline_manager
from timeline.timeline_recorder import EVENT_POSITION_UPDATE

from .records import (
    INTERVAL_24H,
    INTERVAL_DELTAS,
    SUPPORTED_INTERVALS,
    AlertAnalytics,
    AnalyticsSnapshot,
    CameraAnalytics,
    NamedCount,
    ProviderAnalytics,
)

_SPEED_BUCKETS = (
    ("0–5 kn", 0.0, 5.0),
    ("5–10 kn", 5.0, 10.0),
    ("10–15 kn", 10.0, 15.0),
    ("15–20 kn", 15.0, 20.0),
    ("20+ kn", 20.0, None),
)


def _normalize_interval(interval: str | None) -> str:

    value = str(interval or INTERVAL_24H).strip().lower()
    if value in SUPPORTED_INTERVALS:
        return value
    return INTERVAL_24H


def _bucket_speed(speed: float) -> str:

    for label, low, high in _SPEED_BUCKETS:
        if high is None:
            if speed >= low:
                return label
        elif low <= speed < high:
            return label
    return _SPEED_BUCKETS[0][0]


class AnalyticsManager:
    """Aggregates live fleet, timeline, providers, cameras, and alerts."""

    def __init__(self) -> None:

        self._lock = Lock()
        self._interval = INTERVAL_24H
        self._cache: AnalyticsSnapshot | None = None

    @property
    def interval(self) -> str:

        return self._interval

    def set_interval(self, interval: str) -> str:

        normalized = _normalize_interval(interval)
        with self._lock:
            if normalized != self._interval:
                self._interval = normalized
                self._cache = None
        return self._interval

    def snapshot(self, *, force: bool = False) -> AnalyticsSnapshot:

        with self._lock:
            if force or self._cache is None:
                self._cache = self._build_snapshot_locked()
            return self._cache

    def refresh(self) -> AnalyticsSnapshot:

        return self.snapshot(force=True)

    def _build_snapshot_locked(self) -> AnalyticsSnapshot:

        now = datetime.now()
        window = INTERVAL_DELTAS.get(self._interval, timedelta(hours=24))
        since = now - window

        ships = list(registry.all())
        active = [
            ship
            for ship in ships
            if getattr(ship, "ais_visible", False)
            or getattr(ship, "rtl_visible", False)
            or getattr(ship, "camera_visible", False)
            or (ship.last_seen is not None and ship.last_seen >= since)
        ]

        type_counter: Counter[str] = Counter()
        speed_counter: Counter[str] = Counter()
        route_counter: Counter[str] = Counter()

        for ship in ships:
            ship_type = str(ship.ship_type or "").strip() or "Unknown"
            type_counter[ship_type] += 1

            try:
                speed = float(ship.speed or 0.0)
            except (TypeError, ValueError):
                speed = 0.0
            speed_counter[_bucket_speed(speed)] += 1

            destination = str(ship.destination or "").strip()
            if destination:
                route_counter[destination] += 1

        timeline = [
            record
            for record in timeline_manager.all()
            if record.timestamp >= since
            and record.event_type == EVENT_POSITION_UPDATE
        ]

        hour_counter: Counter[str] = Counter()
        for record in timeline:
            hour_counter[f"{record.timestamp.hour:02d}"] += 1

        # Prefer a full 24-slot axis for readability when interval ≤ 24h.
        if window <= timedelta(hours=24):
            traffic = [
                NamedCount(label=f"{hour:02d}", count=hour_counter.get(f"{hour:02d}", 0))
                for hour in range(24)
            ]
        else:
            traffic = [
                NamedCount(label=label, count=count)
                for label, count in sorted(hour_counter.items())
            ]

        speed_distribution = [
            NamedCount(label=label, count=speed_counter.get(label, 0))
            for label, _low, _high in _SPEED_BUCKETS
        ]

        return AnalyticsSnapshot(
            interval=self._interval,
            active_vessels=len(active),
            tracked_vessels=len(ships),
            ship_types=[
                NamedCount(label=label, count=count)
                for label, count in type_counter.most_common(12)
            ],
            speed_distribution=speed_distribution,
            traffic_by_hour=traffic,
            common_routes=[
                NamedCount(label=label, count=count)
                for label, count in route_counter.most_common(10)
            ],
            providers=self._provider_stats(),
            cameras=self._camera_stats(),
            alerts=self._alert_stats(since),
            computed_at=now,
        )

    def _provider_stats(self) -> list[ProviderAnalytics]:

        rtl_stats = rtl_manager.reception_stats()
        ais_status = ais_manager.ais_connection_status()
        rtl_status = ais_manager.rtl_connection_status()

        rows: list[ProviderAnalytics] = []
        for configured in provider_manager.configured_providers():
            try:
                status = provider_display_status(configured.provider_id).text
            except Exception:
                status = "unknown"

            if configured.provider_id == "local":
                rows.append(
                    ProviderAnalytics(
                        provider_id=configured.provider_id,
                        display_name=configured.display_name,
                        status=rtl_status or status,
                        message_count=rtl_stats.message_count,
                        ships_detected=rtl_stats.ships_detected,
                    )
                )
            else:
                rows.append(
                    ProviderAnalytics(
                        provider_id=configured.provider_id,
                        display_name=configured.display_name,
                        status=ais_status or status,
                        message_count=0,
                        ships_detected=sum(
                            1
                            for ship in registry.all()
                            if str(getattr(ship, "source", "")).lower()
                            in ("aisstream", "ais", configured.provider_id)
                        ),
                    )
                )
        return rows

    def _camera_stats(self) -> CameraAnalytics:

        cameras = camera_manager.all()
        enabled = camera_manager.enabled()
        country_counter = Counter(
            str(camera.country or "").strip() or "Unknown"
            for camera in cameras
        )
        return CameraAnalytics(
            total=len(cameras),
            enabled=len(enabled),
            disabled=max(0, len(cameras) - len(enabled)),
            by_country=[
                NamedCount(label=label, count=count)
                for label, count in country_counter.most_common(8)
            ],
        )

    def _alert_stats(self, since: datetime) -> AlertAnalytics:

        events = [
            event
            for event in alert_manager.events()
            if event.timestamp is None or event.timestamp >= since
        ]
        active = [event for event in events if not event.acknowledged]
        history = [event for event in events if event.acknowledged]

        severity = Counter(
            str(event.severity or "info").strip().lower() or "info"
            for event in events
        )
        by_type = Counter(
            ALERT_TYPE_LABELS.get(event.event_type, event.event_type)
            for event in events
        )

        return AlertAnalytics(
            active=len(active),
            history=len(history),
            critical=severity.get("critical", 0),
            warning=severity.get("warning", 0),
            info=severity.get("info", 0),
            by_type=[
                NamedCount(label=label, count=count)
                for label, count in by_type.most_common(8)
            ],
        )


analytics_manager = AnalyticsManager()
