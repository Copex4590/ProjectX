# ============================================================================
# Project X
# Vessel Database Manager Page (SAVE-208)
# ============================================================================

from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from database.vessel_database_manager import (
    AccessStatus,
    DatabaseStatus,
    IntegrityStatus,
    VesselDatabaseManagerSnapshot,
    format_bytes,
    vessel_database_manager,
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


def _status_color(status: DatabaseStatus | IntegrityStatus | AccessStatus) -> str:

    if status in (
        DatabaseStatus.OK,
        IntegrityStatus.OK,
        AccessStatus.READ_WRITE,
    ):
        return ThemeColors.Success
    if status in (
        DatabaseStatus.WARNING,
        AccessStatus.READ_ONLY,
        IntegrityStatus.NOT_CHECKED,
        IntegrityStatus.UNKNOWN,
        DatabaseStatus.UNKNOWN,
    ):
        return ThemeColors.Warning
    return ThemeColors.Danger


class _MetricRow(QWidget):

    def __init__(self, label_key: str, parent=None):
        super().__init__(parent)

        self._label_key = label_key

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        self._label = QLabel()
        self._label.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 10pt;"
        )
        layout.addWidget(self._label)

        layout.addStretch(1)

        self._value = QLabel("—")
        self._value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._value.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 11pt; font-weight: 600;"
        )
        layout.addWidget(self._value)

    def set_value(self, text: str, *, color: str | None = None) -> None:

        self._value.setText(text)
        resolved = color or ThemeColors.TextPrimary
        self._value.setStyleSheet(
            f"color: {resolved}; font-size: 11pt; font-weight: 600;"
        )

    def refresh_translations(self) -> None:

        self._label.setText(tr(self._label_key))


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
        self.body.setSpacing(2)
        self.body.setContentsMargins(0, 4, 0, 0)
        root.addLayout(self.body)

    def refresh_translations(self) -> None:

        self._title.setText(tr(self._title_key))


