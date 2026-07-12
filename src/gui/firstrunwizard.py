# ============================================================================
# First Run Wizard
# ============================================================================

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from debug.obs_freeze_trace import trace_block
from gui.i18n_support import bind_language_refresh
from gui.mapcontroller import MapController
from gui.wizardhelp import add_wizard_back_button, add_wizard_next_button
from i18n import tr
from observation import observation_manager
from observation.coords import max_observation_radius_km
from preferences import preferences_manager

_DEFAULT_COVERAGE_RADIUS_KM = 25.0

_STEP_NAME = 0
_STEP_RADIUS = 1

_NAME_INPUT_STYLE = """
    background: #252a31;
    color: white;
    border: 1px solid #3d4a5c;
    border-radius: 6px;
    padding: 6px 8px;
"""

_NAME_INPUT_ERROR_STYLE = """
    background: #252a31;
    color: white;
    border: 1px solid #e53935;
    border-radius: 6px;
    padding: 6px 8px;
"""


class _FirstRunSuccessDialog(QDialog):

    def __init__(
        self,
        name: str,
        latitude: float,
        longitude: float,
        parent=None,
    ):
        super().__init__(parent)

        self.setModal(True)
        self.setMinimumWidth(420)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel(
            "✓ "
            + tr("First observation point created successfully")
        )
        title.setWordWrap(True)
        title.setStyleSheet(
            "font-size: 14pt; font-weight: bold; color: #e8f5e9;"
        )
        layout.addWidget(title)

        point_label = QLabel(tr("Observation Point"))
        point_label.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        layout.addWidget(point_label)

        point_value = QLabel(name)
        point_value.setStyleSheet(
            "color: white; font-size: 13pt; font-weight: 600;"
        )
        layout.addWidget(point_value)

        layout.addSpacing(4)

        coords_label = QLabel(tr("Coordinates"))
        coords_label.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        layout.addWidget(coords_label)

        lat_value = QLabel(f"{latitude:.6f}")
        lat_value.setStyleSheet("color: white; font-size: 13pt;")
        layout.addWidget(lat_value)

        lon_value = QLabel(f"{longitude:.6f}")
        lon_value.setStyleSheet("color: white; font-size: 13pt;")
        layout.addWidget(lon_value)

        layout.addSpacing(8)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self._continue_button = QPushButton(tr("Continue"))
        self._continue_button.setMinimumWidth(120)
        self._continue_button.clicked.connect(self.accept)
        button_row.addWidget(self._continue_button)
        layout.addLayout(button_row)

        self.setStyleSheet("""
            QDialog {
                background: #1d2127;
            }

            QPushButton {
                background: #243651;
                color: white;
                border: 1px solid #2d5a8e;
                border-radius: 6px;
                padding: 8px 20px;
            }

            QPushButton:hover {
                background: #2d4a6f;
            }
        """)


