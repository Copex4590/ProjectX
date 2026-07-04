# ============================================================================
# Project X
# Event Bridge (EventBus -> Qt signals)
# ============================================================================

from PySide6.QtCore import QObject, Signal

from events import eventbus


class EventBridge(QObject):

    ship_updated = Signal()
    ais_status = Signal(str)
    rtl_status = Signal(str)

    def __init__(self):

        super().__init__()

        eventbus.subscribe("ship.updated", self._on_ship_updated)
        eventbus.subscribe("ais.status", self._on_ais_status)
        eventbus.subscribe("rtl.status", self._on_rtl_status)

    def _on_ship_updated(self, ship=None, **kwargs):

        self.ship_updated.emit()

    def _on_ais_status(self, status):

        self.ais_status.emit(status)

    def _on_rtl_status(self, status):

        self.rtl_status.emit(status)
