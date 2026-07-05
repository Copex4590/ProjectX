# ============================================================================
# Project X
# Camera Integration Wizard
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from camera import (
    Camera,
    SUPPORTED_CAMERA_TYPES,
    camera_manager,
    test_stream,
    validate_stream_url,
)
from camera.camera import FUTURE_CAMERA_TYPES
from gui.i18n_support import bind_language_refresh
from gui.widgets.cameramapwidget import CameraMapWidget
from gui.wizardhelp import show_wizard_help
from i18n import tr
from observation import observation_manager

_STEP_NAME = 0
_STEP_SOURCE = 1
_STEP_URL = 2
_STEP_POSITION = 3
_STEP_HEADING = 4
_STEP_FOV = 5
_STEP_DISTANCE = 6
_STEP_TEST = 7
_STEP_SUMMARY = 8

_SOURCE_TYPES = SUPPORTED_CAMERA_TYPES + FUTURE_CAMERA_TYPES


class _StreamTestWorker(QThread):

    def __init__(self, camera_type: str, stream_url: str, parent=None):
        super().__init__(parent)

        self._camera_type = camera_type
        self._stream_url = stream_url
        self.result = None

    def run(self) -> None:

        self.result = test_stream(self._camera_type, self._stream_url)


class CameraWizard(QDialog):

    def __init__(
        self,
        observation_point_id: str,
        parent=None,
        *,
        camera: Camera | None = None,
    ):
        super().__init__(parent)

        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(560)

        self._observation_point_id = observation_point_id
        self._editing_camera = camera
        self._edit_camera_id = camera.id if camera else None

        self._camera_type = camera.type if camera else "hls"
        self._latitude = camera.latitude if camera else 0.0
        self._longitude = camera.longitude if camera else 0.0
        self._heading = camera.heading if camera else 0.0
        self._field_of_view = camera.field_of_view if camera else 90.0
        self._max_distance = camera.max_distance if camera else 5.0
        self._use_observation_position = True
        self._heading_pick_active = False
        self._test_worker: _StreamTestWorker | None = None
        self._last_test_success: bool | None = None

        point = observation_manager.get(observation_point_id)

        if point is not None and camera is None:
            self._latitude = point.latitude
            self._longitude = point.longitude

        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)

        if camera is not None:
            self._name_input.setText(camera.name)
            self._url_input.setText(camera.stream_url)
            self._heading_input.setValue(int(camera.heading) % 360)
            self._fov_input.setValue(camera.field_of_view)
            self._distance_input.setValue(camera.max_distance)
            self._latitude = camera.latitude
            self._longitude = camera.longitude

            if point is not None:
                position_differs = (
                    abs(camera.latitude - point.latitude) > 1e-6
                    or abs(camera.longitude - point.longitude) > 1e-6
                )

                if position_differs:
                    self._use_observation_position = False
                    self._map_position_option.setChecked(True)
                    self._use_observation_option.setChecked(False)

        self.refresh_translations()
        self._sync_buttons()

    def refresh_translations(self) -> None:

        title = tr("Edit Camera") if self._edit_camera_id else tr("Add Camera")
        self.setWindowTitle(title)

        self._step_title_labels[_STEP_NAME].setText(tr("Step 1 — Camera name"))
        self._name_label.setText(tr("Camera name"))
        self._name_input.setPlaceholderText(tr("Hotel Victoria"))
        self._name_examples.setText(
            tr(
                "Examples: Hotel Victoria, North Bridge Cam, "
                "Port Camera, Home Camera"
            )
        )

        self._step_title_labels[_STEP_SOURCE].setText(
            tr("Step 2 — Camera source")
        )
        self._source_labels["hls"].setText(tr("HLS (.m3u8)"))
        self._source_labels["rtsp"].setText(tr("RTSP"))
        self._source_labels["mjpeg"].setText(tr("MJPEG"))
        self._source_labels["http"].setText(tr("HTTP Stream"))
        self._source_labels["youtube"].setText(tr("YouTube Live"))
        self._source_labels["local"].setText(tr("Local Video"))

        self._step_title_labels[_STEP_URL].setText(tr("Step 3 — Stream URL"))
        self._url_label.setText(tr("Stream URL"))
        self._url_input.setPlaceholderText(tr("https://..."))
        self._url_hint.setText(tr("Enter a valid stream URL."))

        self._step_title_labels[_STEP_POSITION].setText(
            tr("Step 4 — Camera Position")
        )
        self._use_observation_option.setText(tr("Use Observation Point"))
        self._map_position_option.setText(
            tr("Select another position on map")
        )
        self._position_hint.setText(
            tr("Click the map once. A blue camera marker appears.")
        )

        self._step_title_labels[_STEP_HEADING].setText(
            tr("Step 5 — Camera Direction")
        )
        self._heading_label.setText(tr("Heading"))
        self._heading_hint.setText(
            tr("Rotate visually on map or enter 0–359°.")
        )
        self._rotate_map_button.setText(tr("Rotate on map"))

        self._step_title_labels[_STEP_FOV].setText(tr("Step 6 — Field of View"))
        self._fov_label.setText(tr("Field of View"))
        self._fov_custom_label.setText(tr("Custom value"))

        for degrees, button in self._fov_buttons.items():
            button.setText(f"{degrees}°")

        self._step_title_labels[_STEP_DISTANCE].setText(
            tr("Step 7 — Maximum View Distance")
        )
        self._distance_label.setText(tr("Maximum View Distance"))
        self._distance_custom_label.setText(tr("Custom"))

        for kilometers, button in self._distance_buttons.items():
            button.setText(tr("{km} km").format(km=kilometers))

        self._step_title_labels[_STEP_TEST].setText(
            tr("Step 8 — Connection Test")
        )
        self._test_button.setText(tr("Test stream"))
        self._test_hint.setText(tr("Test the stream before saving."))

        self._step_title_labels[_STEP_SUMMARY].setText(tr("Step 9 — Summary"))
        self._summary_hint.setText(tr("Review settings and save."))

        for step, button in self._help_buttons.items():
            button.setText(tr("? Help"))

        self._button_box.button(QDialogButtonBox.StandardButton.Back).setText(
            tr("Back")
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Next).setText(
            tr("Next")
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            tr("Cancel")
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Save).setText(
            tr("Save")
        )

        self._refresh_summary()
        self._refresh_test_result()

    def _build_ui(self) -> None:

        self.setStyleSheet("""
            QDialog {
                background: #1d2127;
            }

            QLabel {
                color: #d5dbe3;
            }

            QLineEdit, QDoubleSpinBox, QSpinBox {
                background: #252a31;
                color: white;
                border: 1px solid #40444b;
                border-radius: 6px;
                padding: 6px 8px;
            }

            QRadioButton {
                color: #d5dbe3;
            }

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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self._step_title_labels: dict[int, QLabel] = {}
        self._help_buttons: dict[int, QPushButton] = {}
        self._source_labels: dict[str, QRadioButton] = {}

        self._build_name_step()
        self._build_source_step()
        self._build_url_step()
        self._build_position_step()
        self._build_heading_step()
        self._build_fov_step()
        self._build_distance_step()
        self._build_test_step()
        self._build_summary_step()

        self._button_box = QDialogButtonBox()
        self._button_box.addButton(QDialogButtonBox.StandardButton.Back)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Next)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Save)
        self._button_box.button(QDialogButtonBox.StandardButton.Save).setVisible(
            False
        )
        layout.addWidget(self._button_box)

    def _make_step_header(self, step: int, parent_layout: QVBoxLayout) -> None:

        row = QHBoxLayout()
        title = QLabel()
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        row.addWidget(title, 1)

        help_button = QPushButton()
        help_button.setFixedWidth(72)
        row.addWidget(help_button)
        parent_layout.addLayout(row)

        self._step_title_labels[step] = title
        self._help_buttons[step] = help_button

    def _build_name_step(self) -> None:

        page = QWidget()
        layout = QVBoxLayout(page)
        self._make_step_header(_STEP_NAME, layout)

        form = QFormLayout()
        self._name_label = QLabel()
        self._name_input = QLineEdit()
        form.addRow(self._name_label, self._name_input)
        layout.addLayout(form)

        self._name_examples = QLabel()
        self._name_examples.setWordWrap(True)
        self._name_examples.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        layout.addWidget(self._name_examples)
        layout.addStretch()
        self._stack.addWidget(page)

    def _build_source_step(self) -> None:

        page = QWidget()
        layout = QVBoxLayout(page)
        self._make_step_header(_STEP_SOURCE, layout)

        self._source_group = QButtonGroup(self)
        index = 0

        for camera_type in _SOURCE_TYPES:
            option = QRadioButton()
            option.setEnabled(camera_type in SUPPORTED_CAMERA_TYPES)

            if camera_type == self._camera_type:
                option.setChecked(True)

            self._source_labels[camera_type] = option
            self._source_group.addButton(option, index)
            layout.addWidget(option)
            index += 1

        layout.addStretch()
        self._stack.addWidget(page)

    def _build_url_step(self) -> None:

        page = QWidget()
        layout = QVBoxLayout(page)
        self._make_step_header(_STEP_URL, layout)

        form = QFormLayout()
        self._url_label = QLabel()
        self._url_input = QLineEdit()
        form.addRow(self._url_label, self._url_input)
        layout.addLayout(form)

        self._url_hint = QLabel()
        self._url_hint.setWordWrap(True)
        self._url_hint.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        layout.addWidget(self._url_hint)

        self._url_error = QLabel()
        self._url_error.setStyleSheet("color: #ef5350;")
        self._url_error.setVisible(False)
        layout.addWidget(self._url_error)
        layout.addStretch()
        self._stack.addWidget(page)

    def _build_position_step(self) -> None:

        page = QWidget()
        layout = QVBoxLayout(page)
        self._make_step_header(_STEP_POSITION, layout)

        self._use_observation_option = QRadioButton()
        self._use_observation_option.setChecked(True)
        self._map_position_option = QRadioButton()
        layout.addWidget(self._use_observation_option)
        layout.addWidget(self._map_position_option)

        self._position_group = QButtonGroup(self)
        self._position_group.addButton(self._use_observation_option, 0)
        self._position_group.addButton(self._map_position_option, 1)

        self._position_map = CameraMapWidget()
        self._position_map.setMinimumHeight(240)
        self._position_map.setVisible(False)
        layout.addWidget(self._position_map)

        self._position_hint = QLabel()
        self._position_hint.setWordWrap(True)
        self._position_hint.setVisible(False)
        self._position_hint.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        layout.addWidget(self._position_hint)
        layout.addStretch()
        self._stack.addWidget(page)

    def _build_heading_step(self) -> None:

        page = QWidget()
        layout = QVBoxLayout(page)
        self._make_step_header(_STEP_HEADING, layout)

        form = QFormLayout()
        self._heading_label = QLabel()
        self._heading_input = QSpinBox()
        self._heading_input.setRange(0, 359)
        form.addRow(self._heading_label, self._heading_input)
        layout.addLayout(form)

        self._rotate_map_button = QPushButton()
        layout.addWidget(self._rotate_map_button)

        self._heading_map = CameraMapWidget()
        self._heading_map.setMinimumHeight(240)
        layout.addWidget(self._heading_map)

        self._heading_hint = QLabel()
        self._heading_hint.setWordWrap(True)
        self._heading_hint.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        layout.addWidget(self._heading_hint)
        layout.addStretch()
        self._stack.addWidget(page)

    def _build_fov_step(self) -> None:

        page = QWidget()
        layout = QVBoxLayout(page)
        self._make_step_header(_STEP_FOV, layout)

        preset_row = QHBoxLayout()
        self._fov_buttons: dict[int, QPushButton] = {}

        for degrees in (60, 90, 120, 180):
            button = QPushButton()
            button.clicked.connect(
                lambda _checked=False, value=degrees: self._fov_input.setValue(
                    float(value)
                )
            )
            self._fov_buttons[degrees] = button
            preset_row.addWidget(button)

        layout.addLayout(preset_row)

        custom_row = QFormLayout()
        self._fov_label = QLabel()
        self._fov_custom_label = QLabel()
        self._fov_input = QDoubleSpinBox()
        self._fov_input.setRange(1.0, 360.0)
        self._fov_input.setDecimals(0)
        self._fov_input.setValue(self._field_of_view)
        custom_row.addRow(self._fov_custom_label, self._fov_input)
        layout.addLayout(custom_row)
        layout.addStretch()
        self._stack.addWidget(page)

    def _build_distance_step(self) -> None:

        page = QWidget()
        layout = QVBoxLayout(page)
        self._make_step_header(_STEP_DISTANCE, layout)

        preset_row = QHBoxLayout()
        self._distance_buttons: dict[int, QPushButton] = {}

        for kilometers in (1, 2, 5, 10):
            button = QPushButton()
            button.clicked.connect(
                lambda _checked=False, value=kilometers: (
                    self._distance_input.setValue(float(value))
                )
            )
            self._distance_buttons[kilometers] = button
            preset_row.addWidget(button)

        layout.addLayout(preset_row)

        custom_row = QFormLayout()
        self._distance_label = QLabel()
        self._distance_custom_label = QLabel()
        self._distance_input = QDoubleSpinBox()
        self._distance_input.setRange(0.1, 1000.0)
        self._distance_input.setDecimals(1)
        self._distance_input.setValue(self._max_distance)
        custom_row.addRow(self._distance_custom_label, self._distance_input)
        layout.addLayout(custom_row)
        layout.addStretch()
        self._stack.addWidget(page)

    def _build_test_step(self) -> None:

        page = QWidget()
        layout = QVBoxLayout(page)
        self._make_step_header(_STEP_TEST, layout)

        self._test_button = QPushButton()
        layout.addWidget(self._test_button)

        self._test_result = QLabel()
        self._test_result.setWordWrap(True)
        layout.addWidget(self._test_result)

        self._test_details = QLabel()
        self._test_details.setWordWrap(True)
        self._test_details.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        layout.addWidget(self._test_details)

        self._test_hint = QLabel()
        self._test_hint.setWordWrap(True)
        self._test_hint.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        layout.addWidget(self._test_hint)
        layout.addStretch()
        self._stack.addWidget(page)

    def _build_summary_step(self) -> None:

        page = QWidget()
        layout = QVBoxLayout(page)
        self._make_step_header(_STEP_SUMMARY, layout)

        self._summary_grid = QFormLayout()
        self._summary_name = QLabel()
        self._summary_point = QLabel()
        self._summary_position = QLabel()
        self._summary_heading = QLabel()
        self._summary_fov = QLabel()
        self._summary_distance = QLabel()
        self._summary_url = QLabel()
        self._summary_url.setWordWrap(True)

        self._summary_captions = {
            "name": QLabel(),
            "point": QLabel(),
            "position": QLabel(),
            "heading": QLabel(),
            "fov": QLabel(),
            "distance": QLabel(),
            "url": QLabel(),
        }

        self._summary_grid.addRow(
            self._summary_captions["name"],
            self._summary_name,
        )
        self._summary_grid.addRow(
            self._summary_captions["point"],
            self._summary_point,
        )
        self._summary_grid.addRow(
            self._summary_captions["position"],
            self._summary_position,
        )
        self._summary_grid.addRow(
            self._summary_captions["heading"],
            self._summary_heading,
        )
        self._summary_grid.addRow(
            self._summary_captions["fov"],
            self._summary_fov,
        )
        self._summary_grid.addRow(
            self._summary_captions["distance"],
            self._summary_distance,
        )
        self._summary_grid.addRow(
            self._summary_captions["url"],
            self._summary_url,
        )
        layout.addLayout(self._summary_grid)

        self._summary_hint = QLabel()
        self._summary_hint.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        layout.addWidget(self._summary_hint)
        layout.addStretch()
        self._stack.addWidget(page)

    def _connect_signals(self) -> None:

        self._button_box.rejected.connect(self.reject)
        self._button_box.button(QDialogButtonBox.StandardButton.Next).clicked.connect(
            self._on_next
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Back).clicked.connect(
            self._on_back
        )
        self._button_box.accepted.connect(self._on_save)

        self._source_group.idClicked.connect(self._on_source_changed)
        self._position_group.idClicked.connect(self._on_position_mode_changed)
        self._position_map.positionSelected.connect(self._on_position_selected)
        self._heading_input.valueChanged.connect(self._on_heading_changed)
        self._rotate_map_button.clicked.connect(self._toggle_heading_pick)
        self._heading_map.headingSelected.connect(self._on_heading_selected)
        self._test_button.clicked.connect(self._run_stream_test)
        self._url_input.textChanged.connect(self._clear_url_error)

        help_topics = {
            _STEP_NAME: (
                "Camera wizard help — name",
                "Camera wizard help body — name",
            ),
            _STEP_SOURCE: (
                "Camera wizard help — source",
                "Camera wizard help body — source",
            ),
            _STEP_URL: (
                "Camera wizard help — url",
                "Camera wizard help body — url",
            ),
            _STEP_POSITION: (
                "Camera wizard help — position",
                "Camera wizard help body — position",
            ),
            _STEP_HEADING: (
                "Camera wizard help — heading",
                "Camera wizard help body — heading",
            ),
            _STEP_FOV: (
                "Camera wizard help — fov",
                "Camera wizard help body — fov",
            ),
            _STEP_DISTANCE: (
                "Camera wizard help — distance",
                "Camera wizard help body — distance",
            ),
            _STEP_TEST: (
                "Camera wizard help — test",
                "Camera wizard help body — test",
            ),
            _STEP_SUMMARY: (
                "Camera wizard help — summary",
                "Camera wizard help body — summary",
            ),
        }

        for step, button in self._help_buttons.items():
            title_key, body_key = help_topics[step]
            button.clicked.connect(
                lambda _checked=False, t=title_key, b=body_key: (
                    show_wizard_help(self, t, b)
                )
            )

    def _current_source_type(self) -> str:

        button_id = self._source_group.checkedId()

        if button_id < 0 or button_id >= len(_SOURCE_TYPES):
            return "hls"

        return _SOURCE_TYPES[button_id]

    def _on_source_changed(self, _button_id: int) -> None:

        self._camera_type = self._current_source_type()

    def _on_position_mode_changed(self, button_id: int) -> None:

        use_map = button_id == 1
        self._use_observation_position = not use_map
        self._position_map.setVisible(use_map)
        self._position_hint.setVisible(use_map)

        if use_map:
            self._position_map.set_camera(
                self._latitude,
                self._longitude,
                self._heading,
            )
            self._position_map.enable_position_pick(True)
        else:
            self._position_map.enable_position_pick(False)
            point = observation_manager.get(self._observation_point_id)

            if point is not None:
                self._latitude = point.latitude
                self._longitude = point.longitude

    def _on_position_selected(self, latitude: float, longitude: float) -> None:

        self._latitude = latitude
        self._longitude = longitude

    def _on_heading_changed(self, value: int) -> None:

        self._heading = float(value)
        self._heading_map.set_heading(self._heading)

    def _toggle_heading_pick(self) -> None:

        self._heading_pick_active = not self._heading_pick_active
        self._heading_map.enable_heading_pick(self._heading_pick_active)
        self._rotate_map_button.setStyleSheet(
            "background: #1e88e5;" if self._heading_pick_active else ""
        )

    def _on_heading_selected(self, heading: float) -> None:

        self._heading = heading % 360.0
        self._heading_input.blockSignals(True)
        self._heading_input.setValue(int(self._heading))
        self._heading_input.blockSignals(False)
        self._heading_map.enable_heading_pick(False)
        self._heading_pick_active = False
        self._rotate_map_button.setStyleSheet("")

    def _clear_url_error(self) -> None:

        self._url_error.setVisible(False)

    def _validate_current_step(self) -> bool:

        step = self._stack.currentIndex()

        if step == _STEP_NAME:
            if not self._name_input.text().strip():
                return False

        elif step == _STEP_URL:
            valid, message = validate_stream_url(
                self._current_source_type(),
                self._url_input.text(),
            )

            if not valid:
                self._url_error.setText(tr(message))
                self._url_error.setVisible(True)
                return False

            self._camera_type = self._current_source_type()

        return True

    def _on_next(self) -> None:

        if not self._validate_current_step():
            return

        step = self._stack.currentIndex()

        if step == _STEP_POSITION:
            if self._use_observation_position:
                point = observation_manager.get(self._observation_point_id)

                if point is not None:
                    self._latitude = point.latitude
                    self._longitude = point.longitude

            self._position_map.enable_position_pick(False)

        if step == _STEP_HEADING:
            self._heading_map.enable_heading_pick(False)
            self._heading_pick_active = False
            self._rotate_map_button.setStyleSheet("")

        if step >= _STEP_SUMMARY:
            return

        self._stack.setCurrentIndex(step + 1)

        if step + 1 == _STEP_HEADING:
            self._heading_map.set_camera(
                self._latitude,
                self._longitude,
                self._heading,
            )

        if step + 1 == _STEP_SUMMARY:
            self._field_of_view = self._fov_input.value()
            self._max_distance = self._distance_input.value()
            self._refresh_summary()

        self._sync_buttons()

    def _on_back(self) -> None:

        step = self._stack.currentIndex()

        if step <= _STEP_NAME:
            return

        if step == _STEP_HEADING:
            self._heading_map.enable_heading_pick(False)
            self._heading_pick_active = False
            self._rotate_map_button.setStyleSheet("")

        self._stack.setCurrentIndex(step - 1)
        self._sync_buttons()

    def _sync_buttons(self) -> None:

        step = self._stack.currentIndex()
        back_button = self._button_box.button(
            QDialogButtonBox.StandardButton.Back
        )
        next_button = self._button_box.button(
            QDialogButtonBox.StandardButton.Next
        )
        save_button = self._button_box.button(
            QDialogButtonBox.StandardButton.Save
        )

        back_button.setEnabled(step > _STEP_NAME)
        next_button.setVisible(step < _STEP_SUMMARY)
        save_button.setVisible(step == _STEP_SUMMARY)

    def _run_stream_test(self) -> None:

        valid, message = validate_stream_url(
            self._current_source_type(),
            self._url_input.text(),
        )

        if not valid:
            self._url_error.setText(tr(message))
            self._url_error.setVisible(True)
            return

        self._camera_type = self._current_source_type()
        self._test_button.setEnabled(False)
        self._test_result.setText(tr("Testing connection..."))

        self._test_worker = _StreamTestWorker(
            self._camera_type,
            self._url_input.text(),
            self,
        )
        self._test_worker.finished.connect(self._on_test_finished)
        self._test_worker.start()

    def _on_test_finished(self) -> None:

        self._test_button.setEnabled(True)
        result = self._test_worker.result if self._test_worker else None

        if result is None:
            self._test_result.setText(tr("Unable to connect"))
            self._last_test_success = False
            self._refresh_test_result()
            return

        self._last_test_success = result.success
        self._refresh_test_result(result)

    def _refresh_test_result(self, result=None) -> None:

        if result is None:
            if self._last_test_success is True:
                self._test_result.setText(tr("✓ Connection successful"))
                self._test_result.setStyleSheet("color: #66bb6a;")
            elif self._last_test_success is False:
                self._test_result.setText(tr("✗ Unable to connect"))
                self._test_result.setStyleSheet("color: #ef5350;")
            else:
                self._test_result.setText("")
                self._test_details.setText("")
            return

        if result.success:
            self._test_result.setText(tr("✓ Connection successful"))
            self._test_result.setStyleSheet("color: #66bb6a;")
        else:
            self._test_result.setText(tr("✗ Unable to connect"))
            self._test_result.setStyleSheet("color: #ef5350;")

        details = [tr("Stream type") + f": {result.stream_type}"]

        if result.resolution:
            details.append(tr("Resolution") + f": {result.resolution}")

        self._test_details.setText("\n".join(details))

    def _refresh_summary(self) -> None:

        point = observation_manager.get(self._observation_point_id)
        point_name = point.name if point else "—"

        self._summary_captions["name"].setText(tr("Camera name"))
        self._summary_captions["point"].setText(tr("Observation Point"))
        self._summary_captions["position"].setText(tr("Position"))
        self._summary_captions["heading"].setText(tr("Heading"))
        self._summary_captions["fov"].setText(tr("Field of View"))
        self._summary_captions["distance"].setText(
            tr("Maximum View Distance")
        )
        self._summary_captions["url"].setText(tr("Stream URL"))

        self._summary_name.setText(self._name_input.text().strip() or "—")
        self._summary_point.setText(point_name)
        self._summary_position.setText(
            f"{self._latitude:.5f}, {self._longitude:.5f}"
        )
        self._summary_heading.setText(f"{int(self._heading)}°")
        self._summary_fov.setText(f"{self._fov_input.value():.0f}°")
        self._summary_distance.setText(
            tr("{km} km").format(km=self._distance_input.value())
        )
        self._summary_url.setText(self._url_input.text().strip() or "—")

    def _on_save(self) -> None:

        if self._stack.currentIndex() != _STEP_SUMMARY:
            return

        if not self._name_input.text().strip():
            return

        valid, message = validate_stream_url(
            self._current_source_type(),
            self._url_input.text(),
        )

        if not valid:
            self._url_error.setText(tr(message))
            self._url_error.setVisible(True)
            self._stack.setCurrentIndex(_STEP_URL)
            self._sync_buttons()
            return

        payload = dict(
            name=self._name_input.text().strip(),
            enabled=True,
            camera_type=self._current_source_type(),
            stream_url=self._url_input.text().strip(),
            latitude=self._latitude,
            longitude=self._longitude,
            heading=self._heading,
            field_of_view=self._fov_input.value(),
            max_distance=self._distance_input.value(),
        )

        if self._edit_camera_id:
            camera_manager.update(self._edit_camera_id, **payload)
        else:
            camera_manager.add(
                self._observation_point_id,
                payload["name"],
                enabled=payload["enabled"],
                camera_type=payload["camera_type"],
                stream_url=payload["stream_url"],
                latitude=payload["latitude"],
                longitude=payload["longitude"],
                heading=payload["heading"],
                field_of_view=payload["field_of_view"],
                max_distance=payload["max_distance"],
            )

        self.accept()
