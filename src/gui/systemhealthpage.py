# ============================================================================
# Project X
# System Health Page
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
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

from gui.i18n_support import bind_language_refresh
from gui.theme import (
    DANGER,
    SUCCESS,
    TEXT,
    TEXT_MUTED,
    WARNING,
    card_stylesheet,
    primary_button_stylesheet,
    secondary_button_stylesheet,
)
from i18n import tr
from system_health import (
    SubsystemAction,
    SubsystemHealth,
    SubsystemState,
    SystemHealthReport,
    generate_diagnostic_report,
    system_health_checker,
)

_STATE_ICONS = {
    SubsystemState.WORKING: "🟢",
    SubsystemState.WARNING: "🟡",
    SubsystemState.ERROR: "🔴",
    SubsystemState.NOT_CONFIGURED: "⚪",
}

_STATE_LABEL_KEYS = {
    SubsystemState.WORKING: "Working",
    SubsystemState.WARNING: "Warning",
    SubsystemState.ERROR: "Error",
    SubsystemState.NOT_CONFIGURED: "Not configured",
}

_ACTION_LABEL_KEYS = {
    SubsystemAction.CONFIGURE: "Configure",
    SubsystemAction.TEST: "Test",
    SubsystemAction.DIAGNOSTICS: "Diagnostics",
    SubsystemAction.OPEN_SETTINGS: "Open Settings",
    SubsystemAction.OPEN_DASHBOARD: "Open Dashboard",
    SubsystemAction.OPEN_MAP: "Open Map",
    SubsystemAction.SETUP: "Setup",
}


class _HealthCheckWorker(QThread):

    finished = Signal(object)

    def __init__(self, *, run_live_tests: bool, parent=None):
        super().__init__(parent)
        self._run_live_tests = run_live_tests

    def run(self) -> None:
        report = system_health_checker.run_full_check(
            run_live_tests=self._run_live_tests,
        )
        self.finished.emit(report)


class _SubsystemRow(QFrame):

    actionTriggered = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._health: SubsystemHealth | None = None

        self.setStyleSheet(card_stylesheet(radius=8))

        layout = QGridLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(6)

        self._status_icon = QLabel()
        self._status_icon.setFixedWidth(28)
        layout.addWidget(self._status_icon, 0, 0, 2, 1)

        self._name_label = QLabel()
        self._name_label.setStyleSheet(
            "color: white; font-size: 12pt; font-weight: 600;"
        )
        layout.addWidget(self._name_label, 0, 1)

        self._state_label = QLabel()
        self._state_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10pt;")
        layout.addWidget(self._state_label, 0, 2)

        self._message_label = QLabel()
        self._message_label.setWordWrap(True)
        self._message_label.setStyleSheet("color: #c5ccd6; font-size: 10pt;")
        layout.addWidget(self._message_label, 1, 1, 1, 2)

        self._action_button = QPushButton()
        self._action_button.setStyleSheet(secondary_button_stylesheet())
        self._action_button.clicked.connect(self._on_action)
        layout.addWidget(self._action_button, 0, 3, 2, 1)

        layout.setColumnStretch(1, 1)

    def set_health(self, health: SubsystemHealth) -> None:

        self._health = health
        self._name_label.setText(tr(health.subsystem_key))
        self._status_icon.setText(_STATE_ICONS.get(health.state, "⚪"))
        self._state_label.setText(
            tr(_STATE_LABEL_KEYS.get(health.state, "Not configured"))
        )

        message = tr(health.message_key)

        if health.message_args:
            try:
                message = message.format(**health.message_args)
            except (KeyError, ValueError):
                pass

        if health.detail:
            message = f"{message} ({health.detail})"

        self._message_label.setText(message)

        if health.action and health.action != SubsystemAction.NONE:
            label_key = _ACTION_LABEL_KEYS.get(health.action, "")
            self._action_button.setText(tr(label_key) if label_key else "")
            self._action_button.setVisible(bool(label_key))
        else:
            self._action_button.setVisible(False)

    def _on_action(self) -> None:

        if self._health is None or not self._health.action:
            return

        self.actionTriggered.emit(
            self._health.action.value,
            self._health.subsystem_key,
        )


