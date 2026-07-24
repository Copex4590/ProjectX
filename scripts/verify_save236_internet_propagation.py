#!/usr/bin/env python3
# SAVE-236 — Internet master propagates to dependent ConnectionPanel rows
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtWidgets import QApplication

from connectivity.internet_state import set_internet_online
from gui.connectionpanel import (
    INTERNET_DEPENDENT_CONNECTIONS,
    STATUS_NOT_WORKING,
    STATUS_WORKING,
    ConnectionPanel,
)
from gui.notifications.connection_notice import (
    CONNECTION_AISSTREAM,
    CONNECTION_API,
    CONNECTION_INTERNET,
    ConnectionNoticeService,
)
from preferences import preferences_manager
from preferences.preferences import Preferences


def main() -> int:
    failures: list[str] = []
    app = QApplication.instance() or QApplication([])

    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    preferences_manager._path = Path(tmp.name)  # noqa: SLF001
    preferences_manager.save(Preferences.defaults())

    service = ConnectionNoticeService()
    panel = ConnectionPanel(service)

    if CONNECTION_AISSTREAM not in INTERNET_DEPENDENT_CONNECTIONS:
        failures.append("AISStream not marked internet-dependent")
    if CONNECTION_API not in INTERNET_DEPENDENT_CONNECTIONS:
        failures.append("API not marked internet-dependent")

    # Simulate configured + live AISStream without waiting for prefs/provider.
    panel._aisstream_configured = staticmethod(lambda: True)  # noqa: SLF001
    panel._ais_live = "connected"  # noqa: SLF001
    set_internet_online(True)
    panel._refresh_aisstream_status(emit_notice=False)  # noqa: SLF001
    if panel._statuses[CONNECTION_AISSTREAM] != STATUS_WORKING:  # noqa: SLF001
        failures.append("AISStream should be green while internet+ws up")

    # Internet drop → immediate red for AISStream (visual only).
    open_before = set(service._open)  # noqa: SLF001
    set_internet_online(False)
    panel._set_status(CONNECTION_INTERNET, STATUS_NOT_WORKING, emit_notice=True)
    panel._refresh_internet_dependent_visuals()  # noqa: SLF001

    if panel._statuses[CONNECTION_AISSTREAM] != STATUS_NOT_WORKING:  # noqa: SLF001
        failures.append("AISStream must go red immediately when Internet drops")
    if panel._real_statuses.get(CONNECTION_AISSTREAM) != STATUS_WORKING:  # noqa: SLF001
        failures.append("AISStream real status must stay working until ws dies")
    if CONNECTION_AISSTREAM in service._open and CONNECTION_AISSTREAM not in open_before:
        failures.append("must not fire false AISStream lost notice on Internet drop")
    if CONNECTION_INTERNET not in service._open:
        failures.append("Internet lost notice should still fire")

    # Close internet dialog so restore path is clean
    for dlg in list(service._open.values()):
        dlg.accept()

    # Internet restore → AISStream stays red until real ws reconnect (still offline).
    panel._ais_live = "offline"  # noqa: SLF001
    panel._real_statuses[CONNECTION_AISSTREAM] = STATUS_NOT_WORKING  # noqa: SLF001
    panel._statuses[CONNECTION_AISSTREAM] = STATUS_NOT_WORKING  # noqa: SLF001
    set_internet_online(True)
    panel._set_status(CONNECTION_INTERNET, STATUS_WORKING, emit_notice=True)
    panel._refresh_internet_dependent_visuals()  # noqa: SLF001
    if panel._statuses[CONNECTION_AISSTREAM] != STATUS_NOT_WORKING:  # noqa: SLF001
        failures.append("AISStream must stay red until websocket reconnects")
    if CONNECTION_AISSTREAM in service._open:
        failures.append("must not fire false AISStream restored on Internet restore")

    # Real websocket reconnect → green + restored notice (after prior working).
    panel._seen_working[CONNECTION_AISSTREAM] = True  # noqa: SLF001
    panel.on_ais_status("connected")
    if panel._statuses[CONNECTION_AISSTREAM] != STATUS_WORKING:  # noqa: SLF001
        failures.append("AISStream green only after real connected")
    if CONNECTION_AISSTREAM not in service._open:
        failures.append("AISStream restored notice should follow real reconnect")

    # Poll path: probe offline triggers dependent refresh
    for dlg in list(service._open.values()):
        dlg.accept()
    panel._ais_live = "connected"  # noqa: SLF001
    set_internet_online(True)
    panel._refresh_aisstream_status(emit_notice=False)  # noqa: SLF001
    with patch.object(ConnectionPanel, "_probe_internet", return_value=False):
        panel._poll_internet()  # noqa: SLF001
    if panel._statuses[CONNECTION_INTERNET] != STATUS_NOT_WORKING:  # noqa: SLF001
        failures.append("Internet poll offline → red")
    if panel._statuses[CONNECTION_AISSTREAM] != STATUS_NOT_WORKING:  # noqa: SLF001
        failures.append("Internet poll offline → AISStream red immediately")

    if failures:
        print("SAVE-236 FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("SAVE-236 smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
