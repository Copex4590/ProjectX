# ============================================================================
# Project X
# Data Upgrade Dialog (SAVE-107-B5)
# ============================================================================

from __future__ import annotations

import logging
from enum import Enum

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
from storage import DataMigrationService, default_data_directory
from version import PROJECT_NAME

logger = logging.getLogger(__name__)


class UpgradeStartupResult(str, Enum):
    CONTINUE = "continue"
    RESTART_REQUESTED = "restart_requested"


class MigrationRestartDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._restart_now = True
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setWindowTitle(PROJECT_NAME)

        self._build_ui()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def restart_now(self) -> bool:

        return self._restart_now

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("Project X Data Upgrade"))
        self._title.setText(tr("Migration complete"))
        self._body.setText(
            tr(
                "Your data has been successfully migrated.\n\n"
                "Project X will now restart to begin using the new storage location."
            )
        )
        self._restart_later_button.setText(tr("Restart later"))
        self._restart_now_button.setText(tr("Restart now"))

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

        self._restart_later_button = QPushButton()
        self._restart_later_button.setStyleSheet(
            secondary_button_stylesheet(padding="8px 16px")
        )
        self._restart_later_button.setMinimumWidth(140)
        self._restart_later_button.clicked.connect(self._on_restart_later)
        button_row.addWidget(self._restart_later_button)

        self._restart_now_button = QPushButton()
        self._restart_now_button.setMinimumWidth(140)
        self._restart_now_button.setDefault(True)
        self._restart_now_button.setAutoDefault(True)
        self._restart_now_button.clicked.connect(self._on_restart_now)
        button_row.addWidget(self._restart_now_button)

        layout.addLayout(button_row)

    def _on_restart_now(self) -> None:

        self._restart_now = True
        self.accept()

    def _on_restart_later(self) -> None:

        self._restart_now = False
        self.accept()


def should_offer_data_upgrade(*, first_run_pending: bool = False) -> bool:
    """Return True when the legacy upgrade dialog should be offered at startup."""

    from app.startup_mode import should_offer_legacy_upgrade

    _ = first_run_pending
    return should_offer_legacy_upgrade()


class DataUpgradeDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._restart_result = UpgradeStartupResult.CONTINUE
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setWindowTitle(PROJECT_NAME)

        self._build_ui()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def restart_result(self) -> UpgradeStartupResult:

        return self._restart_result

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

    def _prompt_restart_after_migration(self) -> None:

        dialog = MigrationRestartDialog(self)
        restart_now = False

        if dialog.exec() == QDialog.DialogCode.Accepted:
            restart_now = dialog.restart_now()

        if restart_now:
            self._restart_result = UpgradeStartupResult.RESTART_REQUESTED
            self.accept()
            return

        preferences_manager.set_storage_activation_deferred_until_restart(True)
        QMessageBox.information(
            self,
            tr("Project X Data Upgrade"),
            tr(
                "Your data has been migrated successfully.\n\n"
                "The new storage location will become active the next time you "
                "start Project X. This session will continue using your "
                "previous storage location."
            ),
        )
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
            self._prompt_restart_after_migration()
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


def run_data_upgrade_if_needed(parent=None) -> UpgradeStartupResult:
    """Prompt existing users to migrate legacy data before the main window loads."""

    if not should_offer_data_upgrade():
        return UpgradeStartupResult.CONTINUE

    dialog = DataUpgradeDialog(parent)
    result = dialog.exec()

    if result == QDialog.DialogCode.Accepted:
        return dialog.restart_result()

    preferences_manager.set_legacy_migration_deferred(True)
    return UpgradeStartupResult.CONTINUE
