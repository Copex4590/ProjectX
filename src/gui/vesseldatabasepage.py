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
from gui.i18n_support import bind_language_refresh
from gui.tableutils import show_empty_table_message
from i18n import tr
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

_TABLE_HEADER_KEYS = (
    "Name",
    "MMSI",
    "IMO",
    "Callsign",
    "Type",
    "Flag",
    "Length",
    "Last Seen",
)


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
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self.refresh()

    def refresh_translations(self) -> None:

        self.title_label.setText(tr("Vessel Database"))
        self.total_vessels_label.setText(tr("Total Vessels"))
        self.search_label.setText(tr("Search"))
        self.type_label.setText(tr("Ship Type"))
        self.flag_label.setText(tr("Flag"))
        self.source_label.setText(tr("Source"))
        self.has_imo_label.setText(tr("Has IMO"))
        self.has_callsign_label.setText(tr("Has Callsign"))
        self.seen_today_label.setText(tr("Seen Today"))
        self.activity_label.setText(tr("Activity"))
        self.sort_label.setText(tr("Sort By"))
        self.search_input.setPlaceholderText(
            tr("MMSI, IMO, name, callsign, or destination")
        )
        self.refresh_button.setText(tr("Refresh"))
        self.clear_button.setText(tr("Clear Filters"))
        self.table.setHorizontalHeaderLabels([
            tr(key) for key in _TABLE_HEADER_KEYS
        ])
        self._refresh_translatable_combos()

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
        self._sync_filter_combo(self.sort_filter, "name")
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

        self.sort_filter.blockSignals(True)
        self._sync_filter_combo(self.sort_filter, key)
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

        self.title_label = QLabel(tr("Vessel Database"))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setProperty("role", "title")
        layout.addWidget(self.title_label)

        summary = QGridLayout()
        self.total_vessels_label = self._summary_label("Total Vessels")
        summary.addWidget(self.total_vessels_label, 0, 0)
        self.total_value = QLabel("0")
        self.total_value.setProperty("role", "summary-value")
        summary.addWidget(self.total_value, 1, 0)
        layout.addLayout(summary)

        controls = QGridLayout()
        controls.setHorizontalSpacing(12)
        controls.setVerticalSpacing(8)

        self.search_label = self._field_label("Search")
        controls.addWidget(self.search_label, 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            tr("MMSI, IMO, name, callsign, or destination")
        )
        controls.addWidget(self.search_input, 0, 1, 1, 5)

        self.type_label = self._field_label("Ship Type")
        controls.addWidget(self.type_label, 1, 0)
        self.type_filter = QComboBox()
        controls.addWidget(self.type_filter, 1, 1)

        self.flag_label = self._field_label("Flag")
        controls.addWidget(self.flag_label, 1, 2)
        self.flag_filter = QComboBox()
        controls.addWidget(self.flag_filter, 1, 3)

        self.source_label = self._field_label("Source")
        controls.addWidget(self.source_label, 1, 4)
        self.source_filter = QComboBox()
        self._fill_source_combo(self.source_filter)
        controls.addWidget(self.source_filter, 1, 5)

        self.has_imo_label = self._field_label("Has IMO")
        controls.addWidget(self.has_imo_label, 2, 0)
        self.has_imo_filter = QComboBox()
        self._fill_yes_no_combo(self.has_imo_filter)
        controls.addWidget(self.has_imo_filter, 2, 1)

        self.has_callsign_label = self._field_label("Has Callsign")
        controls.addWidget(self.has_callsign_label, 2, 2)
        self.has_callsign_filter = QComboBox()
        self._fill_yes_no_combo(self.has_callsign_filter)
        controls.addWidget(self.has_callsign_filter, 2, 3)

        self.seen_today_label = self._field_label("Seen Today")
        controls.addWidget(self.seen_today_label, 2, 4)
        self.seen_today_filter = QComboBox()
        self._fill_yes_no_combo(self.seen_today_filter)
        controls.addWidget(self.seen_today_filter, 2, 5)

        self.activity_label = self._field_label("Activity")
        controls.addWidget(self.activity_label, 3, 0)
        self.activity_filter = QComboBox()
        self._fill_activity_combo(self.activity_filter)
        controls.addWidget(self.activity_filter, 3, 1)

        self.sort_label = self._field_label("Sort By")
        controls.addWidget(self.sort_label, 3, 2)
        self.sort_filter = QComboBox()
        self._fill_sort_combo(self.sort_filter)
        controls.addWidget(self.sort_filter, 3, 3)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self.refresh_button = QPushButton(tr("Refresh"))
        self.clear_button = QPushButton(tr("Clear Filters"))
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.clear_button)
        button_row.addStretch()

        controls.addLayout(button_row, 3, 4, 1, 2)

        layout.addLayout(controls)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            tr(key) for key in _TABLE_HEADER_KEYS
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

    def _summary_label(self, key: str) -> QLabel:

        label = QLabel(tr(key))
        label.setProperty("role", "summary-title")
        return label

    def _field_label(self, key: str) -> QLabel:

        label = QLabel(tr(key))
        label.setProperty("role", "field")
        return label

    def _fill_yes_no_combo(self, combo: QComboBox) -> None:

        for internal, label_key in (
            (_ALL_FILTER, "All"),
            (_YES_FILTER, "Yes"),
            (_NO_FILTER, "No"),
        ):
            combo.addItem(tr(label_key), internal)

    def _fill_activity_combo(self, combo: QComboBox) -> None:

        for internal, label_key in (
            (_ALL_FILTER, "All"),
            (_ACTIVE_FILTER, "Active filter"),
            (_INACTIVE_FILTER, "Inactive"),
        ):
            combo.addItem(tr(label_key), internal)

    def _fill_source_combo(self, combo: QComboBox) -> None:

        for value in _SOURCE_FILTERS:
            combo.addItem(tr(value), value)

    def _fill_sort_combo(self, combo: QComboBox) -> None:

        for key, label_key in _SORT_COLUMNS.items():
            combo.addItem(tr(label_key), key)

    def _refresh_translatable_combos(self) -> None:

        source_value = self.source_filter.currentData() or _ALL_FILTER
        self.source_filter.blockSignals(True)
        self.source_filter.clear()
        self._fill_source_combo(self.source_filter)
        self._sync_filter_combo(self.source_filter, source_value)
        self.source_filter.blockSignals(False)

        for combo in (
            self.has_imo_filter,
            self.has_callsign_filter,
            self.seen_today_filter,
        ):
            current = combo.currentData() or _ALL_FILTER
            combo.blockSignals(True)
            combo.clear()
            self._fill_yes_no_combo(combo)
            self._sync_filter_combo(combo, current)
            combo.blockSignals(False)

        activity_value = self.activity_filter.currentData() or _ALL_FILTER
        self.activity_filter.blockSignals(True)
        self.activity_filter.clear()
        self._fill_activity_combo(self.activity_filter)
        self._sync_filter_combo(self.activity_filter, activity_value)
        self.activity_filter.blockSignals(False)

        sort_value = self.sort_filter.currentData() or "name"
        self.sort_filter.blockSignals(True)
        self.sort_filter.clear()
        self._fill_sort_combo(self.sort_filter)
        self._sync_filter_combo(self.sort_filter, sort_value)
        self.sort_filter.blockSignals(False)

        self._populate_filter_options()

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
            widget.currentIndexChanged.connect(
                lambda _index: self.apply_filters()
            )

        self.sort_filter.currentIndexChanged.connect(self._on_sort_changed)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)

    def _on_sort_changed(self, _index: int) -> None:

        column = self.sort_filter.currentData() or "name"
        self.sort_by(column)

    def _read_filters_from_ui(self) -> None:

        self._filters.search_text = self.search_input.text().strip().lower()
        self._filters.ship_type = self.type_filter.currentData() or _ALL_FILTER
        self._filters.flag = self.flag_filter.currentData() or _ALL_FILTER
        self._filters.source = self.source_filter.currentData() or _ALL_FILTER
        self._filters.has_imo = self.has_imo_filter.currentData() or _ALL_FILTER
        self._filters.has_callsign = (
            self.has_callsign_filter.currentData() or _ALL_FILTER
        )
        self._filters.seen_today = (
            self.seen_today_filter.currentData() or _ALL_FILTER
        )
        self._filters.activity = self.activity_filter.currentData() or _ALL_FILTER

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
        combo.addItem(tr("All"), _ALL_FILTER)

        for value in values:
            combo.addItem(value, value)

        self._sync_filter_combo(combo, current_value)
        combo.blockSignals(False)

    def _sync_filter_combo(self, combo: QComboBox, value: str) -> None:

        index = combo.findData(value or _ALL_FILTER)

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

        if not rows:
            show_empty_table_message(
                self.table,
                "No vessels found",
            )
            return

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
