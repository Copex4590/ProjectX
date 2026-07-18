# ============================================================================
# Project X
# AIS connection notification monitor
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer

from ais.providers import AISProviderType, normalize_provider_type
from ais.user_provider_service import get_enabled_provider_ids, is_provider_configured
from engines.rtl.hybrid_engine import HybridEngine
from gui.notifications.notification_manager import notification_manager
from gui.notifications.severity import NotificationSeverity
from i18n import tr


class AisConnectionMonitor(QObject):
    AIS_CONNECTION_KEY = "ais.connection"

    COUNTDOWN_SECONDS = 30

    def __init__(self, hybrid_engine: HybridEngine, parent=None):
        super().__init__(parent)

        self._hybrid_engine = hybrid_engine
        self._notifications = notification_manager()
        self._last_status = "offline"
        self._awaiting_reconnect = False
        self._countdown_active = False
        self._countdown_remaining = self.COUNTDOWN_SECONDS
        self._vessels_purged = False

        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)

    def on_status(self, status: str) -> None:

        normalized = str(status or "offline").strip().lower() or "offline"

        if normalized == "connected":
            self._handle_connected()
            self._last_status = normalized
            return

        if (
            self._last_status == "connected"
            and normalized == "offline"
            and self._should_monitor_aisstream()
        ):
            self._handle_connection_lost()

        self._last_status = normalized

    def _should_monitor_aisstream(self) -> bool:

        enabled = {
            normalize_provider_type(provider_id)
            for provider_id in get_enabled_provider_ids()
        }

        return (
            AISProviderType.AISSTREAM in enabled
            and is_provider_configured(AISProviderType.AISSTREAM)
        )

    def _handle_connected(self) -> None:

        self._countdown_timer.stop()
        self._countdown_active = False
        self._countdown_remaining = self.COUNTDOWN_SECONDS
        self._vessels_purged = False

        if self._awaiting_reconnect:
            self._awaiting_reconnect = False
            self._notifications.show(
                tr("AIS connection restored."),
                severity=NotificationSeverity.SUCCESS,
                key=self.AIS_CONNECTION_KEY,
                duration_ms=5000,
                sticky=False,
                animate=True,
            )

    def _handle_connection_lost(self) -> None:

        self._awaiting_reconnect = True
        self._countdown_active = True
        self._countdown_remaining = self.COUNTDOWN_SECONDS
        self._vessels_purged = False

        self._notifications.show(
            self._lost_message(),
            severity=NotificationSeverity.WARNING,
            key=self.AIS_CONNECTION_KEY,
            sticky=True,
            animate=True,
        )

        self._countdown_timer.start()

    def _on_countdown_tick(self) -> None:

        if not self._countdown_active:
            self._countdown_timer.stop()
            return

        self._countdown_remaining -= 1

        if self._countdown_remaining > 0:
            self._notifications.update(
                self.AIS_CONNECTION_KEY,
                self._lost_message(),
                severity=NotificationSeverity.WARNING,
            )
            return

        self._countdown_timer.stop()
        self._countdown_active = False

        if not self._vessels_purged:
            self._hybrid_engine.purge_ais_only_vessels()
            self._vessels_purged = True

        self._notifications.update(
            self.AIS_CONNECTION_KEY,
            tr("AIS connection lost."),
            severity=NotificationSeverity.WARNING,
        )

    def _lost_message(self) -> str:

        if self._countdown_remaining <= 0:
            return tr("AIS connection lost.")

        return (
            f"{tr('AIS connection lost.')}\n"
            f"{tr('If the AIS connection is not restored within 30 seconds, vessels belonging to this provider will automatically disappear from the map.')}\n"
            f"{tr('Vessels will disappear in {seconds} seconds.').replace('{seconds}', str(self._countdown_remaining))}"
        )
