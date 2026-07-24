# ============================================================================
# Project X
# Alert Notification Hooks (SAVE-215 — Notification API preparation)
# ============================================================================

from __future__ import annotations

import logging

from alerts.alert_event import AlertEvent
from gui.notifications.severity import NotificationSeverity

logger = logging.getLogger(__name__)


class AlertNotificationSink:
    """Future-facing notification sink interface for alert events."""

    def on_alert(self, event: AlertEvent) -> None:

        raise NotImplementedError


def _map_severity(severity: str) -> NotificationSeverity:

    text = str(severity or "").strip().lower()

    if text == "critical":
        return NotificationSeverity.ERROR

    if text == "warning":
        return NotificationSeverity.WARNING

    return NotificationSeverity.INFO


class DesktopBannerSink(AlertNotificationSink):
    """Bridge alerts to the existing desktop notification banner."""

    def on_alert(self, event: AlertEvent) -> None:

        try:
            from preferences.application_settings import desktop_notifications_enabled

            if not desktop_notifications_enabled():
                return
        except Exception:
            logger.debug(
                "Desktop notification preference check failed; showing alert",
                exc_info=True,
            )

        try:
            from gui.notifications.notification_manager import notification_manager

            key = f"alert.{event.id or event.event_type}"
            notification_manager().show(
                event.message or event.event_type,
                severity=_map_severity(event.severity),
                key=key,
                duration_ms=8000,
            )
        except Exception:
            logger.exception("Failed to show alert notification banner")


class NullNotificationSink(AlertNotificationSink):
    """Placeholder sink reserved for future Tray / Sound / Push APIs."""

    def on_alert(self, event: AlertEvent) -> None:

        return


def install_default_notification_sinks(manager) -> None:

    manager.register_notification_sink(DesktopBannerSink())
    # Reserved extension points:
    # manager.register_notification_sink(SoundNotificationSink())
    # manager.register_notification_sink(TrayNotificationSink())
