# ============================================================================
# Project X
# Camera Diagnostics Panel
# ============================================================================

import re
from typing import Literal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from database.camera_registry import CameraRegistry, camera_registry
from gui.theme import BG_HEADER, TEXT_MUTED, table_stylesheet
from gui.tableutils import show_empty_table_message
from i18n import tr
from engines.camera.diagnostics import (
    CameraDiagnosticsEngine,
    CameraDiagnosticsReport,
    DiagnosticResult,
    DiagnosticSeverity,
    camera_diagnostics_engine,
)

FilterStatus = Literal["all", "ok", "warning", "error"]

def _severity_label(severity: DiagnosticSeverity) -> str:

    labels = {
        DiagnosticSeverity.OK: tr("OK"),
        DiagnosticSeverity.WARNING: tr("Warning"),
        DiagnosticSeverity.ERROR: tr("Error"),
    }
    return labels.get(severity, severity.value)

_PLAYBACK_READY_PATTERN = re.compile(
    r"Playback provider '([^']+)' and backend '([^']+)' are available\."
)


def _normalize_filter(status: str) -> FilterStatus:

    normalized = str(status).strip().lower()

    if normalized in {"ok", "healthy"}:
        return "ok"

    if normalized in {"warning", "warnings"}:
        return "warning"

    if normalized in {"error", "errors"}:
        return "error"

    return "all"


def _camera_label(camera_id: str, registry: CameraRegistry) -> str:

    camera = registry.get(camera_id)

    if camera is None:
        return camera_id or "—"

    name = str(camera.name).strip()

    if name:
        return name

    return camera_id or "—"


def _provider_backend(result: DiagnosticResult) -> tuple[str, str]:

    if result.category != "playback":
        return "—", "—"

    match = _PLAYBACK_READY_PATTERN.search(result.message)

    if match is not None:
        return match.group(1), match.group(2)

    if "provider" in result.message.lower():
        return tr("Unavailable"), "—"

    if "backend" in result.message.lower():
        return "—", tr("Unavailable")

    return "—", "—"


