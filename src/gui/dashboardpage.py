from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from database import registry
from engines.rtl.hybrid_engine import CAMERA_LAT, CAMERA_LON
from camera import camera_manager
from gui.camerawizard import CameraWizard
from gui.i18n_support import bind_language_refresh
from gui.observationwizard import ObservationWizard
from gui.widgets.observationmapwidget import ObservationMapWidget
from i18n import tr
from logbook import logbook_manager
from observation import observation_manager


class InfoCard(QFrame):

    def __init__(self, title_key: str):

        super().__init__()

        self._title_key = title_key

        self.setStyleSheet("""
            QFrame{
                background:#252a31;
                border:1px solid #40444b;
                border-radius:10px;
            }
        """)

        layout = QVBoxLayout(self)

        self.title = QLabel(tr(title_key))
        self.title.setAlignment(Qt.AlignCenter)

        self.title.setStyleSheet("""
            color:#bbbbbb;
            font-size:12pt;
        """)

        self.value = QLabel("--")
        self.value.setAlignment(Qt.AlignCenter)

        self.value.setStyleSheet("""
            color:white;
            font-size:28pt;
            font-weight:bold;
        """)

        layout.addWidget(self.title)
        layout.addWidget(self.value)


class _RenameDialog(QDialog):

    def __init__(self, current_name: str, parent=None):
        super().__init__(parent)

        self.setModal(True)
        self.setMinimumWidth(360)

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
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            tr("Confirm")
        )
        self._button_box.button(
            QDialogButtonBox.StandardButton.Cancel
        ).setText(tr("Cancel"))

    def name(self) -> str:

        return self._input.text().strip()


