# ============================================================================
# Project X
# Global notifications
# ============================================================================

from gui.notifications.notification_manager import (
    NotificationManager,
    notification_manager,
)
from gui.notifications.severity import NotificationSeverity

__all__ = [
    "AisConnectionMonitor",
    "NotificationManager",
    "NotificationSeverity",
    "notification_manager",
]


def __getattr__(name: str):
    if name == "AisConnectionMonitor":
        from gui.notifications.ais_connection_monitor import AisConnectionMonitor

        return AisConnectionMonitor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
