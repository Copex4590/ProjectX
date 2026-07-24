# ============================================================================
# Project X
# Vessel Timeline Page
# ============================================================================

from dataclasses import dataclass
from datetime import date, datetime

from PySide6.QtCore import Qt, QTimer, Signal
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
from shiboken6 import isValid

from database import registry
from engines.timeline.arrival_departure_engine import (
    EVENT_ARRIVAL,
    EVENT_DEPARTURE,
)
from gui.deferred_load import make_loading_label
from gui.i18n_support import bind_language_refresh
from gui.progressive_pipeline import (
    ProgressiveDataPipeline,
    progressive_batch_size,
)
from gui.tableutils import show_empty_table_message
from gui.theme import analytics_page_stylesheet
from i18n import tr
from timeline.timeline_manager import TimelineManager, timeline_manager
from timeline.timeline_recorder import EVENT_POSITION_UPDATE
from timeline.timeline_record import TimelineRecord

_ALL_FILTER = "All"
_TABLE_FILL_CHUNK = 250
_PROGRESSIVE_VISIBLE_CAP = 1000

_EVENT_FILTERS = (
    _ALL_FILTER,
    EVENT_ARRIVAL,
    EVENT_DEPARTURE,
    EVENT_POSITION_UPDATE,
)

_EVENT_LABEL_KEYS = {
    _ALL_FILTER: "All",
    EVENT_ARRIVAL: "ARRIVAL",
    EVENT_DEPARTURE: "DEPARTURE",
    EVENT_POSITION_UPDATE: "POSITION_UPDATE",
}

_TABLE_HEADER_KEYS = (
    "Timestamp",
    "Event",
    "MMSI",
    "Name",
    "Latitude",
    "Longitude",
    "Speed",
    "Source",
)


def _display_text(value: str | None) -> str:

    text = str(value or "").strip()

    if text:
        return text

    return "—"


