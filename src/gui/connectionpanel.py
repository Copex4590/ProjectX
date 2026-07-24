# ============================================================================
# Project X
# Right-side connection status panel (SAVE-235 / SAVE-236)
# ============================================================================

from __future__ import annotations

import socket

from PySide6.QtCore import QSize, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)

from ais.providers import AISProviderType, normalize_provider_type
from ais.user_provider_service import get_enabled_provider_ids, is_provider_configured
from cameras import camera_manager
from cameras.reachability import any_reachable_camera, camera_stream_url
from connectivity.internet_state import is_internet_online, set_internet_online
from events import eventbus
from gui.i18n_support import bind_language_refresh
from gui.notifications.connection_notice import (
    CONNECTION_AISSTREAM,
    CONNECTION_API,
    CONNECTION_CAMERA,
    CONNECTION_GPS,
    CONNECTION_INTERNET,
    CONNECTION_RTL,
    ConnectionNoticeService,
)
from gui.theme import BG_BASE, BORDER
from i18n import tr
from preferences import preferences_manager

# Panel states (SAVE-235)
STATUS_NOT_CONFIGURED = "not_configured"  # ⚪
STATUS_WORKING = "working"  # 🟢
STATUS_NOT_WORKING = "not_working"  # 🔴

# SAVE-236 — panel visuals follow Internet as master for these rows.
# Notices still track each provider's real live status separately.
INTERNET_DEPENDENT_CONNECTIONS = frozenset(
    {
        CONNECTION_AISSTREAM,
        CONNECTION_API,
    }
)

_STATUS_ICON = {
    STATUS_NOT_CONFIGURED: "⚪",
    STATUS_WORKING: "🟢",
    STATUS_NOT_WORKING: "🔴",
}