class VesselDatabaseManagerPage(QWidget):
    """Professional Vessel Database Manager — UI + backend hooks (SAVE-208)."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._snapshot: VesselDatabaseManagerSnapshot | None = None
        self._manager = vessel_database_manager

        self.setStyleSheet(f"background: {ThemeColors.Background};")

        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self.refresh_statistics()

    def _build_ui(self) -> None:

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

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
        header.setSpacing(12)

        self._title_label = QLabel()
        self._title_label.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 18pt; font-weight: 700;"
        )
        header.addWidget(self._title_label)
        header.addStretch(1)

        self._subtitle_label = QLabel()
        self._subtitle_label.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 10pt;"
        )
        header.addWidget(self._subtitle_label, 0, Qt.AlignmentFlag.AlignBottom)

        layout.addLayout(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        self._local_card = _SectionCard("Local Vessel Database")
        self._metric_vessel_count = _MetricRow("Vessel count")
        self._metric_db_size = _MetricRow("Database size")
        self._metric_last_update = _MetricRow("Last update")
        self._metric_version = _MetricRow("Version")
        for row in (
            self._metric_vessel_count,
            self._metric_db_size,
            self._metric_last_update,
            self._metric_version,
        ):
            self._local_card.body.addWidget(row)
        self._path_label = QLabel()
        self._path_label.setWordWrap(True)
        self._path_label.setStyleSheet(
            f"color: {ThemeColors.text_soft()}; font-size: 9pt; padding-top: 6px;"
        )
        self._local_card.body.addWidget(self._path_label)
        grid.addWidget(self._local_card, 0, 0)

        self._sync_card = _SectionCard("Synchronization")
        self._metric_last_sync = _MetricRow("Last Sync")
        self._metric_next_sync = _MetricRow("Next Sync")
        self._sync_card.body.addWidget(self._metric_last_sync)
        self._sync_card.body.addWidget(self._metric_next_sync)
        self._auto_sync_checkbox = QCheckBox()
        self._auto_sync_checkbox.setStyleSheet(
            f"""
            QCheckBox {{
                color: {ThemeColors.TextPrimary};
                font-size: 10pt;
                spacing: 8px;
                padding-top: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {ThemeColors.Border};
                border-radius: 3px;
                background: {ThemeColors.PanelHover};
            }}
            QCheckBox::indicator:checked {{
                background: {ThemeColors.Primary500};
                border-color: {ThemeColors.Primary300};
            }}
            """
        )
        self._sync_card.body.addWidget(self._auto_sync_checkbox)
        grid.addWidget(self._sync_card, 0, 1)

        self._stats_card = _SectionCard("Statistics")
        self._metric_imported = _MetricRow("Imported vessels")
        self._metric_updated = _MetricRow("Updated vessels")
        self._metric_unknown = _MetricRow("Unknown vessels")
        self._metric_failed = _MetricRow("Failed lookups")
        for row in (
            self._metric_imported,
            self._metric_updated,
            self._metric_unknown,
            self._metric_failed,
        ):
            self._stats_card.body.addWidget(row)
        grid.addWidget(self._stats_card, 1, 0)

        self._diagnostics_card = _SectionCard("Diagnostics")
        self._metric_db_status = _MetricRow("Database status")
        self._metric_integrity = _MetricRow("Integrity")
        self._metric_access = _MetricRow("Read/Write access")
        for row in (
            self._metric_db_status,
            self._metric_integrity,
            self._metric_access,
        ):
            self._diagnostics_card.body.addWidget(row)
        grid.addWidget(self._diagnostics_card, 1, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        self._actions_card = _SectionCard("Actions")
        actions = QHBoxLayout()
        actions.setSpacing(10)

        self._refresh_button = QPushButton()
        self._refresh_button.setStyleSheet(primary_button_stylesheet())
        actions.addWidget(self._refresh_button)

        self._sync_button = QPushButton()
        self._sync_button.setStyleSheet(primary_button_stylesheet())
        actions.addWidget(self._sync_button)

        self._verify_button = QPushButton()
        self._verify_button.setStyleSheet(secondary_button_stylesheet())
        actions.addWidget(self._verify_button)

        self._open_folder_button = QPushButton()
        self._open_folder_button.setStyleSheet(secondary_button_stylesheet())
        actions.addWidget(self._open_folder_button)

        actions.addStretch(1)
        self._actions_card.body.addLayout(actions)
        layout.addWidget(self._actions_card)

        self._status_bar = QLabel()
        self._status_bar.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        layout.addWidget(self._status_bar)
        layout.addStretch(1)

    def _connect_signals(self) -> None:

        self._refresh_button.clicked.connect(self.refresh_statistics)
        self._sync_button.clicked.connect(self._on_start_synchronization)
        self._verify_button.clicked.connect(self._on_verify_database)
        self._open_folder_button.clicked.connect(self._on_open_database_folder)
        self._auto_sync_checkbox.toggled.connect(self._on_auto_sync_toggled)

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Database Manager"))
        self._subtitle_label.setText(tr("Vessel database status and maintenance"))

        for card in (
            self._local_card,
            self._sync_card,
            self._stats_card,
            self._diagnostics_card,
            self._actions_card,
        ):
            card.refresh_translations()

        for metric in (
            self._metric_vessel_count,
            self._metric_db_size,
            self._metric_last_update,
            self._metric_version,
            self._metric_last_sync,
            self._metric_next_sync,
            self._metric_imported,
            self._metric_updated,
            self._metric_unknown,
            self._metric_failed,
            self._metric_db_status,
            self._metric_integrity,
            self._metric_access,
        ):
            metric.refresh_translations()

        self._auto_sync_checkbox.setText(tr("Auto Sync"))
        self._refresh_button.setText(tr("Refresh Statistics"))
        self._sync_button.setText(tr("Start Synchronization"))
        self._verify_button.setText(tr("Verify Database"))
        self._open_folder_button.setText(tr("Open Database Folder"))

        if self._snapshot is not None:
            self._apply_snapshot(self._snapshot)

    def refresh_statistics(self) -> None:

        try:
            snapshot = self._manager.collect_snapshot(run_integrity=False)
        except Exception:
            logger.exception("Failed to collect vessel database manager snapshot")
            self._status_bar.setText(tr("Failed to refresh statistics"))
            self._status_bar.setStyleSheet(
                f"color: {ThemeColors.Danger}; font-size: 9pt;"
            )
            return

        self._apply_snapshot(snapshot)
        self._status_bar.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        self._status_bar.setText(
            tr("Statistics refreshed at {time}").format(
                time=_format_timestamp(snapshot.collected_at)
            )
        )

    def _apply_snapshot(self, snapshot: VesselDatabaseManagerSnapshot) -> None:

        self._snapshot = snapshot
        local = snapshot.local
        sync = snapshot.synchronization
        stats = snapshot.statistics
        diag = snapshot.diagnostics

        self._metric_vessel_count.set_value(str(local.vessel_count))
        self._metric_db_size.set_value(format_bytes(local.size_bytes))
        self._metric_last_update.set_value(_format_timestamp(local.last_updated))
        self._metric_version.set_value(local.schema_version)
        self._path_label.setText(str(local.database_path))

        self._metric_last_sync.set_value(_format_timestamp(sync.last_sync))
        self._metric_next_sync.set_value(_format_timestamp(sync.next_sync))
        self._auto_sync_checkbox.blockSignals(True)
        self._auto_sync_checkbox.setChecked(sync.auto_sync_enabled)
        self._auto_sync_checkbox.blockSignals(False)

        self._metric_imported.set_value(str(stats.imported_vessels))
        self._metric_updated.set_value(str(stats.updated_vessels))
        self._metric_unknown.set_value(str(stats.unknown_vessels))
        self._metric_failed.set_value(str(stats.failed_lookups))

        self._metric_db_status.set_value(
            self._database_status_label(diag.database_status),
            color=_status_color(diag.database_status),
        )
        integrity_text = self._integrity_label(diag.integrity)
        if diag.integrity_detail and diag.integrity != IntegrityStatus.OK:
            integrity_text = f"{integrity_text} ({diag.integrity_detail})"
        self._metric_integrity.set_value(
            integrity_text,
            color=_status_color(diag.integrity),
        )
        self._metric_access.set_value(
            self._access_label(diag.access),
            color=_status_color(diag.access),
        )

    def _database_status_label(self, status: DatabaseStatus) -> str:

        mapping = {
            DatabaseStatus.OK: tr("OK"),
            DatabaseStatus.WARNING: tr("Warning"),
            DatabaseStatus.ERROR: tr("Error"),
            DatabaseStatus.UNKNOWN: tr("Unknown"),
        }
        return mapping.get(status, tr("Unknown"))

    def _integrity_label(self, status: IntegrityStatus) -> str:

        mapping = {
            IntegrityStatus.OK: tr("OK"),
            IntegrityStatus.FAILED: tr("Failed"),
            IntegrityStatus.UNKNOWN: tr("Unknown"),
            IntegrityStatus.NOT_CHECKED: tr("Not checked"),
        }
        return mapping.get(status, tr("Unknown"))

    def _access_label(self, status: AccessStatus) -> str:

        mapping = {
            AccessStatus.READ_WRITE: tr("Read/Write"),
            AccessStatus.READ_ONLY: tr("Read-only"),
            AccessStatus.NO_ACCESS: tr("No access"),
            AccessStatus.UNKNOWN: tr("Unknown"),
        }
        return mapping.get(status, tr("Unknown"))

    def _on_auto_sync_toggled(self, checked: bool) -> None:

        self._manager.set_auto_sync(checked)
        self.refresh_statistics()

    def _on_start_synchronization(self) -> None:

        accepted = self._manager.start_synchronization()
        self.refresh_statistics()
        if accepted:
            self._status_bar.setText(tr("Synchronization started"))
            self._status_bar.setStyleSheet(
                f"color: {ThemeColors.Success}; font-size: 9pt;"
            )
        else:
            self._status_bar.setText(tr("Synchronization could not be started"))
            self._status_bar.setStyleSheet(
                f"color: {ThemeColors.Warning}; font-size: 9pt;"
            )

    def _on_verify_database(self) -> None:

        try:
            snapshot = self._manager.collect_snapshot(run_integrity=True)
        except Exception:
            logger.exception("Vessel database verification failed")
            QMessageBox.warning(
                self,
                tr("Verify Database"),
                tr("Verification failed. See application log for details."),
            )
            return

        self._apply_snapshot(snapshot)
        integrity = snapshot.diagnostics.integrity
        if integrity == IntegrityStatus.OK:
            self._status_bar.setText(tr("Database integrity verified"))
            self._status_bar.setStyleSheet(
                f"color: {ThemeColors.Success}; font-size: 9pt;"
            )
        else:
            self._status_bar.setText(tr("Database integrity check reported issues"))
            self._status_bar.setStyleSheet(
                f"color: {ThemeColors.Danger}; font-size: 9pt;"
            )

    def _on_open_database_folder(self) -> None:

        path = self._manager.database_path.parent
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.exception("Cannot create database folder %s", path)
            QMessageBox.warning(
                self,
                tr("Open Database Folder"),
                tr("The database folder could not be opened."),
            )
            return

        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))
        if not opened:
            QMessageBox.information(
                self,
                tr("Open Database Folder"),
                str(path.resolve()),
            )
        else:
            self._status_bar.setText(tr("Opened database folder"))
            self._status_bar.setStyleSheet(
                f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
            )

    def showEvent(self, event) -> None:

        super().showEvent(event)
        self.refresh_statistics()
