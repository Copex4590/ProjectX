# ============================================================================
# Project X
# Alert Center Page
# ============================================================================

from dataclasses import dataclass
from datetime import date, datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from alerts.alert_event import AlertEvent
from alerts.alert_manager import AlertManager, alert_manager
from alerts.alert_rule import SUPPORTED_RULE_TYPES
from database import registry
from gui.i18n_support import bind_language_refresh
from gui.tableutils import show_empty_table_message
from gui.theme import analytics_page_stylesheet
from i18n import tr

_ALL_FILTER = "All"

_SEVERITY_FILTERS = (
    _ALL_FILTER,
    "info",
    "warning",
    "critical",
)

_EVENT_FILTERS = (_ALL_FILTER,) + SUPPORTED_RULE_TYPES

_AUTO_REFRESH_MS = 30000


def _display_text(value: str | None) -> str:

    text = str(value or "").strip()

    if text:
        return text

    return "—"


def _tr_severity(value: str | None) -> str:

    text = str(value or "").strip()

    if not text:
        return "—"

    if text in _SEVERITY_FILTERS[1:]:
        return tr(text)

    return text


def _tr_event_type(value: str | None) -> str:

    text = str(value or "").strip()

    if not text:
        return "—"

    return tr(text)


def _format_timestamp(value: datetime | None) -> str:

    if value is None:
        return "—"

    return value.strftime("%Y-%m-%d %H:%M:%S")


def _parse_filter_date(value: str) -> date | None:

    text = str(value or "").strip()

    if not text:
        return None

    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


@dataclass
class AlertCenterFilters:

    search_text: str = ""
    severity: str = _ALL_FILTER
    event_type: str = _ALL_FILTER
    rule_name: str = _ALL_FILTER
    date_from: str = ""
    date_to: str = ""


