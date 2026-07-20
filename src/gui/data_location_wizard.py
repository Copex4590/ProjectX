# ============================================================================
# First-run Data Location Wizard (SAVE-107-C4)
# ============================================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
)

from gui.data_location_wizard_page import DataLocationWizardPage
from gui.i18n_support import bind_language_refresh
from gui.theme import wizard_shell_stylesheet
from gui.wizardhelp import add_wizard_next_button
from i18n import tr
from app.startup_mode import needs_data_root_wizard
from storage.data_root_initialization import DataRootInitializationService
from storage.data_root_validation import (
    DataRootValidationService,
    ValidationSeverity,
)


class DataLocationWizard(QDialog):
    """First-run wizard for choosing and initializing the Project X data root."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModal(True)
        self.setMinimumWidth(560)
        self.setMinimumHeight(360)

        self._validation_service = DataRootValidationService()
        self._initialization_service = DataRootInitializationService()

        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self._validate_current_selection()

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("Project X Setup"))
        self._page.refresh_translations()
        self._finish_button.setText(tr("Next"))
        self._button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            tr("Cancel")
        )

    def _build_ui(self) -> None:

        self.setStyleSheet(wizard_shell_stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._page = DataLocationWizardPage(self)
        layout.addWidget(self._page)

        button_row = QHBoxLayout()
        self._button_box = QDialogButtonBox()
        self._finish_button = add_wizard_next_button(self._button_box)
        self._finish_button.setText(tr("Next"))
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        button_row.addWidget(self._button_box)
        layout.addLayout(button_row)

    def _connect_signals(self) -> None:

        self._finish_button.clicked.connect(self._on_finish)
        self._button_box.rejected.connect(self.reject)
        self._page.selection_changed.connect(self._validate_current_selection)

    def _validate_current_selection(self) -> None:

        result = self._validation_service.validate(self._page.selected_directory())
        self._apply_validation_result(result)
        self._finish_button.setEnabled(not result.blocks_completion)

    def _apply_validation_result(self, result) -> None:

        self._page.clear_validation_feedback()

        if result.severity is ValidationSeverity.ERROR:
            self._page.set_validation_error(result.message)
            return

        if result.severity is ValidationSeverity.WARNING:
            self._page.set_validation_warning(result.message)

    def _on_finish(self) -> None:

        validation = self._validation_service.validate(self._page.selected_directory())
        self._apply_validation_result(validation)

        if validation.blocks_completion:
            self._finish_button.setEnabled(False)
            return

        initialization = self._initialization_service.initialize(
            self._page.selected_directory(),
        )

        if not initialization.success:
            self._page.set_validation_error(initialization.message)
            self._finish_button.setEnabled(False)
            return

        from observation.observation_manager import reset_observation_manager

        reset_observation_manager()
        self.accept()


def run_data_location_setup_if_needed(parent=None) -> bool:
    """Prompt for data root setup when required before storage activation."""

    if not needs_data_root_wizard():
        return True

    wizard = DataLocationWizard(parent)
    return wizard.exec() == QDialog.DialogCode.Accepted
