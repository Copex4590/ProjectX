# ============================================================================
# Project X
# Event Bridge (EventBus -> Qt signals)
# ============================================================================

from PySide6.QtCore import QObject, Signal

from debug.obs_freeze_trace import trace_block
from events import eventbus


class EventBridge(QObject):

    ship_updated = Signal()
    ais_status = Signal(str)
    rtl_status = Signal(str)
    providers_changed = Signal()

    def __init__(self):

        super().__init__()

        eventbus.subscribe("ship.updated", self._on_ship_updated)
        eventbus.subscribe("ais.status", self._on_ais_status)
        eventbus.subscribe("rtl.status", self._on_rtl_status)
        eventbus.subscribe("providers.changed", self._on_providers_changed)

    def _on_ship_updated(self, ship=None, **kwargs):

        with trace_block("EventBridge._on_ship_updated"):
            self.ship_updated.emit()

    def _on_ais_status(self, status):

        with trace_block("EventBridge._on_ais_status"):
            self.ais_status.emit(status)

    def _on_rtl_status(self, status):

        with trace_block("EventBridge._on_rtl_status"):
            self.rtl_status.emit(status)

    def _on_providers_changed(self, **_kwargs):

        with trace_block("EventBridge._on_providers_changed"):
            self.providers_changed.emit()
