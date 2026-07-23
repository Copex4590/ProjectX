# ============================================================================
# Project X
# Event Bridge (EventBus -> Qt signals)
# ============================================================================

from PySide6.QtCore import QMetaObject, QObject, Qt, QTimer, Signal, Slot

from debug.obs_freeze_trace import trace_block
from events import eventbus

# SAVE-106: coalesce GUI ship refreshes to ~8 Hz (within 5–10/s).
_GUI_SHIP_REFRESH_INTERVAL_MS = 125


class EventBridge(QObject):

    ship_updated = Signal()
    ais_status = Signal(str)
    rtl_status = Signal(str)
    providers_changed = Signal()

    def __init__(self):

        super().__init__()

        self._ship_emit_pending = False
        self._ship_coalesce_timer = QTimer(self)
        self._ship_coalesce_timer.setSingleShot(True)
        self._ship_coalesce_timer.timeout.connect(self._flush_ship_updated)

        eventbus.subscribe("ship.updated", self._on_ship_updated)
        eventbus.subscribe("ais.status", self._on_ais_status)
        eventbus.subscribe("rtl.status", self._on_rtl_status)
        eventbus.subscribe("providers.changed", self._on_providers_changed)

    def _on_ship_updated(self, ship=None, **kwargs):

        with trace_block("EventBridge._on_ship_updated"):
            # EventBus may call from a worker thread — arm the timer on this
            # QObject's thread before emitting to GUI slots.
            QMetaObject.invokeMethod(
                self,
                "_arm_ship_coalesce",
                Qt.ConnectionType.QueuedConnection,
            )

    @Slot()
    def _arm_ship_coalesce(self) -> None:

        self._ship_emit_pending = True

        if not self._ship_coalesce_timer.isActive():
            self._ship_coalesce_timer.start(_GUI_SHIP_REFRESH_INTERVAL_MS)

    @Slot()
    def _flush_ship_updated(self) -> None:

        if not self._ship_emit_pending:
            return

        self._ship_emit_pending = False

        with trace_block("EventBridge._flush_ship_updated"):
            self.ship_updated.emit()

        if self._ship_emit_pending and not self._ship_coalesce_timer.isActive():
            self._ship_coalesce_timer.start(_GUI_SHIP_REFRESH_INTERVAL_MS)

    def _on_ais_status(self, status):

        with trace_block("EventBridge._on_ais_status"):
            self.ais_status.emit(status)

    def _on_rtl_status(self, status):

        with trace_block("EventBridge._on_rtl_status"):
            self.rtl_status.emit(status)

    def _on_providers_changed(self, **_kwargs):

        with trace_block("EventBridge._on_providers_changed"):
            self.providers_changed.emit()
