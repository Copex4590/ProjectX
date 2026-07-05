# ============================================================================
# Project X
# Vessel Database Page
# ============================================================================

from datetime import datetime

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

from database.vessel_database import VesselDatabase, vessel_database
from models.vessel_record import VesselRecord

_ALL_FILTER = "All"


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
        self._search_text = ""
        self._ship_type_filter = _ALL_FILTER
        self._flag_filter = _ALL_FILTER

        self._build_ui()
        self._connect_signals()
        self.refresh()

    def refresh(self) -> list[VesselRecord]:

        self._records = self._database.all()
        self._update_summary()
        self._populate_filter_options()
        self._populate_table()
        return list(self._records)

    def search(self, text: str) -> None:

        self._search_text = str(text).strip().lower()
        self._populate_table()

    def set_filter(
        self,
        *,
        ship_type: str | None = None,
        flag: str | None = None,
    ) -> None:

        if ship_type is not None:
            self._ship_type_filter = ship_type.strip() or _ALL_FILTER
            self._sync_filter_combo(self.type_filter, self._ship_type_filter)

        if flag is not None:
            self._flag_filter = flag.strip() or _ALL_FILTER
            self._sync_filter_combo(self.flag_filter, self._flag_filter)

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
        self.search_input.setPlaceholderText("MMSI, name, or callsign")
        controls.addWidget(self.search_input, 0, 1, 1, 3)

        controls.addWidget(self._field_label("Ship Type"), 1, 0)
        self.type_filter = QComboBox()
        controls.addWidget(self.type_filter, 1, 1)

        controls.addWidget(self._field_label("Flag"), 1, 2)
        self.flag_filter = QComboBox()
        controls.addWidget(self.flag_filter, 1, 3)

        self.refresh_button = QPushButton("Refresh")
        controls.addWidget(self.refresh_button, 0, 4)

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

    def _connect_signals(self) -> None:

        self.refresh_button.clicked.connect(self.refresh)
        self.search_input.textChanged.connect(self.search)
        self.type_filter.currentTextChanged.connect(
            lambda value: self.set_filter(ship_type=value)
        )
        self.flag_filter.currentTextChanged.connect(
            lambda value: self.set_filter(flag=value)
        )
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)

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

        self._fill_filter_combo(self.type_filter, ship_types, self._ship_type_filter)
        self._fill_filter_combo(self.flag_filter, flags, self._flag_filter)

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

    def _filtered_records(self) -> list[VesselRecord]:

        records = list(self._records)

        if self._ship_type_filter != _ALL_FILTER:
            records = [
                record
                for record in records
                if record.ship_type == self._ship_type_filter
            ]

        if self._flag_filter != _ALL_FILTER:
            records = [
                record
                for record in records
                if record.flag == self._flag_filter
            ]

        if not self._search_text:
            return records

        filtered = []

        for record in records:
            haystack = " ".join([
                str(record.mmsi),
                record.name,
                record.callsign,
                record.imo,
            ]).lower()

            if self._search_text in haystack:
                filtered.append(record)

        return filtered

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
