#!/usr/bin/env python3
"""Manual validation helper for notification shutdown HOTFIX."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gui.notifications.ais_connection_monitor import AisConnectionMonitor
from gui.notifications.notification_manager import notification_manager
from gui.notifications.severity import NotificationSeverity


def _count_visible_tool_windows(app: QApplication) -> int:
    count = 0

    for widget in app.topLevelWidgets():
        if widget.isVisible() and widget.windowFlags() & widget.windowFlags().Tool:
            count += 1

    return count


def main() -> int:
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

    app = QApplication(sys.argv)
    manager = notification_manager()

    manager.show(
        "AIS connection lost.\nIf the AIS connection is not restored within 30 seconds, "
        "vessels belonging to this provider will automatically disappear from the map.",
        severity=NotificationSeverity.WARNING,
        key=AisConnectionMonitor.AIS_CONNECTION_KEY,
        sticky=True,
        animate=True,
    )

    banner = manager._banner

    if banner.isHidden():
        print("FAIL: AIS banner is not visible after show()")
        return 1

    print("OK: AIS disconnect banner visible")

    def _simulate_shutdown() -> None:
        monitor = AisConnectionMonitor(hybrid_engine=object(), parent=None)
        monitor._notifications = manager
        monitor._countdown_timer.start()
        monitor.shutdown()

        manager.shutdown()
        app.aboutToQuit.emit()
        manager.shutdown()
        app.processEvents()

        if not banner.isHidden():
            print("FAIL: banner still visible after shutdown")
            app.exit(1)
            return

        if not banner._destroyed:
            print("FAIL: banner was not marked destroyed")
            app.exit(1)
            return

        if not manager._shutdown:
            print("FAIL: manager shutdown flag not set")
            app.exit(1)
            return

        visible_tools = _count_visible_tool_windows(app)

        if visible_tools:
            print(f"FAIL: {visible_tools} visible Tool window(s) remain")
            app.exit(1)
            return

        print("PASS: banner destroyed, no orphan Tool windows, idempotent shutdown")
        app.exit(0)

    QTimer.singleShot(800, _simulate_shutdown)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
