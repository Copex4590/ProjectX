from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.i18n_support import bind_language_refresh
from gui.mapcontroller import MapController
from gui.wizardhelp import add_wizard_back_button, add_wizard_next_button
from i18n import tr
from observation import observation_manager


class ObservationSetupWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._picked_lat: float | None = None
        self._picked_lon: float | None = None

        self._build_ui()
        self._connect_signals()

    def refresh_translations(self) -> None:

        self._step1_title.setText(tr("Step 1 — Observation Point name"))
        self._name_label.setText(tr("Observation Point name"))
        self._name_input.setPlaceholderText(tr("Home"))
        self._examples_label.setText(
            tr(
                "Examples: Home, Hotel Victoria, Parliament, "
                "River Bank, Observation Deck"
            )
        )
        self._step2_title.setText(tr("Step 2 — Choose location"))
        self._map_option.setText(tr("Click on map"))
        self._coords_option.setText(tr("Enter coordinates"))
        self._latitude_label.setText(tr("Latitude"))
        self._longitude_label.setText(tr("Longitude"))
        self._pick_map_button.setText(tr("Select location on Map"))
        self._map_help_label.setText(
            tr("Use the central Map to choose a location.")
        )
        self._update_picked_coords_label()

    def substep_index(self) -> int:

        return self._stack.currentIndex()

    def on_enter(self) -> None:

        if self.substep_index() != 1:
            return

        self._sync_location_mode()

        if self._map_option.isChecked():
            self._start_map_pick()

    def on_leave(self) -> None:

        MapController.instance().cancel_pick_mode()

    def handle_next(self) -> bool:

        if self.substep_index() != 0:
            return False

        if not self._name_input.text().strip():
            return False

        self._picked_lat = None
        self._picked_lon = None
        self._stack.setCurrentIndex(1)
        self._sync_location_mode()
        if self._map_option.isChecked():
            self._start_map_pick()
        return False

    def handle_back(self) -> bool:

        if self.substep_index() != 1:
            return True

        MapController.instance().cancel_pick_mode()
        self._stack.setCurrentIndex(0)
        return False

    def handle_confirm(self) -> bool:

        name = self._name_input.text().strip()

        if not name:
            return False

        if self._picked_lat is None or self._picked_lon is None:
            return False

        observation_manager.create(
            name,
            self._picked_lat,
            self._picked_lon,
            set_active=True,
        )
        return True

    def update_outer_buttons(
        self,
        back_button,
        next_button,
        confirm_button,
    ) -> None:

        on_location_step = self.substep_index() == 1

        back_button.setEnabled(on_location_step)
        next_button.setVisible(not on_location_step)
        confirm_button.setVisible(on_location_step)

    def _build_ui(self) -> None:

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        step1 = QWidget()
        step1_layout = QVBoxLayout(step1)
        self._step1_title = QLabel()
        self._step1_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        step1_layout.addWidget(self._step1_title)

        form = QFormLayout()
        self._name_label = QLabel()
        self._name_input = QLineEdit()
        form.addRow(self._name_label, self._name_input)
        step1_layout.addLayout(form)

        self._examples_label = QLabel()
        self._examples_label.setWordWrap(True)
        self._examples_label.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        step1_layout.addWidget(self._examples_label)
        step1_layout.addStretch()
        self._stack.addWidget(step1)

        step2 = QWidget()
        step2_layout = QVBoxLayout(step2)
        self._step2_title = QLabel()
        self._step2_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        step2_layout.addWidget(self._step2_title)

        mode_row = QHBoxLayout()
        self._map_option = QRadioButton()
        self._coords_option = QRadioButton()
        self._map_option.setChecked(True)
        mode_row.addWidget(self._map_option)
        mode_row.addWidget(self._coords_option)
        mode_row.addStretch()
        step2_layout.addLayout(mode_row)

        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._map_option, 0)
        self._mode_group.addButton(self._coords_option, 1)

        self._map_panel = QWidget()
        map_panel_layout = QVBoxLayout(self._map_panel)
        map_panel_layout.setContentsMargins(0, 0, 0, 0)
        map_panel_layout.setSpacing(8)

        self._map_help_label = QLabel()
        self._map_help_label.setWordWrap(True)
        self._map_help_label.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        map_panel_layout.addWidget(self._map_help_label)

        self._pick_map_button = QPushButton()
        self._pick_map_button.setStyleSheet("""
            QPushButton {
                background: #243651;
                color: white;
                border: 1px solid #2d5a8e;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QPushButton:hover { background: #2d4a6f; }
        """)
        map_panel_layout.addWidget(self._pick_map_button)

        self._picked_coords_label = QLabel()
        self._picked_coords_label.setWordWrap(True)
        self._picked_coords_label.setStyleSheet("color: white; font-weight: 600;")
        map_panel_layout.addWidget(self._picked_coords_label)
        step2_layout.addWidget(self._map_panel)

        coords_form = QFormLayout()
        self._latitude_label = QLabel()
        self._longitude_label = QLabel()
        self._latitude_input = QDoubleSpinBox()
        self._latitude_input.setRange(-90.0, 90.0)
        self._latitude_input.setDecimals(5)
        self._latitude_input.setValue(0.0)
        self._longitude_input = QDoubleSpinBox()
        self._longitude_input.setRange(-180.0, 180.0)
        self._longitude_input.setDecimals(5)
        self._longitude_input.setValue(0.0)
        coords_form.addRow(self._latitude_label, self._latitude_input)
        coords_form.addRow(self._longitude_label, self._longitude_input)
        self._coords_panel = QWidget()
        self._coords_panel.setLayout(coords_form)
        self._coords_panel.setVisible(False)
        step2_layout.addWidget(self._coords_panel)
        step2_layout.addStretch()
        self._stack.addWidget(step2)

        self._sync_location_mode()

    def _connect_signals(self) -> None:

        self._mode_group.idClicked.connect(self._on_mode_changed)
        self._pick_map_button.clicked.connect(self._start_map_pick)
        self._latitude_input.valueChanged.connect(self._on_coords_changed)
        self._longitude_input.valueChanged.connect(self._on_coords_changed)

    def _start_map_pick(self) -> None:

        host = self._pick_host_dialog()
        MapController.instance().begin_location_pick(
            self._on_map_location,
            host=host,
        )

    def _pick_host_dialog(self) -> QDialog | None:

        widget: QWidget | None = self

        while widget is not None:
            if isinstance(widget, QDialog):
                return widget

            widget = widget.parentWidget()

        top = self.window()

        if isinstance(top, QDialog):
            return top

        return None

    def _on_mode_changed(self, _button_id: int) -> None:

        self._sync_location_mode()

        if self._map_option.isChecked() and self.substep_index() == 1:
            self._start_map_pick()

    def _sync_location_mode(self) -> None:

        use_map = self._map_option.isChecked()
        self._map_panel.setVisible(use_map)
        self._coords_panel.setVisible(not use_map)

        if not use_map:
            MapController.instance().cancel_pick_mode()
            self._picked_lat = self._latitude_input.value()
            self._picked_lon = self._longitude_input.value()
            self._update_picked_coords_label()
            return

        self._update_picked_coords_label()

    def _on_map_location(self, latitude: float, longitude: float) -> None:

        self._picked_lat = latitude
        self._picked_lon = longitude
        self._latitude_input.setValue(latitude)
        self._longitude_input.setValue(longitude)
        self._update_picked_coords_label()

    def _on_coords_changed(self) -> None:

        if self._coords_option.isChecked():
            self._picked_lat = self._latitude_input.value()
            self._picked_lon = self._longitude_input.value()
            self._update_picked_coords_label()

    def _update_picked_coords_label(self) -> None:

        if self._picked_lat is None or self._picked_lon is None:
            self._picked_coords_label.setText(tr("No location selected"))
            return

        self._picked_coords_label.setText(
            f"{self._picked_lat:.5f}, {self._picked_lon:.5f}"
        )


