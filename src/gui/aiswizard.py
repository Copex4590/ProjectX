# ============================================================================
# Project X
# AIS Source Setup Wizard
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
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

from ais import AISSTREAM_REGISTER_URL, ais_manager
from ais.providers import AISProviderType, normalize_provider_type
from config.aiscatcher import AIS_CATCHER_HOST, AIS_CATCHER_PORT
from gui.i18n_support import bind_language_refresh
from gui.wizardhelp import add_wizard_back_button, add_wizard_next_button
from i18n import tr
from preferences import preferences_manager

_SUBSTEP_PROVIDER = 0
_SUBSTEP_CONFIGURE = 1

_PROVIDER_CHOICES = (
    AISProviderType.AISSTREAM,
    AISProviderType.LOCAL,
    AISProviderType.HYBRID,
    AISProviderType.LATER,
)


class _AISTestWorker(QThread):

    def __init__(
        self,
        provider_type: str,
        api_key: str,
        host: str,
        port: int,
        parent=None,
    ):
        super().__init__(parent)

        self._provider_type = provider_type
        self._api_key = api_key
        self._host = host
        self._port = port
        self.result = None

    def run(self) -> None:

        self.result = ais_manager.test_configuration(
            provider_type=self._provider_type,
            api_key=self._api_key,
            host=self._host,
            port=self._port,
        )


class AISSetupWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._test_worker: _AISTestWorker | None = None
        self._selected_provider = AISProviderType.LATER
        self._last_test_success = False

        self._build_ui()
        self._connect_signals()
        self._load_preferences()

    def refresh_translations(self) -> None:

        self._provider_title.setText(tr("AIS Source"))
        self._provider_body.setText(
            tr("Choose where vessel data comes from.")
        )
        self._aisstream_option.setText(tr("AISStream (Recommended)"))
        self._local_option.setText(tr("Local AIS receiver (RTL-SDR)"))
        self._hybrid_option.setText(tr("Hybrid (Internet + RTL)"))
        self._later_option.setText(tr("Configure later"))

        self._aisstream_intro_title.setText(tr("AISStream"))
        self._aisstream_intro_body.setText(
            tr(
                "Project X supports AISStream. AISStream provides a free API key "
                "for personal use. Project X will help you configure it."
            )
        )
        self._get_api_key_button.setText(tr("Get API Key"))
        self._have_api_key_button.setText(tr("I already have one"))
        self._instruction_title.setText(tr("How to get your API key"))
        self._instruction_body.setText(
            tr(
                "1. Create a free AISStream account.\n"
                "2. Generate an API key.\n"
                "3. Copy it.\n"
                "4. Return to Project X."
            )
        )
        self._api_key_label.setText(tr("API Key"))
        self._api_key_input.setPlaceholderText(tr("Paste here"))
        self._test_button.setText(tr("Test Connection"))

        self._local_title.setText(tr("Local AIS"))
        self._host_label.setText(tr("Host"))
        self._port_label.setText(tr("Port"))

        self._hybrid_title.setText(tr("Hybrid"))
        self._hybrid_body.setText(tr("Configure both."))
        self._hybrid_api_key_label.setText(tr("API Key"))
        self._hybrid_host_label.setText(tr("Host"))
        self._hybrid_port_label.setText(tr("Port"))

        self._update_result_label()

    def substep_index(self) -> int:

        return self._stack.currentIndex()

    def on_enter(self) -> None:

        self._load_preferences()
        self._update_result_label()

    def on_leave(self) -> None:

        if self._test_worker is not None and self._test_worker.isRunning():
            self._test_worker.wait(1000)

    def handle_next(self) -> bool:

        if self.substep_index() != _SUBSTEP_PROVIDER:
            return False

        self._selected_provider = self._current_provider_choice()

        if self._selected_provider == AISProviderType.LATER:
            ais_manager.save_configuration(
                provider_type=AISProviderType.LATER.value,
                configured=False,
            )
            return True

        self._configure_stack.setCurrentIndex(
            self._configure_index_for_provider(self._selected_provider)
        )
        self._stack.setCurrentIndex(_SUBSTEP_CONFIGURE)

        if self._selected_provider == AISProviderType.AISSTREAM:
            preferences = preferences_manager.get()

            if preferences.aisstream_api_key:
                self._api_key_panel.setVisible(True)

        self._update_result_label()
        return False

    def handle_back(self) -> bool:

        if self.substep_index() != _SUBSTEP_CONFIGURE:
            return True

        self._stack.setCurrentIndex(_SUBSTEP_PROVIDER)
        self._update_result_label()
        return False

    def handle_confirm(self) -> bool:

        if self.substep_index() != _SUBSTEP_CONFIGURE:
            return False

        if self._selected_provider == AISProviderType.LATER:
            return True

        if not self._last_test_success:
            self._result_label.setText(tr("Please test the connection first."))
            self._result_label.setStyleSheet("color: #ef5350;")
            return False

        self._save_current_configuration()
        return True

    def update_outer_buttons(
        self,
        back_button,
        next_button,
        confirm_button,
    ) -> None:

        on_configure_step = self.substep_index() == _SUBSTEP_CONFIGURE

        back_button.setEnabled(on_configure_step)
        next_button.setVisible(not on_configure_step)
        confirm_button.setVisible(on_configure_step)

    def _build_ui(self) -> None:

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        provider_page = QWidget()
        provider_layout = QVBoxLayout(provider_page)

        self._provider_title = QLabel()
        self._provider_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        provider_layout.addWidget(self._provider_title)

        self._provider_body = QLabel()
        self._provider_body.setWordWrap(True)
        self._provider_body.setStyleSheet("color: #9aa4af;")
        provider_layout.addWidget(self._provider_body)

        self._aisstream_option = QRadioButton()
        self._local_option = QRadioButton()
        self._hybrid_option = QRadioButton()
        self._later_option = QRadioButton()
        self._aisstream_option.setChecked(True)

        for option in (
            self._aisstream_option,
            self._local_option,
            self._hybrid_option,
            self._later_option,
        ):
            provider_layout.addWidget(option)

        provider_layout.addStretch()
        self._stack.addWidget(provider_page)

        self._provider_group = QButtonGroup(self)
        self._provider_group.addButton(self._aisstream_option, 0)
        self._provider_group.addButton(self._local_option, 1)
        self._provider_group.addButton(self._hybrid_option, 2)
        self._provider_group.addButton(self._later_option, 3)

        configure_page = QWidget()
        configure_layout = QVBoxLayout(configure_page)

        self._configure_stack = QStackedWidget()
        configure_layout.addWidget(self._configure_stack)

        aisstream_page = QWidget()
        aisstream_layout = QVBoxLayout(aisstream_page)

        self._aisstream_intro_title = QLabel()
        self._aisstream_intro_title.setStyleSheet(
            "font-size: 14pt; font-weight: bold;"
        )
        aisstream_layout.addWidget(self._aisstream_intro_title)

        self._aisstream_intro_body = QLabel()
        self._aisstream_intro_body.setWordWrap(True)
        self._aisstream_intro_body.setStyleSheet("color: #9aa4af;")
        aisstream_layout.addWidget(self._aisstream_intro_body)

        button_row = QHBoxLayout()
        self._get_api_key_button = QPushButton()
        self._have_api_key_button = QPushButton()
        button_row.addWidget(self._get_api_key_button)
        button_row.addWidget(self._have_api_key_button)
        button_row.addStretch()
        aisstream_layout.addLayout(button_row)

        self._instruction_panel = QWidget()
        instruction_layout = QVBoxLayout(self._instruction_panel)
        self._instruction_title = QLabel()
        self._instruction_title.setStyleSheet("font-weight: bold;")
        instruction_layout.addWidget(self._instruction_title)
        self._instruction_body = QLabel()
        self._instruction_body.setWordWrap(True)
        self._instruction_body.setStyleSheet("color: #9aa4af;")
        instruction_layout.addWidget(self._instruction_body)
        self._instruction_panel.setVisible(False)
        aisstream_layout.addWidget(self._instruction_panel)

        self._api_key_panel = QWidget()
        api_key_layout = QFormLayout(self._api_key_panel)
        self._api_key_label = QLabel()
        self._api_key_input = QLineEdit()
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_key_layout.addRow(self._api_key_label, self._api_key_input)
        self._api_key_panel.setVisible(False)
        aisstream_layout.addWidget(self._api_key_panel)

        aisstream_layout.addStretch()
        self._configure_stack.addWidget(aisstream_page)

        local_page = QWidget()
        local_layout = QVBoxLayout(local_page)
        self._local_title = QLabel()
        self._local_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        local_layout.addWidget(self._local_title)

        local_form = QFormLayout()
        self._host_label = QLabel()
        self._host_input = QLineEdit(AIS_CATCHER_HOST)
        self._port_label = QLabel()
        self._port_input = QSpinBox()
        self._port_input.setRange(1, 65535)
        self._port_input.setValue(AIS_CATCHER_PORT)
        local_form.addRow(self._host_label, self._host_input)
        local_form.addRow(self._port_label, self._port_input)
        local_layout.addLayout(local_form)
        local_layout.addStretch()
        self._configure_stack.addWidget(local_page)

        hybrid_page = QWidget()
        hybrid_layout = QVBoxLayout(hybrid_page)
        self._hybrid_title = QLabel()
        self._hybrid_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        hybrid_layout.addWidget(self._hybrid_title)

        self._hybrid_body = QLabel()
        self._hybrid_body.setWordWrap(True)
        self._hybrid_body.setStyleSheet("color: #9aa4af;")
        hybrid_layout.addWidget(self._hybrid_body)

        hybrid_form = QFormLayout()
        self._hybrid_api_key_label = QLabel()
        self._hybrid_api_key_input = QLineEdit()
        self._hybrid_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._hybrid_host_label = QLabel()
        self._hybrid_host_input = QLineEdit(AIS_CATCHER_HOST)
        self._hybrid_port_label = QLabel()
        self._hybrid_port_input = QSpinBox()
        self._hybrid_port_input.setRange(1, 65535)
        self._hybrid_port_input.setValue(AIS_CATCHER_PORT)
        hybrid_form.addRow(self._hybrid_api_key_label, self._hybrid_api_key_input)
        hybrid_form.addRow(self._hybrid_host_label, self._hybrid_host_input)
        hybrid_form.addRow(self._hybrid_port_label, self._hybrid_port_input)
        hybrid_layout.addLayout(hybrid_form)
        hybrid_layout.addStretch()
        self._configure_stack.addWidget(hybrid_page)

        test_row = QHBoxLayout()
        self._test_button = QPushButton()
        test_row.addWidget(self._test_button)
        test_row.addStretch()
        configure_layout.addLayout(test_row)

        self._result_label = QLabel()
        self._result_label.setWordWrap(True)
        configure_layout.addWidget(self._result_label)

        self._stack.addWidget(configure_page)

    def _connect_signals(self) -> None:

        self._get_api_key_button.clicked.connect(self._on_get_api_key)
        self._have_api_key_button.clicked.connect(self._on_have_api_key)
        self._test_button.clicked.connect(self._on_test_connection)

    def _load_preferences(self) -> None:

        preferences = preferences_manager.get()
        provider = normalize_provider_type(preferences.ais_provider)

        if provider == AISProviderType.LOCAL:
            self._local_option.setChecked(True)
        elif provider == AISProviderType.HYBRID:
            self._hybrid_option.setChecked(True)
        elif provider == AISProviderType.LATER:
            self._later_option.setChecked(True)
        else:
            self._aisstream_option.setChecked(True)

        self._api_key_input.setText(preferences.aisstream_api_key)
        self._hybrid_api_key_input.setText(preferences.aisstream_api_key)
        self._host_input.setText(preferences.ais_local_host)
        self._hybrid_host_input.setText(preferences.ais_local_host)
        self._port_input.setValue(preferences.ais_local_port)
        self._hybrid_port_input.setValue(preferences.ais_local_port)
        self._last_test_success = bool(preferences.ais_configured)

    def _current_provider_choice(self) -> AISProviderType:

        button_id = self._provider_group.checkedId()

        if button_id < 0 or button_id >= len(_PROVIDER_CHOICES):
            return AISProviderType.AISSTREAM

        return _PROVIDER_CHOICES[button_id]

    def _configure_index_for_provider(self, provider: AISProviderType) -> int:

        if provider == AISProviderType.LOCAL:
            return 1

        if provider == AISProviderType.HYBRID:
            return 2

        return 0

    def _on_get_api_key(self) -> None:

        self._instruction_panel.setVisible(True)
        self._api_key_panel.setVisible(True)
        QDesktopServices.openUrl(QUrl(AISSTREAM_REGISTER_URL))

    def _on_have_api_key(self) -> None:

        self._instruction_panel.setVisible(False)
        self._api_key_panel.setVisible(True)
        self._api_key_input.setFocus()

    def _current_test_values(self) -> tuple[str, str, str, int]:

        provider = self._selected_provider

        if provider == AISProviderType.LOCAL:
            return (
                provider.value,
                "",
                self._host_input.text().strip(),
                self._port_input.value(),
            )

        if provider == AISProviderType.HYBRID:
            return (
                provider.value,
                self._hybrid_api_key_input.text().strip(),
                self._hybrid_host_input.text().strip(),
                self._hybrid_port_input.value(),
            )

        return (
            provider.value,
            self._api_key_input.text().strip(),
            AIS_CATCHER_HOST,
            AIS_CATCHER_PORT,
        )

    def _on_test_connection(self) -> None:

        if self._test_worker is not None and self._test_worker.isRunning():
            return

        provider_type, api_key, host, port = self._current_test_values()
        self._result_label.setText(tr("Testing connection..."))
        self._result_label.setStyleSheet("color: #bbbbbb;")
        self._test_button.setEnabled(False)
        self._last_test_success = False

        self._test_worker = _AISTestWorker(
            provider_type,
            api_key,
            host,
            port,
            self,
        )
        self._test_worker.finished.connect(self._on_test_finished)
        self._test_worker.start()

    def _on_test_finished(self) -> None:

        self._test_button.setEnabled(True)
        result = self._test_worker.result if self._test_worker else None

        if result is None:
            self._result_label.setText(tr("AISStream unavailable."))
            self._result_label.setStyleSheet("color: #ef5350;")
            return

        if result.success:
            self._last_test_success = True
            self._result_label.setText(
                f"✓ {tr(result.message)}\n{tr('AIS provider configured.')}"
            )
            self._result_label.setStyleSheet("color: #66bb6a;")
            self._save_current_configuration()
            return

        self._last_test_success = False
        self._result_label.setText(tr(result.message))
        self._result_label.setStyleSheet("color: #ef5350;")

    def _save_current_configuration(self) -> None:

        provider_type, api_key, host, port = self._current_test_values()

        ais_manager.save_configuration(
            provider_type=provider_type,
            api_key=api_key,
            host=host,
            port=port,
            configured=self._last_test_success,
        )

    def _update_result_label(self) -> None:

        if self._last_test_success:
            self._result_label.setText(
                f"✓ {tr('Connection successful')}\n{tr('AIS provider configured.')}"
            )
            self._result_label.setStyleSheet("color: #66bb6a;")
            return

        self._result_label.clear()


