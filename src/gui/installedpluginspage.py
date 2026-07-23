# ============================================================================
# Project X
# Installed Plugins Page (SAVE-212)
# ============================================================================

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.paths import plugins_dir
from gui.i18n_support import bind_language_refresh
from gui.theme import (
    ThemeColors,
    card_stylesheet,
    primary_button_stylesheet,
    secondary_button_stylesheet,
)
from i18n import tr
from plugins.manager import plugin_manager
from plugins.registry import PluginRecord, PluginState

logger = logging.getLogger(__name__)


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


class InstalledPluginsPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._records: list[PluginRecord] = []
        self._selected_id: str | None = None

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

        self._list_card = _SectionCard("Installed Plugins")
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
        self._table.setMinimumHeight(260)
        self._list_card.body.addWidget(self._table)

        row_actions = QHBoxLayout()
        row_actions.setSpacing(10)

        self._refresh_button = QPushButton()
        self._refresh_button.setStyleSheet(secondary_button_stylesheet())
        row_actions.addWidget(self._refresh_button)

        self._enable_button = QPushButton()
        self._enable_button.setStyleSheet(primary_button_stylesheet())
        row_actions.addWidget(self._enable_button)

        self._disable_button = QPushButton()
        self._disable_button.setStyleSheet(secondary_button_stylesheet())
        row_actions.addWidget(self._disable_button)

        row_actions.addStretch(1)
        self._list_card.body.addLayout(row_actions)
        layout.addWidget(self._list_card)

        self._details_card = _SectionCard("Details")
        self._details = QTextEdit()
        self._details.setReadOnly(True)
        self._details.setMinimumHeight(160)
        self._details.setStyleSheet(
            f"""
            QTextEdit {{
                background: {ThemeColors.Panel};
                color: {ThemeColors.TextPrimary};
                border: 1px solid {ThemeColors.Border};
                border-radius: 6px;
                padding: 10px;
                font-size: 10pt;
            }}
            """
        )
        self._details_card.body.addWidget(self._details)
        layout.addWidget(self._details_card)

        self._status_label = QLabel()
        self._status_label.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        layout.addWidget(self._status_label)
        layout.addStretch(1)

        self._update_action_buttons()

    def _connect_signals(self) -> None:

        self._refresh_button.clicked.connect(self.refresh_list)
        self._enable_button.clicked.connect(self._enable_selected)
        self._disable_button.clicked.connect(self._disable_selected)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Installed Plugins"))
        self._path_label.setText(str(plugins_dir()))
        self._list_card.refresh_translations()
        self._details_card.refresh_translations()
        self._refresh_button.setText(tr("Refresh"))
        self._enable_button.setText(tr("Enable"))
        self._disable_button.setText(tr("Disable"))
        self._table.setHorizontalHeaderLabels(
            [
                tr("Name"),
                tr("Version"),
                tr("Author"),
                tr("Status"),
                tr("ID"),
            ]
        )
        self._render_details()

    def refresh_list(self) -> None:

        try:
            plugin_manager.initialize()
            self._records = plugin_manager.list_plugins()
        except Exception:
            logger.exception("Failed to list plugins")
            self._records = []
            self._status_label.setText(tr("Failed to load plugins"))
            self._status_label.setStyleSheet(
                f"color: {ThemeColors.Danger}; font-size: 9pt;"
            )
            return

        selected = self._selected_id
        self._table.setRowCount(0)

        for record in self._records:
            row = self._table.rowCount()
            self._table.insertRow(row)
            values = (
                record.metadata.name,
                record.metadata.version,
                record.metadata.author or "—",
                self._status_label_for(record),
                record.metadata.id,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 3:
                    item.setForeground(self._status_brush(record))
                self._table.setItem(row, column, item)

        self._table.resizeColumnsToContents()

        if selected:
            for row in range(self._table.rowCount()):
                item = self._table.item(row, 4)
                if item is not None and item.text() == selected:
                    self._table.selectRow(row)
                    break

        count = len(self._records)
        self._status_label.setText(
            tr("{count} plugin(s) installed").replace("{count}", str(count))
        )
        self._status_label.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        self._on_selection_changed()

    def _status_label_for(self, record: PluginRecord) -> str:

        if record.state == PluginState.ENABLED or record.enabled:
            return tr("Enabled")
        if record.state == PluginState.ERROR:
            return tr("Error")
        if record.state in (PluginState.DISABLED, PluginState.LOADED):
            return tr("Disabled")
        return tr("Discovered")

    def _status_brush(self, record: PluginRecord):

        from PySide6.QtGui import QBrush, QColor

        if record.state == PluginState.ENABLED or record.enabled:
            return QBrush(QColor(ThemeColors.Success))
        if record.state == PluginState.ERROR:
            return QBrush(QColor(ThemeColors.Danger))
        return QBrush(QColor(ThemeColors.TextSecondary))

    def _selected_record(self) -> PluginRecord | None:

        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None

        row = rows[0].row()
        item = self._table.item(row, 4)
        if item is None:
            return None

        plugin_id = item.text()
        for record in self._records:
            if record.plugin_id == plugin_id:
                return record
        return plugin_manager.get_plugin(plugin_id)

    def _on_selection_changed(self) -> None:

        record = self._selected_record()
        self._selected_id = record.plugin_id if record else None
        self._render_details()
        self._update_action_buttons()

    def _update_action_buttons(self) -> None:

        record = self._selected_record()
        has_selection = record is not None
        enabled = bool(record and record.enabled)

        self._enable_button.setEnabled(has_selection and not enabled)
        self._disable_button.setEnabled(has_selection and enabled)

    def _render_details(self) -> None:

        record = self._selected_record()
        if record is None:
            self._details.setPlainText(tr("Select a plugin to view details."))
            return

        meta = record.metadata
        deps = meta.dependencies or {}
        dep_lines = (
            "\n".join(f"  - {dep_id}: {requirement}" for dep_id, requirement in deps.items())
            if deps
            else f"  {tr('None')}"
        )

        error_block = ""
        if record.error or record.dependency_errors:
            parts = []
            if record.error:
                parts.append(record.error)
            parts.extend(record.dependency_errors)
            error_block = f"\n{tr('Error')}: " + " | ".join(parts)

        path_text = str(meta.path) if meta.path else "—"

        self._details.setPlainText(
            "\n".join(
                [
                    f"{tr('Name')}: {meta.name}",
                    f"{tr('ID')}: {meta.id}",
                    f"{tr('Version')}: {meta.version}",
                    f"{tr('Author')}: {meta.author or '—'}",
                    f"{tr('Status')}: {self._status_label_for(record)}",
                    f"{tr('API version')}: {meta.api_version}",
                    f"{tr('License')}: {meta.license or '—'}",
                    f"{tr('Homepage')}: {meta.homepage or '—'}",
                    f"{tr('Path')}: {path_text}",
                    f"{tr('Description')}: {meta.description or '—'}",
                    f"{tr('Dependencies')}:",
                    dep_lines,
                ]
            )
            + error_block
        )

    def _enable_selected(self) -> None:

        record = self._selected_record()
        if record is None:
            return

        result = plugin_manager.enable(record.plugin_id)
        if not result.success:
            QMessageBox.warning(
                self,
                tr("Enable"),
                result.message or tr("Failed to enable plugin"),
            )
        self.refresh_list()

    def _disable_selected(self) -> None:

        record = self._selected_record()
        if record is None:
            return

        result = plugin_manager.disable(record.plugin_id)
        if not result.success:
            QMessageBox.warning(
                self,
                tr("Disable"),
                result.message or tr("Failed to disable plugin"),
            )
        self.refresh_list()
