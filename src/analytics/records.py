# ============================================================================
# Project X
# Analytics Dashboard records (SAVE-216)
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


INTERVAL_1H = "1h"
INTERVAL_6H = "6h"
INTERVAL_24H = "24h"
INTERVAL_7D = "7d"
INTERVAL_30D = "30d"

SUPPORTED_INTERVALS = (
    INTERVAL_1H,
    INTERVAL_6H,
    INTERVAL_24H,
    INTERVAL_7D,
    INTERVAL_30D,
)

INTERVAL_LABELS = {
    INTERVAL_1H: "Last 1 hour",
    INTERVAL_6H: "Last 6 hours",
    INTERVAL_24H: "Last 24 hours",
    INTERVAL_7D: "Last 7 days",
    INTERVAL_30D: "Last 30 days",
}

INTERVAL_DELTAS = {
    INTERVAL_1H: timedelta(hours=1),
    INTERVAL_6H: timedelta(hours=6),
    INTERVAL_24H: timedelta(hours=24),
    INTERVAL_7D: timedelta(days=7),
    INTERVAL_30D: timedelta(days=30),
}


@dataclass(frozen=True)
class NamedCount:

    label: str
    count: int


@dataclass
class ProviderAnalytics:

    provider_id: str
    display_name: str
    status: str
    message_count: int = 0
    ships_detected: int = 0


@dataclass
class CameraAnalytics:

    total: int = 0
    enabled: int = 0
    disabled: int = 0
    by_country: list[NamedCount] = field(default_factory=list)


@dataclass
class AlertAnalytics:

    active: int = 0
    history: int = 0
    critical: int = 0
    warning: int = 0
    info: int = 0
    by_type: list[NamedCount] = field(default_factory=list)


@dataclass
class AnalyticsSnapshot:

    interval: str = INTERVAL_24H
    active_vessels: int = 0
    tracked_vessels: int = 0
    ship_types: list[NamedCount] = field(default_factory=list)
    speed_distribution: list[NamedCount] = field(default_factory=list)
    traffic_by_hour: list[NamedCount] = field(default_factory=list)
    common_routes: list[NamedCount] = field(default_factory=list)
    providers: list[ProviderAnalytics] = field(default_factory=list)
    cameras: CameraAnalytics = field(default_factory=CameraAnalytics)
    alerts: AlertAnalytics = field(default_factory=AlertAnalytics)
    computed_at: datetime = field(default_factory=datetime.now)
