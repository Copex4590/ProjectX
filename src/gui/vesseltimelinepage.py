# ============================================================================
# Project X
# Vessel Timeline Page
# ============================================================================

from dataclasses import dataclass
from datetime import date, datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
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

from database import registry
from engines.timeline.arrival_departure_engine import (
    EVENT_ARRIVAL,
    EVENT_DEPARTURE,
)
from timeline.timeline_manager import TimelineManager, timeline_manager
from timeline.timeline_recorder import EVENT_POSITION_UPDATE
from timeline.timeline_record import TimelineRecord

_ALL_FILTER = "All"

_EVENT_FILTERS = (
    _ALL_FILTER,
    EVENT_ARRIVAL,
    EVENT_DEPARTURE,
    EVENT_POSITION_UPDATE,
)


def _display_text(value: str | None) -> str:

    text = str(value or "").strip()

    if text:
        return text

    return "—"


def _format_timestamp(value: datetime | None) -> str:

    if value is None:
        return "—"

    return value.strftime("%Y-%m-%d %H:%M:%S")


def _format_coordinate(value: float | None) -> str:

    if value is None:
        return "—"

    return f"{value:.5f}"


def _format_speed(value: float | None) -> str:

    if value is None:
        return "—"

    return f"{value:.1f}"


def _parse_filter_date(value: str) -> date | None:

    text = str(value or "").strip()

    if not text:
        return None

    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


@dataclass
class TimelineViewerFilters:

    search_text: str = ""
    event_type: str = _ALL_FILTER
    date_from: str = ""
    date_to: str = ""


