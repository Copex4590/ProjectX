#!/usr/bin/env python3
# SAVE-236.6 — live RTL host/port reload on Save
from __future__ import annotations

import inspect
import os
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from events import eventbus
from engines.rtl.hybrid_engine import HybridEngine
from ais.user_provider_service import (
    save_aisstream_configuration,
    save_local_configuration,
)
from preferences import preferences_manager
from preferences.preferences import Preferences


def main() -> int:
    failures: list[str] = []

    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    preferences_manager._path = Path(tmp.name)  # noqa: SLF001
    preferences_manager.save(
        replace(
            Preferences.defaults(),
            rtl_sdr_configured=True,
            ais_local_host="127.0.0.1",
            ais_local_port=10110,
            ais_enabled_providers=["local"],
        )
    )

    # save_local_configuration must publish rtl.config.changed
    seen: list[str] = []

    def _on_changed(**_kwargs):
        seen.append("rtl.config.changed")

    eventbus.subscribe("rtl.config.changed", _on_changed)
    try:
        save_local_configuration(host="127.0.0.1", port=19999)
    finally:
        eventbus.unsubscribe("rtl.config.changed", _on_changed)

    prefs = preferences_manager.get()
    if prefs.ais_local_port != 19999:
        failures.append(f"port not saved, got {prefs.ais_local_port}")
    if "rtl.config.changed" not in seen:
        failures.append("save_local_configuration must publish rtl.config.changed")

    # request_rtl_reconnect disconnects and publishes offline
    engine = HybridEngine.__new__(HybridEngine)
    engine._rtl_reconnect_requested = False
    engine._rtl_client = MagicMock()
    statuses: list[str] = []

    def _on_status(status="", **_kwargs):
        statuses.append(status)

    eventbus.subscribe("rtl.status", _on_status)
    try:
        HybridEngine.request_rtl_reconnect(engine)
    finally:
        eventbus.unsubscribe("rtl.status", _on_status)

    if not engine._rtl_reconnect_requested:
        failures.append("reconnect flag not set")
    if engine._rtl_client is not None:
        failures.append("RTL client should be cleared")
    if "offline" not in statuses:
        failures.append("reconnect must publish rtl.status offline")

    # AISStream save path must NOT publish rtl.config.changed
    ais_src = inspect.getsource(save_aisstream_configuration)
    if "rtl.config.changed" in ais_src:
        failures.append("AISStream save must not publish rtl.config.changed")

    local_src = inspect.getsource(save_local_configuration)
    if "rtl.config.changed" not in local_src:
        failures.append("save_local_configuration source must publish rtl.config.changed")

    worker_src = inspect.getsource(HybridEngine.rtl_worker)
    if "_rtl_reconnect_requested" not in worker_src:
        failures.append("rtl_worker must honor _rtl_reconnect_requested")

    if failures:
        print("SAVE-236.6 FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("SAVE-236.6 smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
