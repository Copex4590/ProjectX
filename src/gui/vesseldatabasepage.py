# ============================================================================
# Project X
# Vessel Database Page
# ============================================================================

from dataclasses import dataclass
from datetime import datetime, timedelta

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
from database.vessel_database import VesselDatabase, vessel_database
from models.ship import Ship
from models.vessel_record import VesselRecord

_ALL_FILTER = "All"
_YES_FILTER = "Yes"
_NO_FILTER = "No"
_ACTIVE_FILTER = "Active"
_INACTIVE_FILTER = "Inactive"

_SORT_COLUMNS = {
    "name": "Name",
    "mmsi": "MMSI",
    "last_seen": "Last Seen",
    "length": "Length",
    "ship_type": "Ship Type",
}

_SOURCE_FILTERS = (_ALL_FILTER, "RTL", "AIS", "Hybrid")


def _format_last_seen(value: datetime | None) -> str:

    if value is None:
        return "—"

    return value.strftime("%Y-%m-%d %H:%M:%S")


def _format_length(value: float | None) -> str:

    if value is None:
        return "—"

    return f"{value:.1f}"


def _display_text(value: str | None) -> str:

    text = str(value or "").strip()

    if text:
        return text

    return "—"


def _normalize_source(ship: Ship | None) -> str:

    if ship is None:
        return ""

    source_text = str(ship.source or "").strip().lower()

    if ship.ais_visible and ship.rtl_visible:
        return "hybrid"

    if "hybrid" in source_text:
        return "hybrid"

    if ship.rtl_visible or "rtl" in source_text:
        return "rtl"

    if ship.ais_visible or "ais" in source_text:
        return "ais"

    return source_text


@dataclass
class ViewerFilters:

    search_text: str = ""
    ship_type: str = _ALL_FILTER
    flag: str = _ALL_FILTER
    source: str = _ALL_FILTER
    has_imo: str = _ALL_FILTER
    has_callsign: str = _ALL_FILTER
    seen_today: str = _ALL_FILTER
    activity: str = _ALL_FILTER
    sort_column: str = "name"
    sort_ascending: bool = True


