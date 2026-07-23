# ============================================================================
# Project X
# Professional Alerts Panel (SAVE-215) — Alert Center
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from alerts.alert_event import AlertEvent
from alerts.alert_manager import EVENT_ALERT_FIRED, AlertManager, alert_manager
from alerts.alert_rule import ALERT_TYPE_LABELS, SUPPORTED_RULE_TYPES
from database import registry
from events import eventbus
from gui.i18n_support import bind_language_refresh
from gui.tableutils import show_empty_table_message
from gui.theme import (
    ThemeColors,
    card_stylesheet,
    primary_button_stylesheet,
    secondary_button_stylesheet,
)
from i18n import tr

_ALL_FILTER = "All"
_SEVERITY_FILTERS = (_ALL_FILTER, "info", "warning", "critical")
_EVENT_FILTERS = (_ALL_FILTER,) + SUPPORTED_RULE_TYPES
_AUTO_REFRESH_MS = 15000


def _display_text(value: str | None) -> str:

    text = str(value or "").strip()
    return text if text else "—"


def _format_timestamp(value: datetime | None) -> str:

    if value is None:
        return "—"
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _event_label(event_type: str) -> str:

    return ALERT_TYPE_LABELS.get(event_type, event_type)


@dataclass
class AlertFilters:

    search_text: str = ""
    severity: str = _ALL_FILTER
    event_type: str = _ALL_FILTER
    ack_state: str = _ALL_FILTER  # All / Active / Acknowledged


class _GuiBridge(QWidget):
    refresh_requested = Signal()


