# ============================================================================
# Project X
# RTL-SDR Manager
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from config.aiscatcher import AIS_CATCHER_HOST, AIS_CATCHER_PORT
from engines.ais.ais_catcher_launcher import ensure_ais_catcher_ready, is_port_open
from events import eventbus
from preferences import preferences_manager
from rtl.aiscatcher_status import get_aiscatcher_status
from rtl.device_detector import RTLDeviceInfo, detect_rtl_device
from rtl.diagnostics import RTLDiagnosticsReport, run_rtl_diagnostics
from rtl.reception_monitor import ReceptionTestResult, count_rtl_ships, run_reception_test


@dataclass(frozen=True)
class RTLReceptionStats:

    message_count: int = 0
    ships_detected: int = 0
    signal_quality: str = "none"
    last_message: str = ""


class RTLManager:

    def __init__(self):

        self._lock = Lock()
        self._rtl_status = "offline"
        self._message_count = 0
        self._last_message = ""
        self._signal_quality = "none"
        self._started = False

    def start(self) -> None:

        if self._started:
            return

        eventbus.subscribe("rtl.status", self._on_rtl_status)
        eventbus.subscribe("ship.updated", self._on_ship_updated)
        self._started = True

    def rtl_connection_status(self) -> str:

        with self._lock:
            return self._rtl_status

    def is_configured(self) -> bool:

        preferences = preferences_manager.get()
        return bool(preferences.rtl_sdr_configured)

    def is_connected(self) -> bool:

        with self._lock:
            return self._rtl_status == "connected"

    def status_label(self) -> str:

        if self.is_connected():
            return "connected"

        if self.is_configured():
            return "configured"

        return "not_configured"

    def reception_stats(self) -> RTLReceptionStats:

        with self._lock:
            return RTLReceptionStats(
                message_count=self._message_count,
                ships_detected=count_rtl_ships(),
                signal_quality=self._signal_quality,
                last_message=self._last_message,
            )

    def detect_device(self) -> RTLDeviceInfo:

        return detect_rtl_device()

    def ais_catcher_status(self):

        preferences = preferences_manager.get()
        return get_aiscatcher_status(
            host=preferences.ais_local_host,
            port=preferences.ais_local_port,
        )

    def test_tcp_connection(self) -> bool:

        preferences = preferences_manager.get()
        return is_port_open(
            preferences.ais_local_host or AIS_CATCHER_HOST,
            int(preferences.ais_local_port or AIS_CATCHER_PORT),
            timeout=2.0,
        )

    def test_reception(self, duration_seconds: float = 10.0) -> ReceptionTestResult:

        preferences = preferences_manager.get()
        result = run_reception_test(
            host=preferences.ais_local_host,
            port=preferences.ais_local_port,
            duration_seconds=duration_seconds,
        )

        if result.success:
            with self._lock:
                self._message_count = max(self._message_count, result.message_count)
                self._signal_quality = result.signal_quality

                if result.last_message:
                    self._last_message = result.last_message

        return result

    def ensure_ais_catcher(self) -> bool:

        preferences = preferences_manager.get()

        if not preferences.rtl_auto_start_ais_catcher:
            return self.test_tcp_connection()

        return ensure_ais_catcher_ready()

    def run_diagnostics(self) -> RTLDiagnosticsReport:

        report = run_rtl_diagnostics()
        stats = self.reception_stats()

        return RTLDiagnosticsReport(
            device=report.device,
            ais_catcher_installed=report.ais_catcher_installed,
            ais_catcher_running=report.ais_catcher_running,
            tcp_connected=report.tcp_connected,
            signal_quality=stats.signal_quality,
            last_message=stats.last_message,
            message_count=stats.message_count,
            ships_detected=stats.ships_detected,
            host=report.host,
            port=report.port,
        )

    def mark_configured(self, *, owned: bool = True, setup_os: str = "") -> None:

        preferences_manager.set_rtl_configuration(
            owned=owned,
            configured=True,
            setup_os=setup_os,
        )

    def mark_internet_only(self) -> None:

        preferences_manager.set_rtl_configuration(
            owned=False,
            configured=False,
            setup_completed=True,
        )

    def _on_rtl_status(self, status: str = "", **kwargs) -> None:

        with self._lock:
            self._rtl_status = str(status or "offline")

    def _on_ship_updated(self, ship=None, **kwargs) -> None:

        if ship is None:
            return

        source = str(getattr(ship, "source", "")).upper()
        rtl_visible = bool(getattr(ship, "rtl_visible", False))

        if source != "RTL" and not rtl_visible:
            return

        with self._lock:
            self._message_count += 1
            self._last_message = (
                f"{getattr(ship, 'name', '') or getattr(ship, 'mmsi', '')} "
                f"@ {getattr(ship, 'lat', '')}, {getattr(ship, 'lon', '')}"
            ).strip()

            if self._message_count >= 20:
                self._signal_quality = "good"
            elif self._message_count >= 5:
                self._signal_quality = "fair"
            elif self._message_count >= 1:
                self._signal_quality = "weak"


rtl_manager = RTLManager()
