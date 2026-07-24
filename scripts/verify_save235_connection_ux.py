#!/usr/bin/env python3
# SAVE-235 smoke tests (offscreen)
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtWidgets import QApplication

from gui.connectionpanel import (
    STATUS_NOT_CONFIGURED,
    STATUS_NOT_WORKING,
    STATUS_WORKING,
    ConnectionPanel,
)
from gui.notifications.connection_notice import (
    CONNECTION_AISSTREAM,
    CONNECTION_INTERNET,
    ConnectionNoticeService,
    is_connection_notice_suppressed,
    set_connection_notice_suppressed,
)
from gui.notifications.connection_notice_dialog import ConnectionNoticeDialog
from i18n import language_manager
from preferences import preferences_manager
from preferences.preferences import Preferences


def main() -> int:
    failures: list[str] = []
    app = QApplication.instance() or QApplication([])

    # Isolated preferences file
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    preferences_manager._path = Path(tmp.name)  # noqa: SLF001
    preferences_manager.save(Preferences.defaults())

    language_manager.set_language("hu")

    service = ConnectionNoticeService()
    panel = ConnectionPanel(service)

    # Database row removed; expected rows present
    expected = {"internet", "aisstream", "rtl", "gps", "camera", "api"}
    if set(panel._labels) != expected:  # noqa: SLF001
        failures.append(f"panel rows={set(panel._labels)}")

    if "database" in panel._labels:  # noqa: SLF001
        failures.append("database row still present")

    # Status icons
    panel._set_status(CONNECTION_AISSTREAM, STATUS_NOT_CONFIGURED, emit_notice=False)
    if "⚪" not in panel._labels[CONNECTION_AISSTREAM].text():
        failures.append("not_configured icon")

    panel._seen_working[CONNECTION_AISSTREAM] = True
    panel._statuses[CONNECTION_AISSTREAM] = STATUS_WORKING
    panel._set_status(CONNECTION_AISSTREAM, STATUS_NOT_WORKING, emit_notice=True)
    if "🔴" not in panel._labels[CONNECTION_AISSTREAM].text():
        failures.append("not_working icon")

    dlg = list(service._open.values())[0] if service._open else None
    if dlg is None:
        failures.append("lost dialog not shown")
    else:
        body = dlg._body.text()
        if "AISStream" not in body or "megszakadt" not in body:
            failures.append(f"lost body hu unexpected: {body!r}")
        if "újracsatlakozik" not in body:
            failures.append("missing reconnect line")
        # No separate title label
        if hasattr(dlg, "_title"):
            failures.append("dialog still has title widget")
        if dlg.windowTitle():
            failures.append(f"window title should be empty, got {dlg.windowTitle()!r}")
        dlg._dont_show_checkbox.setChecked(True)
        dlg.accept()

    if not is_connection_notice_suppressed(CONNECTION_AISSTREAM):
        failures.append("suppress not saved")

    # Suppressed: no new dialog
    service.show_lost(CONNECTION_AISSTREAM)
    if CONNECTION_AISSTREAM in service._open:
        failures.append("suppressed notice still shown")

    # Alerts engine must not bridge ais.status → banner anymore
    import inspect
    from alerts import engine as alerts_engine_mod

    src = inspect.getsource(alerts_engine_mod.ProfessionalAlertsEngine.start)
    if 'subscribe("ais.status"' in src or "subscribe('ais.status'" in src:
        failures.append("alerts engine still subscribes to ais.status")

    from alerts.notify_hooks import DesktopBannerSink
    from alerts.alert_event import AlertEvent

    # AIS_LOST must be ignored by the banner sink (early return).
    sink = DesktopBannerSink()
    sink.on_alert(
        AlertEvent(
            rule_id=0,
            event_type="AIS_LOST",
            message="AIS Lost",
            severity="warning",
            mmsi=0,
        )
    )

    # Camera reachability: enabled alone is not enough
    from cameras.reachability import is_camera_reachable
    from models.camera import Camera

    cam = Camera(
        id="t1",
        name="Test",
        enabled=True,
        stream_url="",
    )
    if is_camera_reachable(cam):
        failures.append("empty stream should not be reachable")

    cam2 = Camera(
        id="t2",
        name="Test2",
        enabled=False,
        stream_url="http://127.0.0.1:9/stream",
    )
    if is_camera_reachable(cam2, timeout_s=0.3):
        failures.append("disabled camera should not be reachable")

    # Restored dialog (clear suppress for test)
    set_connection_notice_suppressed(CONNECTION_AISSTREAM, False)
    panel._statuses[CONNECTION_AISSTREAM] = STATUS_NOT_WORKING
    panel._seen_working[CONNECTION_AISSTREAM] = True
    panel._set_status(CONNECTION_AISSTREAM, STATUS_WORKING, emit_notice=True)
    dlg2 = service._open.get(CONNECTION_AISSTREAM)
    if dlg2 is None:
        failures.append("restored dialog missing")
    else:
        body2 = dlg2._body.text()
        if "helyreállt" not in body2:
            failures.append(f"restored body: {body2!r}")
        if "újracsatlakozik" in body2:
            failures.append("restored should not include reconnect line")
        dlg2.accept()

    # Internet row uses working/not_working only
    if panel._statuses[CONNECTION_INTERNET] not in {
        STATUS_WORKING,
        STATUS_NOT_WORKING,
    }:
        failures.append("internet should not be not_configured")

    # EN text check
    language_manager.set_language("en")
    d_en = ConnectionNoticeDialog(
        connection_id="aisstream",
        connection_label="AISStream",
        restored=False,
    )
    if "was lost" not in d_en._body.text():
        failures.append(f"en lost text: {d_en._body.text()!r}")
    if d_en._close_button.text() != "Close":
        failures.append(f"en dismiss: {d_en._close_button.text()!r}")
    d_en.close()

    language_manager.set_language("hu")
    d_hu = ConnectionNoticeDialog(
        connection_id="aisstream",
        connection_label="AISStream",
        restored=False,
    )
    if d_hu._close_button.text() != "Bezár":
        failures.append(f"hu dismiss: {d_hu._close_button.text()!r}")
    d_hu.close()

    if failures:
        print("SAVE-235 FAIL:")
        for item in failures:
            print(" -", item)
        return 1

    print("SAVE-235 smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
