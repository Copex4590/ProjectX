# ============================================================================
# Project X
# Statistics Dashboard Page
# ============================================================================

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from statistics.statistics_manager import StatisticsManager, statistics_manager

_AUTO_REFRESH_MS = 30000


class SummaryCard(QFrame):

    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        self.setStyleSheet("""
            QFrame {
                background: #252a31;
                border: 1px solid #40444b;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #9aa4af; font-size: 10pt;")

        self.value_label = QLabel("0")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setStyleSheet(
            "color: white; font-size: 24pt; font-weight: bold;"
        )

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:

        self.value_label.setText(value)


class TopListPanel(QFrame):

    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        self.setStyleSheet("""
            QFrame {
                background: #252a31;
                border: 1px solid #40444b;
                border-radius: 10px;
            }

            QListWidget {
                background: transparent;
                color: white;
                border: none;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        heading = QLabel(title)
        heading.setStyleSheet("color: #d5dbe3; font-size: 11pt; font-weight: 600;")
        layout.addWidget(heading)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

    def set_items(self, items: list[str]) -> None:

        self.list_widget.clear()

        if not items:
            item = QListWidgetItem("No data")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(item)
            return

        for text in items:
            self.list_widget.addItem(text)


class SimpleBarChart(QFrame):

    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        self._title = title
        self._values: list[int] = []
        self._labels: list[str] = []
        self.setMinimumHeight(220)
        self.setStyleSheet("""
            QFrame {
                background: #252a31;
                border: 1px solid #40444b;
                border-radius: 10px;
            }
        """)

    def set_values(self, values: list[int], labels: list[str] | None = None) -> None:

        self._values = list(values)
        self._labels = list(labels or [])
        self.update()

    def paintEvent(self, event) -> None:

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#252a31"))

        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor("#d5dbe3"))
        painter.drawText(12, 24, self._title)

        chart_rect = self.rect().adjusted(16, 36, -16, -16)

        if not self._values or max(self._values, default=0) <= 0:
            painter.setPen(QColor("#9aa4af"))
            painter.drawText(
                chart_rect,
                Qt.AlignmentFlag.AlignCenter,
                "No data",
            )
            painter.end()
            return

        max_value = max(self._values)
        bar_count = len(self._values)
        gap = 4
        bar_width = max(4, (chart_rect.width() - gap * (bar_count - 1)) // bar_count)

        for index, value in enumerate(self._values):
            if value <= 0:
                continue

            bar_height = int((value / max_value) * (chart_rect.height() - 18))
            x = chart_rect.left() + index * (bar_width + gap)
            y = chart_rect.bottom() - bar_height
            painter.fillRect(x, y, bar_width, bar_height, QColor("#1976d2"))

        painter.setPen(QColor("#6b7688"))
        painter.drawLine(
            chart_rect.left(),
            chart_rect.bottom(),
            chart_rect.right(),
            chart_rect.bottom(),
        )

        painter.end()


class StatisticsPage(QWidget):

    def __init__(
        self,
        manager: StatisticsManager | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._manager = manager or statistics_manager
        self._auto_refresh_enabled = False

        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.setInterval(_AUTO_REFRESH_MS)
        self._auto_refresh_timer.timeout.connect(self.refresh)

        self._build_ui()
        self.refresh()

    def refresh(self) -> None:

        self._manager.refresh()
        dashboard = self._manager.dashboard_statistics()
        global_stats = dashboard.global_stats

        self.total_vessels_card.set_value(str(global_stats.total_vessels))
        self.active_vessels_card.set_value(str(global_stats.active_vessels))
        self.arrivals_today_card.set_value(str(global_stats.arrivals_today))
        self.departures_today_card.set_value(str(global_stats.departures_today))
        self.position_updates_card.set_value(
            str(global_stats.position_updates_today)
        )

        self.ship_types_panel.set_items([
            f"{label} ({count})"
            for label, count in dashboard.top_ship_types
        ])
        self.flags_panel.set_items([
            f"{label} ({count})"
            for label, count in dashboard.top_flags
        ])
        self.active_vessels_panel.set_items([
            f"{entry.name} ({entry.activity_count})"
            for entry in dashboard.top_active_vessels
        ])

        hour_labels = [f"{hour:02d}" for hour in range(24)]
        self.arrivals_chart.set_values(
            dashboard.arrivals_by_hour,
            hour_labels,
        )
        self.departures_chart.set_values(
            dashboard.departures_by_hour,
            hour_labels,
        )
        self.activity_chart.set_values(
            dashboard.activity_last_24_hours,
            [f"-{23 - hour}h" for hour in range(24)],
        )

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

        self.setStyleSheet("background: #1d2127;")

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer_layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)

        title = QLabel("Statistics Dashboard")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color: white; font-size: 26pt; font-weight: bold;"
        )
        layout.addWidget(title)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background: #1976d2;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
            }
        """)
        controls.addWidget(self.refresh_button)

        self.auto_refresh_checkbox = QCheckBox("Auto Refresh")
        self.auto_refresh_checkbox.setStyleSheet("color: #d5dbe3;")
        controls.addWidget(self.auto_refresh_checkbox)
        controls.addStretch()
        layout.addLayout(controls)

        summary = QGridLayout()
        summary.setHorizontalSpacing(12)
        summary.setVerticalSpacing(12)

        self.total_vessels_card = SummaryCard("Total Vessels")
        self.active_vessels_card = SummaryCard("Active Vessels")
        self.arrivals_today_card = SummaryCard("Arrivals Today")
        self.departures_today_card = SummaryCard("Departures Today")
        self.position_updates_card = SummaryCard("Position Updates Today")

        summary.addWidget(self.total_vessels_card, 0, 0)
        summary.addWidget(self.active_vessels_card, 0, 1)
        summary.addWidget(self.arrivals_today_card, 0, 2)
        summary.addWidget(self.departures_today_card, 1, 0)
        summary.addWidget(self.position_updates_card, 1, 1)
        layout.addLayout(summary)

        lists = QGridLayout()
        lists.setHorizontalSpacing(12)

        self.ship_types_panel = TopListPanel("Top 10 Ship Types")
        self.flags_panel = TopListPanel("Top 10 Flags")
        self.active_vessels_panel = TopListPanel("Top 10 Most Active Vessels")

        lists.addWidget(self.ship_types_panel, 0, 0)
        lists.addWidget(self.flags_panel, 0, 1)
        lists.addWidget(self.active_vessels_panel, 0, 2)
        layout.addLayout(lists)

        charts = QGridLayout()
        charts.setHorizontalSpacing(12)
        charts.setVerticalSpacing(12)

        self.arrivals_chart = SimpleBarChart("Arrivals by Hour")
        self.departures_chart = SimpleBarChart("Departures by Hour")
        self.activity_chart = SimpleBarChart("Vessel Activity (Last 24 Hours)")

        charts.addWidget(self.arrivals_chart, 0, 0)
        charts.addWidget(self.departures_chart, 0, 1)
        charts.addWidget(self.activity_chart, 1, 0, 1, 2)
        layout.addLayout(charts)

        layout.addStretch()

        self.refresh_button.clicked.connect(self.refresh)
        self.auto_refresh_checkbox.toggled.connect(self.set_auto_refresh)