class ConnectionPanel(QFrame):

    _ROWS = (
        (CONNECTION_INTERNET, "Internet"),
        (CONNECTION_AISSTREAM, "AISStream"),
        (CONNECTION_RTL, "RTL Receiver"),
        (CONNECTION_GPS, "GPS"),
        (CONNECTION_CAMERA, "Camera"),
        (CONNECTION_API, "API"),
    )

    def __init__(self, notice_service: ConnectionNoticeService | None = None):
        super().__init__()

        self._notices = notice_service or ConnectionNoticeService(self)
        self._statuses: dict[str, str] = {
            key: STATUS_NOT_CONFIGURED for key, _ in self._ROWS
        }
        # Internet is always "configured" — only online/offline differs.
        self._statuses[CONNECTION_INTERNET] = STATUS_WORKING
        # Real (non-visual) statuses drive Connection Notice popups.
        self._real_statuses: dict[str, str] = {
            CONNECTION_INTERNET: STATUS_WORKING,
        }
        self._seen_working: dict[str, bool] = {CONNECTION_INTERNET: True}
        self._ais_live = "offline"
        self._rtl_live = "offline"

        self.setFixedWidth(240)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self.setStyleSheet(
            f"""
            QFrame{{
                background:{BG_BASE};
                border-left:1px solid {BORDER};
            }}

            QLabel{{
                color:white;
                padding:6px;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        self._title_label = QLabel(tr("Connections"))
        self._title_label.setStyleSheet(
            """
            font-size:14pt;
            font-weight:bold;
            """
        )
        layout.addWidget(self._title_label)

        self._labels: dict[str, QLabel] = {}
        for key, _label in self._ROWS:
            widget = QLabel()
            self._labels[key] = widget
            layout.addWidget(widget)

        layout.addStretch()

        self._internet_timer = QTimer(self)
        self._internet_timer.setInterval(5000)
        self._internet_timer.timeout.connect(self._poll_internet)
        self._internet_timer.start()

        self._camera_timer = QTimer(self)
        self._camera_timer.setInterval(15000)
        self._camera_timer.timeout.connect(self._poll_cameras)
        self._camera_timer.start()

        bind_language_refresh(self.refresh_translations)
        self.refresh_all()
        QTimer.singleShot(0, self._poll_internet)
        QTimer.singleShot(500, self._poll_cameras)

    def minimumSizeHint(self) -> QSize:
        return QSize(240, 0)

    def sizeHint(self) -> QSize:
        return QSize(240, 300)

    def set_notice_service(self, service: ConnectionNoticeService) -> None:

        self._notices = service

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Connections"))
        self._render_labels()

    def refresh_all(self) -> None:

        self._refresh_aisstream_status(emit_notice=False)
        self._refresh_rtl_status(emit_notice=False)
        self._refresh_camera_status(emit_notice=False)
        self._refresh_gps_status()
        self._refresh_api_status()
        self._render_labels()

    def on_ais_status(self, status) -> None:

        self._ais_live = str(status or "offline").strip().lower() or "offline"
        self._refresh_aisstream_status(emit_notice=True)

    def on_rtl_status(self, status) -> None:

        self._rtl_live = str(status or "offline").strip().lower() or "offline"
        self._refresh_rtl_status(emit_notice=True)

    def _render_labels(self) -> None:

        for key, label_key in self._ROWS:
            icon = _STATUS_ICON[self._statuses[key]]
            self._labels[key].setText(f"{icon} {tr(label_key)}")

    def _visual_status(self, connection_id: str, real_status: str) -> str:
        """Panel icon status; Internet-dependent rows go red while offline."""

        if (
            connection_id in INTERNET_DEPENDENT_CONNECTIONS
            and real_status != STATUS_NOT_CONFIGURED
            and not is_internet_online()
        ):
            return STATUS_NOT_WORKING
        return real_status

    def _set_status(
        self,
        connection_id: str,
        status: str,
        *,
        emit_notice: bool,
        real_status: str | None = None,
    ) -> None:
        """Update panel icon from ``status``; notices follow ``real_status``.

        For Internet-independent rows, ``real_status`` defaults to ``status``.
        Internet-dependent providers may show 🔴 while still ``working`` in
        ``real_status`` (SAVE-236) so Connection Notices stay truthful.
        """

        notice_status = status if real_status is None else real_status
        previous_real = self._real_statuses.get(
            connection_id, self._statuses.get(connection_id)
        )

        if notice_status != previous_real:
            self._real_statuses[connection_id] = notice_status
            if emit_notice:
                if notice_status == STATUS_WORKING:
                    had_working = self._seen_working.get(connection_id, False)
                    self._seen_working[connection_id] = True
                    if previous_real == STATUS_NOT_WORKING and had_working:
                        self._notices.show_restored(connection_id)
                elif (
                    previous_real == STATUS_WORKING
                    and notice_status == STATUS_NOT_WORKING
                ):
                    self._notices.show_lost(connection_id)
            elif notice_status == STATUS_WORKING:
                self._seen_working[connection_id] = True

        if self._statuses.get(connection_id) != status:
            self._statuses[connection_id] = status
        self._render_labels()

    def _poll_internet(self) -> None:

        online = self._probe_internet()
        changed = set_internet_online(online)
        status = STATUS_WORKING if online else STATUS_NOT_WORKING
        self._set_status(
            CONNECTION_INTERNET,
            status,
            emit_notice=True,
        )
        # Propagate master Internet state to dependent panel rows immediately.
        if changed:
            eventbus.publish("internet.status", online=online)
            self._refresh_internet_dependent_visuals()

    def _refresh_internet_dependent_visuals(self) -> None:
        """Recompute icons for Internet-dependent providers (no false notices)."""

        self._refresh_aisstream_status(emit_notice=False)
        self._refresh_api_status()

    @staticmethod
    def _probe_internet() -> bool:

        try:
            socket.create_connection(("1.1.1.1", 443), timeout=2.0)
            return True
        except OSError:
            return False

    def _refresh_aisstream_status(self, *, emit_notice: bool) -> None:

        configured = self._aisstream_configured()
        if not configured:
            self._set_status(
                CONNECTION_AISSTREAM,
                STATUS_NOT_CONFIGURED,
                emit_notice=False,
                real_status=STATUS_NOT_CONFIGURED,
            )
            return

        real = (
            STATUS_WORKING
            if self._ais_live == "connected"
            else STATUS_NOT_WORKING
        )
        self._set_status(
            CONNECTION_AISSTREAM,
            self._visual_status(CONNECTION_AISSTREAM, real),
            emit_notice=emit_notice,
            real_status=real,
        )

    def _refresh_rtl_status(self, *, emit_notice: bool) -> None:

        prefs = preferences_manager.get()
        configured = bool(prefs.rtl_sdr_configured)
        if not configured:
            self._set_status(
                CONNECTION_RTL,
                STATUS_NOT_CONFIGURED,
                emit_notice=False,
            )
            return

        working = self._rtl_live == "connected"
        self._set_status(
            CONNECTION_RTL,
            STATUS_WORKING if working else STATUS_NOT_WORKING,
            emit_notice=emit_notice,
        )

    def _poll_cameras(self) -> None:

        self._refresh_camera_status(emit_notice=True)

    def _refresh_camera_status(self, *, emit_notice: bool) -> None:

        try:
            camera_manager.ensure_loaded()
            cameras = list(camera_manager.all())
            enabled = list(camera_manager.enabled())
        except Exception:
            cameras = []
            enabled = []

        configured = bool(cameras) or any(
            camera_stream_url(camera) for camera in cameras
        )
        if not configured:
            self._set_status(
                CONNECTION_CAMERA,
                STATUS_NOT_CONFIGURED,
                emit_notice=False,
            )
            return

        # Green only when at least one enabled camera stream host is reachable.
        working = any_reachable_camera(enabled, timeout_s=1.5)
        self._set_status(
            CONNECTION_CAMERA,
            STATUS_WORKING if working else STATUS_NOT_WORKING,
            emit_notice=emit_notice,
        )

    def _refresh_gps_status(self) -> None:

        # GPS is not implemented in Alpha — always not configured.
        self._set_status(
            CONNECTION_GPS,
            STATUS_NOT_CONFIGURED,
            emit_notice=False,
        )

    def _refresh_api_status(self) -> None:

        # No standalone API integration yet — always not configured.
        # When configured later, use real API health here; visuals still
        # follow Internet via INTERNET_DEPENDENT_CONNECTIONS.
        real = STATUS_NOT_CONFIGURED
        self._set_status(
            CONNECTION_API,
            self._visual_status(CONNECTION_API, real),
            emit_notice=False,
            real_status=real,
        )

    @staticmethod
    def _aisstream_configured() -> bool:

        enabled = {
            normalize_provider_type(provider_id)
            for provider_id in get_enabled_provider_ids()
        }
        return (
            AISProviderType.AISSTREAM in enabled
            and is_provider_configured(AISProviderType.AISSTREAM)
        )
