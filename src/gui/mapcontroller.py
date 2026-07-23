from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, QTimer, Signal

from debug.obs_freeze_trace import trace_block, trace_enter, trace_exit, trace_event, trace_timer_callback
from gui.map_core import MAP_PAGE_INDEX, PickMode
from gui.observationreferencedialog import ObservationReferenceDialog
from gui.widgets.mapwidget import MapWidget
from i18n import tr
from observation import observation_manager
from PySide6.QtWidgets import QApplication, QDialog, QWidget
from shiboken6 import isValid


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
        self._show_parent_during_pick = True
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

    def set_show_parent_during_pick(self, enabled: bool) -> None:

        self._show_parent_during_pick = bool(enabled)

    def show_parent_during_pick(self) -> bool:

        return self._show_parent_during_pick

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
        self.request_show_map()
        QTimer.singleShot(
            0,
            trace_timer_callback(
                "MapController.begin_location_pick->QTimer._start_pick_session",
                self._start_pick_session,
            ),
        )

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

        with trace_block("MapController.on_map_page_visible"):
            self.clear_stale_pick_mode()

            if self._pick_mode != PickMode.LOCATION:
                return

            self.activate_location_pick()

            for delay_ms in (50, 150):
                QTimer.singleShot(
                    delay_ms,
                    trace_timer_callback(
                        f"MapController.on_map_page_visible->refresh({delay_ms}ms)",
                        self._widget.refresh_location_pick_view,
                    ),
                )
                QTimer.singleShot(
                    delay_ms,
                    trace_timer_callback(
                        f"MapController.on_map_page_visible->focus({delay_ms}ms)",
                        self._focus_map_for_pick,
                    ),
                )

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

        with trace_block(
            f"MapController.cancel_pick_mode restore_host={restore_host}"
        ):
            self._pending_pick_host = None
            self._pending_pick_message = None
            self._location_pick_callback = None
            self._set_pick_mode(PickMode.NONE)
            self._widget.end_location_pick()
            self.release_application_modality()

            if restore_host:
                self._restore_pick_host()
            else:
                self._pick_host = None
                self._pick_host_was_modal = False

    def pick_mode(self) -> PickMode:

        return self._pick_mode

    def clear_stale_pick_mode(self) -> None:

        if self._pick_mode != PickMode.LOCATION:
            return

        if self._location_pick_callback is not None:
            return

        trace_event(
            "MapController.clear_stale_pick_mode orphaned PickMode.LOCATION"
        )
        self.cancel_pick_mode(restore_host=False)

    def refresh_observation_points(self) -> None:

        with trace_block("MapController.refresh_observation_points"):
            trace_enter("MapController.refresh_observation_points.observation_manager.all")
            points = observation_manager.all()
            trace_exit("MapController.refresh_observation_points.observation_manager.all")

            trace_enter("MapController.refresh_observation_points.observation_manager.reference")
            reference = observation_manager.reference()
            reference_id = reference.id if reference else None
            trace_exit("MapController.refresh_observation_points.observation_manager.reference")

            def _point_payload(point) -> dict:
                return {
                    "id": point.id,
                    "name": point.name,
                    "lat": point.latitude,
                    "lon": point.longitude,
                    "active": point.active,
                    "reference": point.id == reference_id,
                    "coverage_radius_km": point.coverage_radius_km,
                }

            if self._pick_mode == PickMode.LOCATION:
                if points:
                    payload = [_point_payload(point) for point in points]
                    self._widget.set_observation_points(payload)
                return

            if not points:
                trace_enter("MapController.refresh_observation_points.clear_observation_points")
                self._widget.clear_observation_points(
                    tr("No observation point configured")
                )
                trace_exit("MapController.refresh_observation_points.clear_observation_points")
                return

            trace_enter("MapController.refresh_observation_points.build_payload")
            payload = [_point_payload(point) for point in points]
            trace_exit("MapController.refresh_observation_points.build_payload")

            trace_enter("MapController.refresh_observation_points.set_observation_points")
            self._widget.set_observation_points(payload)
            trace_exit("MapController.refresh_observation_points.set_observation_points")

    def update_ships(self, payload: str) -> None:

        with trace_block(
            f"MapController.update_ships bytes={len(payload)}"
        ):
            self._widget.update_ships(payload)

    def focus_ship(self, mmsi: int) -> None:

        self._widget.focus_ship(mmsi)

    def set_playback_active(self, mmsi: int | None) -> None:

        self._widget.set_playback_active(mmsi)

    def set_playback_trail(self, points: list[tuple[float, float]]) -> None:

        self._widget.set_playback_trail(points)

    def set_playback_cursor(
        self,
        lat: float | None,
        lon: float | None,
        heading: float | None = None,
    ) -> None:

        self._widget.set_playback_cursor(lat, lon, heading)

    def clear_playback(self) -> None:

        self._widget.clear_playback()

    def maybe_prompt_reference_selection(self) -> None:

        with trace_block("MapController.maybe_prompt_reference_selection"):
            if self._reference_prompt_open:
                return

            trace_enter("MapController.maybe_prompt_reference_selection.needs_reference_selection")
            needs_reference = observation_manager.needs_reference_selection()
            trace_exit("MapController.maybe_prompt_reference_selection.needs_reference_selection")

            if not needs_reference:
                return

            trace_enter("MapController.maybe_prompt_reference_selection.active_points")
            active_points = observation_manager.active_points()
            trace_exit("MapController.maybe_prompt_reference_selection.active_points")

            if len(active_points) <= 1:
                return

            parent = self._dialog_parent
            self._reference_prompt_open = True

            try:
                trace_enter("MapController.maybe_prompt_reference_selection.create_dialog")
                dialog = ObservationReferenceDialog(active_points, parent)
                trace_exit("MapController.maybe_prompt_reference_selection.create_dialog")

                trace_enter("MapController.maybe_prompt_reference_selection.dialog.exec")
                accepted = dialog.exec() == QDialog.DialogCode.Accepted
                trace_exit("MapController.maybe_prompt_reference_selection.dialog.exec")

                if not accepted:
                    return

                point_id = dialog.selected_point_id()

                if point_id:
                    trace_enter("MapController.maybe_prompt_reference_selection.set_reference")
                    observation_manager.set_reference(point_id)
                    trace_exit("MapController.maybe_prompt_reference_selection.set_reference")
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
        self._clear_pick_host()
        self.release_application_modality()

        try:
            callback(latitude, longitude)
        except RuntimeError:
            trace_event(
                "MapController._on_location_selected ignored deleted pick host"
            )

    def _set_pick_mode(self, mode: PickMode) -> None:

        if self._pick_mode == mode:
            return

        trace_enter(f"MapController._set_pick_mode {self._pick_mode}->{mode}")
        self._pick_mode = mode
        self.pick_mode_changed.emit(mode)
        trace_exit(f"MapController._set_pick_mode {self._pick_mode}")

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

        if (
            self._show_parent_during_pick
            and parent is not None
            and isValid(parent)
            and not parent.isVisible()
        ):
            parent.show()

        if dialog is not None and isValid(dialog):
            self._pick_host = dialog
            self._pick_host_was_modal = dialog.isModal()
            self.release_application_modality(dialog)

            if dialog.isVisible():
                dialog.hide()

        self.release_application_modality()

        if parent is not None and isValid(parent):
            parent.raise_()
            parent.activateWindow()
            parent.setFocus(Qt.FocusReason.OtherFocusReason)

        self._widget.raise_()
        self._widget.setFocus(Qt.FocusReason.OtherFocusReason)

    def _restore_pick_host(self) -> None:

        dialog = self._pick_host
        self._pick_host = None

        if dialog is None or not isValid(dialog):
            return

        dialog.show()

        if self._pick_host_was_modal:
            dialog.setModal(True)

        dialog.raise_()
        dialog.activateWindow()
        self._pick_host_was_modal = False

    def _clear_pick_host(self) -> None:

        self._pick_host = None
        self._pick_host_was_modal = False
