# ============================================================================
# Project X
# RTL-SDR Diagnostics
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass

from config.aiscatcher import AIS_CATCHER_HOST, AIS_CATCHER_PORT
from engines.ais.ais_catcher_launcher import is_port_open
from preferences import preferences_manager
from rtl.aiscatcher_status import get_aiscatcher_status
from rtl.device_detector import RTLDeviceInfo, detect_rtl_device
from rtl.reception_monitor import count_rtl_ships


@dataclass(frozen=True)
class RTLDiagnosticsReport:

    device: RTLDeviceInfo
    ais_catcher_installed: bool
    ais_catcher_running: bool
    tcp_connected: bool
    signal_quality: str
    last_message: str
    message_count: int
    ships_detected: int
    host: str
    port: int


def run_rtl_diagnostics() -> RTLDiagnosticsReport:

    preferences = preferences_manager.get()
    host = preferences.ais_local_host or AIS_CATCHER_HOST
    port = int(preferences.ais_local_port or AIS_CATCHER_PORT)

    device = detect_rtl_device()
    catcher = get_aiscatcher_status(host=host, port=port)
    tcp_connected = is_port_open(host, port, timeout=1.0)

    return RTLDiagnosticsReport(
        device=device,
        ais_catcher_installed=catcher.installed,
        ais_catcher_running=catcher.running,
        tcp_connected=tcp_connected,
        signal_quality=preferences_manager.get().ais_configured and "monitoring" or "none",
        last_message="",
        message_count=0,
        ships_detected=count_rtl_ships(),
        host=host,
        port=port,
    )
