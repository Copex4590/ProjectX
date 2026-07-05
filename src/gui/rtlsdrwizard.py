# ============================================================================
# Project X
# RTL-SDR Setup Assistant
# ============================================================================

from __future__ import annotations

import platform

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.i18n_support import bind_language_refresh
from gui.wizardhelp import show_wizard_help
from i18n import tr
from observation import observation_manager
from preferences import preferences_manager
from rtl import rtl_manager

_STEP_OWNERSHIP = 0
_STEP_NO_RECEIVER = 1
_STEP_OS = 2
_STEP_OS_GUIDE = 3
_STEP_RECEIVER_TEST = 4
_STEP_AIS_CATCHER = 5
_STEP_RECEPTION_TEST = 6
_STEP_OBSERVATION = 7
_STEP_FINISH = 8


class _RTLDetectWorker(QThread):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.device = None

    def run(self) -> None:
        self.device = rtl_manager.detect_device()


class _RTLReceptionWorker(QThread):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = None

    def run(self) -> None:
        self.result = rtl_manager.test_reception(duration_seconds=10.0)


class RTLSdrWizard(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModal(True)
        self.setMinimumWidth(680)
        self.setMinimumHeight(560)

        self._owns_receiver = True
        self._setup_os = "linux" if platform.system().lower() == "linux" else "windows"
        self._detect_worker: _RTLDetectWorker | None = None
        self._reception_worker: _RTLReceptionWorker | None = None

        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self._sync_buttons()

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("RTL-SDR Setup"))
        self._ownership_title.setText(tr("Do you already own an RTL-SDR receiver?"))
        self._yes_option.setText(tr("Yes"))
        self._no_option.setText(tr("No"))
        self._no_receiver_title.setText(tr("What is RTL-SDR?"))
        self._no_receiver_body.setText(tr("RTL-SDR setup — no receiver body"))
        self._internet_only_button.setText(tr("Continue using Internet AIS only"))
        self._os_title.setText(tr("Operating System"))
        self._windows_option.setText(tr("Windows"))
        self._linux_option.setText(tr("Linux"))
        self._guide_title.setText(tr("Setup guide"))
        self._guide_body.setText(self._guide_text())
        self._receiver_title.setText(tr("Receiver Test"))
        self._detect_button.setText(tr("Detect RTL device"))
        self._catcher_title.setText(tr("AIS-Catcher"))
        self._auto_start_checkbox.setText(tr("Start automatically"))
        self._start_catcher_button.setText(tr("Start AIS-Catcher"))
        self._reception_title.setText(tr("Reception Test"))
        self._start_reception_button.setText(tr("Start reception test"))
        self._observation_title.setText(tr("Observation Point Optimization"))
        self._observation_body.setText(self._observation_text())
        self._finish_title.setText(tr("RTL-SDR configured."))
        self._finish_body.setText(tr("Hybrid mode is now available."))

        self._button_box.button(QDialogButtonBox.StandardButton.Back).setText(tr("Back"))
        self._button_box.button(QDialogButtonBox.StandardButton.Next).setText(tr("Next"))
        self._button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("Cancel"))
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Finish"))

    def _build_ui(self) -> None:

        self.setStyleSheet("""
            QDialog { background: #1d2127; }
            QLabel { color: #d5dbe3; }
            QRadioButton, QCheckBox { color: #d5dbe3; }
            QPushButton {
                background: #343a42; color: white;
                border: 1px solid #4a5159; border-radius: 6px; padding: 6px 12px;
            }
            QPushButton:hover { background: #3f464f; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        ownership = QWidget()
        ownership_layout = QVBoxLayout(ownership)
        self._ownership_title = QLabel()
        self._ownership_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        ownership_layout.addWidget(self._ownership_title)
        self._yes_option = QRadioButton()
        self._no_option = QRadioButton()
        self._yes_option.setChecked(True)
        ownership_layout.addWidget(self._yes_option)
        ownership_layout.addWidget(self._no_option)
        ownership_layout.addStretch()
        self._stack.addWidget(ownership)
        self._ownership_group = QButtonGroup(self)
        self._ownership_group.addButton(self._yes_option, 1)
        self._ownership_group.addButton(self._no_option, 0)

        no_receiver = QWidget()
        no_layout = QVBoxLayout(no_receiver)
        self._no_receiver_title = QLabel()
        self._no_receiver_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        no_layout.addWidget(self._no_receiver_title)
        self._no_receiver_body = QLabel()
        self._no_receiver_body.setWordWrap(True)
        self._no_receiver_body.setStyleSheet("color: #9aa4af;")
        no_layout.addWidget(self._no_receiver_body)
        help_row = QHBoxLayout()
        self._no_help_button = QPushButton(tr("What is this?"))
        help_row.addWidget(self._no_help_button)
        help_row.addStretch()
        no_layout.addLayout(help_row)
        no_layout.addStretch()
        self._internet_only_button = QPushButton()
        no_layout.addWidget(self._internet_only_button, alignment=Qt.AlignCenter)
        self._stack.addWidget(no_receiver)

        os_page = QWidget()
        os_layout = QVBoxLayout(os_page)
        self._os_title = QLabel()
        self._os_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        os_layout.addWidget(self._os_title)
        self._windows_option = QRadioButton()
        self._linux_option = QRadioButton()
        if self._setup_os == "linux":
            self._linux_option.setChecked(True)
        else:
            self._windows_option.setChecked(True)
        os_layout.addWidget(self._windows_option)
        os_layout.addWidget(self._linux_option)
        os_layout.addStretch()
        self._stack.addWidget(os_page)
        self._os_group = QButtonGroup(self)
        self._os_group.addButton(self._windows_option, 0)
        self._os_group.addButton(self._linux_option, 1)

        guide_page = QWidget()
        guide_layout = QVBoxLayout(guide_page)
        self._guide_title = QLabel()
        self._guide_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        guide_layout.addWidget(self._guide_title)
        self._guide_body = QLabel()
        self._guide_body.setWordWrap(True)
        self._guide_body.setStyleSheet("color: #9aa4af;")
        guide_layout.addWidget(self._guide_body)
        guide_help_row = QHBoxLayout()
        self._guide_help_button = QPushButton(tr("How do I fix common problems?"))
        guide_help_row.addWidget(self._guide_help_button)
        guide_help_row.addStretch()
        guide_layout.addLayout(guide_help_row)
        guide_layout.addStretch()
        self._stack.addWidget(guide_page)

        receiver_page = QWidget()
        receiver_layout = QVBoxLayout(receiver_page)
        self._receiver_title = QLabel()
        self._receiver_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        receiver_layout.addWidget(self._receiver_title)
        self._detect_button = QPushButton()
        receiver_layout.addWidget(self._detect_button)
        self._device_form = QFormLayout()
        self._manufacturer_value = QLabel("—")
        self._serial_value = QLabel("—")
        self._tuner_value = QLabel("—")
        self._sample_rate_value = QLabel("—")
        self._device_form.addRow(tr("Manufacturer"), self._manufacturer_value)
        self._device_form.addRow(tr("Serial"), self._serial_value)
        self._device_form.addRow(tr("Tuner"), self._tuner_value)
        self._device_form.addRow(tr("Sample rate"), self._sample_rate_value)
        receiver_layout.addLayout(self._device_form)
        self._receiver_result = QLabel()
        self._receiver_result.setWordWrap(True)
        receiver_layout.addWidget(self._receiver_result)
        receiver_layout.addStretch()
        self._stack.addWidget(receiver_page)

        catcher_page = QWidget()
        catcher_layout = QVBoxLayout(catcher_page)
        self._catcher_title = QLabel()
        self._catcher_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        catcher_layout.addWidget(self._catcher_title)
        self._catcher_status_label = QLabel()
        self._catcher_status_label.setWordWrap(True)
        catcher_layout.addWidget(self._catcher_status_label)
        self._auto_start_checkbox = QCheckBox()
        self._auto_start_checkbox.setChecked(True)
        catcher_layout.addWidget(self._auto_start_checkbox)
        self._start_catcher_button = QPushButton()
        catcher_layout.addWidget(self._start_catcher_button)
        catcher_layout.addStretch()
        self._stack.addWidget(catcher_page)

        reception_page = QWidget()
        reception_layout = QVBoxLayout(reception_page)
        self._reception_title = QLabel()
        self._reception_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        reception_layout.addWidget(self._reception_title)
        self._start_reception_button = QPushButton()
        reception_layout.addWidget(self._start_reception_button)
        self._reception_messages = QLabel("0")
        self._reception_ships = QLabel("0")
        self._reception_signal = QLabel("—")
        reception_form = QFormLayout()
        reception_form.addRow(tr("AIS messages received"), self._reception_messages)
        reception_form.addRow(tr("Ships detected"), self._reception_ships)
        reception_form.addRow(tr("Signal quality"), self._reception_signal)
        reception_layout.addLayout(reception_form)
        self._reception_result = QLabel()
        self._reception_result.setWordWrap(True)
        reception_layout.addWidget(self._reception_result)
        reception_layout.addStretch()
        self._stack.addWidget(reception_page)

        observation_page = QWidget()
        observation_layout = QVBoxLayout(observation_page)
        self._observation_title = QLabel()
        self._observation_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        observation_layout.addWidget(self._observation_title)
        self._observation_body = QLabel()
        self._observation_body.setWordWrap(True)
        self._observation_body.setStyleSheet("color: #9aa4af;")
        observation_layout.addWidget(self._observation_body)
        observation_layout.addStretch()
        self._stack.addWidget(observation_page)

        finish_page = QWidget()
        finish_layout = QVBoxLayout(finish_page)
        self._finish_title = QLabel()
        self._finish_title.setAlignment(Qt.AlignCenter)
        self._finish_title.setStyleSheet("font-size: 16pt; font-weight: bold; color: white;")
        finish_layout.addWidget(self._finish_title)
        self._finish_body = QLabel()
        self._finish_body.setAlignment(Qt.AlignCenter)
        self._finish_body.setWordWrap(True)
        finish_layout.addWidget(self._finish_body)
        finish_layout.addStretch()
        self._stack.addWidget(finish_page)

        button_row = QHBoxLayout()
        self._button_box = QDialogButtonBox()
        self._button_box.addButton(QDialogButtonBox.StandardButton.Back)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Next)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        button_row.addWidget(self._button_box)
        layout.addLayout(button_row)

    def _connect_signals(self) -> None:

        self._button_box.rejected.connect(self.reject)
        self._button_box.button(QDialogButtonBox.StandardButton.Next).clicked.connect(self._on_next)
        self._button_box.button(QDialogButtonBox.StandardButton.Back).clicked.connect(self._on_back)
        self._button_box.accepted.connect(self._on_finish)
        self._internet_only_button.clicked.connect(self._on_internet_only)
        self._detect_button.clicked.connect(self._on_detect_device)
        self._start_catcher_button.clicked.connect(self._on_start_catcher)
        self._start_reception_button.clicked.connect(self._on_start_reception)
        self._no_help_button.clicked.connect(
            lambda: show_wizard_help(
                self,
                "RTL-SDR help — what is RTL-SDR",
                "RTL-SDR help body — what is RTL-SDR",
            )
        )
        self._guide_help_button.clicked.connect(self._on_guide_help)

    def _guide_text(self) -> str:

        if self._setup_os == "linux":
            return tr("RTL-SDR setup guide — Linux")

        return tr("RTL-SDR setup guide — Windows")

    def _observation_text(self) -> str:

        active = observation_manager.active()

        if active is None:
            return tr("RTL-SDR observation tips — no point")

        return tr("RTL-SDR observation tips").format(
            name=active.name,
            latitude=f"{active.latitude:.5f}",
            longitude=f"{active.longitude:.5f}",
        )

    def _on_guide_help(self) -> None:

        if self._setup_os == "linux":
            show_wizard_help(
                self,
                "RTL-SDR help — Linux problems",
                "RTL-SDR help body — Linux problems",
            )
            return

        show_wizard_help(
            self,
            "RTL-SDR help — Windows problems",
            "RTL-SDR help body — Windows problems",
        )

    def _sync_buttons(self) -> None:

        step = self._stack.currentIndex()
        back_button = self._button_box.button(QDialogButtonBox.StandardButton.Back)
        next_button = self._button_box.button(QDialogButtonBox.StandardButton.Next)
        finish_button = self._button_box.button(QDialogButtonBox.StandardButton.Ok)

        back_button.setVisible(step not in (_STEP_OWNERSHIP, _STEP_FINISH))
        next_button.setVisible(step not in (_STEP_FINISH, _STEP_NO_RECEIVER))
        finish_button.setVisible(step == _STEP_FINISH)
        cancel_button = self._button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setVisible(step != _STEP_FINISH)

    def _on_next(self) -> None:

        step = self._stack.currentIndex()

        if step == _STEP_OWNERSHIP:
            self._owns_receiver = self._ownership_group.checkedId() == 1

            if self._owns_receiver:
                self._stack.setCurrentIndex(_STEP_OS)
            else:
                self._stack.setCurrentIndex(_STEP_NO_RECEIVER)

        elif step == _STEP_OS:
            self._setup_os = "linux" if self._os_group.checkedId() == 1 else "windows"
            self._guide_body.setText(self._guide_text())
            self._stack.setCurrentIndex(_STEP_OS_GUIDE)

        elif step == _STEP_OS_GUIDE:
            self._stack.setCurrentIndex(_STEP_RECEIVER_TEST)

        elif step == _STEP_RECEIVER_TEST:
            self._refresh_catcher_status()
            self._stack.setCurrentIndex(_STEP_AIS_CATCHER)

        elif step == _STEP_AIS_CATCHER:
            self._stack.setCurrentIndex(_STEP_RECEPTION_TEST)

        elif step == _STEP_RECEPTION_TEST:
            self._observation_body.setText(self._observation_text())
            self._stack.setCurrentIndex(_STEP_OBSERVATION)

        elif step == _STEP_OBSERVATION:
            rtl_manager.mark_configured(owned=True, setup_os=self._setup_os)
            preferences_manager.set_rtl_configuration(
                auto_start_ais_catcher=self._auto_start_checkbox.isChecked(),
                setup_completed=True,
            )
            self._stack.setCurrentIndex(_STEP_FINISH)

        self._sync_buttons()

    def _on_back(self) -> None:

        step = self._stack.currentIndex()

        if step == _STEP_NO_RECEIVER:
            self._stack.setCurrentIndex(_STEP_OWNERSHIP)
        elif step == _STEP_OS:
            self._stack.setCurrentIndex(_STEP_OWNERSHIP)
        elif step == _STEP_OS_GUIDE:
            self._stack.setCurrentIndex(_STEP_OS)
        elif step == _STEP_RECEIVER_TEST:
            self._stack.setCurrentIndex(_STEP_OS_GUIDE)
        elif step == _STEP_AIS_CATCHER:
            self._stack.setCurrentIndex(_STEP_RECEIVER_TEST)
        elif step == _STEP_RECEPTION_TEST:
            self._refresh_catcher_status()
            self._stack.setCurrentIndex(_STEP_AIS_CATCHER)
        elif step == _STEP_OBSERVATION:
            self._stack.setCurrentIndex(_STEP_RECEPTION_TEST)

        self._sync_buttons()

    def _on_finish(self) -> None:

        self.accept()

    def _on_internet_only(self) -> None:

        rtl_manager.mark_internet_only()
        self.accept()

    def _on_detect_device(self) -> None:

        if self._detect_worker and self._detect_worker.isRunning():
            return

        self._receiver_result.setText(tr("Detecting RTL device..."))
        self._detect_worker = _RTLDetectWorker(self)
        self._detect_worker.finished.connect(self._on_detect_finished)
        self._detect_worker.start()

    def _on_detect_finished(self) -> None:

        device = self._detect_worker.device if self._detect_worker else None

        if device is None:
            self._receiver_result.setText(tr("Receiver not detected"))
            self._receiver_result.setStyleSheet("color: #ef5350;")
            return

        self._manufacturer_value.setText(device.manufacturer or "—")
        self._serial_value.setText(device.serial or "—")
        self._tuner_value.setText(device.tuner or "—")
        self._sample_rate_value.setText(device.sample_rate or "—")

        if device.detected:
            self._receiver_result.setText(f"✓ {tr('Receiver detected')}")
            self._receiver_result.setStyleSheet("color: #66bb6a;")
        else:
            self._receiver_result.setText(f"✗ {tr('Receiver not detected')}")
            self._receiver_result.setStyleSheet("color: #ef5350;")

    def _refresh_catcher_status(self) -> None:

        status = rtl_manager.ais_catcher_status()
        parts = [
            f"{tr('Installed')}: {'✓' if status.installed else '✗'}",
            f"{tr('Running')}: {'✓' if status.running else '✗'}",
            f"{tr('Port')}: {status.port}",
        ]
        self._catcher_status_label.setText("\n".join(parts))

    def _on_start_catcher(self) -> None:

        preferences_manager.set_rtl_configuration(
            auto_start_ais_catcher=self._auto_start_checkbox.isChecked(),
        )

        if rtl_manager.ensure_ais_catcher():
            self._catcher_status_label.setText(
                f"✓ {tr('AIS-Catcher is running on port')} {rtl_manager.ais_catcher_status().port}"
            )
            self._catcher_status_label.setStyleSheet("color: #66bb6a;")
        else:
            self._catcher_status_label.setText(tr("AIS-Catcher could not be started."))
            self._catcher_status_label.setStyleSheet("color: #ef5350;")

        self._refresh_catcher_status()

    def _on_start_reception(self) -> None:

        if self._reception_worker and self._reception_worker.isRunning():
            return

        self._reception_result.setText(tr("Running reception test..."))
        self._reception_worker = _RTLReceptionWorker(self)
        self._reception_worker.finished.connect(self._on_reception_finished)
        self._reception_worker.start()

    def _on_reception_finished(self) -> None:

        result = self._reception_worker.result if self._reception_worker else None

        if result is None:
            self._reception_result.setText(tr("Reception test failed."))
            self._reception_result.setStyleSheet("color: #ef5350;")
            return

        self._reception_messages.setText(str(result.message_count))
        self._reception_ships.setText(str(result.ships_detected))
        quality_labels = {
            "weak": tr("Weak"),
            "fair": tr("Fair"),
            "good": tr("Good"),
            "none": tr("No signal"),
        }
        self._reception_signal.setText(
            quality_labels.get(result.signal_quality, tr("No signal"))
        )

        if result.success:
            self._reception_result.setText(f"✓ {tr('Reception test successful')}")
            self._reception_result.setStyleSheet("color: #66bb6a;")
        else:
            self._reception_result.setText(
                result.message or tr("No AIS messages received yet.")
            )
            self._reception_result.setStyleSheet("color: #ef5350;")

    def showEvent(self, event) -> None:

        super().showEvent(event)
        self._refresh_catcher_status()
        self._observation_body.setText(self._observation_text())
