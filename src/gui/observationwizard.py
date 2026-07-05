# ============================================================================
# Project X
# Observation Point Setup Wizard
# ============================================================================

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
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from engines.rtl.hybrid_engine import CAMERA_LAT, CAMERA_LON
from gui.i18n_support import bind_language_refresh
from gui.widgets.observationmapwidget import ObservationMapWidget
from i18n import tr
from observation import observation_manager


class ObservationSetupWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._picked_lat = CAMERA_LAT
        self._picked_lon = CAMERA_LON

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
        self._confirm_label.setText(
            tr("Click the map once. A red marker appears. Confirm to save.")
        )

    def substep_index(self) -> int:

        return self._stack.currentIndex()

    def on_enter(self) -> None:

        if self.substep_index() == 1:
            self._sync_location_mode()

    def on_leave(self) -> None:

        self._map_widget.enable_pick_mode(False)

    def handle_next(self) -> bool:

        if self.substep_index() != 0:
            return False

        if not self._name_input.text().strip():
            return False

        self._stack.setCurrentIndex(1)
        self._sync_location_mode()
        return False

    def handle_back(self) -> bool:

        if self.substep_index() != 1:
            return True

        self._stack.setCurrentIndex(0)
        self._map_widget.enable_pick_mode(False)
        return False

    def handle_confirm(self) -> bool:

        name = self._name_input.text().strip()

        if not name:
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

        self._map_widget = ObservationMapWidget()
        self._map_widget.setMinimumHeight(260)
        step2_layout.addWidget(self._map_widget)

        coords_form = QFormLayout()
        self._latitude_label = QLabel()
        self._longitude_label = QLabel()
        self._latitude_input = QDoubleSpinBox()
        self._latitude_input.setRange(-90.0, 90.0)
        self._latitude_input.setDecimals(5)
        self._latitude_input.setValue(CAMERA_LAT)
        self._longitude_input = QDoubleSpinBox()
        self._longitude_input.setRange(-180.0, 180.0)
        self._longitude_input.setDecimals(5)
        self._longitude_input.setValue(CAMERA_LON)
        coords_form.addRow(self._latitude_label, self._latitude_input)
        coords_form.addRow(self._longitude_label, self._longitude_input)
        self._coords_panel = QWidget()
        self._coords_panel.setLayout(coords_form)
        self._coords_panel.setVisible(False)
        step2_layout.addWidget(self._coords_panel)

        self._confirm_label = QLabel()
        self._confirm_label.setWordWrap(True)
        self._confirm_label.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        step2_layout.addWidget(self._confirm_label)

        self._stack.addWidget(step2)

        self._map_widget.set_observation_point(self._picked_lat, self._picked_lon)
        self._sync_location_mode()

    def _connect_signals(self) -> None:

        self._mode_group.idClicked.connect(self._on_mode_changed)
        self._map_widget.locationSelected.connect(self._on_map_location)
        self._latitude_input.valueChanged.connect(self._on_coords_changed)
        self._longitude_input.valueChanged.connect(self._on_coords_changed)

    def _on_mode_changed(self, _button_id: int) -> None:

        self._sync_location_mode()

    def _sync_location_mode(self) -> None:

        use_map = self._map_option.isChecked()
        self._map_widget.setVisible(use_map)
        self._coords_panel.setVisible(not use_map)
        self._map_widget.enable_pick_mode(use_map)

        if use_map:
            self._map_widget.set_observation_point(
                self._picked_lat,
                self._picked_lon,
            )
        else:
            self._picked_lat = self._latitude_input.value()
            self._picked_lon = self._longitude_input.value()

    def _on_map_location(self, latitude: float, longitude: float) -> None:

        self._picked_lat = latitude
        self._picked_lon = longitude
        self._latitude_input.setValue(latitude)
        self._longitude_input.setValue(longitude)

    def _on_coords_changed(self) -> None:

        if self._coords_option.isChecked():
            self._picked_lat = self._latitude_input.value()
            self._picked_lon = self._longitude_input.value()
            self._map_widget.set_observation_point(
                self._picked_lat,
                self._picked_lon,
            )


class ObservationWizard(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModal(True)
        self.setMinimumWidth(560)
        self.setMinimumHeight(520)

        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("Observation Point Setup"))
        self._setup.refresh_translations()
        self._button_box.button(QDialogButtonBox.StandardButton.Back).setText(
            tr("Back")
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Next).setText(
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
                border: 1px solid #40444b;
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
        self._button_box.addButton(
            QDialogButtonBox.StandardButton.Back
        )
        self._button_box.addButton(
            QDialogButtonBox.StandardButton.Next
        )
        self._button_box.addButton(
            QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.addButton(
            QDialogButtonBox.StandardButton.Ok
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Back).setEnabled(
            False
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setVisible(
            False
        )
        layout.addWidget(self._button_box)

    def _connect_signals(self) -> None:

        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)
        self._button_box.button(QDialogButtonBox.StandardButton.Next).clicked.connect(
            self._on_next
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Back).clicked.connect(
            self._on_back
        )

    def _sync_buttons(self) -> None:

        self._setup.update_outer_buttons(
            self._button_box.button(QDialogButtonBox.StandardButton.Back),
            self._button_box.button(QDialogButtonBox.StandardButton.Next),
            self._button_box.button(QDialogButtonBox.StandardButton.Ok),
        )

    def _on_next(self) -> None:

        self._setup.handle_next()
        self._sync_buttons()

    def _on_back(self) -> None:

        if self._setup.handle_back():
            self._button_box.button(
                QDialogButtonBox.StandardButton.Back
            ).setEnabled(False)

        self._sync_buttons()

    def _on_accept(self) -> None:

        if self._setup.handle_confirm():
            self.accept()