class SystemHealthPage(QWidget):

    configureAisRequested = Signal()
    testAisRequested = Signal()
    rtlSetupRequested = Signal()
    rtlDiagnosticsRequested = Signal()
    openSettingsRequested = Signal()
    openDashboardRequested = Signal()
    openMapRequested = Signal()
    cameraDiagnosticsRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._report: SystemHealthReport | None = None
        self._worker: _HealthCheckWorker | None = None
        self._rows: list[_SubsystemRow] = []

        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self.refresh()

    def attach_hybrid_engine(self, hybrid_engine) -> None:

        system_health_checker.attach_hybrid_engine(hybrid_engine)

    def refresh(self) -> None:

        self._apply_report(
            system_health_checker.run_full_check(run_live_tests=False)
        )

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("System Health"))
        self._summary_label.setText(self._summary_text())
        self._run_check_button.setText(tr("Run Full System Check"))
        self._save_report_button.setText(tr("Save Diagnostic Report"))
        self._run_check_button.setToolTip(
            tr("Test every subsystem and refresh status")
        )
        self._save_report_button.setToolTip(
            tr("Save a diagnostic report to diagnostics.txt")
        )

        if self._report is not None:
            self._apply_report(self._report)

    def _build_ui(self) -> None:

        self.setStyleSheet(f"background: {BG_DEEP};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(25, 25, 25, 25)
        outer.setSpacing(12)

        self._title_label = QLabel()
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet(
            "color: white; font-size: 26pt; font-weight: bold;"
        )
        outer.addWidget(self._title_label)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self._run_check_button = QPushButton()
        self._run_check_button.setStyleSheet(primary_button_stylesheet(padding="8px 14px"))
        button_row.addWidget(self._run_check_button)

        self._save_report_button = QPushButton()
        self._save_report_button.setStyleSheet(secondary_button_stylesheet(padding="8px 14px"))
        button_row.addWidget(self._save_report_button)
        button_row.addStretch()
        outer.addLayout(button_row)

        self._summary_label = QLabel()
        self._summary_label.setWordWrap(True)
        self._summary_label.setStyleSheet(f"color: {DANGER}; font-size: 11pt;")
        self._summary_label.setVisible(False)
        outer.addWidget(self._summary_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(8)
        self._rows_layout.addStretch()

        scroll.setWidget(self._rows_container)
        outer.addWidget(scroll, 1)

    def _connect_signals(self) -> None:

        self._run_check_button.clicked.connect(self._run_full_check)
        self._save_report_button.clicked.connect(self._save_report)

    def _summary_text(self) -> str:

        if self._report is None:
            return ""

        if self._report.has_errors:
            return tr(
                "Some subsystems need attention. "
                "Use the action buttons below to fix them."
            )

        if self._report.has_warnings:
            return tr(
                "Some subsystems reported warnings. "
                "Review the details below."
            )

        return tr("All checked subsystems are operational.")

    def _apply_report(self, report: SystemHealthReport) -> None:

        self._report = report
        self._summary_label.setText(self._summary_text())

        if report.has_errors:
            self._summary_label.setStyleSheet(f"color: {DANGER}; font-size: 11pt;")
            self._summary_label.setVisible(True)
        elif report.has_warnings:
            self._summary_label.setStyleSheet(f"color: {WARNING}; font-size: 11pt;")
            self._summary_label.setVisible(True)
        else:
            self._summary_label.setStyleSheet(f"color: {SUCCESS}; font-size: 11pt;")
            self._summary_label.setVisible(True)

        while self._rows:
            row = self._rows.pop()
            self._rows_layout.removeWidget(row)
            row.deleteLater()

        for health in report.subsystems:
            row = _SubsystemRow()
            row.set_health(health)
            row.actionTriggered.connect(self._on_row_action)
            self._rows.append(row)
            self._rows_layout.insertWidget(
                self._rows_layout.count() - 1,
                row,
            )

    def _on_row_action(self, action: str, subsystem_key: str) -> None:

        if action == SubsystemAction.CONFIGURE.value:
            self.configureAisRequested.emit()
        elif action == SubsystemAction.TEST.value:
            if subsystem_key == "Internet":
                self._run_full_check()
            else:
                self.testAisRequested.emit()
        elif action == SubsystemAction.SETUP.value:
            self.rtlSetupRequested.emit()
        elif action == SubsystemAction.DIAGNOSTICS.value:
            if subsystem_key == "Camera Framework":
                self.cameraDiagnosticsRequested.emit()
            else:
                self.rtlDiagnosticsRequested.emit()
        elif action == SubsystemAction.OPEN_SETTINGS.value:
            self.openSettingsRequested.emit()
        elif action == SubsystemAction.OPEN_DASHBOARD.value:
            self.openDashboardRequested.emit()
        elif action == SubsystemAction.OPEN_MAP.value:
            self.openMapRequested.emit()

    def _run_full_check(self) -> None:

        if self._worker and self._worker.isRunning():
            return

        self._run_check_button.setEnabled(False)
        self._run_check_button.setText(tr("Running system check..."))

        self._worker = _HealthCheckWorker(run_live_tests=True, parent=self)
        self._worker.finished.connect(self._on_check_finished)
        self._worker.start()

    def _on_check_finished(self, report: SystemHealthReport) -> None:

        self._run_check_button.setEnabled(True)
        self._run_check_button.setText(tr("Run Full System Check"))
        self._apply_report(report)

    def _save_report(self) -> None:

        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Save Diagnostic Report"),
            "diagnostics.txt",
            tr("Text files (*.txt)"),
        )

        if not path:
            return

        try:
            content = generate_diagnostic_report(run_live_tests=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
        except OSError:
            QMessageBox.warning(
                self,
                tr("Save Diagnostic Report"),
                tr("Could not save the diagnostic report."),
            )
            return

        QMessageBox.information(
            self,
            tr("Save Diagnostic Report"),
            tr("Diagnostic report saved successfully."),
        )

    def showEvent(self, event) -> None:

        super().showEvent(event)
        self.refresh()
