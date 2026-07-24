# ============================================================================
# Project X
# Analytics Dashboard (SAVE-216)
# ============================================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
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

from alerts.alert_manager import EVENT_ALERT_CLEARED, EVENT_ALERT_FIRED
from analytics.export import export_csv, export_pdf, export_png
from analytics.manager import AnalyticsManager, analytics_manager
from analytics.records import (
    INTERVAL_LABELS,
    SUPPORTED_INTERVALS,
    AnalyticsSnapshot,
    NamedCount,
)
from events import eventbus
from gui.i18n_support import bind_language_refresh
from gui.theme import (
    ThemeColors,
    card_stylesheet,
    primary_button_stylesheet,
    secondary_button_stylesheet,
)
from gui.widgets.analytics_charts import BarChartWidget, LineChartWidget, PieChartWidget
from i18n import tr

_LIVE_REFRESH_MS = 10000


class _GuiBridge(QWidget):
    refresh_requested = Signal()


class MetricCard(QFrame):

    def __init__(self, title_key: str, parent=None):
        super().__init__(parent)
        self._title_key = title_key
        self.setStyleSheet(card_stylesheet(radius=10))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)

        self._title = QLabel(tr(title_key))
        self._title.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 10pt;"
        )
        self._value = QLabel("0")
        self._value.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 22pt; font-weight: 700;"
        )
        self._subtitle = QLabel("")
        self._subtitle.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        layout.addWidget(self._title)
        layout.addWidget(self._value)
        layout.addWidget(self._subtitle)

    def set_value(self, value: str, subtitle: str = "") -> None:

        self._value.setText(value)
        self._subtitle.setText(subtitle)

    def refresh_translations(self) -> None:

        self._title.setText(tr(self._title_key))


class ListPanel(QFrame):

    def __init__(self, title_key: str, parent=None):
        super().__init__(parent)
        self._title_key = title_key
        self.setStyleSheet(card_stylesheet(radius=10))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        self._heading = QLabel(tr(title_key))
        self._heading.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 11pt; font-weight: 600;"
        )
        layout.addWidget(self._heading)

        self._body = QLabel(tr("No data"))
        self._body.setWordWrap(True)
        self._body.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._body.setStyleSheet(
            f"color: {ThemeColors.text_body()}; font-size: 10pt; line-height: 1.4;"
        )
        layout.addWidget(self._body, 1)

    def set_lines(self, lines: list[str]) -> None:

        if not lines:
            self._body.setText(tr("No data"))
            return
        self._body.setText("\n".join(lines))

    def refresh_translations(self) -> None:

        self._heading.setText(tr(self._title_key))


