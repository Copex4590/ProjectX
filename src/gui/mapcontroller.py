from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import (
    QDialog,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QWidget,
)

from camera import camera_manager
from gui.camerawizard import CameraWizard
from gui.observationreferencedialog import ObservationReferenceDialog
from gui.widgets.mapwidget import MapWidget
from i18n import tr
from observation import observation_manager


class _RenameDialog(QDialog):

    def __init__(self, current_name: str, parent: QWidget | None = None):
        super().__init__(parent)

        self.setModal(True)
        self.setMinimumWidth(360)

        from PySide6.QtWidgets import (
            QDialogButtonBox,
            QLabel,
            QLineEdit,
            QVBoxLayout,
        )
        from gui.i18n_support import bind_language_refresh

        layout = QVBoxLayout(self)

        self._label = QLabel()
        layout.addWidget(self._label)

        self._input = QLineEdit(current_name)
        layout.addWidget(self._input)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self._button_box)

        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("Rename"))
        self._label.setText(tr("Observation Point name"))
        self._button_box.button(
            QDialogButtonBox.StandardButton.Ok
        ).setText(tr("Confirm"))
        self._button_box.button(
            QDialogButtonBox.StandardButton.Cancel
        ).setText(tr("Cancel"))

    def name(self) -> str:

        return self._input.text().strip()


class MapController(QObject):

    _instance: MapController | None = None

    def __init__(self):
        super().__init__()

        self._dialog_parent: QWidget | None = None
        self._reference_prompt_open = False
        self._widget = MapWidget()
        self._widget.observationActionRequested.connect(
            self._handle_observation_action
        )
        self._widget.mapEmptyActionRequested.connect(
            self._handle_map_empty_action
        )
        self._widget.observationMoved.connect(self._handle_observation_moved)

    @classmethod
    def instance(cls) -> MapController:

        if cls._instance is None:
            cls._instance = MapController()

        return cls._instance

    def widget(self) -> MapWidget:

        return self._widget

    def set_dialog_parent(self, parent: QWidget | None) -> None:

        self._dialog_parent = parent

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

    def _parent(self) -> QWidget | None:

        return self._dialog_parent

    def _handle_map_empty_action(
        self,
        action: str,
        latitude: float,
        longitude: float,
    ) -> None:

        if action != "create":
            return

        parent = self._parent()
        name, accepted = QInputDialog.getText(
            parent,
            tr("Create observation point"),
            tr("Observation Point name"),
            QLineEdit.EchoMode.Normal,
            tr("Observation Point"),
        )

        if not accepted:
            return

        observation_manager.create(
            name,
            latitude,
            longitude,
            set_active=True,
        )
        self.maybe_prompt_reference_selection()

    def _handle_observation_moved(
        self,
        point_id: str,
        latitude: float,
        longitude: float,
    ) -> None:

        observation_manager.move(point_id, latitude, longitude)
        self._widget.enable_move_mode(None)

    def _handle_observation_action(self, point_id: str, action: str) -> None:

        point = observation_manager.get(point_id)

        if point is None:
            return

        parent = self._parent()

        if action == "rename":
            dialog = _RenameDialog(point.name, parent)

            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            observation_manager.rename(point_id, dialog.name())
            return

        if action == "move":
            self._widget.enable_move_mode(point_id)
            QMessageBox.information(
                parent,
                tr("Move observation point"),
                tr("Click the map to place the observation point at a new location."),
            )
            return

        if action == "activate":
            observation_manager.activate_point(point_id)
            self.maybe_prompt_reference_selection()
            return

        if action == "deactivate":
            observation_manager.deactivate_point(point_id)
            self.maybe_prompt_reference_selection()
            return

        if action == "delete":
            answer = QMessageBox.question(
                parent,
                tr("Delete"),
                tr("Delete observation point '{name}'?").format(
                    name=point.name
                ),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if answer != QMessageBox.StandardButton.Yes:
                return

            observation_manager.delete(point_id)
            self.maybe_prompt_reference_selection()
            return

        if action == "assign_camera":
            wizard = CameraWizard(point_id, parent)

            if wizard.exec() == CameraWizard.DialogCode.Accepted:
                camera_manager.load()

            return

        if action == "open_camera":
            cameras = camera_manager.by_observation(point_id)

            if not cameras:
                QMessageBox.information(
                    parent,
                    tr("Open camera"),
                    tr("No camera is assigned to this observation point."),
                )
                return

            QMessageBox.information(
                parent,
                tr("Open camera"),
                tr(
                    "Camera playback opens from the map sidebar for now. "
                    "A dedicated resizable camera window arrives in a later phase."
                ),
            )