class AISWizard(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModal(True)
        self.setMinimumWidth(620)
        self.setMinimumHeight(520)

        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self._sync_buttons()

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("AIS Source"))
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

    def _build_ui(self) -> None:

        self.setStyleSheet("""
            QDialog {
                background: #1d2127;
            }

            QLabel {
                color: #d5dbe3;
            }

            QLineEdit, QSpinBox {
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
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._setup = AISSetupWidget()
        layout.addWidget(self._setup)

        button_row = QHBoxLayout()
        self._button_box = QDialogButtonBox()
        self._back_button = add_wizard_back_button(self._button_box)
        self._next_button = add_wizard_next_button(self._button_box)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        button_row.addWidget(self._button_box)
        layout.addLayout(button_row)

    def _connect_signals(self) -> None:

        self._button_box.rejected.connect(self.reject)
        self._next_button.clicked.connect(
            self._on_next
        )
        self._back_button.clicked.connect(
            self._on_back
        )
        self._button_box.accepted.connect(self._on_confirm)

    def _sync_buttons(self) -> None:

        back_button = self._back_button
        next_button = self._next_button
        confirm_button = self._button_box.button(
            QDialogButtonBox.StandardButton.Ok
        )

        self._setup.update_outer_buttons(
            back_button,
            next_button,
            confirm_button,
        )

    def _on_next(self) -> None:

        if self._setup.handle_next():
            self.accept()
            return

        self._sync_buttons()

    def _on_back(self) -> None:

        if self._setup.handle_back():
            self._setup.on_leave()

        self._sync_buttons()

    def _on_confirm(self) -> None:

        if not self._setup.handle_confirm():
            return

        self._setup.on_leave()
        self.accept()

    def showEvent(self, event) -> None:

        super().showEvent(event)
        self._setup.on_enter()
        self._sync_buttons()
