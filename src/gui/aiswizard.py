# ============================================================================
# Project X
# AIS Providers Setup Wizard
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ais import AISSTREAM_REGISTER_URL, ais_manager
from ais.providers import AISProviderType, normalize_provider_type
from ais.user_provider_service import (
    derive_enabled_providers,
    is_provider_configured,
    save_aisstream_configuration,
    save_local_configuration,
    set_enabled_providers,
)
from config.aiscatcher import AIS_CATCHER_HOST, AIS_CATCHER_PORT
from gui.i18n_support import bind_language_refresh
from gui.theme import DANGER, SUCCESS, TEXT_MUTED, wizard_shell_stylesheet
from gui.thread_utils import stop_qthread
from gui.wizardhelp import add_wizard_back_button, add_wizard_next_button
from i18n import tr
from preferences import preferences_manager

_SUBSTEP_PROVIDERS = 0
_SUBSTEP_CONFIGURE = 1

_PROVIDER_OPTIONS = (
    AISProviderType.AISSTREAM,
    AISProviderType.LOCAL,
    AISProviderType.MARINE_TRAFFIC,
    AISProviderType.AISHUB,
)


def _configuration_prompt(provider: AISProviderType) -> str:

    if provider == AISProviderType.LOCAL:
        return tr("RTL-SDR requires additional configuration.")

    if provider == AISProviderType.MARINE_TRAFFIC:
        return tr("MarineTraffic requires an API key.")

    if provider == AISProviderType.AISHUB:
        return tr("AISHub requires additional configuration.")

    return tr("AISStream requires an API key.")


