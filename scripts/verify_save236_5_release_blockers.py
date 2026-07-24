#!/usr/bin/env python3
# SAVE-236.5 — release blocker stabilization smoke
from __future__ import annotations

import inspect
import os
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtWidgets import QApplication

from ais.ais_manager import ais_manager
from ais.providers import AISProviderType
from ais.user_provider_service import provider_display_status
from connectivity.internet_state import set_internet_online
from engines.rtl import hybrid_engine as hybrid_engine_mod
from i18n import language_manager
from preferences import preferences_manager
from preferences.preferences import Preferences


def main() -> int:
    failures: list[str] = []
    QApplication.instance() or QApplication([])

    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    preferences_manager._path = Path(tmp.name)  # noqa: SLF001
    preferences_manager.save(
        replace(
            Preferences.defaults(),
            aisstream_api_key="test-key",
            ais_configured=True,
            rtl_sdr_configured=True,
            ais_local_host="127.0.0.1",
            ais_local_port=19999,
            ais_enabled_providers=["aisstream", "local"],
        )
    )

    language_manager.set_language("hu")
    set_internet_online(True)

    # 1) Providers panel mirrors Internet master for AISStream
    ais_manager._ais_status = "connected"  # noqa: SLF001
    status = provider_display_status(AISProviderType.AISSTREAM.value)
    if status.icon != "🟢" or "Kapcsolódva" not in status.text:
        failures.append(f"online+connected expected green Kapcsolódva, got {status}")

    set_internet_online(False)
    status = provider_display_status(AISProviderType.AISSTREAM.value)
    if status.icon != "🔴":
        failures.append(f"internet down must force AISStream red, got {status}")

    set_internet_online(True)
    ais_manager._ais_status = "offline"  # noqa: SLF001
    status = provider_display_status(AISProviderType.AISSTREAM.value)
    if status.icon != "🔴" or "Csatlakozás" not in status.text:
        failures.append(f"reconnecting must show Csatlakozás..., got {status}")

    # 2) Auth error durable UX
    ais_manager._ais_status = "auth_error"  # noqa: SLF001
    status = provider_display_status(AISProviderType.AISSTREAM.value)
    if status.icon != "🔴" or "Hitelesítési hiba" not in status.text:
        failures.append(f"auth_error display, got {status}")
    if "API kulcs" not in status.text:
        failures.append(f"auth_error message missing detail, got {status}")

    worker_src = inspect.getsource(hybrid_engine_mod.HybridEngine.aisstream_worker)
    if "auth_error" not in worker_src or "401" not in worker_src:
        failures.append("HybridEngine must stop reconnect on 401/403 auth_error")

    # 3) RTL endpoint from preferences (not hardcoded 10110)
    engine = hybrid_engine_mod.HybridEngine.__new__(hybrid_engine_mod.HybridEngine)
    host, port = hybrid_engine_mod.HybridEngine._rtl_endpoint(engine)
    if host != "127.0.0.1" or port != 19999:
        failures.append(f"RTL endpoint should use prefs, got {host}:{port}")

    rtl_src = inspect.getsource(hybrid_engine_mod.HybridEngine.rtl_worker)
    if "connect(AIS_CATCHER_HOST" in rtl_src or "is_port_open(AIS_CATCHER_HOST" in rtl_src:
        failures.append("rtl_worker still hardcodes AIS_CATCHER_HOST/PORT")
    if "_rtl_endpoint" not in rtl_src:
        failures.append("rtl_worker must call _rtl_endpoint()")

    if failures:
        print("SAVE-236.5 FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("SAVE-236.5 smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