class VesselTimelinePage(QWidget):

    vesselSelected = Signal(int)

    def __init__(
        self,
        manager: TimelineManager | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._manager = manager or timeline_manager
        self._records: list[TimelineRecord] = []
        self._name_lookup: dict[int, str] = {}
        self._filters = TimelineViewerFilters()

        self._build_ui()
        self._connect_signals()
        self.refresh()

    def refresh(self) -> list[TimelineRecord]:

        self._records = self._manager.all()
        self._name_lookup = {
            ship.mmsi: _display_text(ship.name)
            for ship in registry.all()
            if _display_text(ship.name) != "—"
        }
        self._update_summary()
        self._populate_table()
        return list(self._records)

    def apply_filters(self) -> list[TimelineRecord]:

        self._read_filters_from_ui()
        self._populate_table()
        return self._filtered_records()

    def clear_filters(self) -> None:

        self._filters = TimelineViewerFilters()

        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)

        self._sync_filter_combo(self.event_filter, _ALL_FILTER)

        self.date_from_input.blockSignals(True)
        self.date_from_input.clear()
        self.date_from_input.blockSignals(False)

        self.date_to_input.blockSignals(True)
        self.date_to_input.clear()
        self.date_to_input.blockSignals(False)

        self._populate_table()

    def _build_ui(self) -> None:

        self.setStyleSheet("""
            QLabel[role="title"] {
                color: white;
                font-size: 26pt;
                font-weight: bold;
            }

            QLabel[role="summary-title"] {
                color: #9aa4af;
                font-size: 9pt;
                font-weight: 600;
            }

            QLabel[role="summary-value"] {
                color: white;
                font-size: 16pt;
                font-weight: bold;
            }

            QLabel[role="field"] {
                color: #d5dbe3;
                font-size: 10pt;
                font-weight: 600;
            }

            QLineEdit, QComboBox {
                background: #252a31;
                color: white;
                border: 1px solid #40444b;
                border-radius: 6px;
                padding: 6px 8px;
            }

            QPushButton {
                background: #1976d2;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
            }

            QTableWidget {
                background: #252a31;
                color: white;
                border: 1px solid #40444b;
                gridline-color: #40444b;
            }

            QHeaderView::section {
                background: #2f353d;
                color: #d5dbe3;
                border: 1px solid #40444b;
                padding: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)

        title = QLabel("Vessel Timeline")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setProperty("role", "title")
        layout.addWidget(title)

        summary = QGridLayout()
        summary.addWidget(self._summary_label("Total Events"), 0, 0)
        self.total_value = QLabel("0")
        self.total_value.setProperty("role", "summary-value")
        summary.addWidget(self.total_value, 1, 0)

        summary.addWidget(self._summary_label("Arrivals"), 0, 1)
        self.arrival_value = QLabel("0")
        self.arrival_value.setProperty("role", "summary-value")
        summary.addWidget(self.arrival_value, 1, 1)

        summary.addWidget(self._summary_label("Departures"), 0, 2)
        self.departure_value = QLabel("0")
        self.departure_value.setProperty("role", "summary-value")
        summary.addWidget(self.departure_value, 1, 2)

        summary.addWidget(self._summary_label("Position Updates"), 0, 3)
        self.position_value = QLabel("0")
        self.position_value.setProperty("role", "summary-value")
        summary.addWidget(self.position_value, 1, 3)
        layout.addLayout(summary)

        controls = QGridLayout()
        controls.setHorizontalSpacing(12)
        controls.setVerticalSpacing(8)

        controls.addWidget(self._field_label("Search"), 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("MMSI or vessel name")
        controls.addWidget(self.search_input, 0, 1, 1, 3)

        controls.addWidget(self._field_label("Event Type"), 1, 0)
        self.event_filter = QComboBox()
        for value in _EVENT_FILTERS:
            self.event_filter.addItem(value)
        controls.addWidget(self.event_filter, 1, 1)

        controls.addWidget(self._field_label("Date From"), 1, 2)
        self.date_from_input = QLineEdit()
        self.date_from_input.setPlaceholderText("YYYY-MM-DD")
        controls.addWidget(self.date_from_input, 1, 3)

        controls.addWidget(self._field_label("Date To"), 2, 0)
        self.date_to_input = QLineEdit()
        self.date_to_input.setPlaceholderText("YYYY-MM-DD")
        controls.addWidget(self.date_to_input, 2, 1)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self.refresh_button = QPushButton("Refresh")
        self.clear_button = QPushButton("Clear Filters")
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.clear_button)
        button_row.addStretch()

        controls.addLayout(button_row, 2, 2, 1, 2)

        layout.addLayout(controls)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Timestamp",
            "Event",
            "MMSI",
            "Name",
            "Latitude",
            "Longitude",
            "Speed",
            "Source",
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

    def _summary_label(self, text: str) -> QLabel:

        label = QLabel(text)
        label.setProperty("role", "summary-title")
        return label

    def _field_label(self, text: str) -> QLabel:

        label = QLabel(text)
        label.setProperty("role", "field")
        return label

    def _connect_signals(self) -> None:

        self.refresh_button.clicked.connect(self.refresh)
        self.clear_button.clicked.connect(self.clear_filters)
        self.search_input.textChanged.connect(
            lambda _value: self.apply_filters()
        )
        self.event_filter.currentTextChanged.connect(
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
        self._filters.event_type = self.event_filter.currentText()
        self._filters.date_from = self.date_from_input.text().strip()
        self._filters.date_to = self.date_to_input.text().strip()

    def _sync_filter_combo(self, combo: QComboBox, value: str) -> None:

        index = combo.findText(value or _ALL_FILTER)

        if index < 0:
            index = 0

        combo.setCurrentIndex(index)

    def _vessel_name(self, mmsi: int) -> str:

        return self._name_lookup.get(mmsi, "—")

    def _update_summary(self) -> None:

        self.total_value.setText(str(len(self._records)))
        self.arrival_value.setText(
            str(sum(1 for record in self._records if record.event_type == EVENT_ARRIVAL))
        )
        self.departure_value.setText(
            str(sum(1 for record in self._records if record.event_type == EVENT_DEPARTURE))
        )
        self.position_value.setText(
            str(
                sum(
                    1
                    for record in self._records
                    if record.event_type == EVENT_POSITION_UPDATE
                )
            )
        )

    def _matches_search(self, record: TimelineRecord) -> bool:

        if not self._filters.search_text:
            return True

        name = self._vessel_name(record.mmsi).lower()
        haystack = " ".join([
            str(record.mmsi),
            name,
        ]).lower()

        return self._filters.search_text in haystack

    def _matches_event_type(self, record: TimelineRecord) -> bool:

        if self._filters.event_type == _ALL_FILTER:
            return True

        return record.event_type == self._filters.event_type

    def _matches_date_range(self, record: TimelineRecord) -> bool:

        date_from = _parse_filter_date(self._filters.date_from)
        date_to = _parse_filter_date(self._filters.date_to)

        if date_from is None and date_to is None:
            return True

        record_date = record.timestamp.date()

        if date_from is not None and record_date < date_from:
            return False

        if date_to is not None and record_date > date_to:
            return False

        return True

    def _filtered_records(self) -> list[TimelineRecord]:

        records = list(self._records)

        records = [
            record
            for record in records
            if self._matches_event_type(record)
        ]

        records = [
            record
            for record in records
            if self._matches_date_range(record)
        ]

        records = [
            record
            for record in records
            if self._matches_search(record)
        ]

        return records

    def _populate_table(self) -> None:

        rows = self._filtered_records()
        self.table.setRowCount(len(rows))

        for row_index, record in enumerate(rows):
            values = [
                _format_timestamp(record.timestamp),
                _display_text(record.event_type),
                str(record.mmsi),
                self._vessel_name(record.mmsi),
                _format_coordinate(record.latitude),
                _format_coordinate(record.longitude),
                _format_speed(record.speed),
                _display_text(record.source),
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setData(Qt.ItemDataRole.UserRole, record.mmsi)
                self.table.setItem(row_index, column_index, item)

        self.table.resizeColumnsToContents()

    def _on_row_double_clicked(self, row: int, _column: int) -> None:

        item = self.table.item(row, 0)

        if item is None:
            return

        mmsi = item.data(Qt.ItemDataRole.UserRole)

        if mmsi is None:
            return

        self.vesselSelected.emit(int(mmsi))