class DashboardPage(QWidget):

    def __init__(self):
        super().__init__()

        self._move_mode = False
        self._move_lat = CAMERA_LAT
        self._move_lon = CAMERA_LON

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._title_label = QLabel(tr("Dashboard"))
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setStyleSheet("""
            font-size:26pt;
            font-weight:bold;
            color:white;
        """)
        layout.addWidget(self._title_label)

        self._observation_card = QFrame()
        self._observation_card.setStyleSheet("""
            QFrame {
                background: #252a31;
                border: 1px solid #40444b;
                border-radius: 10px;
            }
        """)
        observation_layout = QVBoxLayout(self._observation_card)
        observation_layout.setContentsMargins(16, 16, 16, 16)
        observation_layout.setSpacing(10)

        self._observation_title = QLabel()
        self._observation_title.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: white;"
        )
        observation_layout.addWidget(self._observation_title)

        info_grid = QGridLayout()
        info_grid.setColumnStretch(1, 1)

        self._name_caption = QLabel()
        self._name_value = QLabel()
        self._coords_caption = QLabel()
        self._coords_value = QLabel()
        self._status_caption = QLabel()
        self._status_value = QLabel()

        for caption in (
            self._name_caption,
            self._coords_caption,
            self._status_caption,
        ):
            caption.setStyleSheet("color: #9aa4af;")

        for value in (
            self._name_value,
            self._coords_value,
            self._status_value,
        ):
            value.setStyleSheet("color: white; font-weight: 600;")
            value.setWordWrap(True)

        info_grid.addWidget(self._name_caption, 0, 0)
        info_grid.addWidget(self._name_value, 0, 1)
        info_grid.addWidget(self._coords_caption, 1, 0)
        info_grid.addWidget(self._coords_value, 1, 1)
        info_grid.addWidget(self._status_caption, 2, 0)
        info_grid.addWidget(self._status_value, 2, 1)
        observation_layout.addLayout(info_grid)

        self._map_widget = ObservationMapWidget()
        self._map_widget.setMinimumHeight(220)
        observation_layout.addWidget(self._map_widget)

        self._move_hint = QLabel()
        self._move_hint.setWordWrap(True)
        self._move_hint.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        self._move_hint.setVisible(False)
        observation_layout.addWidget(self._move_hint)

        selector_row = QHBoxLayout()
        self._point_selector_label = QLabel()
        self._point_selector = QComboBox()
        selector_row.addWidget(self._point_selector_label)
        selector_row.addWidget(self._point_selector, 1)
        self._selector_panel = QWidget()
        self._selector_panel.setLayout(selector_row)
        self._selector_panel.setVisible(False)
        observation_layout.addWidget(self._selector_panel)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self._move_button = QPushButton()
        self._rename_button = QPushButton()
        self._create_button = QPushButton()
        self._delete_button = QPushButton()
        self._set_active_button = QPushButton()
        self._save_move_button = QPushButton()
        self._cancel_move_button = QPushButton()

        for button in (
            self._move_button,
            self._rename_button,
            self._create_button,
            self._delete_button,
            self._set_active_button,
            self._save_move_button,
            self._cancel_move_button,
        ):
            button.setStyleSheet("""
                QPushButton {
                    background: #343a42;
                    color: white;
                    border: 1px solid #4a5159;
                    border-radius: 6px;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background: #3f464f;
                }
                QPushButton:disabled {
                    color: #7a8494;
                }
            """)

        button_row.addWidget(self._move_button)
        button_row.addWidget(self._rename_button)
        button_row.addWidget(self._create_button)
        button_row.addWidget(self._delete_button)
        button_row.addWidget(self._set_active_button)
        button_row.addWidget(self._save_move_button)
        button_row.addWidget(self._cancel_move_button)
        button_row.addStretch()
        observation_layout.addLayout(button_row)

        self._save_move_button.setVisible(False)
        self._cancel_move_button.setVisible(False)

        layout.addWidget(self._observation_card)

        self._cameras_card = QFrame()
        self._cameras_card.setStyleSheet("""
            QFrame {
                background: #252a31;
                border: 1px solid #40444b;
                border-radius: 10px;
            }
        """)
        cameras_layout = QVBoxLayout(self._cameras_card)
        cameras_layout.setContentsMargins(16, 16, 16, 16)
        cameras_layout.setSpacing(10)

        self._cameras_title = QLabel()
        self._cameras_title.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: white;"
        )
        cameras_layout.addWidget(self._cameras_title)

        self._cameras_list = QVBoxLayout()
        self._cameras_list.setSpacing(6)
        cameras_layout.addLayout(self._cameras_list)

        self._no_cameras_label = QLabel()
        self._no_cameras_label.setStyleSheet("color: #9aa4af;")
        self._no_cameras_label.setVisible(False)
        cameras_layout.addWidget(self._no_cameras_label)

        self._add_camera_button = QPushButton()
        self._add_camera_button.setStyleSheet("""
            QPushButton {
                background: #343a42;
                color: white;
                border: 1px solid #4a5159;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: #3f464f;
            }
            QPushButton:disabled {
                color: #7a8494;
            }
        """)
        cameras_layout.addWidget(self._add_camera_button)
        layout.addWidget(self._cameras_card)

        self._logbook_card = QFrame()
        self._logbook_card.setStyleSheet("""
            QFrame {
                background: #252a31;
                border: 1px solid #40444b;
                border-radius: 10px;
            }
        """)
        logbook_layout = QVBoxLayout(self._logbook_card)
        logbook_layout.setContentsMargins(16, 16, 16, 16)
        logbook_layout.setSpacing(10)

        self._logbook_title = QLabel()
        self._logbook_title.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: white;"
        )
        logbook_layout.addWidget(self._logbook_title)

        self._import_logbook_button = QPushButton()
        self._import_logbook_button.setStyleSheet("""
            QPushButton {
                background: #343a42;
                color: white;
                border: 1px solid #4a5159;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: #3f464f;
            }
        """)
        logbook_layout.addWidget(self._import_logbook_button)
        layout.addWidget(self._logbook_card)

        grid = QGridLayout()

        self.ships = InfoCard("Ships")
        self.ais = InfoCard("AIS")
        self.last = InfoCard("Last Ship")

        self.ais.value.setText(tr("CONNECTED"))

        grid.addWidget(self.ships, 0, 0)
        grid.addWidget(self.ais, 0, 1)
        grid.addWidget(self.last, 0, 2)

        layout.addLayout(grid)
        layout.addStretch()

        self._move_button.clicked.connect(self._start_move_mode)
        self._save_move_button.clicked.connect(self._save_move)
        self._cancel_move_button.clicked.connect(self._cancel_move_mode)
        self._rename_button.clicked.connect(self._rename_active)
        self._create_button.clicked.connect(self._create_new)
        self._delete_button.clicked.connect(self._delete_active)
        self._set_active_button.clicked.connect(self._set_selected_active)
        self._point_selector.currentIndexChanged.connect(
            self._on_selector_changed
        )
        self._map_widget.locationSelected.connect(self._on_map_location)
        self._add_camera_button.clicked.connect(self._add_camera)
        self._import_logbook_button.clicked.connect(self._import_legacy_logbook)

        bind_language_refresh(self.refresh_translations)

        self.refresh_translations()
        self.update_dashboard()
        self.refresh_observation()
        self.refresh_cameras()

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Dashboard"))
        self.ships.title.setText(tr("Ships"))
        self.ais.title.setText(tr("AIS"))
        self.last.title.setText(tr("Last Ship"))
        self.ais.value.setText(tr("CONNECTED"))

        self._observation_title.setText(tr("Observation Point"))
        self._name_caption.setText(tr("Name"))
        self._coords_caption.setText(tr("Coordinates"))
        self._status_caption.setText(tr("Status"))
        self._point_selector_label.setText(tr("Observation Point"))
        self._move_hint.setText(
            tr("Click the map once. A red marker appears. Confirm to save.")
        )

        self._move_button.setText(tr("Move on map"))
        self._rename_button.setText(tr("Rename"))
        self._create_button.setText(tr("Create new"))
        self._delete_button.setText(tr("Delete"))
        self._set_active_button.setText(tr("Set active"))
        self._save_move_button.setText(tr("Confirm"))
        self._cancel_move_button.setText(tr("Cancel"))
        self._cameras_title.setText(tr("Attached Cameras"))
        self._no_cameras_label.setText(tr("No cameras attached."))
        self._add_camera_button.setText(tr("Add Camera"))
        self._logbook_title.setText(tr("Vessel Logbook"))
        self._import_logbook_button.setText(tr("Import Legacy Logbook"))

        self.refresh_observation()
        self.refresh_cameras()

    def refresh_observation(self) -> None:

        if self._move_mode:
            return

        points = observation_manager.all()
        active = observation_manager.active()

        self._populate_selector(points, active)

        if active is not None:
            self._name_value.setText(active.name)
            self._coords_value.setText(
                f"{active.latitude:.5f}, {active.longitude:.5f}"
            )
            self._status_value.setText(tr("Active"))
            self._map_widget.set_observation_point(
                active.latitude,
                active.longitude,
            )
            self._move_lat = active.latitude
            self._move_lon = active.longitude
            has_point = True
        else:
            self._name_value.setText(tr("Camera fallback"))
            self._coords_value.setText(
                f"{CAMERA_LAT:.5f}, {CAMERA_LON:.5f}"
            )
            self._status_value.setText(tr("Using CAMERA_LAT / CAMERA_LON"))
            self._map_widget.set_observation_point(CAMERA_LAT, CAMERA_LON)
            self._move_lat = CAMERA_LAT
            self._move_lon = CAMERA_LON
            has_point = False

        self._move_button.setEnabled(has_point)
        self._rename_button.setEnabled(has_point)
        self._delete_button.setEnabled(has_point)
        self._set_active_button.setEnabled(
            has_point and len(points) > 1
        )
        self._selector_panel.setVisible(len(points) > 1)
        self.refresh_cameras()

    def refresh_cameras(self) -> None:

        while self._cameras_list.count():
            item = self._cameras_list.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

        active = observation_manager.active()
        has_point = active is not None
        self._add_camera_button.setEnabled(has_point)

        if not has_point:
            self._no_cameras_label.setVisible(True)
            return

        cameras = camera_manager.by_observation(active.id)
        self._no_cameras_label.setVisible(not cameras)

        for camera in cameras:
            row = QHBoxLayout()
            row_widget = QWidget()
            row_widget.setLayout(row)

            name_label = QLabel(camera.name)
            name_label.setStyleSheet("color: white; font-weight: 600;")
            row.addWidget(name_label, 1)

            status_text = tr("Enabled") if camera.enabled else tr("Disabled")
            status_label = QLabel(status_text)
            status_label.setStyleSheet(
                "color: #66bb6a;" if camera.enabled else "color: #9aa4af;"
            )
            row.addWidget(status_label)

            edit_button = QPushButton(tr("Edit"))
            delete_button = QPushButton(tr("Delete"))

            for button in (edit_button, delete_button):
                button.setStyleSheet("""
                    QPushButton {
                        background: #343a42;
                        color: white;
                        border: 1px solid #4a5159;
                        border-radius: 6px;
                        padding: 4px 10px;
                    }
                    QPushButton:hover {
                        background: #3f464f;
                    }
                """)

            edit_button.clicked.connect(
                lambda _checked=False, item=camera: self._edit_camera(item)
            )
            delete_button.clicked.connect(
                lambda _checked=False, item=camera: self._delete_camera(item)
            )

            row.addWidget(edit_button)
            row.addWidget(delete_button)
            self._cameras_list.addWidget(row_widget)

    def _import_legacy_logbook(self) -> None:

        source = QFileDialog.getExistingDirectory(
            self,
            tr("Import Legacy Logbook"),
            "",
            QFileDialog.Option.ShowDirsOnly,
        )

        if not source:
            return

        try:
            result = logbook_manager.import_legacy(source)
        except FileNotFoundError as exc:
            QMessageBox.warning(
                self,
                tr("Import Legacy Logbook"),
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            tr("Import Legacy Logbook"),
            tr(
                "Legacy logbook import complete. "
                "Imported: {imported}, skipped: {skipped}."
            ).format(
                imported=result.imported_folders,
                skipped=result.skipped_folders,
            ),
        )

    def _add_camera(self) -> None:

        point_id = self._active_point_id()

        if point_id is None:
            return

        wizard = CameraWizard(point_id, self)

        if wizard.exec() == QDialog.DialogCode.Accepted:
            self.refresh_cameras()

    def _edit_camera(self, camera) -> None:

        point_id = self._active_point_id()

        if point_id is None:
            return

        wizard = CameraWizard(point_id, self, camera=camera)

        if wizard.exec() == QDialog.DialogCode.Accepted:
            self.refresh_cameras()

    def _delete_camera(self, camera) -> None:

        answer = QMessageBox.question(
            self,
            tr("Delete"),
            tr("Delete camera '{name}'?").format(name=camera.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        camera_manager.remove(camera.id)
        self.refresh_cameras()

    def _populate_selector(self, points, active) -> None:

        self._point_selector.blockSignals(True)
        self._point_selector.clear()

        for point in points:
            label = point.name

            if point.active:
                label = f"{label} ({tr('Active')})"

            self._point_selector.addItem(label, point.id)

        if active is not None:
            for index in range(self._point_selector.count()):
                if self._point_selector.itemData(index) == active.id:
                    self._point_selector.setCurrentIndex(index)
                    break

        self._point_selector.blockSignals(False)

    def _active_point_id(self) -> str | None:

        active = observation_manager.active()
        return active.id if active else None

    def _start_move_mode(self) -> None:

        point_id = self._active_point_id()

        if point_id is None:
            return

        active = observation_manager.active()

        if active is None:
            return

        self._move_mode = True
        self._move_lat = active.latitude
        self._move_lon = active.longitude

        self._move_hint.setVisible(True)
        self._save_move_button.setVisible(True)
        self._cancel_move_button.setVisible(True)
        self._move_button.setVisible(False)
        self._rename_button.setEnabled(False)
        self._create_button.setEnabled(False)
        self._delete_button.setEnabled(False)
        self._set_active_button.setEnabled(False)
        self._point_selector.setEnabled(False)

        self._map_widget.enable_pick_mode(True)
        self._map_widget.set_observation_point(
            self._move_lat,
            self._move_lon,
        )

    def _on_map_location(self, latitude: float, longitude: float) -> None:

        if not self._move_mode:
            return

        self._move_lat = latitude
        self._move_lon = longitude

    def _save_move(self) -> None:

        point_id = self._active_point_id()

        if point_id is None:
            self._cancel_move_mode()
            return

        observation_manager.move(point_id, self._move_lat, self._move_lon)
        self._exit_move_mode()
        self.refresh_observation()

    def _cancel_move_mode(self) -> None:

        self._exit_move_mode()
        self.refresh_observation()

    def _exit_move_mode(self) -> None:

        self._move_mode = False
        self._move_hint.setVisible(False)
        self._save_move_button.setVisible(False)
        self._cancel_move_button.setVisible(False)
        self._move_button.setVisible(True)
        self._rename_button.setEnabled(True)
        self._create_button.setEnabled(True)
        self._map_widget.enable_pick_mode(False)
        self._point_selector.setEnabled(True)

    def _rename_active(self) -> None:

        active = observation_manager.active()

        if active is None:
            return

        dialog = _RenameDialog(active.name, self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        new_name = dialog.name()

        if not new_name:
            return

        observation_manager.rename(active.id, new_name)

    def _create_new(self) -> None:

        wizard = ObservationWizard(self)

        if wizard.exec() == QDialog.DialogCode.Accepted:
            self.refresh_observation()

    def _delete_active(self) -> None:

        active = observation_manager.active()

        if active is None:
            return

        answer = QMessageBox.question(
            self,
            tr("Delete"),
            tr("Delete observation point '{name}'?").format(
                name=active.name
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        observation_manager.delete(active.id)

    def _set_selected_active(self) -> None:

        point_id = self._point_selector.currentData()

        if not point_id:
            return

        observation_manager.set_active(str(point_id))

    def _on_selector_changed(self, _index: int) -> None:

        if self._move_mode:
            return

        point_id = self._point_selector.currentData()

        if not point_id:
            return

        active = observation_manager.active()

        if active is not None and active.id == point_id:
            return

        observation_manager.set_active(str(point_id))

    def update_dashboard(self):

        ships = registry.all()

        self.ships.value.setText(str(len(ships)))

        if ships:
            self.last.value.setText(ships[-1].name)
        else:
            self.last.value.setText("--")

    def on_ship_updated(self):

        ships = registry.all()

        self.ships.value.setText(str(len(ships)))

        if ships:
            self.last.value.setText(ships[-1].name)
        else:
            self.last.value.setText("--")
