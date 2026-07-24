# ============================================================================
# Project X
# Connection notice service (SAVE-235)
# ============================================================================

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from gui.notifications.connection_notice_dialog import ConnectionNoticeDialog
from i18n import tr
from preferences import preferences_manager

# Stable ids used for suppression prefs + dialogs.
CONNECTION_INTERNET = "internet"
CONNECTION_AISSTREAM = "aisstream"
CONNECTION_RTL = "rtl"
CONNECTION_GPS = "gps"
CONNECTION_CAMERA = "camera"
CONNECTION_API = "api"

_LABEL_KEYS = {
    CONNECTION_INTERNET: "Internet",
    CONNECTION_AISSTREAM: "AISStream",
    CONNECTION_RTL: "RTL Receiver",
    CONNECTION_GPS: "GPS",
    CONNECTION_CAMERA: "Camera",
    CONNECTION_API: "API",
}


def connection_display_name(connection_id: str) -> str:

    key = _LABEL_KEYS.get(connection_id, connection_id)
    return tr(key)


def is_connection_notice_suppressed(connection_id: str) -> bool:

    prefs = preferences_manager.get()
    suppressed = prefs.connection_notice_suppressed or {}
    return bool(suppressed.get(str(connection_id), False))


def set_connection_notice_suppressed(connection_id: str, suppressed: bool) -> None:

    current = preferences_manager.get()
    data = dict(current.connection_notice_suppressed or {})
    data[str(connection_id)] = bool(suppressed)
    current.connection_notice_suppressed = data
    preferences_manager.save(current)


class ConnectionNoticeService:
    """Show sticky connection lost/restored dialogs (user must close)."""

    def __init__(self, parent: QWidget | None = None):

        self._parent = parent
        self._open: dict[str, ConnectionNoticeDialog] = {}

    def set_parent(self, parent: QWidget | None) -> None:

        self._parent = parent

    def show_lost(self, connection_id: str) -> None:

        self._show(connection_id, restored=False)

    def show_restored(self, connection_id: str) -> None:

        self._show(connection_id, restored=True)

    def _show(self, connection_id: str, *, restored: bool) -> None:

        connection_id = str(connection_id)
        if is_connection_notice_suppressed(connection_id):
            return

        existing = self._open.get(connection_id)
        if existing is not None:
            try:
                existing.close()
            except RuntimeError:
                pass
            self._open.pop(connection_id, None)

        dialog = ConnectionNoticeDialog(
            connection_id=connection_id,
            connection_label=connection_display_name(connection_id),
            restored=restored,
            parent=self._parent,
        )
        self._open[connection_id] = dialog
        dialog.finished.connect(
            lambda _result, cid=connection_id, dlg=dialog: self._on_finished(
                cid, dlg
            )
        )
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _on_finished(self, connection_id: str, dialog: ConnectionNoticeDialog) -> None:

        if dialog.dont_show_again():
            set_connection_notice_suppressed(connection_id, True)

        if self._open.get(connection_id) is dialog:
            self._open.pop(connection_id, None)
