# ============================================================================
# Project X
# Analytics Dashboard exports (SAVE-216)
# ============================================================================

from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPdfWriter
from PySide6.QtWidgets import QWidget

from .records import AnalyticsSnapshot, INTERVAL_LABELS


def export_csv(snapshot: AnalyticsSnapshot, path: str | Path) -> Path:

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["section", "label", "value"])
        writer.writerow(["meta", "interval", snapshot.interval])
        writer.writerow(
            ["meta", "computed_at", snapshot.computed_at.isoformat(timespec="seconds")]
        )
        writer.writerow(["active_vessels", "count", snapshot.active_vessels])
        writer.writerow(["tracked_vessels", "count", snapshot.tracked_vessels])

        for item in snapshot.ship_types:
            writer.writerow(["ship_type", item.label, item.count])
        for item in snapshot.speed_distribution:
            writer.writerow(["speed", item.label, item.count])
        for item in snapshot.traffic_by_hour:
            writer.writerow(["traffic_hour", item.label, item.count])
        for item in snapshot.common_routes:
            writer.writerow(["route", item.label, item.count])
        for provider in snapshot.providers:
            writer.writerow(
                [
                    "provider",
                    provider.display_name,
                    f"{provider.status}|msg={provider.message_count}|ships={provider.ships_detected}",
                ]
            )
        writer.writerow(["cameras", "total", snapshot.cameras.total])
        writer.writerow(["cameras", "enabled", snapshot.cameras.enabled])
        writer.writerow(["cameras", "disabled", snapshot.cameras.disabled])
        for item in snapshot.cameras.by_country:
            writer.writerow(["camera_country", item.label, item.count])
        writer.writerow(["alerts", "active", snapshot.alerts.active])
        writer.writerow(["alerts", "history", snapshot.alerts.history])
        writer.writerow(["alerts", "critical", snapshot.alerts.critical])
        writer.writerow(["alerts", "warning", snapshot.alerts.warning])
        writer.writerow(["alerts", "info", snapshot.alerts.info])
        for item in snapshot.alerts.by_type:
            writer.writerow(["alert_type", item.label, item.count])

    return target


def export_png(widget: QWidget, path: str | Path) -> Path:

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    pixmap = widget.grab()
    if pixmap.isNull():
        raise RuntimeError("Failed to capture analytics dashboard image")
    if not pixmap.save(str(target), "PNG"):
        raise RuntimeError(f"Failed to write PNG: {target}")
    return target


def export_pdf(snapshot: AnalyticsSnapshot, path: str | Path) -> Path:

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    writer = QPdfWriter(str(target))
    writer.setTitle("Project X Analytics Dashboard")

    painter = QPainter(writer)
    try:
        margin = 48
        y = margin
        page_width = writer.width() - 2 * margin

        def draw_line(text: str, *, bold: bool = False) -> None:
            nonlocal y
            font = painter.font()
            font.setBold(bold)
            font.setPointSize(11 if bold else 9)
            painter.setFont(font)
            painter.drawText(
                QRectF(margin, y, page_width, 22),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                text,
            )
            y += 22
            if y > writer.height() - margin:
                writer.newPage()
                y = margin

        interval_label = INTERVAL_LABELS.get(snapshot.interval, snapshot.interval)
        draw_line("Project X — Analytics Dashboard", bold=True)
        draw_line(f"Interval: {interval_label}")
        draw_line(
            f"Computed: {snapshot.computed_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        draw_line("")
        draw_line(
            f"Active vessels: {snapshot.active_vessels}  |  Tracked: {snapshot.tracked_vessels}",
            bold=True,
        )
        draw_line("Ship types", bold=True)
        for item in snapshot.ship_types:
            draw_line(f"  {item.label}: {item.count}")
        draw_line("Speed distribution", bold=True)
        for item in snapshot.speed_distribution:
            draw_line(f"  {item.label}: {item.count}")
        draw_line("Hourly traffic", bold=True)
        for item in snapshot.traffic_by_hour:
            if item.count:
                draw_line(f"  {item.label}: {item.count}")
        draw_line("Common routes", bold=True)
        for item in snapshot.common_routes:
            draw_line(f"  {item.label}: {item.count}")
        draw_line("Providers", bold=True)
        for provider in snapshot.providers:
            draw_line(
                f"  {provider.display_name}: {provider.status} "
                f"(msg={provider.message_count}, ships={provider.ships_detected})"
            )
        draw_line("Cameras", bold=True)
        draw_line(
            f"  total={snapshot.cameras.total} enabled={snapshot.cameras.enabled} "
            f"disabled={snapshot.cameras.disabled}"
        )
        draw_line("Alerts", bold=True)
        draw_line(
            f"  active={snapshot.alerts.active} history={snapshot.alerts.history} "
            f"critical={snapshot.alerts.critical} warning={snapshot.alerts.warning} "
            f"info={snapshot.alerts.info}"
        )
        for item in snapshot.alerts.by_type:
            draw_line(f"  {item.label}: {item.count}")
    finally:
        painter.end()

    if not target.exists() or target.stat().st_size < 32:
        raise RuntimeError(f"Failed to write PDF: {target}")
    return target