class CameraDiagnosticsPanel(QFrame):

    def __init__(
        self,
        engine: CameraDiagnosticsEngine | None = None,
        registry: CameraRegistry | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._engine = engine or camera_diagnostics_engine
        self._registry = registry or camera_registry
        self._reports: list[CameraDiagnosticsReport] = []
        self._filter: FilterStatus = "all"

        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)

    def refresh(self) -> list[CameraDiagnosticsReport]:

        self._reports = self._engine.diagnose_all()
        self._update_summary()
        self._populate_table()
        return list(self._reports)

    def set_filter(self, status: str) -> FilterStatus:

        self._filter = _normalize_filter(status)
        self._sync_filter_combo()
        self._populate_table()
        return self._filter

    def _build_ui(self) -> None:

        self.setStyleSheet(f"""
            QLabel[role="section"] {{
                color: white;
                font-size: 14pt;
                font-weight: bold;
            }}

            QLabel[role="summary-title"] {{
                color: {TEXT_MUTED};
                font-size: 9pt;
                font-weight: 600;
            }}

            QLabel[role="summary-value"] {{
                color: white;
                font-size: 16pt;
                font-weight: bold;
            }}

            {table_stylesheet()}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(10)

        self._title_label = QLabel(tr("Camera Diagnostics"))
        self._title_label.setProperty("role", "section")
        layout.addWidget(self._title_label)

        summary = QGridLayout()
        summary.setHorizontalSpacing(16)

        self.total_value = self._summary_value("Total Cameras")
        self.healthy_value = self._summary_value("Healthy")
        self.warnings_value = self._summary_value("Warnings")
        self.errors_value = self._summary_value("Errors")

        summary.addWidget(self.total_value["title"], 0, 0)
        summary.addWidget(self.total_value["value"], 1, 0)
        summary.addWidget(self.healthy_value["title"], 0, 1)
        summary.addWidget(self.healthy_value["value"], 1, 1)
        summary.addWidget(self.warnings_value["title"], 0, 2)
        summary.addWidget(self.warnings_value["value"], 1, 2)
        summary.addWidget(self.errors_value["title"], 0, 3)
        summary.addWidget(self.errors_value["value"], 1, 3)

        layout.addLayout(summary)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.refresh_button = QPushButton()
        controls.addWidget(self.refresh_button)

        self._filter_label = self._field_label(tr("Filter"))
        controls.addWidget(self._filter_label)
        self.filter_combo = QComboBox()
        controls.addWidget(self.filter_combo)
        controls.addStretch()

        layout.addLayout(controls)

        self.table = QTableWidget(0, 6)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

        self.refresh_translations()

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Camera Diagnostics"))

        for summary in (
            self.total_value,
            self.healthy_value,
            self.warnings_value,
            self.errors_value,
        ):
            summary["title"].setText(tr(summary["title_key"]))

        self.refresh_button.setText(tr("Refresh"))
        self._filter_label.setText(tr("Filter"))

        filter_index = self.filter_combo.currentIndex()
        self.filter_combo.blockSignals(True)
        self.filter_combo.clear()
        self.filter_combo.addItem(tr("All"), "all")
        self.filter_combo.addItem(tr("OK"), "ok")
        self.filter_combo.addItem(tr("Warning"), "warning")
        self.filter_combo.addItem(tr("Error"), "error")
        if 0 <= filter_index < self.filter_combo.count():
            self.filter_combo.setCurrentIndex(filter_index)
        self.filter_combo.blockSignals(False)

        self.table.setHorizontalHeaderLabels([
            tr("Camera"),
            tr("Status"),
            tr("Provider"),
            tr("Backend"),
            tr("Message"),
            tr("Recommendation"),
        ])

        if self._reports:
            self._populate_table()

    def _summary_value(self, title_key: str) -> dict[str, QLabel | str]:

        title = QLabel(tr(title_key))
        title.setProperty("role", "summary-title")

        value = QLabel("0")
        value.setProperty("role", "summary-value")

        return {"title": title, "value": value, "title_key": title_key}

    def _field_label(self, text: str) -> QLabel:

        label = QLabel(text)
        label.setProperty("role", "summary-title")
        return label

    def _connect_signals(self) -> None:

        self.refresh_button.clicked.connect(self.refresh)
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)

    def _on_filter_changed(self) -> None:

        filter_value = self.filter_combo.currentData(Qt.ItemDataRole.UserRole)
        self.set_filter(str(filter_value or "all"))

    def _sync_filter_combo(self) -> None:

        self.filter_combo.blockSignals(True)

        for index in range(self.filter_combo.count()):
            if self.filter_combo.itemData(index) == self._filter:
                self.filter_combo.setCurrentIndex(index)
                break

        self.filter_combo.blockSignals(False)

    def _update_summary(self) -> None:

        total = len(self._reports)
        healthy = sum(
            1
            for report in self._reports
            if report.status == DiagnosticSeverity.OK
        )
        warnings = sum(
            1
            for report in self._reports
            if report.status == DiagnosticSeverity.WARNING
        )
        errors = sum(
            1
            for report in self._reports
            if report.status == DiagnosticSeverity.ERROR
        )

        self.total_value["value"].setText(str(total))
        self.healthy_value["value"].setText(str(healthy))
        self.warnings_value["value"].setText(str(warnings))
        self.errors_value["value"].setText(str(errors))

    def _populate_table(self) -> None:

        rows = self._filtered_rows()

        if not rows:
            show_empty_table_message(
                self.table,
                "No cameras",
            )
            return

        self.table.setRowCount(len(rows))

        for row_index, result in enumerate(rows):
            provider, backend = _provider_backend(result)

            values = [
                _camera_label(result.camera_id, self._registry),
                _severity_label(result.severity),
                provider,
                backend,
                result.message,
                result.recommendation,
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_index, column_index, item)

        self.table.resizeColumnsToContents()

    def _filtered_rows(self) -> list[DiagnosticResult]:

        rows: list[DiagnosticResult] = []

        for report in self._reports:
            for result in report.results:
                if self._matches_filter(result):
                    rows.append(result)

        return rows

    def _matches_filter(self, result: DiagnosticResult) -> bool:

        if self._filter == "all":
            return True

        if self._filter == "ok":
            return result.severity == DiagnosticSeverity.OK

        if self._filter == "warning":
            return result.severity == DiagnosticSeverity.WARNING

        if self._filter == "error":
            return result.severity == DiagnosticSeverity.ERROR

        return True