class FirstRunWizard(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModal(False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumWidth(560)
        self.setMinimumHeight(420)

        self._picked_lat: float | None = None
        self._picked_lon: float | None = None

        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self._stack.setCurrentIndex(_STEP_NAME)
        self._sync_buttons()
        QTimer.singleShot(0, self._focus_name_input)

    def showEvent(self, event) -> None:

        super().showEvent(event)

        if self._stack.currentIndex() == _STEP_NAME:
            QTimer.singleShot(0, self._focus_name_input)

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("Project X Setup"))
        self._name_title.setText(tr("Observation Point Name"))
        self._name_input.setPlaceholderText(tr("e.g. Home"))
        self._name_error.setText(
            tr("Enter the observation point name first.")
        )
        self._radius_title.setText(tr("Observation radius (km)"))
        self._coverage_radius_label.setText(tr("Observation radius (km)"))
        self._continue_button.setText(tr("Continue"))
        self._back_button.setText(tr("Back"))
        self._button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            tr("Cancel")
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

            QPushButton {
                background: #243651;
                color: white;
                border: 1px solid #2d5a8e;
                border-radius: 6px;
                padding: 6px 12px;
            }

            QPushButton:hover {
                background: #2d4a6f;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        name_page = QWidget()
        name_layout = QVBoxLayout(name_page)
        self._name_title = QLabel()
        self._name_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        name_layout.addWidget(self._name_title)
        self._name_input = QLineEdit()
        self._name_input.setStyleSheet(_NAME_INPUT_STYLE)
        self._name_input.returnPressed.connect(self._on_continue)
        name_layout.addWidget(self._name_input)
        self._name_error = QLabel()
        self._name_error.setWordWrap(True)
        self._name_error.setStyleSheet("color: #e53935; font-size: 10pt;")
        self._name_error.hide()
        name_layout.addWidget(self._name_error)
        name_layout.addStretch()
        self._stack.addWidget(name_page)

        radius_page = QWidget()
        radius_layout = QVBoxLayout(radius_page)
        self._radius_title = QLabel()
        self._radius_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        radius_layout.addWidget(self._radius_title)
        radius_form = QFormLayout()
        self._coverage_radius_label = QLabel()
        self._coverage_radius_input = QDoubleSpinBox()
        self._coverage_radius_input.setMinimum(0.1)
        self._coverage_radius_input.setDecimals(1)
        self._coverage_radius_input.setSuffix(" km")
        self._coverage_radius_input.setValue(_DEFAULT_COVERAGE_RADIUS_KM)
        radius_form.addRow(
            self._coverage_radius_label,
            self._coverage_radius_input,
        )
        radius_layout.addLayout(radius_form)
        self._radius_error = QLabel()
        self._radius_error.setWordWrap(True)
        self._radius_error.setStyleSheet("color: #e53935; font-size: 10pt;")
        self._radius_error.hide()
        radius_layout.addWidget(self._radius_error)
        radius_layout.addStretch()
        self._stack.addWidget(radius_page)

        button_row = QHBoxLayout()
        self._button_box = QDialogButtonBox()
        self._back_button = add_wizard_back_button(self._button_box)
        self._continue_button = add_wizard_next_button(self._button_box)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        button_row.addWidget(self._button_box)
        layout.addLayout(button_row)

    def _connect_signals(self) -> None:

        self._continue_button.clicked.connect(self._on_continue)
        self._back_button.clicked.connect(self._on_back)
        self._button_box.rejected.connect(self._on_cancel)
        self._name_input.textChanged.connect(self._clear_name_error)
        self._coverage_radius_input.valueChanged.connect(self._clear_radius_error)

    def _focus_name_input(self) -> None:

        if self._stack.currentIndex() == _STEP_NAME:
            self._name_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _clear_name_error(self) -> None:

        self._name_error.hide()
        self._name_input.setStyleSheet(_NAME_INPUT_STYLE)

    def _show_name_error(self) -> None:

        self._name_error.show()
        self._name_input.setStyleSheet(_NAME_INPUT_ERROR_STYLE)
        self._name_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _clear_radius_error(self) -> None:

        self._radius_error.hide()

    def _show_radius_error(self, message: str) -> None:

        self._radius_error.setText(message)
        self._radius_error.show()
        self._coverage_radius_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _sync_radius_limits(self) -> None:

        if self._picked_lat is None or self._picked_lon is None:
            return

        max_radius_km = max_observation_radius_km(
            self._picked_lat,
            self._picked_lon,
        )
        max_spinbox_value = max(0.1, max_radius_km)
        self._coverage_radius_input.setMaximum(max_spinbox_value)

        if self._coverage_radius_input.value() > max_spinbox_value:
            self._coverage_radius_input.setValue(max_spinbox_value)

    def _sync_buttons(self) -> None:

        step = self._stack.currentIndex()
        self._back_button.setEnabled(step > _STEP_NAME)
        self._back_button.setVisible(step > _STEP_NAME)
        self._continue_button.setVisible(True)

    def _on_continue(self) -> None:

        step = self._stack.currentIndex()

        if step == _STEP_NAME:
            if not self._name_input.text().strip():
                self._show_name_error()
                return

            self._clear_name_error()
            self._picked_lat = None
            self._picked_lon = None
            self._start_map_pick()
            return

        if step == _STEP_RADIUS:
            self._complete_observation_setup()

    def _on_back(self) -> None:

        step = self._stack.currentIndex()

        if step == _STEP_RADIUS:
            MapController.instance().cancel_pick_mode()
            self._picked_lat = None
            self._picked_lon = None
            self._stack.setCurrentIndex(_STEP_NAME)
            self._sync_buttons()
            QTimer.singleShot(0, self._focus_name_input)

    def _on_cancel(self) -> None:

        MapController.instance().cancel_pick_mode()
        self.reject()

    def _start_map_pick(self) -> None:

        MapController.instance().begin_location_pick(
            self._on_map_location,
            overlay_message=tr("Use the central Map to choose a location."),
            host=self,
        )

    def _on_map_location(self, latitude: float, longitude: float) -> None:

        self._picked_lat = latitude
        self._picked_lon = longitude
        self._stack.setCurrentIndex(_STEP_RADIUS)
        self._sync_radius_limits()
        self._sync_buttons()
        self.show()
        self.raise_()
        self.activateWindow()
        self._coverage_radius_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _complete_observation_setup(self) -> None:

        name = self._name_input.text().strip()

        if not name or self._picked_lat is None or self._picked_lon is None:
            return

        coverage_radius_km = self._coverage_radius_input.value()
        max_radius_km = max_observation_radius_km(
            self._picked_lat,
            self._picked_lon,
        )

        if coverage_radius_km <= 0:
            self._show_radius_error(
                tr("Observation radius must be greater than zero.")
            )
            return

        if coverage_radius_km > max_radius_km:
            self._show_radius_error(
                tr(
                    "Observation radius cannot exceed {max} km at this location."
                ).replace("{max}", f"{max_radius_km:.1f}")
            )
            return

        with trace_block("FirstRunWizard._complete_observation_setup.create"):
            observation_manager.create(
                name,
                self._picked_lat,
                self._picked_lon,
                coverage_radius_km=coverage_radius_km,
                set_active=True,
            )

        if not self._show_success_dialog(name, self._picked_lat, self._picked_lon):
            return

        preferences_manager.set_first_run_completed(True)
        self.accept()

    def _show_success_dialog(
        self,
        name: str,
        latitude: float,
        longitude: float,
    ) -> bool:

        dialog = _FirstRunSuccessDialog(name, latitude, longitude, self)
        return dialog.exec() == QDialog.DialogCode.Accepted

    def reject(self) -> None:

        MapController.instance().cancel_pick_mode()
        super().reject()