class VesselDatabasePage(QWidget):

    vesselSelected = Signal(int)

    def __init__(
        self,
        database: VesselDatabase | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._database = database or vessel_database
        self._records: list[VesselRecord] = []
        self._registry_lookup: dict[int, Ship] = {}
        self._filters = ViewerFilters()

        self._build_ui()
        self._connect_signals()
        self.refresh()

    def refresh(self) -> list[VesselRecord]:

        self._records = self._database.all()
        self._registry_lookup = {
            ship.mmsi: ship
            for ship in registry.all()
        }
        self._update_summary()
        self._populate_filter_options()
        self._populate_table()
        return list(self._records)

    def search(self, text: str) -> None:

        self._filters.search_text = str(text).strip().lower()
        self.search_input.blockSignals(True)
        self.search_input.setText(str(text).strip())
        self.search_input.blockSignals(False)
        self._populate_table()

    def set_filter(
        self,
        *,
        ship_type: str | None = None,
        flag: str | None = None,
    ) -> None:

        if ship_type is not None:
            self._filters.ship_type = ship_type.strip() or _ALL_FILTER
            self._sync_filter_combo(self.type_filter, self._filters.ship_type)

        if flag is not None:
            self._filters.flag = flag.strip() or _ALL_FILTER
            self._sync_filter_combo(self.flag_filter, self._filters.flag)

        self._populate_table()

    def apply_filters(self) -> list[VesselRecord]:

        self._read_filters_from_ui()
        self._populate_table()
        return self._filtered_records()

    def clear_filters(self) -> None:

        self._filters = ViewerFilters()

        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)

        self._sync_filter_combo(self.type_filter, _ALL_FILTER)
        self._sync_filter_combo(self.flag_filter, _ALL_FILTER)
        self._sync_filter_combo(self.source_filter, _ALL_FILTER)
        self._sync_filter_combo(self.has_imo_filter, _ALL_FILTER)
        self._sync_filter_combo(self.has_callsign_filter, _ALL_FILTER)
        self._sync_filter_combo(self.seen_today_filter, _ALL_FILTER)
        self._sync_filter_combo(self.activity_filter, _ALL_FILTER)

        self.sort_filter.blockSignals(True)
        self._sync_filter_combo(self.sort_filter, _SORT_COLUMNS["name"])
        self.sort_filter.blockSignals(False)

        self._populate_table()

    def sort_by(self, column: str) -> None:

        normalized = str(column).strip().lower().replace(" ", "_")

        if normalized == "last_seen":
            key = "last_seen"
        elif normalized in _SORT_COLUMNS:
            key = normalized
        elif normalized == "type":
            key = "ship_type"
        else:
            key = "name"

        if self._filters.sort_column == key:
            self._filters.sort_ascending = not self._filters.sort_ascending
        else:
            self._filters.sort_column = key
            self._filters.sort_ascending = True

        label = _SORT_COLUMNS.get(key, "Name")
        self.sort_filter.blockSignals(True)
        self._sync_filter_combo(self.sort_filter, label)
        self.sort_filter.blockSignals(False)
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

        title = QLabel("Vessel Database")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setProperty("role", "title")
        layout.addWidget(title)

        summary = QGridLayout()
        summary.addWidget(self._summary_label("Total Vessels"), 0, 0)
        self.total_value = QLabel("0")
        self.total_value.setProperty("role", "summary-value")
        summary.addWidget(self.total_value, 1, 0)
        layout.addLayout(summary)

        controls = QGridLayout()
        controls.setHorizontalSpacing(12)
        controls.setVerticalSpacing(8)

        controls.addWidget(self._field_label("Search"), 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "MMSI, IMO, name, callsign, or destination"
        )
        controls.addWidget(self.search_input, 0, 1, 1, 5)

        controls.addWidget(self._field_label("Ship Type"), 1, 0)
        self.type_filter = QComboBox()
        controls.addWidget(self.type_filter, 1, 1)

        controls.addWidget(self._field_label("Flag"), 1, 2)
        self.flag_filter = QComboBox()
        controls.addWidget(self.flag_filter, 1, 3)

        controls.addWidget(self._field_label("Source"), 1, 4)
        self.source_filter = QComboBox()
        for value in _SOURCE_FILTERS:
            self.source_filter.addItem(value)
        controls.addWidget(self.source_filter, 1, 5)

        controls.addWidget(self._field_label("Has IMO"), 2, 0)
        self.has_imo_filter = QComboBox()
        self._fill_yes_no_combo(self.has_imo_filter)
        controls.addWidget(self.has_imo_filter, 2, 1)

        controls.addWidget(self._field_label("Has Callsign"), 2, 2)
        self.has_callsign_filter = QComboBox()
        self._fill_yes_no_combo(self.has_callsign_filter)
        controls.addWidget(self.has_callsign_filter, 2, 3)

        controls.addWidget(self._field_label("Seen Today"), 2, 4)
        self.seen_today_filter = QComboBox()
        self._fill_yes_no_combo(self.seen_today_filter)
        controls.addWidget(self.seen_today_filter, 2, 5)

        controls.addWidget(self._field_label("Activity"), 3, 0)
        self.activity_filter = QComboBox()
        self.activity_filter.addItems([
            _ALL_FILTER,
            _ACTIVE_FILTER,
            _INACTIVE_FILTER,
        ])
        controls.addWidget(self.activity_filter, 3, 1)

        controls.addWidget(self._field_label("Sort By"), 3, 2)
        self.sort_filter = QComboBox()
        for label in _SORT_COLUMNS.values():
            self.sort_filter.addItem(label)
        controls.addWidget(self.sort_filter, 3, 3)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self.refresh_button = QPushButton("Refresh")
        self.clear_button = QPushButton("Clear Filters")
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.clear_button)
        button_row.addStretch()

        controls.addLayout(button_row, 3, 4, 1, 2)

        layout.addLayout(controls)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Name",
            "MMSI",
            "IMO",
            "Callsign",
            "Type",
            "Flag",
            "Length",
            "Last Seen",
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

    def _fill_yes_no_combo(self, combo: QComboBox) -> None:

        combo.addItems([_ALL_FILTER, _YES_FILTER, _NO_FILTER])

    def _connect_signals(self) -> None:

        self.refresh_button.clicked.connect(self.refresh)
        self.clear_button.clicked.connect(self.clear_filters)
        self.search_input.textChanged.connect(self.search)

        for widget in (
            self.type_filter,
            self.flag_filter,
            self.source_filter,
            self.has_imo_filter,
            self.has_callsign_filter,
            self.seen_today_filter,
            self.activity_filter,
        ):
            widget.currentTextChanged.connect(
                lambda _value: self.apply_filters()
            )

        self.sort_filter.currentTextChanged.connect(self._on_sort_changed)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)

    def _on_sort_changed(self, label: str) -> None:

        reverse_map = {value: key for key, value in _SORT_COLUMNS.items()}
        column = reverse_map.get(label, "name")
        self.sort_by(column)

    def _read_filters_from_ui(self) -> None:

        self._filters.search_text = self.search_input.text().strip().lower()
        self._filters.ship_type = self.type_filter.currentText()
        self._filters.flag = self.flag_filter.currentText()
        self._filters.source = self.source_filter.currentText()
        self._filters.has_imo = self.has_imo_filter.currentText()
        self._filters.has_callsign = self.has_callsign_filter.currentText()
        self._filters.seen_today = self.seen_today_filter.currentText()
        self._filters.activity = self.activity_filter.currentText()

    def _update_summary(self) -> None:

        self.total_value.setText(str(len(self._records)))

    def _populate_filter_options(self) -> None:

        ship_types = sorted({
            record.ship_type.strip()
            for record in self._records
            if record.ship_type.strip()
        })
        flags = sorted({
            record.flag.strip()
            for record in self._records
            if record.flag.strip()
        })

        self._fill_filter_combo(
            self.type_filter,
            ship_types,
            self._filters.ship_type,
        )
        self._fill_filter_combo(
            self.flag_filter,
            flags,
            self._filters.flag,
        )

    def _fill_filter_combo(
        self,
        combo: QComboBox,
        values: list[str],
        current_value: str,
    ) -> None:

        combo.blockSignals(True)
        combo.clear()
        combo.addItem(_ALL_FILTER)

        for value in values:
            combo.addItem(value)

        self._sync_filter_combo(combo, current_value)
        combo.blockSignals(False)

    def _sync_filter_combo(self, combo: QComboBox, value: str) -> None:

        index = combo.findText(value or _ALL_FILTER)

        if index < 0:
            index = 0

        combo.setCurrentIndex(index)

    def _registry_ship(self, record: VesselRecord) -> Ship | None:

        return self._registry_lookup.get(record.mmsi)

    def _matches_search(self, record: VesselRecord) -> bool:

        if not self._filters.search_text:
            return True

        ship = self._registry_ship(record)
        destination = ""

        if ship is not None:
            destination = str(ship.destination or "").strip()

        haystack = " ".join([
            str(record.mmsi),
            record.imo,
            record.name,
            record.callsign,
            destination,
        ]).lower()

        return self._filters.search_text in haystack

    def _matches_source(self, record: VesselRecord) -> bool:

        if self._filters.source == _ALL_FILTER:
            return True

        source = _normalize_source(self._registry_ship(record))
        target = self._filters.source.strip().lower()

        return source == target

    def _matches_yes_no(self, value: str, has_value: bool) -> bool:

        if value == _ALL_FILTER:
            return True

        if value == _YES_FILTER:
            return has_value

        if value == _NO_FILTER:
            return not has_value

        return True

    def _is_seen_today(self, record: VesselRecord) -> bool:

        if record.last_seen is None:
            return False

        return record.last_seen.date() == datetime.now().date()

    def _is_active(self, record: VesselRecord) -> bool:

        if record.last_seen is None:
            return False

        return record.last_seen >= datetime.now() - timedelta(hours=24)

    def _filtered_records(self) -> list[VesselRecord]:

        records = list(self._records)

        if self._filters.ship_type != _ALL_FILTER:
            records = [
                record
                for record in records
                if record.ship_type == self._filters.ship_type
            ]

        if self._filters.flag != _ALL_FILTER:
            records = [
                record
                for record in records
                if record.flag == self._filters.flag
            ]

        records = [
            record
            for record in records
            if self._matches_source(record)
        ]

        records = [
            record
            for record in records
            if self._matches_yes_no(
                self._filters.has_imo,
                bool(record.imo.strip()),
            )
        ]

        records = [
            record
            for record in records
            if self._matches_yes_no(
                self._filters.has_callsign,
                bool(record.callsign.strip()),
            )
        ]

        if self._filters.seen_today != _ALL_FILTER:
            records = [
                record
                for record in records
                if self._matches_yes_no(
                    self._filters.seen_today,
                    self._is_seen_today(record),
                )
            ]

        if self._filters.activity == _ACTIVE_FILTER:
            records = [
                record
                for record in records
                if self._is_active(record)
            ]
        elif self._filters.activity == _INACTIVE_FILTER:
            records = [
                record
                for record in records
                if not self._is_active(record)
            ]

        records = [
            record
            for record in records
            if self._matches_search(record)
        ]

        return self._sorted_records(records)

    def _sorted_records(self, records: list[VesselRecord]) -> list[VesselRecord]:

        column = self._filters.sort_column

        if column == "mmsi":
            key_fn = lambda record: record.mmsi
        elif column == "last_seen":
            key_fn = lambda record: record.last_seen or datetime.min
        elif column == "length":
            key_fn = lambda record: (
                record.length if record.length is not None else -1.0
            )
        elif column == "ship_type":
            key_fn = lambda record: record.ship_type.lower()
        else:
            key_fn = lambda record: record.name.lower()

        return sorted(
            records,
            key=key_fn,
            reverse=not self._filters.sort_ascending,
        )

    def _populate_table(self) -> None:

        rows = self._filtered_records()
        self.table.setRowCount(len(rows))

        for row_index, record in enumerate(rows):
            values = [
                _display_text(record.name),
                str(record.mmsi),
                _display_text(record.imo),
                _display_text(record.callsign),
                _display_text(record.ship_type),
                _display_text(record.flag),
                _format_length(record.length),
                _format_last_seen(record.last_seen),
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