class ObservationWizard(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModal(False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumWidth(560)
        self.setMinimumHeight(420)

        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("Observation Point Setup"))
        self._setup.refresh_translations()
        self._back_button.setText(
            tr("Back")
        )
        self._next_button.setText(
            tr("Next")
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            tr("Cancel")
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            tr("Confirm")
        )
        self._sync_buttons()

    def _build_ui(self) -> None:

        self.setStyleSheet("""
            QDialog {
                background: #1d2127;
            }

            QLabel {
                color: #d5dbe3;
            }

            QLineEdit, QDoubleSpinBox {
                background: #252a31;
                color: white;
                border: 1px solid #3d4a5c;
                border-radius: 6px;
                padding: 6px 8px;
            }

            QRadioButton {
                color: #d5dbe3;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._setup = ObservationSetupWidget()
        layout.addWidget(self._setup)

        self._button_box = QDialogButtonBox()
        self._back_button = add_wizard_back_button(self._button_box)
        self._next_button = add_wizard_next_button(self._button_box)
        self._button_box.addButton(
            QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.addButton(
            QDialogButtonBox.StandardButton.Ok
        )
        self._back_button.setEnabled(
            False
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setVisible(
            False
        )
        layout.addWidget(self._button_box)

    def _connect_signals(self) -> None:

        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)
        self._next_button.clicked.connect(
            self._on_next
        )
        self._back_button.clicked.connect(
            self._on_back
        )

    def _sync_buttons(self) -> None:

        self._setup.update_outer_buttons(
            self._back_button,
            self._next_button,
            self._button_box.button(QDialogButtonBox.StandardButton.Ok),
        )

    def _on_next(self) -> None:

        self._setup.handle_next()
        self._sync_buttons()

    def _on_back(self) -> None:

        if self._setup.handle_back():
            self._back_button.setEnabled(False)

        self._sync_buttons()

    def _on_accept(self) -> None:

        if self._setup.handle_confirm():
            self.accept()

    def reject(self) -> None:

        self._setup.on_leave()
        super().reject()

    def accept(self) -> None:

        self._setup.on_leave()
        super().accept()