class AlertCenterPage(QWidget):
    """Professional Alerts panel (Active / History / Clear / Export)."""

    vesselSelected = Signal(int)

    def __init__(self, manager: AlertManager | None = None, parent=None):
        super().__init__(parent)

        self._manager = manager or alert_manager
        self._events: list[AlertEvent] = []
        self._filters = AlertFilters()
        self._bridge = _GuiBridge()
        self._bridge.refresh_requested.connect(self.refresh)

        self.setStyleSheet(f"background: {ThemeColors.Background};")
        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self.refresh()

        self._timer = QTimer(self)
        self._timer.setInterval(_AUTO_REFRESH_MS)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

        eventbus.subscribe(EVENT_ALERT_FIRED, self._on_alert_fired)

    def _on_alert_fired(self, *args, **kwargs) -> None:

        self._bridge.refresh_requested.emit()

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
        layout.setSpacing(14)

        header = QHBoxLayout()
        self._title = QLabel()
        self._title.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 18pt; font-weight: 700;"
        )
        header.addWidget(self._title)
        header.addStretch(1)
        layout.addLayout(header)

        summary = QHBoxLayout()
        self._active_count = self._metric_card("Active")
        self._history_count = self._metric_card("History")
        self._critical_count = self._metric_card("Critical")
        self._rules_count = self._metric_card("Enabled Rules")
        for card in (
            self._active_count,
            self._history_count,
            self._critical_count,
            self._rules_count,
        ):
            summary.addWidget(card)
        layout.addLayout(summary)

        filters = QFrame()
        filters.setStyleSheet(card_stylesheet(radius=10))
        filters_layout = QVBoxLayout(filters)
        filters_layout.setContentsMargins(14, 12, 14, 12)
        filters_layout.setSpacing(8)

        row1 = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("Search MMSI, message…"))
        self._search.setStyleSheet(self._input_style())
        row1.addWidget(self._search, 2)

        self._severity = QComboBox()
        self._severity.setStyleSheet(self._combo_style())
        row1.addWidget(self._severity)

        self._event_type = QComboBox()
        self._event_type.setStyleSheet(self._combo_style())
        row1.addWidget(self._event_type)

        self._ack_filter = QComboBox()
        self._ack_filter.setStyleSheet(self._combo_style())
        row1.addWidget(self._ack_filter)
        filters_layout.addLayout(row1)

        actions = QHBoxLayout()
        self._refresh_btn = QPushButton()
        self._refresh_btn.setStyleSheet(secondary_button_stylesheet())
        actions.addWidget(self._refresh_btn)

        self._ack_btn = QPushButton()
        self._ack_btn.setStyleSheet(primary_button_stylesheet())
        actions.addWidget(self._ack_btn)

        self._clear_btn = QPushButton()
        self._clear_btn.setStyleSheet(secondary_button_stylesheet())
        actions.addWidget(self._clear_btn)

        self._export_btn = QPushButton()
        self._export_btn.setStyleSheet(secondary_button_stylesheet())
        actions.addWidget(self._export_btn)
        actions.addStretch(1)
        filters_layout.addLayout(actions)
        layout.addWidget(filters)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{
                border: 1px solid {ThemeColors.Border};
                border-radius: 8px;
                background: {ThemeColors.Panel};
            }}
            QTabBar::tab {{
                background: {ThemeColors.panel_header()};
                color: {ThemeColors.TextSecondary};
                padding: 8px 14px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{
                background: {ThemeColors.Primary700};
                color: {ThemeColors.TextPrimary};
            }}
            """
        )

        self._active_table = self._make_table()
        self._history_table = self._make_table()
        self._tabs.addTab(self._active_table, tr("Active"))
        self._tabs.addTab(self._history_table, tr("History"))
        layout.addWidget(self._tabs, 1)

        self._status = QLabel()
        self._status.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        layout.addWidget(self._status)

        self._populate_filter_combos()

    def _metric_card(self, title_key: str) -> QFrame:

        card = QFrame()
        card.setStyleSheet(card_stylesheet(radius=10))
        card.setProperty("title_key", title_key)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        title = QLabel(tr(title_key))
        title.setObjectName("metricTitle")
        title.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        value = QLabel("0")
        value.setObjectName("metricValue")
        value.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 16pt; font-weight: 700;"
        )
        layout.addWidget(title)
        layout.addWidget(value)
        card._title_label = title  # type: ignore[attr-defined]
        card._value_label = value  # type: ignore[attr-defined]
        return card

    def _make_table(self) -> QTableWidget:

        table = QTableWidget(0, 7)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setStyleSheet(
            f"""
            QTableWidget {{
                background: {ThemeColors.Panel};
                alternate-background-color: {ThemeColors.panel_header()};
                color: {ThemeColors.TextPrimary};
                gridline-color: {ThemeColors.Border};
                border: none;
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
            }}
            """
        )
        table.setMinimumHeight(280)
        table.cellDoubleClicked.connect(self._on_row_double_clicked)
        return table

    def _input_style(self) -> str:

        return f"""
            QLineEdit {{
                background: {ThemeColors.Panel};
                color: {ThemeColors.TextPrimary};
                border: 1px solid {ThemeColors.Border};
                border-radius: 6px;
                padding: 6px 10px;
            }}
        """

    def _combo_style(self) -> str:

        return f"""
            QComboBox {{
                background: {ThemeColors.Panel};
                color: {ThemeColors.TextPrimary};
                border: 1px solid {ThemeColors.Border};
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 120px;
            }}
        """

    def _populate_filter_combos(self) -> None:

        self._severity.blockSignals(True)
        self._severity.clear()
        for value in _SEVERITY_FILTERS:
            self._severity.addItem(tr("All") if value == _ALL_FILTER else tr(value), value)
        self._severity.blockSignals(False)

        self._event_type.blockSignals(True)
        self._event_type.clear()
        for value in _EVENT_FILTERS:
            label = tr("All") if value == _ALL_FILTER else tr(_event_label(value))
            self._event_type.addItem(label, value)
        self._event_type.blockSignals(False)

        self._ack_filter.blockSignals(True)
        self._ack_filter.clear()
        for value, label in (
            (_ALL_FILTER, "All"),
            ("active", "Active"),
            ("acked", "Acknowledged"),
        ):
            self._ack_filter.addItem(tr(label), value)
        self._ack_filter.blockSignals(False)

    def _connect_signals(self) -> None:

        self._refresh_btn.clicked.connect(self.refresh)
        self._ack_btn.clicked.connect(self._acknowledge_selected)
        self._clear_btn.clicked.connect(self._clear_alerts)
        self._export_btn.clicked.connect(self._export_alerts)
        self._search.textChanged.connect(lambda _v: self._apply_filters())
        self._severity.currentIndexChanged.connect(lambda _i: self._apply_filters())
        self._event_type.currentIndexChanged.connect(lambda _i: self._apply_filters())
        self._ack_filter.currentIndexChanged.connect(lambda _i: self._apply_filters())
        self._tabs.currentChanged.connect(lambda _i: self._apply_filters())

    def refresh_translations(self) -> None:

        self._title.setText(tr("Alerts"))
        self._refresh_btn.setText(tr("Refresh"))
        self._ack_btn.setText(tr("Acknowledge"))
        self._clear_btn.setText(tr("Clear"))
        self._export_btn.setText(tr("Export"))
        self._search.setPlaceholderText(tr("Search MMSI, message…"))
        self._tabs.setTabText(0, tr("Active"))
        self._tabs.setTabText(1, tr("History"))
        headers = [
            tr("Time"),
            tr("Priority"),
            tr("Type"),
            tr("Vessel"),
            tr("Message"),
            tr("Acknowledged"),
            tr("ID"),
        ]
        self._active_table.setHorizontalHeaderLabels(headers)
        self._history_table.setHorizontalHeaderLabels(headers)

        for card in (
            self._active_count,
            self._history_count,
            self._critical_count,
            self._rules_count,
        ):
            key = card.property("title_key")
            card._title_label.setText(tr(str(key)))

        self._populate_filter_combos()
        self._apply_filters()

    def refresh(self) -> list[AlertEvent]:

        self._events = self._manager.events()
        active = self._manager.active_events()
        history = self._manager.history_events()
        critical = sum(1 for event in active if event.severity == "critical")
        enabled_rules = sum(1 for rule in self._manager.rules() if rule.enabled)

        self._active_count._value_label.setText(str(len(active)))
        self._history_count._value_label.setText(str(len(history)))
        self._critical_count._value_label.setText(str(critical))
        self._rules_count._value_label.setText(str(enabled_rules))
        self._apply_filters()
        self._status.setText(
            tr("{count} alert(s)").replace("{count}", str(len(self._events)))
        )
        return list(self._events)

    def _read_filters(self) -> None:

        self._filters.search_text = self._search.text().strip().lower()
        self._filters.severity = self._severity.currentData() or _ALL_FILTER
        self._filters.event_type = self._event_type.currentData() or _ALL_FILTER
        self._filters.ack_state = self._ack_filter.currentData() or _ALL_FILTER

    def _filtered(self, *, acknowledged: bool | None) -> list[AlertEvent]:

        self._read_filters()
        rows: list[AlertEvent] = []

        for event in self._events:
            if acknowledged is True and not event.acknowledged:
                continue
            if acknowledged is False and event.acknowledged:
                continue
            if self._filters.ack_state == "active" and event.acknowledged:
                continue
            if self._filters.ack_state == "acked" and not event.acknowledged:
                continue
            if (
                self._filters.severity != _ALL_FILTER
                and event.severity != self._filters.severity
            ):
                continue
            if (
                self._filters.event_type != _ALL_FILTER
                and event.event_type != self._filters.event_type
            ):
                continue
            if self._filters.search_text:
                name = ""
                ship = registry.get(event.mmsi)
                if ship is not None:
                    name = str(ship.name or "")
                haystack = f"{event.mmsi} {name} {event.message} {event.event_type}".lower()
                if self._filters.search_text not in haystack:
                    continue
            rows.append(event)

        rows.sort(key=lambda item: item.timestamp, reverse=True)
        return rows

    def _apply_filters(self) -> None:

        active_rows = self._filtered(acknowledged=False)
        history_rows = self._filtered(acknowledged=True)
        self._fill_table(self._active_table, active_rows)
        self._fill_table(self._history_table, history_rows)

    def _fill_table(self, table: QTableWidget, rows: list[AlertEvent]) -> None:

        if not rows:
            show_empty_table_message(table, "No alerts found")
            return

        table.setRowCount(len(rows))
        names = {
            ship.mmsi: str(ship.name or "")
            for ship in registry.all()
        }

        for row_index, event in enumerate(rows):
            vessel = names.get(event.mmsi, "")
            if event.mmsi <= 0:
                vessel_label = tr("System")
            elif vessel:
                vessel_label = f"{vessel} ({event.mmsi})"
            else:
                vessel_label = str(event.mmsi)

            priority = str((event.metadata or {}).get("priority", "—"))
            values = [
                _format_timestamp(event.timestamp),
                priority,
                tr(_event_label(event.event_type)),
                vessel_label,
                _display_text(event.message),
                tr("Yes") if event.acknowledged else tr("No"),
                str(event.id or ""),
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, event.id)
                item.setData(Qt.ItemDataRole.UserRole + 1, event.mmsi)
                if column == 0 and event.timestamp is not None:
                    item.setData(
                        Qt.ItemDataRole.EditRole,
                        event.timestamp.timestamp(),
                    )
                if event.severity == "critical" and column == 2:
                    item.setForeground(Qt.GlobalColor.red)
                table.setItem(row_index, column, item)

        table.resizeColumnsToContents()

    def _current_table(self) -> QTableWidget:

        if self._tabs.currentIndex() == 1:
            return self._history_table
        return self._active_table

    def _selected_event_id(self) -> int | None:

        table = self._current_table()
        rows = table.selectionModel().selectedRows()
        if not rows:
            return None
        item = table.item(rows[0].row(), 0)
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _acknowledge_selected(self) -> None:

        event_id = self._selected_event_id()
        if event_id is None:
            QMessageBox.information(
                self,
                tr("Acknowledge"),
                tr("Select an active alert first."),
            )
            return

        self._manager.acknowledge(event_id)
        self.refresh()

    def _clear_alerts(self) -> None:

        answer = QMessageBox.question(
            self,
            tr("Clear"),
            tr("Clear acknowledged alert history?\nActive alerts are kept."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._manager.clear_history()
        self.refresh()

    def _export_alerts(self) -> None:

        path, _filter = QFileDialog.getSaveFileName(
            self,
            tr("Export"),
            str(Path.home() / "projectx-alerts.csv"),
            "CSV (*.csv)",
        )
        if not path:
            return

        try:
            self._manager.export_events(path)
            self._status.setText(tr("Exported to {path}").replace("{path}", path))
            self._status.setStyleSheet(
                f"color: {ThemeColors.Success}; font-size: 9pt;"
            )
        except Exception as error:
            QMessageBox.warning(self, tr("Export"), str(error))

    def _on_row_double_clicked(self, row: int, _column: int) -> None:

        table = self.sender()
        if not isinstance(table, QTableWidget):
            table = self._current_table()

        item = table.item(row, 0)
        if item is None:
            return

        mmsi = item.data(Qt.ItemDataRole.UserRole + 1)
        try:
            resolved = int(mmsi)
        except (TypeError, ValueError):
            return

        if resolved > 0:
            self.vesselSelected.emit(resolved)