def _provider_label(provider: AISProviderType) -> str:

    if provider == AISProviderType.AISSTREAM:
        return tr("AISStream")

    if provider == AISProviderType.LOCAL:
        return tr("RTL-SDR")

    if provider == AISProviderType.MARINE_TRAFFIC:
        return tr("MarineTraffic")

    if provider == AISProviderType.AISHUB:
        return tr("AISHub")

    return provider.value


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
        self._selected_provider = AISProviderType.AISSTREAM
        self._last_test_success = False
        self._provider_checkboxes: dict[AISProviderType, QCheckBox] = {}
        self._configure_dismissed: set[AISProviderType] = set()

        self._build_ui()
        self._connect_signals()
        self._load_preferences()

    def refresh_translations(self) -> None:

        self._provider_title.setText(tr("AIS Providers"))
        self._provider_body.setText(
            tr("Choose which AIS providers Project X should use.")
        )

        for provider, checkbox in self._provider_checkboxes.items():
            checkbox.setText(_provider_label(provider))

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

        self._local_title.setText(tr("RTL-SDR"))
        self._host_label.setText(tr("Host"))
        self._port_label.setText(tr("Port"))

        self._future_title.setText(tr("Configuration"))
        self._future_body.setText(
            tr("This provider will be configurable in a future Project X release.")
        )

    def substep_index(self) -> int:

        return self._stack.currentIndex()

    def on_enter(self) -> None:

        self._configure_dismissed.clear()
        self._load_preferences()

    def on_leave(self) -> None:

        if self._test_worker is not None and self._test_worker.isRunning():
            stop_qthread(self._test_worker, label="AISTestWorker")
            self._test_worker = None

    def handle_next(self) -> bool:

        if self.substep_index() != _SUBSTEP_PROVIDERS:
            return False

        return self._complete_provider_selection()

    def handle_back(self) -> bool:

        if self.substep_index() != _SUBSTEP_CONFIGURE:
            return True

        self._stack.setCurrentIndex(_SUBSTEP_PROVIDERS)
        return False

    def handle_confirm(self) -> bool:

        if self.substep_index() != _SUBSTEP_CONFIGURE:
            return False

        if self._test_worker is not None and self._test_worker.isRunning():
            return False

        if self._selected_provider == AISProviderType.AISSTREAM:
            if not self._api_key_input.text().strip():
                return False

            self._save_aisstream_configuration()
        elif self._selected_provider == AISProviderType.LOCAL:
            self._save_local_configuration()
        elif self._selected_provider in (
            AISProviderType.MARINE_TRAFFIC,
            AISProviderType.AISHUB,
        ):
            pass
        else:
            return False

        return self._complete_provider_selection(after_configure=True)

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
        self._provider_body.setStyleSheet(f"color: {TEXT_MUTED};")
        provider_layout.addWidget(self._provider_body)

        for provider in _PROVIDER_OPTIONS:
            checkbox = QCheckBox()
            if provider == AISProviderType.AISSTREAM:
                checkbox.setChecked(True)
            self._provider_checkboxes[provider] = checkbox
            provider_layout.addWidget(checkbox)

        provider_layout.addStretch()
        self._stack.addWidget(provider_page)

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
        self._aisstream_intro_body.setStyleSheet(f"color: {TEXT_MUTED};")
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
        self._instruction_body.setStyleSheet(f"color: {TEXT_MUTED};")
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

        future_page = QWidget()
        future_layout = QVBoxLayout(future_page)
        self._future_title = QLabel()
        self._future_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        future_layout.addWidget(self._future_title)
        self._future_body = QLabel()
        self._future_body.setWordWrap(True)
        self._future_body.setStyleSheet(f"color: {TEXT_MUTED};")
        future_layout.addWidget(self._future_body)
        future_layout.addStretch()
        self._configure_stack.addWidget(future_page)

        test_row = QHBoxLayout()
        self._test_button = QPushButton()
        test_row.addWidget(self._test_button)
        test_row.addStretch()
        configure_layout.addLayout(test_row)

        self._stack.addWidget(configure_page)

    def _connect_signals(self) -> None:

        self._get_api_key_button.clicked.connect(self._on_get_api_key)
        self._have_api_key_button.clicked.connect(self._on_have_api_key)
        self._test_button.clicked.connect(self._on_test_connection)

    def _load_preferences(self) -> None:

        preferences = preferences_manager.get()
        enabled_values = preferences.ais_enabled_providers

        if enabled_values is None:
            enabled_values = derive_enabled_providers(
                normalize_provider_type(preferences.ais_provider)
            )

        enabled = {
            normalize_provider_type(value)
            for value in enabled_values
        }

        for provider, checkbox in self._provider_checkboxes.items():
            checkbox.setChecked(provider in enabled)

        self._api_key_input.setText(preferences.aisstream_api_key)
        self._host_input.setText(preferences.ais_local_host)
        self._port_input.setValue(preferences.ais_local_port)
        self._last_test_success = bool(
            preferences.aisstream_api_key.strip() and preferences.ais_configured
        )

    def _enabled_providers(self) -> set[AISProviderType]:

        return {
            provider
            for provider, checkbox in self._provider_checkboxes.items()
            if checkbox.isChecked()
        }

    def _save_enabled_providers(self, enabled: set[AISProviderType]) -> None:

        set_enabled_providers(enabled)

    def _unconfigured_enabled_providers(
        self,
        enabled: set[AISProviderType],
    ) -> list[AISProviderType]:

        return [
            provider
            for provider in _PROVIDER_OPTIONS
            if provider in enabled and not is_provider_configured(provider)
        ]

    def _prompt_configure_provider(self, provider: AISProviderType) -> bool:

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.setWindowTitle(tr("AIS Providers"))
        dialog.setText(_configuration_prompt(provider))
        configure_button = dialog.addButton(
            tr("Configure now"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        dialog.addButton(tr("Later"), QMessageBox.ButtonRole.RejectRole)
        dialog.exec()

        return dialog.clickedButton() == configure_button

    def _begin_provider_configuration(self, provider: AISProviderType) -> None:

        self._selected_provider = provider

        if provider == AISProviderType.LOCAL:
            from gui.rtlsdrwizard import RTLSdrWizard

            RTLSdrWizard(self.window()).exec()
            self._load_preferences()
            self._stack.setCurrentIndex(_SUBSTEP_PROVIDERS)
            return

        self._configure_stack.setCurrentIndex(
            self._configure_index_for_provider(provider)
        )
        self._stack.setCurrentIndex(_SUBSTEP_CONFIGURE)

        show_test = provider == AISProviderType.AISSTREAM
        self._test_button.setVisible(show_test)

        if provider == AISProviderType.AISSTREAM:
            preferences = preferences_manager.get()

            if preferences.aisstream_api_key:
                self._api_key_panel.setVisible(True)

    def _configure_index_for_provider(self, provider: AISProviderType) -> int:

        if provider == AISProviderType.LOCAL:
            return 1

        if provider in (AISProviderType.MARINE_TRAFFIC, AISProviderType.AISHUB):
            return 2

        return 0

    def _complete_provider_selection(self, *, after_configure: bool = False) -> bool:

        enabled = self._enabled_providers()
        self._save_enabled_providers(enabled)

        if after_configure:
            return True

        pending = self._unconfigured_enabled_providers(enabled)
        pending = [
            provider
            for provider in pending
            if provider not in self._configure_dismissed
        ]

        while pending:
            next_provider = pending[0]

            if self._prompt_configure_provider(next_provider):
                self._begin_provider_configuration(next_provider)
                return False

            self._configure_dismissed.add(next_provider)
            pending = pending[1:]

        return True

    def _on_get_api_key(self) -> None:

        self._instruction_panel.setVisible(True)
        self._api_key_panel.setVisible(True)
        QDesktopServices.openUrl(QUrl(AISSTREAM_REGISTER_URL))

    def _on_have_api_key(self) -> None:

        self._instruction_panel.setVisible(False)
        self._api_key_panel.setVisible(True)
        self._api_key_input.setFocus()

    def _on_test_connection(self) -> None:

        if self._selected_provider != AISProviderType.AISSTREAM:
            return

        self._run_aisstream_test()

    def _run_aisstream_test(self) -> bool:

        if self._test_worker is not None and self._test_worker.isRunning():
            return False

        provider_type = AISProviderType.AISSTREAM.value
        api_key = self._api_key_input.text().strip()
        self._test_button.setEnabled(False)
        self._last_test_success = False

        self._test_worker = _AISTestWorker(
            provider_type,
            api_key,
            AIS_CATCHER_HOST,
            AIS_CATCHER_PORT,
            self,
        )

        self._test_worker.finished.connect(self._on_test_finished)
        self._test_worker.start()
        return False

    def _on_test_finished(self) -> None:

        self._test_button.setEnabled(True)
        result = self._test_worker.result if self._test_worker else None

        if result is not None and result.success:
            self._last_test_success = True
            self._save_aisstream_configuration()

    def _save_aisstream_configuration(self) -> None:

        save_aisstream_configuration(self._api_key_input.text().strip())

    def _save_local_configuration(self) -> None:

        save_local_configuration(
            host=self._host_input.text().strip(),
            port=self._port_input.value(),
        )


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

        self.setWindowTitle(tr("AIS Providers"))
        self._setup.refresh_translations()
        self._back_button.setText(tr("Back"))
        self._continue_button.setText(tr("Continue"))
        self._button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            tr("Cancel")
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            tr("Confirm")
        )

    def _build_ui(self) -> None:

        self.setStyleSheet(wizard_shell_stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._setup = AISSetupWidget()
        layout.addWidget(self._setup)

        button_row = QHBoxLayout()
        self._button_box = QDialogButtonBox()
        self._back_button = add_wizard_back_button(self._button_box)
        self._continue_button = add_wizard_next_button(self._button_box)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        button_row.addWidget(self._button_box)
        layout.addLayout(button_row)

    def _connect_signals(self) -> None:

        self._button_box.rejected.connect(self.reject)
        self._continue_button.clicked.connect(self._on_continue)
        self._back_button.clicked.connect(self._on_back)
        self._button_box.accepted.connect(self._on_confirm)

    def _sync_buttons(self) -> None:

        back_button = self._back_button
        next_button = self._continue_button
        confirm_button = self._button_box.button(
            QDialogButtonBox.StandardButton.Ok
        )

        self._setup.update_outer_buttons(
            back_button,
            next_button,
            confirm_button,
        )

    def _on_continue(self) -> None:

        if self._setup.handle_next():
            self.accept()
            return

        self._sync_buttons()

    def _on_back(self) -> None:

        if self._setup.handle_back():
            self._setup.on_leave()
            return

        self._sync_buttons()

    def _on_confirm(self) -> None:

        if not self._setup.handle_confirm():
            return

        self._setup.on_leave()
        self.accept()

    def reject(self) -> None:

        self._setup.on_leave()
        super().reject()

    def closeEvent(self, event) -> None:

        self._setup.on_leave()
        super().closeEvent(event)

    def showEvent(self, event) -> None:

        super().showEvent(event)
        self._setup.on_enter()
        self._sync_buttons()
