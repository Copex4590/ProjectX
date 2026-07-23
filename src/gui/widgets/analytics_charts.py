# ============================================================================
# Project X
# Analytics chart widgets (SAVE-216)
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QFrame

from analytics.records import NamedCount
from gui.theme import ThemeColors, card_stylesheet
from i18n import tr

_CHART_PALETTE = (
    ThemeColors.Primary500,
    ThemeColors.Primary300,
    ThemeColors.Success,
    ThemeColors.Warning,
    ThemeColors.Danger,
    ThemeColors.Primary100,
    ThemeColors.Primary700,
    "#7ec8e3",
)


class _ChartBase(QFrame):

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._title = title
        self._items: list[NamedCount] = []
        self.setMinimumHeight(240)
        self.setStyleSheet(card_stylesheet(radius=10))

    def set_title(self, title: str) -> None:

        self._title = title
        self.update()

    def set_items(self, items: list[NamedCount]) -> None:

        self._items = list(items)
        self.update()

    def _draw_title(self, painter: QPainter) -> QRectF:

        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(ThemeColors.TextPrimary))
        painter.drawText(14, 24, self._title)
        return self.rect().adjusted(16, 36, -16, -16)

    def _draw_empty(self, painter: QPainter, chart_rect: QRectF) -> None:

        painter.setPen(QColor(ThemeColors.TextSecondary))
        painter.drawText(
            chart_rect,
            int(Qt.AlignmentFlag.AlignCenter),
            tr("No data"),
        )


class BarChartWidget(_ChartBase):
    """Simple vertical bar chart."""

    def paintEvent(self, event) -> None:  # noqa: N802

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(ThemeColors.Panel))
        chart_rect = self._draw_title(painter)

        if not self._items or max((item.count for item in self._items), default=0) <= 0:
            self._draw_empty(painter, chart_rect)
            painter.end()
            return

        max_value = max(item.count for item in self._items)
        count = len(self._items)
        gap = 6
        bar_width = max(8, int((chart_rect.width() - gap * (count - 1)) / count))
        base_y = chart_rect.bottom() - 18

        for index, item in enumerate(self._items):
            height = int((item.count / max_value) * (chart_rect.height() - 28))
            x = chart_rect.left() + index * (bar_width + gap)
            y = base_y - height
            color = QColor(_CHART_PALETTE[index % len(_CHART_PALETTE)])
            painter.fillRect(int(x), int(y), bar_width, height, color)

            painter.setPen(QColor(ThemeColors.TextSecondary))
            label = item.label[:6]
            painter.drawText(
                QRectF(x - 4, base_y + 2, bar_width + 8, 16),
                int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop),
                label,
            )

        painter.end()


class LineChartWidget(_ChartBase):
    """Simple polyline chart."""

    def paintEvent(self, event) -> None:  # noqa: N802

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(ThemeColors.Panel))
        chart_rect = self._draw_title(painter)

        if not self._items:
            self._draw_empty(painter, chart_rect)
            painter.end()
            return

        values = [item.count for item in self._items]
        max_value = max(values) if values else 0
        if max_value <= 0:
            self._draw_empty(painter, chart_rect)
            painter.end()
            return

        plot = chart_rect.adjusted(8, 8, -8, -22)
        step = plot.width() / max(1, len(values) - 1)
        points: list[QPointF] = []
        for index, value in enumerate(values):
            x = plot.left() + index * step
            y = plot.bottom() - (value / max_value) * plot.height()
            points.append(QPointF(x, y))

        # Soft fill under the line.
        fill = QPolygonF(points + [QPointF(plot.right(), plot.bottom()), QPointF(plot.left(), plot.bottom())])
        fill_color = QColor(ThemeColors.Primary500)
        fill_color.setAlpha(55)
        painter.setBrush(fill_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(fill)

        pen = QPen(QColor(ThemeColors.Primary300), 2.2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for index in range(1, len(points)):
            painter.drawLine(points[index - 1], points[index])

        painter.setBrush(QColor(ThemeColors.Primary500))
        for point in points[:: max(1, len(points) // 12)]:
            painter.drawEllipse(point, 3.0, 3.0)

        painter.setPen(QColor(ThemeColors.TextSecondary))
        if self._items:
            painter.drawText(
                QRectF(plot.left(), plot.bottom() + 2, 40, 16),
                int(Qt.AlignmentFlag.AlignLeft),
                self._items[0].label,
            )
            painter.drawText(
                QRectF(plot.right() - 40, plot.bottom() + 2, 40, 16),
                int(Qt.AlignmentFlag.AlignRight),
                self._items[-1].label,
            )

        painter.end()


class PieChartWidget(_ChartBase):
    """Simple pie / donut chart with legend."""

    def paintEvent(self, event) -> None:  # noqa: N802

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(ThemeColors.Panel))
        chart_rect = self._draw_title(painter)

        items = [item for item in self._items if item.count > 0]
        total = sum(item.count for item in items)
        if total <= 0:
            self._draw_empty(painter, chart_rect)
            painter.end()
            return

        size = min(chart_rect.height(), chart_rect.width() * 0.48)
        pie = QRectF(
            chart_rect.left() + 8,
            chart_rect.center().y() - size / 2,
            size,
            size,
        )

        start = 90 * 16
        for index, item in enumerate(items):
            span = int(round(item.count / total * 360 * 16))
            color = QColor(_CHART_PALETTE[index % len(_CHART_PALETTE)])
            painter.setBrush(color)
            painter.setPen(QPen(QColor(ThemeColors.Panel), 1))
            painter.drawPie(pie, start, -span)
            start -= span

        # Donut hole
        hole = pie.adjusted(size * 0.28, size * 0.28, -size * 0.28, -size * 0.28)
        painter.setBrush(QColor(ThemeColors.Panel))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(hole)

        legend_x = pie.right() + 18
        legend_y = chart_rect.top() + 4
        for index, item in enumerate(items[:8]):
            color = QColor(_CHART_PALETTE[index % len(_CHART_PALETTE)])
            painter.fillRect(int(legend_x), int(legend_y + 4), 10, 10, color)
            painter.setPen(QColor(ThemeColors.TextPrimary))
            percent = (item.count / total) * 100.0
            painter.drawText(
                int(legend_x + 16),
                int(legend_y + 13),
                f"{item.label} ({item.count}, {percent:.0f}%)",
            )
            legend_y += 20

        painter.end()