class AnalyticsDashboardPage(QWidget):
    """Professional Analytics Dashboard with live charts and exports."""

    def __init__(self, manager: AnalyticsManager | None = None, parent=None):
        super().__init__(parent)

        self._manager = manager or analytics_manager
        self._snapshot = AnalyticsSnapshot()
        self._bridge = _GuiBridge()
        self._bridge.refresh_requested.connect(self._request_live_refresh)
        self._live_pending = False

        self.setStyleSheet(f"background: {ThemeColors.Background};")
        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self.refresh()

        self._timer = QTimer(self)
        self._timer.setInterval(_LIVE_REFRESH_MS)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

        self._subscribe_events()

    def _subscribe_events(self) -> None:

        eventbus.subscribe("ship.updated", self._on_bus_event)
        eventbus.subscribe("ais.status", self._on_bus_event)
        eventbus.subscribe("rtl.status", self._on_bus_event)
        eventbus.subscribe("providers.changed", self._on_bus_event)
        eventbus.subscribe(EVENT_ALERT_FIRED, self._on_bus_event)
        eventbus.subscribe(EVENT_ALERT_CLEARED, self._on_bus_event)

    def shutdown(self) -> None:

        self._timer.stop()
        eventbus.unsubscribe("ship.updated", self._on_bus_event)
        eventbus.unsubscribe("ais.status", self._on_bus_event)
        eventbus.unsubscribe("rtl.status", self._on_bus_event)
        eventbus.unsubscribe("providers.changed", self._on_bus_event)
        eventbus.unsubscribe(EVENT_ALERT_FIRED, self._on_bus_event)
        eventbus.unsubscribe(EVENT_ALERT_CLEARED, self._on_bus_event)

    def _on_bus_event(self, *args, **kwargs) -> None:

        self._bridge.refresh_requested.emit()

    def _request_live_refresh(self) -> None:

        if self._live_pending:
            return
        self._live_pending = True
        QTimer.singleShot(400, self._flush_live_refresh)

    def _flush_live_refresh(self) -> None:

        self._live_pending = False
        self.refresh()

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

        self._content = QWidget()
        self._content.setStyleSheet(f"background: {ThemeColors.Background};")
        scroll.setWidget(self._content)

        layout = QVBoxLayout(self._content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        self._title = QLabel()
        self._title.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 18pt; font-weight: 700;"
        )
        header.addWidget(self._title)
        header.addStretch(1)

        self._updated = QLabel()
        self._updated.setStyleSheet(f"color: {ThemeColors.TextSecondary}; font-size: 9pt;")
        header.addWidget(self._updated)
        layout.addLayout(header)

        controls = QFrame()
        controls.setStyleSheet(card_stylesheet(radius=10))
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(14, 10, 14, 10)
        controls_layout.setSpacing(8)

        self._interval_label = QLabel()
        self._interval_label.setStyleSheet(f"color: {ThemeColors.TextSecondary};")
        controls_layout.addWidget(self._interval_label)

        self._interval = QComboBox()
        self._interval.setStyleSheet(self._combo_style())
        for key in SUPPORTED_INTERVALS:
            self._interval.addItem(tr(INTERVAL_LABELS[key]), key)
        controls_layout.addWidget(self._interval)

        self._refresh_btn = QPushButton()
        self._refresh_btn.setStyleSheet(secondary_button_stylesheet())
        controls_layout.addWidget(self._refresh_btn)

        self._export_csv_btn = QPushButton()
        self._export_csv_btn.setStyleSheet(secondary_button_stylesheet())
        controls_layout.addWidget(self._export_csv_btn)

        self._export_png_btn = QPushButton()
        self._export_png_btn.setStyleSheet(secondary_button_stylesheet())
        controls_layout.addWidget(self._export_png_btn)

        self._export_pdf_btn = QPushButton()
        self._export_pdf_btn.setStyleSheet(primary_button_stylesheet())
        controls_layout.addWidget(self._export_pdf_btn)

        controls_layout.addStretch(1)
        layout.addWidget(controls)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(12)
        metrics.setVerticalSpacing(12)
        self._active_card = MetricCard("Active Vessels")
        self._tracked_card = MetricCard("Tracked Vessels")
        self._camera_card = MetricCard("Cameras")
        self._alert_card = MetricCard("Alerts")
        metrics.addWidget(self._active_card, 0, 0)
        metrics.addWidget(self._tracked_card, 0, 1)
        metrics.addWidget(self._camera_card, 0, 2)
        metrics.addWidget(self._alert_card, 0, 3)
        layout.addLayout(metrics)

        charts = QGridLayout()
        charts.setHorizontalSpacing(12)
        charts.setVerticalSpacing(12)

        self._ship_type_pie = PieChartWidget(tr("Vessels by Type"))
        self._speed_bars = BarChartWidget(tr("Speed Distribution"))
        self._traffic_line = LineChartWidget(tr("Hourly Traffic"))
        self._routes_bars = BarChartWidget(tr("Most Common Routes"))

        charts.addWidget(self._ship_type_pie, 0, 0)
        charts.addWidget(self._speed_bars, 0, 1)
        charts.addWidget(self._traffic_line, 1, 0, 1, 2)
        charts.addWidget(self._routes_bars, 2, 0, 1, 2)
        layout.addLayout(charts)

        side = QGridLayout()
        side.setHorizontalSpacing(12)
        side.setVerticalSpacing(12)
        self._providers_panel = ListPanel("Provider Statistics")
        self._cameras_panel = ListPanel("Camera Statistics")
        self._alerts_panel = ListPanel("Alerts Statistics")
        self._severity_pie = PieChartWidget(tr("Alerts by Severity"))
        side.addWidget(self._providers_panel, 0, 0)
        side.addWidget(self._cameras_panel, 0, 1)
        side.addWidget(self._alerts_panel, 1, 0)
        side.addWidget(self._severity_pie, 1, 1)
        layout.addLayout(side)
        layout.addStretch(1)

    def _connect_signals(self) -> None:

        self._refresh_btn.clicked.connect(self.refresh)
        self._interval.currentIndexChanged.connect(self._on_interval_changed)
        self._export_csv_btn.clicked.connect(self._export_csv)
        self._export_png_btn.clicked.connect(self._export_png)
        self._export_pdf_btn.clicked.connect(self._export_pdf)

    def _on_interval_changed(self, _index: int = 0) -> None:

        key = self._interval.currentData()
        if key:
            self._manager.set_interval(str(key))
        self.refresh()

    def refresh_translations(self) -> None:

        self._title.setText(tr("Analytics Dashboard"))
        self._interval_label.setText(tr("Time interval"))
        self._refresh_btn.setText(tr("Refresh"))
        self._export_csv_btn.setText(tr("Export CSV"))
        self._export_png_btn.setText(tr("Export PNG"))
        self._export_pdf_btn.setText(tr("Export PDF"))

        current = self._interval.currentData()
        self._interval.blockSignals(True)
        self._interval.clear()
        for key in SUPPORTED_INTERVALS:
            self._interval.addItem(tr(INTERVAL_LABELS[key]), key)
        if current is not None:
            idx = self._interval.findData(current)
            if idx >= 0:
                self._interval.setCurrentIndex(idx)
        self._interval.blockSignals(False)

        self._active_card.refresh_translations()
        self._tracked_card.refresh_translations()
        self._camera_card.refresh_translations()
        self._alert_card.refresh_translations()
        self._providers_panel.refresh_translations()
        self._cameras_panel.refresh_translations()
        self._alerts_panel.refresh_translations()

        self._ship_type_pie.set_title(tr("Vessels by Type"))
        self._speed_bars.set_title(tr("Speed Distribution"))
        self._traffic_line.set_title(tr("Hourly Traffic"))
        self._routes_bars.set_title(tr("Most Common Routes"))
        self._severity_pie.set_title(tr("Alerts by Severity"))

    def refresh(self) -> None:

        self._snapshot = self._manager.refresh()
        snap = self._snapshot

        self._active_card.set_value(
            str(snap.active_vessels),
            tr("Live / recent in interval"),
        )
        self._tracked_card.set_value(
            str(snap.tracked_vessels),
            tr("In memory registry"),
        )
        self._camera_card.set_value(
            str(snap.cameras.total),
            tr("{enabled} enabled").format(enabled=snap.cameras.enabled),
        )
        self._alert_card.set_value(
            str(snap.alerts.active),
            tr("{history} acknowledged").format(history=snap.alerts.history),
        )

        self._ship_type_pie.set_items(snap.ship_types)
        self._speed_bars.set_items(snap.speed_distribution)
        self._traffic_line.set_items(snap.traffic_by_hour)
        self._routes_bars.set_items(snap.common_routes)

        self._providers_panel.set_lines([
            f"{row.display_name}: {row.status} — "
            f"{tr('messages')}={row.message_count}, {tr('ships')}={row.ships_detected}"
            for row in snap.providers
        ])
        camera_lines = [
            f"{tr('Total')}: {snap.cameras.total}",
            f"{tr('Enabled')}: {snap.cameras.enabled}",
            f"{tr('Disabled')}: {snap.cameras.disabled}",
        ]
        camera_lines.extend(
            f"{item.label}: {item.count}" for item in snap.cameras.by_country
        )
        self._cameras_panel.set_lines(camera_lines)

        alert_lines = [
            f"{tr('Active')}: {snap.alerts.active}",
            f"{tr('History')}: {snap.alerts.history}",
            f"{tr('Critical')}: {snap.alerts.critical}",
            f"{tr('Warning')}: {snap.alerts.warning}",
            f"{tr('Info')}: {snap.alerts.info}",
        ]
        alert_lines.extend(
            f"{item.label}: {item.count}" for item in snap.alerts.by_type
        )
        self._alerts_panel.set_lines(alert_lines)

        self._severity_pie.set_items([
            NamedCount(tr("Critical"), snap.alerts.critical),
            NamedCount(tr("Warning"), snap.alerts.warning),
            NamedCount(tr("Info"), snap.alerts.info),
        ])

        self._updated.setText(
            tr("Updated {time}").format(
                time=snap.computed_at.strftime("%Y-%m-%d %H:%M:%S")
            )
        )

    def _export_csv(self) -> None:

        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Export CSV"),
            str(Path.home() / "projectx-analytics.csv"),
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            export_csv(self._snapshot, path)
            QMessageBox.information(self, tr("Export CSV"), tr("CSV export completed."))
        except Exception as exc:
            QMessageBox.warning(self, tr("Export CSV"), str(exc))

    def _export_png(self) -> None:

        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Export PNG"),
            str(Path.home() / "projectx-analytics.png"),
            "PNG (*.png)",
        )
        if not path:
            return
        try:
            export_png(self._content, path)
            QMessageBox.information(self, tr("Export PNG"), tr("PNG export completed."))
        except Exception as exc:
            QMessageBox.warning(self, tr("Export PNG"), str(exc))

    def _export_pdf(self) -> None:

        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Export PDF"),
            str(Path.home() / "projectx-analytics.pdf"),
            "PDF (*.pdf)",
        )
        if not path:
            return
        try:
            export_pdf(self._snapshot, path)
            QMessageBox.information(self, tr("Export PDF"), tr("PDF export completed."))
        except Exception as exc:
            QMessageBox.warning(self, tr("Export PDF"), str(exc))

    @staticmethod
    def _combo_style() -> str:

        return f"""
            QComboBox {{
                background: {ThemeColors.Panel};
                color: {ThemeColors.TextPrimary};
                border: 1px solid {ThemeColors.Border};
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 140px;
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background: {ThemeColors.Panel};
                color: {ThemeColors.TextPrimary};
                selection-background-color: {ThemeColors.Primary700};
            }}
        """
