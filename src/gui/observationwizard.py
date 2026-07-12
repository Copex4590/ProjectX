from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from debug.obs_freeze_trace import trace_block, trace_enter, trace_exit
from gui.i18n_support import bind_language_refresh
from gui.mapcontroller import MapController
from gui.wizardhelp import add_wizard_back_button, add_wizard_next_button
from i18n import tr
from observation import observation_manager
from observation.coords import max_observation_radius_km
from shiboken6 import isValid

_SUBSTEP_MAP = 0
_SUBSTEP_NAME = 1
_SUBSTEP_RADIUS = 2

_DEFAULT_COVERAGE_RADIUS_KM = 25.0
_MAP_PICK_CONFIRM_DELAY_MS = 750

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


class ObservationSetupWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._picked_lat: float | None = None
        self._picked_lon: float | None = None

        self._build_ui()
        self._connect_signals()

    def refresh_translations(self) -> None:

        self._map_title.setText(tr("Step 1 — Choose location"))
        self._map_help_label.setText(
            tr("Use the central Map to choose a location.")
        )
        self._name_title.setText(tr("Step 2 — Observation Point name"))
        self._name_label.setText(tr("Observation Point name"))
        self._name_input.setPlaceholderText(tr("Home"))
        self._examples_label.setText(
            tr(
                "Examples: Home, Hotel Victoria, Parliament, "
                "River Bank, Observation Deck"
            )
        )
        self._name_error.setText(tr("Enter the observation point name first."))
        self._radius_title.setText(tr("Step 3 — Observation Radius"))
        self._coverage_radius_label.setText(tr("Observation radius (km)"))
        self._update_picked_coords_label()

    def substep_index(self) -> int:

        return self._stack.currentIndex()

    def begin_map_selection(self) -> None:

        self._picked_lat = None
        self._picked_lon = None
        self._stack.setCurrentIndex(_SUBSTEP_MAP)
        self._update_picked_coords_label()
        self._start_map_pick()

    def on_enter(self) -> None:

        if self.substep_index() == _SUBSTEP_MAP:
            self._start_map_pick()

    def on_leave(self) -> None:

        with trace_block("ObservationSetupWidget.on_leave"):
            MapController.instance().cancel_pick_mode(restore_host=False)

    def handle_next(self) -> bool:

        substep = self.substep_index()

        if substep == _SUBSTEP_MAP:
            if self._picked_lat is None or self._picked_lon is None:
                return False

            MapController.instance().cancel_pick_mode(restore_host=False)
            self._stack.setCurrentIndex(_SUBSTEP_NAME)
            self._name_input.setFocus(Qt.FocusReason.OtherFocusReason)
            return False

        if substep == _SUBSTEP_NAME:
            if not self._name_input.text().strip():
                self._show_name_error()
                return False

            self._clear_name_error()
            self._stack.setCurrentIndex(_SUBSTEP_RADIUS)
            self._sync_radius_limits()
            self._coverage_radius_input.setFocus(Qt.FocusReason.OtherFocusReason)
            return False

        return False

    def handle_back(self) -> bool:

        substep = self.substep_index()

        if substep == _SUBSTEP_RADIUS:
            self._stack.setCurrentIndex(_SUBSTEP_NAME)
            self._name_input.setFocus(Qt.FocusReason.OtherFocusReason)
            return False

        if substep == _SUBSTEP_NAME:
            self.begin_map_selection()
            return False

        return True

    def handle_confirm(self) -> bool:

        with trace_block("ObservationSetupWidget.handle_confirm"):
            name = self._name_input.text().strip()

            if not name:
                self._show_name_error()
                return False

            if self._picked_lat is None or self._picked_lon is None:
                return False

            coverage_radius_km = self._coverage_radius_input.value()
            max_radius_km = max_observation_radius_km(
                self._picked_lat,
                self._picked_lon,
            )

            if coverage_radius_km <= 0:
                self._show_radius_validation_error(
                    tr("Observation radius must be greater than zero.")
                )
                return False

            if coverage_radius_km > max_radius_km:
                self._show_radius_validation_error(
                    tr(
                        "Observation radius cannot exceed {max} km at this location."
                    ).replace("{max}", f"{max_radius_km:.1f}")
                )
                return False

            trace_enter("ObservationSetupWidget.handle_confirm.create")
            observation_manager.create(
                name,
                self._picked_lat,
                self._picked_lon,
                coverage_radius_km=coverage_radius_km,
                set_active=True,
            )
            trace_exit("ObservationSetupWidget.handle_confirm.create")
            return True

    def update_outer_buttons(
        self,
        back_button,
        next_button,
        confirm_button,
    ) -> None:

        substep = self.substep_index()

        back_button.setEnabled(substep > _SUBSTEP_MAP)
        next_button.setVisible(substep < _SUBSTEP_RADIUS)
        confirm_button.setVisible(substep == _SUBSTEP_RADIUS)

    def _build_ui(self) -> None:

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        map_page = QWidget()
        map_layout = QVBoxLayout(map_page)
        self._map_title = QLabel()
        self._map_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        map_layout.addWidget(self._map_title)
        self._map_help_label = QLabel()
        self._map_help_label.setWordWrap(True)
        self._map_help_label.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        map_layout.addWidget(self._map_help_label)
        self._picked_coords_label = QLabel()
        self._picked_coords_label.setWordWrap(True)
        self._picked_coords_label.setStyleSheet("color: white; font-weight: 600;")
        map_layout.addWidget(self._picked_coords_label)
        map_layout.addStretch()
        self._stack.addWidget(map_page)

        name_page = QWidget()
        name_layout = QVBoxLayout(name_page)
        self._name_title = QLabel()
        self._name_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        name_layout.addWidget(self._name_title)
        name_form = QFormLayout()
        self._name_label = QLabel()
        self._name_input = QLineEdit()
        self._name_input.setStyleSheet(_NAME_INPUT_STYLE)
        name_form.addRow(self._name_label, self._name_input)
        name_layout.addLayout(name_form)
        self._name_error = QLabel()
        self._name_error.setWordWrap(True)
        self._name_error.setStyleSheet("color: #e53935; font-size: 10pt;")
        self._name_error.hide()
        name_layout.addWidget(self._name_error)
        self._examples_label = QLabel()
        self._examples_label.setWordWrap(True)
        self._examples_label.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        name_layout.addWidget(self._examples_label)
        name_layout.addStretch()
        self._stack.addWidget(name_page)

        radius_page = QWidget()
        radius_layout = QVBoxLayout(radius_page)
        self._radius_title = QLabel()
        self._radius_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        radius_layout.addWidget(self._radius_title)
        coverage_form = QFormLayout()
        self._coverage_radius_label = QLabel()
        self._coverage_radius_input = QDoubleSpinBox()
        self._coverage_radius_input.setMinimum(0.1)
        self._coverage_radius_input.setDecimals(1)
        self._coverage_radius_input.setSuffix(" km")
        self._coverage_radius_input.setValue(_DEFAULT_COVERAGE_RADIUS_KM)
        coverage_form.addRow(
            self._coverage_radius_label,
            self._coverage_radius_input,
        )
        radius_layout.addLayout(coverage_form)
        radius_layout.addStretch()
        self._stack.addWidget(radius_page)

    def _connect_signals(self) -> None:

        self._name_input.textChanged.connect(self._clear_name_error)

    def _start_map_pick(self) -> None:

        host = self._pick_host_dialog()
        MapController.instance().begin_location_pick(
            self._on_map_location,
            overlay_message=tr("Use the central Map to choose a location."),
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

    def _on_map_location(self, latitude: float, longitude: float) -> None:

        if not isValid(self):
            return

        self._picked_lat = latitude
        self._picked_lon = longitude
        self._update_picked_coords_label()

        MapController.instance().cancel_pick_mode(restore_host=False)

        QTimer.singleShot(
            _MAP_PICK_CONFIRM_DELAY_MS,
            lambda lat=latitude, lon=longitude: self._advance_after_map_pick(
                lat,
                lon,
            ),
        )

    def _advance_after_map_pick(
        self,
        latitude: float,
        longitude: float,
    ) -> None:

        if not isValid(self):
            return

        self._picked_lat = latitude
        self._picked_lon = longitude
        self._update_picked_coords_label()
        self._stack.setCurrentIndex(_SUBSTEP_NAME)

        host = self._pick_host_dialog()
        if host is not None and isValid(host):
            host.show()
            host.raise_()
            host.activateWindow()

        self._name_input.setFocus(Qt.FocusReason.OtherFocusReason)

        parent = self.window()
        if isValid(parent) and hasattr(parent, "_sync_buttons"):
            parent._sync_buttons()

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

    def _clear_name_error(self) -> None:

        self._name_error.hide()
        self._name_input.setStyleSheet(_NAME_INPUT_STYLE)

    def _show_name_error(self) -> None:

        self._name_error.show()
        self._name_input.setStyleSheet(_NAME_INPUT_ERROR_STYLE)
        self._name_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _show_radius_validation_error(self, message: str) -> None:

        QMessageBox.warning(
            self.window(),
            tr("Observation Point Setup"),
            message,
        )

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

    def start_setup(self) -> None:

        self._setup.begin_map_selection()

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("Observation Point Setup"))
        self._setup.refresh_translations()
        self._back_button.setText(tr("Back"))
        self._next_button.setText(tr("Next"))
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
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._setup = ObservationSetupWidget(self)
        layout.addWidget(self._setup)

        self._button_box = QDialogButtonBox()
        self._back_button = add_wizard_back_button(self._button_box)
        self._next_button = add_wizard_next_button(self._button_box)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self._back_button.setEnabled(False)
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setVisible(False)
        layout.addWidget(self._button_box)

    def _connect_signals(self) -> None:

        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)
        self._next_button.clicked.connect(self._on_next)
        self._back_button.clicked.connect(self._on_back)

    def _sync_buttons(self) -> None:

        self._setup.update_outer_buttons(
            self._back_button,
            self._next_button,
            self._button_box.button(QDialogButtonBox.StandardButton.Ok),
        )

    def _on_next(self) -> None:

        self._setup.handle_next()
        self.show()
        self.raise_()
        self.activateWindow()
        self._sync_buttons()

    def _on_back(self) -> None:

        if self._setup.handle_back():
            self._back_button.setEnabled(False)
        else:
            if self._setup.substep_index() == _SUBSTEP_MAP:
                self.hide()

        self._sync_buttons()

    def _on_accept(self) -> None:

        with trace_block("ObservationWizard._on_accept"):
            if self._setup.handle_confirm():
                self.accept()

    def reject(self) -> None:

        with trace_block("ObservationWizard.reject"):
            MapController.instance().cancel_pick_mode(restore_host=False)
            self._setup.on_leave()
            super().reject()

    def accept(self) -> None:

        with trace_block("ObservationWizard.accept"):
            MapController.instance().cancel_pick_mode(restore_host=False)
            self._setup.on_leave()
            super().accept()