def _tr_event_type(value: str | None) -> str:

    text = str(value or "").strip()

    if not text:
        return "—"

    return tr(text)


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
        self._staging_records: list[TimelineRecord] = []
        self._name_lookup: dict[int, str] = {}
        self._pending_name_lookup: dict[int, str] = {}
        self._filters = TimelineViewerFilters()
        self._data_ready = False
        self._atomic_refresh = False
        self._populate_generation = 0
        self._fill_rows: list[TimelineRecord] = []
        self._fill_index = 0
        self._fill_generation = 0

        self._pipeline = ProgressiveDataPipeline(self)
        self._pipeline.batch_ready.connect(self._on_progressive_batch)
        self._pipeline.finished.connect(self._on_progressive_finished)
        self._pipeline.failed.connect(self._on_progressive_failed)
        self._progressive_repaint_token = 0
        self._pending_append: list[TimelineRecord] = []
        self._append_pump_active = False

        self._build_ui()
        self._connect_signals()

    def initialize(self) -> None:
        """One-shot: language binding (models only; no data load)."""

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def activate(self) -> None:
        """Show immediately; stream data in batches if cache is empty."""

        if self._data_ready:
            return
        self._request_progressive_load(force=False)

    def on_ship_updated(self) -> None:
        """EventBridge coalesced ship update — refresh name lookup only (SAVE-232)."""

        if not self._data_ready:
            return
        self._name_lookup = {
            ship.mmsi: _display_text(ship.name)
            for ship in registry.all()
            if _display_text(ship.name) != "—"
        }

    def hideEvent(self, event) -> None:
        """Cancel in-flight progressive load when leaving the page."""

        self._cancel_progressive_on_leave()
        super().hideEvent(event)

    def refresh_translations(self) -> None:

        self.title_label.setText(tr("Vessel Timeline"))
        self.total_events_label.setText(tr("Total Events"))
        self.arrivals_label.setText(tr("Arrivals"))
        self.departures_label.setText(tr("Departures"))
        self.position_updates_label.setText(tr("Position Updates"))
        self.search_label.setText(tr("Search"))
        self.event_type_label.setText(tr("Event Type"))
        self.date_from_label.setText(tr("Date From"))
        self.date_to_label.setText(tr("Date To"))
        self.search_input.setPlaceholderText(tr("MMSI or vessel name"))
        self.date_from_input.setPlaceholderText(tr("YYYY-MM-DD"))
        self.date_to_input.setPlaceholderText(tr("YYYY-MM-DD"))
        self.refresh_button.setText(tr("Refresh"))
        self.clear_button.setText(tr("Clear Filters"))
        self.table.setHorizontalHeaderLabels([
            tr(key) for key in _TABLE_HEADER_KEYS
        ])
        self._refresh_event_filter()

    def refresh(self) -> list[TimelineRecord]:
        """Manual refresh — progressive reload; cache swaps atomically on success."""

        self._request_progressive_load(force=True)
        return list(self._records)

    def shutdown(self) -> None:

        self._populate_generation += 1
        self._pipeline.cancel()

    def _cancel_progressive_on_leave(self) -> None:

        if not self._pipeline.busy:
            return
        self._pipeline.cancel()
        self._staging_records = []
        self._pending_name_lookup = {}
        if self._atomic_refresh:
            self._atomic_refresh = False
        self._set_loading(False)

    def _request_progressive_load(self, *, force: bool) -> None:

        if not force and self._data_ready:
            return
        self._atomic_refresh = bool(force and self._data_ready)
        self._staging_records = []
        self._pending_name_lookup = {}
        started = self._pipeline.start(
            self._produce_batches,
            force=force,
            assemble=self._assemble_batches,
        )
        if started:
            self._set_loading(True, tr("Loading timeline…"))
            self._start_ui_pulse()

    def _produce_batches(self):

        name_lookup = {
            ship.mmsi: _display_text(ship.name)
            for ship in registry.all()
            if _display_text(ship.name) != "—"
        }
        yield {"meta": True, "name_lookup": name_lookup}
        batch_size = progressive_batch_size()
        for batch in self._manager.iter_batches(batch_size):
            yield {"meta": False, "records": batch}

    @staticmethod
    def _assemble_batches(batches: list) -> tuple[list[TimelineRecord], dict[int, str]]:

        records: list[TimelineRecord] = []
        name_lookup: dict[int, str] = {}
        for batch in batches:
            if not isinstance(batch, dict):
                continue
            if batch.get("meta"):
                name_lookup = dict(batch.get("name_lookup") or {})
                continue
            records.extend(batch.get("records") or [])
        return records, name_lookup

    def _on_progressive_batch(self, batch: object, index: int) -> None:

        if not isValid(self):
            return
        if not isinstance(batch, dict):
            return
        if batch.get("meta"):
            self._pending_name_lookup = dict(batch.get("name_lookup") or {})
            return

        records = list(batch.get("records") or [])
        self._staging_records.extend(records)
        if self._atomic_refresh:
            return

        self._records = list(self._staging_records)
        if self._pending_name_lookup:
            self._name_lookup = dict(self._pending_name_lookup)
        first_visible = (
            self._pipeline.metrics is not None
            and self._pipeline.metrics.time_to_first_visible_ms is None
        )
        self._update_summary()
        if first_visible:
            self._pending_append.clear()
            self._populate_table()
            if self.table.rowCount() > 0:
                self._pipeline.note_first_visible()
        elif self._filters_are_active():
            self._pending_append.clear()
            self._schedule_progressive_repaint(immediate=False)
        elif self.table.rowCount() < _PROGRESSIVE_VISIBLE_CAP:
            self._pending_append.extend(records)
            self._set_loading(
                True,
                tr("Loading timeline… ({count})").format(
                    count=len(self._staging_records),
                ),
            )
            self._kick_append_pump()
        else:
            self._set_loading(
                True,
                tr("Loading timeline… ({count})").format(
                    count=len(self._staging_records),
                ),
            )

    def _filters_are_active(self) -> bool:

        filters = self._filters
        return bool(
            filters.search_text
            or (
                filters.event_type
                and filters.event_type != _ALL_FILTER
            )
            or filters.date_from
            or filters.date_to
        )

    def _kick_append_pump(self) -> None:

        if self._append_pump_active:
            return
        self._append_pump_active = True
        QTimer.singleShot(0, self._append_table_pump)

    def _append_table_pump(self) -> None:

        if not isValid(self) or self._atomic_refresh:
            self._append_pump_active = False
            self._pending_append.clear()
            return
        if not self._pending_append:
            self._append_pump_active = False
            return

        chunk = self._pending_append[:_TABLE_FILL_CHUNK]
        del self._pending_append[:_TABLE_FILL_CHUNK]
        start = self.table.rowCount()
        self.table.setRowCount(start + len(chunk))
        for offset, record in enumerate(chunk):
            row_index = start + offset
            values = [
                _format_timestamp(record.timestamp),
                _tr_event_type(record.event_type),
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

        if self._pending_append:
            QTimer.singleShot(0, self._append_table_pump)
        else:
            self._append_pump_active = False

    def _schedule_progressive_repaint(self, *, immediate: bool) -> None:

        self._progressive_repaint_token += 1
        token = self._progressive_repaint_token

        def _flush() -> None:
            if token != self._progressive_repaint_token:
                return
            if not isValid(self) or self._atomic_refresh:
                return
            self._update_summary()
            self._populate_table()
            if self.table.rowCount() > 0:
                self._pipeline.note_first_visible()

        if immediate:
            _flush()
        else:
            QTimer.singleShot(80, _flush)

    def _on_progressive_finished(
        self,
        payload: tuple[list[TimelineRecord], dict[int, str]],
    ) -> None:

        if not isValid(self):
            return
        records, name_lookup = payload
        # Atomic cache replace after successful completion (esp. refresh).
        self._progressive_repaint_token += 1
        self._pending_append.clear()
        self._append_pump_active = False
        self._records = list(records)
        self._name_lookup = dict(name_lookup)
        self._staging_records = []
        self._pending_name_lookup = {}
        self._atomic_refresh = False
        self._data_ready = True
        self._update_summary()
        self._populate_table()
        self._pipeline.note_first_visible()

    def _on_progressive_failed(self, message: str) -> None:

        if not isValid(self):
            return
        self._atomic_refresh = False
        self._staging_records = []
        self._set_loading(True, tr("Failed to load: {error}").format(error=message))

    def _start_ui_pulse(self) -> None:

        def _pulse() -> None:
            if not isValid(self) or not self._pipeline.busy:
                return
            self._pipeline.note_ui_pulse()
            QTimer.singleShot(16, _pulse)

        QTimer.singleShot(16, _pulse)

    def _set_loading(self, visible: bool, text: str | None = None) -> None:

        if text is not None:
            self.loading_label.setText(text)
        self.loading_label.setVisible(visible)
        self.refresh_button.setEnabled(not self._pipeline.busy)

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

        self.setStyleSheet(analytics_page_stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)

        self.title_label = QLabel(tr("Vessel Timeline"))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setProperty("role", "title")
        layout.addWidget(self.title_label)

        self.loading_label = make_loading_label()
        layout.addWidget(self.loading_label)

        summary = QGridLayout()
        self.total_events_label = self._summary_label("Total Events")
        summary.addWidget(self.total_events_label, 0, 0)
        self.total_value = QLabel("0")
        self.total_value.setProperty("role", "summary-value")
        summary.addWidget(self.total_value, 1, 0)

        self.arrivals_label = self._summary_label("Arrivals")
        summary.addWidget(self.arrivals_label, 0, 1)
        self.arrival_value = QLabel("0")
        self.arrival_value.setProperty("role", "summary-value")
        summary.addWidget(self.arrival_value, 1, 1)

        self.departures_label = self._summary_label("Departures")
        summary.addWidget(self.departures_label, 0, 2)
        self.departure_value = QLabel("0")
        self.departure_value.setProperty("role", "summary-value")
        summary.addWidget(self.departure_value, 1, 2)

        self.position_updates_label = self._summary_label("Position Updates")
        summary.addWidget(self.position_updates_label, 0, 3)
        self.position_value = QLabel("0")
        self.position_value.setProperty("role", "summary-value")
        summary.addWidget(self.position_value, 1, 3)
        layout.addLayout(summary)

        controls = QGridLayout()
        controls.setHorizontalSpacing(12)
        controls.setVerticalSpacing(8)

        self.search_label = self._field_label("Search")
        controls.addWidget(self.search_label, 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("MMSI or vessel name"))
        controls.addWidget(self.search_input, 0, 1, 1, 3)

        self.event_type_label = self._field_label("Event Type")
        controls.addWidget(self.event_type_label, 1, 0)
        self.event_filter = QComboBox()
        self._fill_event_filter(self.event_filter)
        controls.addWidget(self.event_filter, 1, 1)

        self.date_from_label = self._field_label("Date From")
        controls.addWidget(self.date_from_label, 1, 2)
        self.date_from_input = QLineEdit()
        self.date_from_input.setPlaceholderText(tr("YYYY-MM-DD"))
        controls.addWidget(self.date_from_input, 1, 3)

        self.date_to_label = self._field_label("Date To")
        controls.addWidget(self.date_to_label, 2, 0)
        self.date_to_input = QLineEdit()
        self.date_to_input.setPlaceholderText(tr("YYYY-MM-DD"))
        controls.addWidget(self.date_to_input, 2, 1)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self.refresh_button = QPushButton(tr("Refresh"))
        self.clear_button = QPushButton(tr("Clear Filters"))
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.clear_button)
        button_row.addStretch()

        controls.addLayout(button_row, 2, 2, 1, 2)

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

    def _fill_event_filter(self, combo: QComboBox) -> None:

        for value in _EVENT_FILTERS:
            label_key = _EVENT_LABEL_KEYS.get(value, value)
            combo.addItem(tr(label_key), value)

    def _refresh_event_filter(self) -> None:

        current = self.event_filter.currentData() or _ALL_FILTER
        self.event_filter.blockSignals(True)
        self.event_filter.clear()
        self._fill_event_filter(self.event_filter)
        self._sync_filter_combo(self.event_filter, current)
        self.event_filter.blockSignals(False)

    def _connect_signals(self) -> None:

        self.refresh_button.clicked.connect(self.refresh)
        self.clear_button.clicked.connect(self.clear_filters)
        self.search_input.textChanged.connect(
            lambda _value: self.apply_filters()
        )
        self.event_filter.currentIndexChanged.connect(
            lambda _index: self.apply_filters()
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
        self._filters.event_type = self.event_filter.currentData() or _ALL_FILTER
        self._filters.date_from = self.date_from_input.text().strip()
        self._filters.date_to = self.date_to_input.text().strip()

    def _sync_filter_combo(self, combo: QComboBox, value: str) -> None:

        index = combo.findData(value or _ALL_FILTER)

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
        self._populate_generation += 1
        generation = self._populate_generation

        if not rows:
            show_empty_table_message(
                self.table,
                "No events found",
            )
            if not self._pipeline.busy:
                self._set_loading(False)
            return

        self.table.setRowCount(len(rows))
        self._fill_rows = rows
        self._fill_index = 0
        self._fill_generation = generation
        self._set_loading(True, tr("Rendering timeline…"))
        self._fill_table_chunk()

    def _fill_table_chunk(self) -> None:

        if self._fill_generation != self._populate_generation:
            return
        if not isValid(self):
            return

        rows = self._fill_rows
        start = self._fill_index
        end = min(start + _TABLE_FILL_CHUNK, len(rows))

        for row_index in range(start, end):
            record = rows[row_index]
            values = [
                _format_timestamp(record.timestamp),
                _tr_event_type(record.event_type),
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

        self._fill_index = end

        if end < len(rows):
            QTimer.singleShot(0, self._fill_table_chunk)
            return

        self.table.resizeColumnsToContents()
        if self._pipeline.busy:
            self._set_loading(True, tr("Loading timeline…"))
        else:
            self._set_loading(False)

    def _on_row_double_clicked(self, row: int, _column: int) -> None:

        item = self.table.item(row, 0)

        if item is None:
            return

        mmsi = item.data(Qt.ItemDataRole.UserRole)

        if mmsi is None:
            return

        self.vesselSelected.emit(int(mmsi))
