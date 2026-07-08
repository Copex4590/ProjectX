from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, QTimer, Signal

from gui.map_core import MAP_PAGE_INDEX, PickMode
from gui.observationreferencedialog import ObservationReferenceDialog
from gui.widgets.mapwidget import MapWidget
from i18n import tr
from observation import observation_manager
from PySide6.QtWidgets import QApplication, QDialog, QWidget


LocationPickCallback = Callable[[float, float], None]


class MapController(QObject):

    """Single owner of the application's map surface and geographic routing."""

    _instance: MapController | None = None

    navigation_requested = Signal(int)
    pick_mode_changed = Signal(object)

    def __init__(self):
        super().__init__()

        self._dialog_parent: QWidget | None = None
        self._reference_prompt_open = False
        self._pick_mode = PickMode.NONE
        self._location_pick_callback: LocationPickCallback | None = None
        self._pick_host: QDialog | None = None
        self._pick_host_was_modal = False
        self._pending_pick_host: QWidget | None = None
        self._pending_pick_message: str | None = None
        self._widget = MapWidget()
        self._widget.locationSelected.connect(
            self._on_location_selected,
            Qt.ConnectionType.QueuedConnection,
        )

    @classmethod
    def instance(cls) -> MapController:

        if cls._instance is None:
            cls._instance = MapController()

        return cls._instance

    @classmethod
    def map_page_index(cls) -> int:

        return MAP_PAGE_INDEX

    def widget(self) -> MapWidget:

        return self._widget

    def set_dialog_parent(self, parent: QWidget | None) -> None:

        self._dialog_parent = parent

    def request_show_map(self) -> None:

        self.navigation_requested.emit(MAP_PAGE_INDEX)

    def begin_location_pick(
        self,
        callback: LocationPickCallback,
        *,
        overlay_message: str | None = None,
        host: QWidget | None = None,
    ) -> None:

        self._location_pick_callback = callback
        self._set_pick_mode(PickMode.LOCATION)
        self._pending_pick_message = overlay_message or tr(
            "Click the map to set the location. Press Esc to cancel."
        )
        self._pending_pick_host = host
        self._widget.clear_pick_marker()
        self.request_show_map()
        QTimer.singleShot(0, self._start_pick_session)

    def _start_pick_session(self) -> None:

        if self._pick_mode != PickMode.LOCATION:
            return

        host = self._pending_pick_host
        self._pending_pick_host = None
        self._suspend_pick_host(host)
        self.activate_location_pick()

    def activate_location_pick(self) -> None:

        if self._pick_mode != PickMode.LOCATION:
            return

        if self._pending_pick_message is not None:
            message = self._pending_pick_message
            self._pending_pick_message = None
            self._widget.begin_location_pick(message)
            return

        self._widget.refresh_location_pick_view()

    def on_map_page_visible(self) -> None:

        if self._pick_mode != PickMode.LOCATION:
            return

        self.activate_location_pick()

        for delay_ms in (50, 150):
            QTimer.singleShot(
                delay_ms,
                self._widget.refresh_location_pick_view,
            )
            QTimer.singleShot(delay_ms, self._focus_map_for_pick)

    def _focus_map_for_pick(self) -> None:

        if self._pick_mode != PickMode.LOCATION:
            return

        parent = self._dialog_parent

        if parent is not None:
            parent.raise_()
            parent.activateWindow()

        self._widget.raise_()
        self._widget.setFocus(Qt.FocusReason.OtherFocusReason)

    def cancel_pick_mode(self, *, restore_host: bool = True) -> None:

        self._pending_pick_host = None
        self._pending_pick_message = None
        self._location_pick_callback = None
        self._set_pick_mode(PickMode.NONE)
        self._widget.end_location_pick()
        self._widget.clear_pick_marker()
        self.release_application_modality()

        if restore_host:
            self._restore_pick_host()
        else:
            self._pick_host = None
            self._pick_host_was_modal = False

    def pick_mode(self) -> PickMode:

        return self._pick_mode

    def refresh_observation_points(self) -> None:

        points = observation_manager.all()

        if not points:
            self._widget.clear_observation_points(
                tr("No observation point configured")
            )
            return

        payload = [
            {
                "id": point.id,
                "name": point.name,
                "lat": point.latitude,
                "lon": point.longitude,
                "active": point.active,
            }
            for point in points
        ]
        self._widget.set_observation_points(payload)

    def update_ships(self, payload: str) -> None:

        self._widget.update_ships(payload)

    def focus_ship(self, mmsi: int) -> None:

        self._widget.focus_ship(mmsi)

    def maybe_prompt_reference_selection(self) -> None:

        if self._reference_prompt_open:
            return

        if not observation_manager.needs_reference_selection():
            return

        active_points = observation_manager.active_points()

        if len(active_points) <= 1:
            return

        parent = self._dialog_parent
        self._reference_prompt_open = True

        try:
            dialog = ObservationReferenceDialog(active_points, parent)

            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            point_id = dialog.selected_point_id()

            if point_id:
                observation_manager.set_reference(point_id)
        finally:
            self._reference_prompt_open = False

    def _on_location_selected(self, latitude: float, longitude: float) -> None:

        if self._pick_mode != PickMode.LOCATION:
            return

        self._widget.set_pick_marker(latitude, longitude)

        callback = self._location_pick_callback

        if callback is None:
            return

        self._location_pick_callback = None
        self._set_pick_mode(PickMode.NONE)
        self._widget.end_location_pick()
        self._restore_pick_host()
        callback(latitude, longitude)

    def _set_pick_mode(self, mode: PickMode) -> None:

        if self._pick_mode == mode:
            return

        self._pick_mode = mode
        self.pick_mode_changed.emit(mode)

    @staticmethod
    def _resolve_pick_dialog(host: QWidget | None) -> QDialog | None:

        if host is None:
            return None

        if isinstance(host, QDialog):
            return host

        widget: QWidget | None = host

        while widget is not None:
            if isinstance(widget, QDialog):
                return widget

            widget = widget.parentWidget()

        top = host.window()

        if isinstance(top, QDialog):
            return top

        return None

    @staticmethod
    def release_application_modality(*dialogs: QDialog | None) -> None:

        app = QApplication.instance()

        if app is None:
            return

        seen: set[int] = set()
        candidates: list[QDialog] = []

        for dialog in dialogs:
            if dialog is None:
                continue

            key = id(dialog)

            if key in seen:
                continue

            seen.add(key)
            candidates.append(dialog)

        active_modal = app.activeModalWidget()

        if isinstance(active_modal, QDialog):
            key = id(active_modal)

            if key not in seen:
                seen.add(key)
                candidates.append(active_modal)

        for dialog in candidates:
            dialog.setModal(False)
            dialog.setWindowModality(Qt.WindowModality.NonModal)

    def _suspend_pick_host(self, host: QWidget | None) -> None:

        dialog = self._resolve_pick_dialog(host)
        parent = self._dialog_parent

        if parent is not None and not parent.isVisible():
            parent.show()

        if dialog is not None:
            self._pick_host = dialog
            self._pick_host_was_modal = dialog.isModal()
            self.release_application_modality(dialog)

            if dialog.isVisible():
                dialog.hide()

        self.release_application_modality()

        if parent is not None:
            parent.raise_()
            parent.activateWindow()
            parent.setFocus(Qt.FocusReason.OtherFocusReason)

        self._widget.raise_()
        self._widget.setFocus(Qt.FocusReason.OtherFocusReason)

    def _restore_pick_host(self) -> None:

        dialog = self._pick_host
        self._pick_host = None

        if dialog is None:
            return

        dialog.show()

        if self._pick_host_was_modal:
            dialog.setModal(True)

        dialog.raise_()
        dialog.activateWindow()
        self._pick_host_was_modal = False
