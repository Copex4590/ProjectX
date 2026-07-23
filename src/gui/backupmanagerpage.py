# ============================================================================
# Project X
# Backup & Restore Manager Page (SAVE-210)
# ============================================================================

from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from backup.backup_manager import (
    BackupEntry,
    BackupKind,
    backup_manager,
    format_bytes,
)
from gui.i18n_support import bind_language_refresh
from gui.theme import (
    ThemeColors,
    card_stylesheet,
    primary_button_stylesheet,
    secondary_button_stylesheet,
)
from i18n import tr

logger = logging.getLogger(__name__)


def _format_timestamp(value: datetime | None) -> str:

    if value is None:
        return "—"
    return value.strftime("%Y-%m-%d %H:%M:%S")


class _SectionCard(QFrame):

    def __init__(self, title_key: str, parent=None):
        super().__init__(parent)

        self._title_key = title_key
        self.setStyleSheet(card_stylesheet(radius=10))

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        self._title = QLabel()
        self._title.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 12pt; font-weight: 700;"
        )
        root.addWidget(self._title)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {ThemeColors.Border};")
        root.addWidget(divider)

        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        self.body.setContentsMargins(0, 4, 0, 0)
        root.addLayout(self.body)

    def refresh_translations(self) -> None:

        self._title.setText(tr(self._title_key))


class BackupManagerPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._manager = backup_manager
        self._entries: list[BackupEntry] = []
        self._selected_path: str | None = None

        self.setStyleSheet(f"background: {ThemeColors.Background};")
        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self.refresh_list()

    def _build_ui(self) -> None:

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {ThemeColors.Background}; border: none; }}"
        )
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet(f"background: {ThemeColors.Background};")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        self._title_label = QLabel()
        self._title_label.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 18pt; font-weight: 700;"
        )
        header.addWidget(self._title_label)
        header.addStretch(1)

        self._path_label = QLabel()
        self._path_label.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        header.addWidget(self._path_label, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(header)

        self._actions_card = _SectionCard("Create Backup")
        actions = QHBoxLayout()
        actions.setSpacing(10)

        self._full_button = QPushButton()
        self._full_button.setStyleSheet(primary_button_stylesheet())
        actions.addWidget(self._full_button)

        self._database_button = QPushButton()
        self._database_button.setStyleSheet(primary_button_stylesheet())
        actions.addWidget(self._database_button)

        self._settings_button = QPushButton()
        self._settings_button.setStyleSheet(secondary_button_stylesheet())
        actions.addWidget(self._settings_button)

        self._open_folder_button = QPushButton()
        self._open_folder_button.setStyleSheet(secondary_button_stylesheet())
        actions.addWidget(self._open_folder_button)

        actions.addStretch(1)
        self._actions_card.body.addLayout(actions)
        layout.addWidget(self._actions_card)

        self._list_card = _SectionCard("Backup List")
        self._table = QTableWidget(0, 5)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet(
            f"""
            QTableWidget {{
                background: {ThemeColors.Panel};
                alternate-background-color: {ThemeColors.panel_header()};
                color: {ThemeColors.TextPrimary};
                gridline-color: {ThemeColors.Border};
                border: 1px solid {ThemeColors.Border};
                border-radius: 6px;
            }}
            QHeaderView::section {{
                background: {ThemeColors.panel_header()};
                color: {ThemeColors.TextSecondary};
                padding: 8px;
                border: none;
                border-bottom: 1px solid {ThemeColors.Border};
                font-weight: 600;
            }}
            QTableWidget::item:selected {{
                background: {ThemeColors.Primary700};
                color: {ThemeColors.TextPrimary};
            }}
            """
        )
        self._table.setMinimumHeight(280)
        self._list_card.body.addWidget(self._table)

        row_actions = QHBoxLayout()
        row_actions.setSpacing(10)

        self._refresh_button = QPushButton()
        self._refresh_button.setStyleSheet(secondary_button_stylesheet())
        row_actions.addWidget(self._refresh_button)

        self._restore_button = QPushButton()
        self._restore_button.setStyleSheet(primary_button_stylesheet())
        row_actions.addWidget(self._restore_button)

        self._delete_button = QPushButton()
        self._delete_button.setStyleSheet(secondary_button_stylesheet())
        row_actions.addWidget(self._delete_button)

        row_actions.addStretch(1)
        self._list_card.body.addLayout(row_actions)
        layout.addWidget(self._list_card)

        self._status_label = QLabel()
        self._status_label.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        layout.addWidget(self._status_label)
        layout.addStretch(1)

    def _connect_signals(self) -> None:

        self._full_button.clicked.connect(
            lambda: self._create_backup(BackupKind.FULL)
        )
        self._database_button.clicked.connect(
            lambda: self._create_backup(BackupKind.DATABASE)
        )
        self._settings_button.clicked.connect(
            lambda: self._create_backup(BackupKind.SETTINGS)
        )
        self._open_folder_button.clicked.connect(self._open_backups_folder)
        self._refresh_button.clicked.connect(self.refresh_list)
        self._restore_button.clicked.connect(self._restore_selected)
        self._delete_button.clicked.connect(self._delete_selected)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Backup & Restore"))
        self._path_label.setText(str(self._manager.backups_root))
        self._actions_card.refresh_translations()
        self._list_card.refresh_translations()

        self._full_button.setText(tr("Full Backup"))
        self._database_button.setText(tr("Database Backup"))
        self._settings_button.setText(tr("Settings Backup"))
        self._open_folder_button.setText(tr("Open Backups Folder"))
        self._refresh_button.setText(tr("Refresh List"))
        self._restore_button.setText(tr("Restore Backup"))
        self._delete_button.setText(tr("Delete Backup"))

        headers = [
            tr("Type"),
            tr("Date"),
            tr("Size"),
            tr("Files"),
            tr("Name"),
        ]
        self._table.setHorizontalHeaderLabels(headers)
        self.refresh_list()

    def refresh_list(self) -> None:

        try:
            self._entries = self._manager.list_backups()
        except Exception:
            logger.exception("Failed to list backups")
            self._entries = []
            self._status_label.setText(tr("Failed to list backups"))
            self._status_label.setStyleSheet(
                f"color: {ThemeColors.Danger}; font-size: 9pt;"
            )
            return

        self._table.setRowCount(len(self._entries))
        for row, entry in enumerate(self._entries):
            values = [
                entry.kind.value,
                _format_timestamp(entry.created_at),
                format_bytes(entry.size_bytes),
                str(entry.file_count),
                entry.path.name,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, str(entry.path))
                self._table.setItem(row, column, item)

        self._table.resizeColumnsToContents()
        self._status_label.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        self._status_label.setText(
            tr("{count} backup(s)").format(count=len(self._entries))
        )
        self._on_selection_changed()

    def showEvent(self, event) -> None:

        super().showEvent(event)
        self.refresh_list()

    def _selected_entry(self) -> BackupEntry | None:

        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        index = rows[0].row()
        if index < 0 or index >= len(self._entries):
            return None
        return self._entries[index]

    def _on_selection_changed(self) -> None:

        entry = self._selected_entry()
        enabled = entry is not None
        self._restore_button.setEnabled(enabled)
        self._delete_button.setEnabled(enabled)
        self._selected_path = str(entry.path) if entry else None

    def _create_backup(self, kind: BackupKind) -> None:

        result = self._manager.create_backup(kind)
        if result.success:
            self._status_label.setStyleSheet(
                f"color: {ThemeColors.Success}; font-size: 9pt;"
            )
            self._status_label.setText(tr(result.message))
        else:
            self._status_label.setStyleSheet(
                f"color: {ThemeColors.Danger}; font-size: 9pt;"
            )
            self._status_label.setText(tr(result.message))
            QMessageBox.warning(
                self,
                tr("Create Backup"),
                tr(result.message),
            )
        self.refresh_list()

    def _restore_selected(self) -> None:

        entry = self._selected_entry()
        if entry is None:
            return

        confirm = QMessageBox.question(
            self,
            tr("Restore Backup"),
            tr(
                "Restore this backup?\n\n"
                "Current database and settings files may be overwritten.\n\n"
                "{name}"
            ).format(name=entry.path.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        result = self._manager.restore_backup(entry.path)
        if result.success:
            self._status_label.setStyleSheet(
                f"color: {ThemeColors.Success}; font-size: 9pt;"
            )
            self._status_label.setText(tr(result.message))
            QMessageBox.information(
                self,
                tr("Restore Backup"),
                tr(result.message)
                + "\n\n"
                + tr("Restart Project X if settings do not apply immediately."),
            )
        else:
            self._status_label.setStyleSheet(
                f"color: {ThemeColors.Danger}; font-size: 9pt;"
            )
            self._status_label.setText(tr(result.message))
            QMessageBox.warning(
                self,
                tr("Restore Backup"),
                tr(result.message),
            )

    def _delete_selected(self) -> None:

        entry = self._selected_entry()
        if entry is None:
            return

        confirm = QMessageBox.question(
            self,
            tr("Delete Backup"),
            tr("Delete this backup permanently?\n\n{name}").format(
                name=entry.path.name
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        result = self._manager.delete_backup(entry.path)
        if result.success:
            self._status_label.setStyleSheet(
                f"color: {ThemeColors.Success}; font-size: 9pt;"
            )
        else:
            self._status_label.setStyleSheet(
                f"color: {ThemeColors.Danger}; font-size: 9pt;"
            )
            QMessageBox.warning(
                self,
                tr("Delete Backup"),
                tr(result.message),
            )
        self._status_label.setText(tr(result.message))
        self.refresh_list()

    def _open_backups_folder(self) -> None:

        path = self._manager.backups_root
        path.mkdir(parents=True, exist_ok=True)
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))
        if not opened:
            QMessageBox.information(
                self,
                tr("Open Backups Folder"),
                str(path.resolve()),
            )