class AlertCenterPage(QWidget):

    vesselSelected = Signal(int)

    def __init__(
        self,
        manager: AlertManager | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._manager = manager or alert_manager
        self._events: list[AlertEvent] = []
        self._rule_lookup: dict[int, str] = {}
        self._name_lookup: dict[int, str] = {}
        self._filters = AlertCenterFilters()
        self._auto_refresh_enabled = False

        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.setInterval(_AUTO_REFRESH_MS)
        self._auto_refresh_timer.timeout.connect(self.refresh)

        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh()

    def refresh(self) -> list[AlertEvent]:

        self._events = self._manager.events()
        self._rule_lookup = {
            rule.id: _display_text(rule.name)
            for rule in self._manager.rules()
            if rule.id is not None
        }
        self._name_lookup = {
            ship.mmsi: _display_text(ship.name)
            for ship in registry.all()
            if _display_text(ship.name) != "—"
        }
        self._refresh_rule_filter_options()
        self._update_summary()
        self._populate_table()
        return list(self._events)

    def apply_filters(self) -> list[AlertEvent]:

        self._read_filters_from_ui()
        self._populate_table()
        return self._filtered_events()

    def clear_filters(self) -> None:

        self._filters = AlertCenterFilters()

        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)

        self._sync_filter_combo(self.severity_filter, _ALL_FILTER)
        self._sync_filter_combo(self.event_filter, _ALL_FILTER)
        self._sync_filter_combo(self.rule_filter, _ALL_FILTER)

        self.date_from_input.blockSignals(True)
        self.date_from_input.clear()
        self.date_from_input.blockSignals(False)

        self.date_to_input.blockSignals(True)
        self.date_to_input.clear()
        self.date_to_input.blockSignals(False)

        self._populate_table()

    def set_auto_refresh(self, enabled: bool) -> None:

        self._auto_refresh_enabled = bool(enabled)
        self.auto_refresh_checkbox.blockSignals(True)
        self.auto_refresh_checkbox.setChecked(self._auto_refresh_enabled)
        self.auto_refresh_checkbox.blockSignals(False)

        if self._auto_refresh_enabled:
            self._auto_refresh_timer.start()
        else:
            self._auto_refresh_timer.stop()

    def _build_ui(self) -> None:

        self.setStyleSheet(analytics_page_stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)

        self._title_label = QLabel(tr("Alert Center"))
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setProperty("role", "title")
        layout.addWidget(self._title_label)

        summary = QGridLayout()
        self._total_alerts_label = self._summary_label(tr("Total Alerts"))
        summary.addWidget(self._total_alerts_label, 0, 0)
        self.total_alerts_value = QLabel("0")
        self.total_alerts_value.setProperty("role", "summary-value")
        summary.addWidget(self.total_alerts_value, 1, 0)

        self._active_rules_label = self._summary_label(tr("Active Rules"))
        summary.addWidget(self._active_rules_label, 0, 1)
        self.active_rules_value = QLabel("0")
        self.active_rules_value.setProperty("role", "summary-value")
        summary.addWidget(self.active_rules_value, 1, 1)

        self._alerts_today_label = self._summary_label(tr("Alerts Today"))
        summary.addWidget(self._alerts_today_label, 0, 2)
        self.alerts_today_value = QLabel("0")
        self.alerts_today_value.setProperty("role", "summary-value")
        summary.addWidget(self.alerts_today_value, 1, 2)

        self._critical_alerts_label = self._summary_label(tr("Critical Alerts"))
        summary.addWidget(self._critical_alerts_label, 0, 3)
        self.critical_alerts_value = QLabel("0")
        self.critical_alerts_value.setProperty("role", "summary-value")
        summary.addWidget(self.critical_alerts_value, 1, 3)
        layout.addLayout(summary)

        controls = QGridLayout()
        controls.setHorizontalSpacing(12)
        controls.setVerticalSpacing(8)

        self._search_label = self._field_label(tr("Search"))
        controls.addWidget(self._search_label, 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            tr("MMSI, vessel name, or message")
        )
        controls.addWidget(self.search_input, 0, 1, 1, 3)

        self._severity_label = self._field_label(tr("Severity"))
        controls.addWidget(self._severity_label, 1, 0)
        self.severity_filter = QComboBox()
        self._populate_severity_filter()
        controls.addWidget(self.severity_filter, 1, 1)

        self._event_type_label = self._field_label(tr("Event Type"))
        controls.addWidget(self._event_type_label, 1, 2)
        self.event_filter = QComboBox()
        self._populate_event_filter()
        controls.addWidget(self.event_filter, 1, 3)

        self._rule_label = self._field_label(tr("Rule"))
        controls.addWidget(self._rule_label, 2, 0)
        self.rule_filter = QComboBox()
        self.rule_filter.addItem(tr("All"), _ALL_FILTER)
        controls.addWidget(self.rule_filter, 2, 1)

        self._date_from_label = self._field_label(tr("Date From"))
        controls.addWidget(self._date_from_label, 2, 2)
        self.date_from_input = QLineEdit()
        self.date_from_input.setPlaceholderText(tr("YYYY-MM-DD"))
        controls.addWidget(self.date_from_input, 2, 3)

        self._date_to_label = self._field_label(tr("Date To"))
        controls.addWidget(self._date_to_label, 3, 0)
        self.date_to_input = QLineEdit()
        self.date_to_input.setPlaceholderText(tr("YYYY-MM-DD"))
        controls.addWidget(self.date_to_input, 3, 1)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self.refresh_button = QPushButton(tr("Refresh"))
        self.clear_button = QPushButton(tr("Clear Filters"))
        self.auto_refresh_checkbox = QCheckBox(tr("Auto Refresh"))
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.clear_button)
        button_row.addWidget(self.auto_refresh_checkbox)
        button_row.addStretch()

        controls.addLayout(button_row, 3, 2, 1, 2)
        layout.addLayout(controls)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(self._table_header_labels())
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)

        layout.addWidget(self.table)

    def _summary_label(self, text: str) -> QLabel:

        label = QLabel(text)
        label.setProperty("role", "summary-title")
        return label

    def _field_label(self, text: str) -> QLabel:

        label = QLabel(text)
        label.setProperty("role", "field")
        return label

    @staticmethod
    def _table_header_labels() -> list[str]:

        return [
            tr("Time"),
            tr("Severity"),
            tr("Event"),
            tr("Vessel"),
            tr("Rule"),
            tr("Message"),
        ]

    def _populate_severity_filter(self) -> None:

        current = self.severity_filter.currentData()

        self.severity_filter.blockSignals(True)
        self.severity_filter.clear()

        for value in _SEVERITY_FILTERS:
            label = tr("All") if value == _ALL_FILTER else tr(value)
            self.severity_filter.addItem(label, value)

        self._sync_filter_combo(self.severity_filter, current or _ALL_FILTER)
        self.severity_filter.blockSignals(False)

    def _populate_event_filter(self) -> None:

        current = self.event_filter.currentData()

        self.event_filter.blockSignals(True)
        self.event_filter.clear()

        for value in _EVENT_FILTERS:
            label = tr("All") if value == _ALL_FILTER else tr(value)
            self.event_filter.addItem(label, value)

        self._sync_filter_combo(self.event_filter, current or _ALL_FILTER)
        self.event_filter.blockSignals(False)

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Alert Center"))
        self._total_alerts_label.setText(tr("Total Alerts"))
        self._active_rules_label.setText(tr("Active Rules"))
        self._alerts_today_label.setText(tr("Alerts Today"))
        self._critical_alerts_label.setText(tr("Critical Alerts"))

        self._search_label.setText(tr("Search"))
        self._severity_label.setText(tr("Severity"))
        self._event_type_label.setText(tr("Event Type"))
        self._rule_label.setText(tr("Rule"))
        self._date_from_label.setText(tr("Date From"))
        self._date_to_label.setText(tr("Date To"))

        self.search_input.setPlaceholderText(
            tr("MMSI, vessel name, or message")
        )
        self.date_from_input.setPlaceholderText(tr("YYYY-MM-DD"))
        self.date_to_input.setPlaceholderText(tr("YYYY-MM-DD"))

        self.refresh_button.setText(tr("Refresh"))
        self.clear_button.setText(tr("Clear Filters"))
        self.auto_refresh_checkbox.setText(tr("Auto Refresh"))
        self.refresh_button.setToolTip(tr("Reload alerts from the database"))
        self.clear_button.setToolTip(tr("Reset all alert filters"))

        self._populate_severity_filter()
        self._populate_event_filter()
        self._refresh_rule_filter_options()

        self.table.setHorizontalHeaderLabels(self._table_header_labels())
        self._populate_table()

    def _connect_signals(self) -> None:

        self.refresh_button.clicked.connect(self.refresh)
        self.clear_button.clicked.connect(self.clear_filters)
        self.auto_refresh_checkbox.toggled.connect(self.set_auto_refresh)
        self.search_input.textChanged.connect(
            lambda _value: self.apply_filters()
        )
        self.severity_filter.currentTextChanged.connect(
            lambda _value: self.apply_filters()
        )
        self.event_filter.currentTextChanged.connect(
            lambda _value: self.apply_filters()
        )
        self.rule_filter.currentTextChanged.connect(
            lambda _value: self.apply_filters()
        )
        self.date_from_input.textChanged.connect(
            lambda _value: self.apply_filters()
        )
        self.date_to_input.textChanged.connect(
            lambda _value: self.apply_filters()
        )
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)

    def _read_filters_from_ui(self) -> None:

        self._filters.search_text = self.search_input.text().strip().lower()
        self._filters.severity = (
            self.severity_filter.currentData() or _ALL_FILTER
        )
        self._filters.event_type = (
            self.event_filter.currentData() or _ALL_FILTER
        )
        self._filters.rule_name = (
            self.rule_filter.currentData() or _ALL_FILTER
        )
        self._filters.date_from = self.date_from_input.text().strip()
        self._filters.date_to = self.date_to_input.text().strip()

    def _sync_filter_combo(self, combo: QComboBox, value: str) -> None:

        index = combo.findData(value or _ALL_FILTER)

        if index < 0:
            index = 0

        combo.setCurrentIndex(index)

    def _refresh_rule_filter_options(self) -> None:

        current = self.rule_filter.currentData()
        names = sorted({
            _display_text(rule.name)
            for rule in self._manager.rules()
            if _display_text(rule.name) != "—"
        })

        self.rule_filter.blockSignals(True)
        self.rule_filter.clear()
        self.rule_filter.addItem(tr("All"), _ALL_FILTER)

        for name in names:
            self.rule_filter.addItem(name, name)

        self._sync_filter_combo(self.rule_filter, current or _ALL_FILTER)
        self.rule_filter.blockSignals(False)

    def _vessel_name(self, mmsi: int) -> str:

        return self._name_lookup.get(mmsi, "—")

    def _rule_name(self, event: AlertEvent) -> str:

        metadata_name = _display_text(
            (event.metadata or {}).get("rule_name")
        )

        if metadata_name != "—":
            return metadata_name

        return self._rule_lookup.get(event.rule_id, "—")

    def _update_summary(self) -> None:

        today = date.today()

        self.total_alerts_value.setText(str(len(self._events)))
        self.active_rules_value.setText(
            str(sum(1 for rule in self._manager.rules() if rule.enabled))
        )
        self.alerts_today_value.setText(
            str(
                sum(
                    1
                    for event in self._events
                    if event.timestamp.date() == today
                )
            )
        )
        self.critical_alerts_value.setText(
            str(
                sum(
                    1
                    for event in self._events
                    if event.severity == "critical"
                )
            )
        )

    def _matches_search(self, event: AlertEvent) -> bool:

        if not self._filters.search_text:
            return True

        vessel_name = self._vessel_name(event.mmsi).lower()
        haystack = " ".join([
            str(event.mmsi),
            vessel_name,
            _display_text(event.message).lower(),
        ])

        return self._filters.search_text in haystack

    def _matches_severity(self, event: AlertEvent) -> bool:

        if self._filters.severity == _ALL_FILTER:
            return True

        return event.severity == self._filters.severity

    def _matches_event_type(self, event: AlertEvent) -> bool:

        if self._filters.event_type == _ALL_FILTER:
            return True

        return event.event_type == self._filters.event_type

    def _matches_rule(self, event: AlertEvent) -> bool:

        if self._filters.rule_name == _ALL_FILTER:
            return True

        return self._rule_name(event) == self._filters.rule_name

    def _matches_date_range(self, event: AlertEvent) -> bool:

        date_from = _parse_filter_date(self._filters.date_from)
        date_to = _parse_filter_date(self._filters.date_to)

        if date_from is None and date_to is None:
            return True

        event_date = event.timestamp.date()

        if date_from is not None and event_date < date_from:
            return False

        if date_to is not None and event_date > date_to:
            return False

        return True

    def _filtered_events(self) -> list[AlertEvent]:

        events = list(self._events)

        events = [
            event
            for event in events
            if self._matches_severity(event)
        ]

        events = [
            event
            for event in events
            if self._matches_event_type(event)
        ]

        events = [
            event
            for event in events
            if self._matches_rule(event)
        ]

        events = [
            event
            for event in events
            if self._matches_date_range(event)
        ]

        events = [
            event
            for event in events
            if self._matches_search(event)
        ]

        events.sort(key=lambda event: event.timestamp, reverse=True)

        return events

    def _populate_table(self) -> None:

        rows = self._filtered_events()

        if not rows:
            show_empty_table_message(
                self.table,
                "No alerts found",
            )
            return

        sorting_enabled = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))

        for row_index, event in enumerate(rows):
            vessel_label = self._vessel_name(event.mmsi)
            if vessel_label != "—":
                vessel_label = f"{vessel_label} ({event.mmsi})"
            else:
                vessel_label = str(event.mmsi)

            values = [
                _format_timestamp(event.timestamp),
                _tr_severity(event.severity),
                _tr_event_type(event.event_type),
                vessel_label,
                self._rule_name(event),
                _display_text(event.message),
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setData(Qt.ItemDataRole.UserRole, event.mmsi)

                if column_index == 0 and event.timestamp is not None:
                    item.setData(
                        Qt.ItemDataRole.EditRole,
                        event.timestamp.timestamp(),
                    )

                self.table.setItem(row_index, column_index, item)

        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(sorting_enabled)

    def _on_row_double_clicked(self, row: int, _column: int) -> None:

        item = self.table.item(row, 0)

        if item is None:
            return

        mmsi = item.data(Qt.ItemDataRole.UserRole)

        if mmsi is None:
            return

        self.vesselSelected.emit(int(mmsi))
