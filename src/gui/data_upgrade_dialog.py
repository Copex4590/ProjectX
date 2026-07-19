# ============================================================================
# Project X
# Data Upgrade Dialog (SAVE-107-B5)
# ============================================================================

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
)

from gui.i18n_support import bind_language_refresh
from gui.theme import TEXT, secondary_button_stylesheet, wizard_shell_stylesheet
from i18n import tr
from preferences import preferences_manager
from storage import DataMigrationService, default_data_directory, ensure_active_layout, legacy_data_exists
from version import PROJECT_NAME

logger = logging.getLogger(__name__)


def should_offer_data_upgrade(*, first_run_pending: bool) -> bool:

    preferences = preferences_manager.get()

    if first_run_pending:
        return False

    if preferences.has_data_directory() or preferences.legacy_migration_deferred:
        return False

    return legacy_data_exists()


class DataUpgradeDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._migration_succeeded = False
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setWindowTitle(PROJECT_NAME)

        self._build_ui()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def migration_succeeded(self) -> bool:

        return self._migration_succeeded

    def refresh_translations(self) -> None:

        destination = default_data_directory()
        self.setWindowTitle(tr("Project X Data Upgrade"))
        self._title.setText(tr("Move your existing Project X data"))
        self._body.setText(
            tr(
                "Project X can now store your ships, logs, and saved data in a "
                "dedicated folder at:\n\n{destination}\n\n"
                "We found existing data from a previous version. "
                "Would you like to move it there now?"
            ).format(destination=destination)
        )
        self._move_button.setText(tr("Move my data"))
        self._keep_button.setText(tr("Keep current location for now"))

    def _build_ui(self) -> None:

        self.setStyleSheet(wizard_shell_stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self._title = QLabel()
        self._title.setWordWrap(True)
        self._title.setStyleSheet("font-size: 14pt; font-weight: bold; color: white;")
        layout.addWidget(self._title)

        self._body = QLabel()
        self._body.setWordWrap(True)
        self._body.setStyleSheet(f"color: {TEXT}; font-size: 11pt;")
        layout.addWidget(self._body)

        layout.addSpacing(8)

        button_row = QHBoxLayout()
        button_row.addStretch()

        self._keep_button = QPushButton()
        self._keep_button.setStyleSheet(
            secondary_button_stylesheet(padding="8px 16px")
        )
        self._keep_button.setMinimumWidth(180)
        self._keep_button.clicked.connect(self._on_keep_current_location)
        button_row.addWidget(self._keep_button)

        self._move_button = QPushButton()
        self._move_button.setMinimumWidth(140)
        self._move_button.clicked.connect(self._on_move_data)
        button_row.addWidget(self._move_button)

        layout.addLayout(button_row)

    def _on_keep_current_location(self) -> None:

        preferences_manager.set_legacy_migration_deferred(True)
        self.accept()

    def _on_move_data(self) -> None:

        destination = default_data_directory()
        progress = QProgressDialog(
            tr("Moving your Project X data..."),
            "",
            0,
            0,
            self,
        )
        progress.setWindowTitle(tr("Project X Data Upgrade"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.show()

        try:
            result = DataMigrationService().run(destination)
        finally:
            progress.close()

        if result.success:
            ensure_active_layout()
            self._migration_succeeded = True
            QMessageBox.information(
                self,
                tr("Project X Data Upgrade"),
                tr(
                    "Your Project X data was moved successfully to:\n\n{destination}"
                ).format(destination=destination),
            )
            self.accept()
            return

        logger.error("Data upgrade migration failed: %s", result.message)

        QMessageBox.critical(
            self,
            tr("Project X Data Upgrade"),
            tr(
                "Project X could not move your data automatically.\n\n{details}\n\n"
                "Your original data has been left unchanged. "
                "Project X will continue using your current data location."
            ).format(details=result.message),
        )
        self.reject()


def run_data_upgrade_if_needed(*, first_run_pending: bool, parent=None) -> bool:
    """Prompt existing users to migrate legacy data before the main window loads."""

    if not should_offer_data_upgrade(first_run_pending=first_run_pending):
        return True

    dialog = DataUpgradeDialog(parent)
    result = dialog.exec()

    if result == QDialog.DialogCode.Accepted:
        return True

    preferences_manager.set_legacy_migration_deferred(True)
    return True
