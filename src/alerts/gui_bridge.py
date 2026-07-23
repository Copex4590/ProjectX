# ============================================================================
# Project X
# Alerts GUI bridge — marshal notifications onto the Qt thread (SAVE-215)
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from alerts.alert_event import AlertEvent
from alerts.alert_manager import EVENT_ALERT_FIRED, alert_manager
from events import eventbus


class AlertsGuiBridge(QObject):
    """Receives EventBus alert events and delivers notification sinks on GUI thread."""

    alert_fired = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.alert_fired.connect(self._deliver)
        eventbus.subscribe(EVENT_ALERT_FIRED, self._on_bus_alert)

    def _on_bus_alert(self, *args, **kwargs) -> None:

        event = kwargs.get("event")
        if event is None and args:
            event = args[0]
        if event is None:
            return
        self.alert_fired.emit(event)

    def _deliver(self, event: object) -> None:

        if not isinstance(event, AlertEvent):
            return

        for sink in list(alert_manager._notification_sinks):
            try:
                sink.on_alert(event)
            except Exception:
                pass


_alerts_gui_bridge: AlertsGuiBridge | None = None


def install_alerts_gui_bridge(parent=None) -> AlertsGuiBridge:

    global _alerts_gui_bridge

    if _alerts_gui_bridge is None:
        _alerts_gui_bridge = AlertsGuiBridge(parent)

    return _alerts_gui_bridge
