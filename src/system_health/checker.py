# ============================================================================
# Project X
# System Health Checker
# ============================================================================

from __future__ import annotations

import platform
import socket
from pathlib import Path

from ais import ais_manager
from ais.providers import normalize_provider_type
from ais.providers.provider import AISProviderType
from camera import camera_manager
from engines.ais.ais_catcher_launcher import is_port_open
from engines.camera.diagnostics import camera_diagnostics_engine
from i18n import language_manager
from logbook import logbook_manager
from observation import observation_manager
from preferences import preferences_manager
from rtl.aiscatcher_status import get_aiscatcher_status
from rtl.device_detector import detect_rtl_device
from rtl import rtl_manager
from system_health.subsystem_status import (
    SubsystemAction,
    SubsystemHealth,
    SubsystemState,
    SystemHealthReport,
)
from version import PROJECT_VERSION

_MAP_HTML = (
    Path(__file__).resolve().parents[1] / "resources" / "map" / "map.html"
)


class SystemHealthChecker:

    def __init__(self, hybrid_engine=None):

        self._hybrid_engine = hybrid_engine

    def attach_hybrid_engine(self, hybrid_engine) -> None:

        self._hybrid_engine = hybrid_engine

    def run_full_check(self, *, run_live_tests: bool = False) -> SystemHealthReport:

        checks = [
            self.check_internet(run_live_test=run_live_tests),
            self.check_ais_provider(),
            self.check_aisstream_api(run_live_test=run_live_tests),
            self.check_observation_point(),
            self.check_camera_framework(run_live_test=run_live_tests),
            self.check_rtl_sdr(),
            self.check_ais_catcher(),
            self.check_hybrid_mode(),
            self.check_map_engine(),
            self.check_logbook(),
            self.check_translations(),
            self.check_configuration(),
        ]

        return SystemHealthReport.from_subsystems(checks)

    def check_internet(self, *, run_live_test: bool = False) -> SubsystemHealth:

        if not run_live_test:
            return SubsystemHealth(
                subsystem_key="Internet",
                state=SubsystemState.NOT_CONFIGURED,
                message_key="Run a full system check to test internet connectivity.",
                action=SubsystemAction.TEST,
            )

        try:
            socket.create_connection(("1.1.1.1", 443), timeout=4.0)
        except OSError:
            return SubsystemHealth(
                subsystem_key="Internet",
                state=SubsystemState.ERROR,
                message_key="No Internet connection.",
                action=SubsystemAction.TEST,
            )

        return SubsystemHealth(
            subsystem_key="Internet",
            state=SubsystemState.WORKING,
            message_key="Internet connection is available.",
            action=SubsystemAction.TEST,
        )

    def check_ais_provider(self) -> SubsystemHealth:

        preferences = preferences_manager.get()
        provider = normalize_provider_type(preferences.ais_provider)

        if provider == AISProviderType.LATER:
            return SubsystemHealth(
                subsystem_key="AIS Provider",
                state=SubsystemState.NOT_CONFIGURED,
                message_key="AIS source is not configured yet.",
                action=SubsystemAction.CONFIGURE,
            )

        if not preferences.ais_configured:
            return SubsystemHealth(
                subsystem_key="AIS Provider",
                state=SubsystemState.WARNING,
                message_key="AIS provider selected but not fully configured.",
                action=SubsystemAction.CONFIGURE,
            )

        if ais_manager.is_connected():
            return SubsystemHealth(
                subsystem_key="AIS Provider",
                state=SubsystemState.WORKING,
                message_key="AIS provider is configured and connected.",
                detail=ais_manager.provider_name(),
                action=SubsystemAction.TEST,
            )

        return SubsystemHealth(
            subsystem_key="AIS Provider",
            state=SubsystemState.WARNING,
            message_key="AIS provider is configured but not connected.",
            detail=ais_manager.provider_name(),
            action=SubsystemAction.TEST,
        )

    def check_aisstream_api(
        self,
        *,
        run_live_test: bool = False,
    ) -> SubsystemHealth:

        preferences = preferences_manager.get()
        provider = normalize_provider_type(preferences.ais_provider)

        if provider not in (
            AISProviderType.AISSTREAM,
            AISProviderType.HYBRID,
        ):
            return SubsystemHealth(
                subsystem_key="AISStream API",
                state=SubsystemState.NOT_CONFIGURED,
                message_key="AISStream is not the active AIS provider.",
                action=SubsystemAction.CONFIGURE,
            )

        api_key = str(preferences.aisstream_api_key or "").strip()

        if not api_key:
            return SubsystemHealth(
                subsystem_key="AISStream API",
                state=SubsystemState.ERROR,
                message_key="Please paste your API key.",
                action=SubsystemAction.CONFIGURE,
            )

        if not run_live_test:
            return SubsystemHealth(
                subsystem_key="AISStream API",
                state=SubsystemState.WORKING,
                message_key="AISStream API key is saved.",
                action=SubsystemAction.TEST,
            )

        result = ais_manager.test_configuration(
            provider_type="aisstream",
            api_key=api_key,
        )

        if result.success:
            return SubsystemHealth(
                subsystem_key="AISStream API",
                state=SubsystemState.WORKING,
                message_key="Connection successful",
                action=SubsystemAction.TEST,
            )

        message_key = result.message if result.message else "AISStream unavailable."

        return SubsystemHealth(
            subsystem_key="AISStream API",
            state=SubsystemState.ERROR,
            message_key=message_key,
            action=SubsystemAction.CONFIGURE,
        )

    def check_observation_point(self) -> SubsystemHealth:

        active = observation_manager.active()

        if active is None:
            points = observation_manager.all()

            if not points:
                return SubsystemHealth(
                    subsystem_key="Observation Point",
                    state=SubsystemState.NOT_CONFIGURED,
                    message_key="No observation point",
                    action=SubsystemAction.OPEN_DASHBOARD,
                )

            return SubsystemHealth(
                subsystem_key="Observation Point",
                state=SubsystemState.WARNING,
                message_key="Observation points exist but none is active.",
                action=SubsystemAction.OPEN_DASHBOARD,
            )

        return SubsystemHealth(
            subsystem_key="Observation Point",
            state=SubsystemState.WORKING,
            message_key="Observation point '{name}' is active.",
            message_args={"name": active.name},
            action=SubsystemAction.OPEN_DASHBOARD,
        )

    def check_camera_framework(
        self,
        *,
        run_live_test: bool = False,
    ) -> SubsystemHealth:

        try:
            camera_count = len(camera_manager.all())
        except OSError:
            return SubsystemHealth(
                subsystem_key="Camera Framework",
                state=SubsystemState.ERROR,
                message_key="Camera framework is unavailable.",
                action=SubsystemAction.DIAGNOSTICS,
            )

        if camera_count == 0:
            return SubsystemHealth(
                subsystem_key="Camera Framework",
                state=SubsystemState.NOT_CONFIGURED,
                message_key="No cameras",
                action=SubsystemAction.OPEN_DASHBOARD,
            )

        if not run_live_test:
            return SubsystemHealth(
                subsystem_key="Camera Framework",
                state=SubsystemState.WORKING,
                message_key="Managing {count} camera(s).",
                message_args={"count": camera_count},
                action=SubsystemAction.DIAGNOSTICS,
            )

        try:
            reports = camera_diagnostics_engine.diagnose_all()
        except OSError:
            return SubsystemHealth(
                subsystem_key="Camera Framework",
                state=SubsystemState.ERROR,
                message_key="Camera diagnostics could not be completed.",
                action=SubsystemAction.DIAGNOSTICS,
            )

        error_count = sum(len(report.errors) for report in reports)

        if error_count:
            return SubsystemHealth(
                subsystem_key="Camera Framework",
                state=SubsystemState.ERROR,
                message_key="Camera diagnostics found {count} error(s).",
                message_args={"count": error_count},
                action=SubsystemAction.DIAGNOSTICS,
            )

        warning_count = sum(len(report.warnings) for report in reports)

        if warning_count:
            return SubsystemHealth(
                subsystem_key="Camera Framework",
                state=SubsystemState.WARNING,
                message_key="Camera diagnostics found {count} warning(s).",
                message_args={"count": warning_count},
                action=SubsystemAction.DIAGNOSTICS,
            )

        return SubsystemHealth(
            subsystem_key="Camera Framework",
            state=SubsystemState.WORKING,
            message_key="All {count} camera(s) passed diagnostics.",
            message_args={"count": len(reports)},
            action=SubsystemAction.DIAGNOSTICS,
        )

    def check_rtl_sdr(self) -> SubsystemHealth:

        preferences = preferences_manager.get()

        if not preferences.rtl_sdr_configured:
            return SubsystemHealth(
                subsystem_key="RTL-SDR",
                state=SubsystemState.NOT_CONFIGURED,
                message_key="Not configured",
                action=SubsystemAction.SETUP,
            )

        status = rtl_manager.status_label()

        if status == "connected":
            return SubsystemHealth(
                subsystem_key="RTL-SDR",
                state=SubsystemState.WORKING,
                message_key="Connected",
                action=SubsystemAction.DIAGNOSTICS,
            )

        device = detect_rtl_device()

        if not device.detected:
            return SubsystemHealth(
                subsystem_key="RTL-SDR",
                state=SubsystemState.ERROR,
                message_key="Receiver not detected",
                action=SubsystemAction.SETUP,
            )

        return SubsystemHealth(
            subsystem_key="RTL-SDR",
            state=SubsystemState.WARNING,
            message_key="Configured but not connected.",
            action=SubsystemAction.DIAGNOSTICS,
        )

    def check_ais_catcher(self) -> SubsystemHealth:

        preferences = preferences_manager.get()
        status = get_aiscatcher_status(
            host=preferences.ais_local_host,
            port=preferences.ais_local_port,
        )

        if not status.installed:
            return SubsystemHealth(
                subsystem_key="AIS-Catcher",
                state=SubsystemState.NOT_CONFIGURED,
                message_key="Not installed",
                action=SubsystemAction.SETUP,
            )

        if status.running:
            return SubsystemHealth(
                subsystem_key="AIS-Catcher",
                state=SubsystemState.WORKING,
                message_key="AIS-Catcher is running on port {port}",
                message_args={"port": status.port},
                action=SubsystemAction.DIAGNOSTICS,
            )

        if is_port_open(status.host, status.port, timeout=1.0):
            return SubsystemHealth(
                subsystem_key="AIS-Catcher",
                state=SubsystemState.WORKING,
                message_key="AIS-Catcher port {port} is reachable.",
                message_args={"port": status.port},
                action=SubsystemAction.DIAGNOSTICS,
            )

        return SubsystemHealth(
            subsystem_key="AIS-Catcher",
            state=SubsystemState.ERROR,
            message_key="AIS-Catcher could not be started.",
            action=SubsystemAction.SETUP,
        )

    def check_hybrid_mode(self) -> SubsystemHealth:

        preferences = preferences_manager.get()
        provider = normalize_provider_type(preferences.ais_provider)

        if provider != AISProviderType.HYBRID:
            return SubsystemHealth(
                subsystem_key="Hybrid Mode",
                state=SubsystemState.NOT_CONFIGURED,
                message_key="Hybrid mode is not selected as the AIS provider.",
                action=SubsystemAction.CONFIGURE,
            )

        if not preferences.ais_configured:
            return SubsystemHealth(
                subsystem_key="Hybrid Mode",
                state=SubsystemState.WARNING,
                message_key="Hybrid mode requires AIS configuration.",
                action=SubsystemAction.CONFIGURE,
            )

        engine = self._hybrid_engine

        if engine is None:
            return SubsystemHealth(
                subsystem_key="Hybrid Mode",
                state=SubsystemState.WARNING,
                message_key="Hybrid engine is not available.",
                action=SubsystemAction.CONFIGURE,
            )

        if getattr(engine, "running", False):
            return SubsystemHealth(
                subsystem_key="Hybrid Mode",
                state=SubsystemState.WORKING,
                message_key="Hybrid mode is now available.",
                action=SubsystemAction.TEST,
            )

        return SubsystemHealth(
            subsystem_key="Hybrid Mode",
            state=SubsystemState.ERROR,
            message_key="Hybrid engine is not running.",
            action=SubsystemAction.DIAGNOSTICS,
        )

    def check_map_engine(self) -> SubsystemHealth:

        if not _MAP_HTML.is_file():
            return SubsystemHealth(
                subsystem_key="Map Engine",
                state=SubsystemState.ERROR,
                message_key="Map resources are missing.",
                action=SubsystemAction.OPEN_MAP,
            )

        return SubsystemHealth(
            subsystem_key="Map Engine",
            state=SubsystemState.WORKING,
            message_key="Map engine resources are loaded.",
            action=SubsystemAction.OPEN_MAP,
        )

    def check_logbook(self) -> SubsystemHealth:

        base_dir = logbook_manager.base_dir

        try:
            base_dir.mkdir(parents=True, exist_ok=True)
            test_file = base_dir / ".health_check"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
        except OSError:
            return SubsystemHealth(
                subsystem_key="Logbook",
                state=SubsystemState.ERROR,
                message_key="Logbook storage is not writable.",
                action=SubsystemAction.OPEN_DASHBOARD,
            )

        return SubsystemHealth(
            subsystem_key="Logbook",
            state=SubsystemState.WORKING,
            message_key="Logbook storage is ready.",
            action=SubsystemAction.OPEN_DASHBOARD,
        )

    def check_translations(self) -> SubsystemHealth:

        catalog = language_manager.translations()

        if not catalog:
            return SubsystemHealth(
                subsystem_key="Translations",
                state=SubsystemState.ERROR,
                message_key="Translation catalog could not be loaded.",
                action=SubsystemAction.OPEN_SETTINGS,
            )

        return SubsystemHealth(
            subsystem_key="Translations",
            state=SubsystemState.WORKING,
            message_key="Language '{language}' loaded ({count} strings).",
            message_args={
                "language": language_manager.current_language,
                "count": len(catalog),
            },
            action=SubsystemAction.OPEN_SETTINGS,
        )

    def check_configuration(self) -> SubsystemHealth:

        preferences = preferences_manager.get()

        if preferences.version < 1:
            return SubsystemHealth(
                subsystem_key="Configuration",
                state=SubsystemState.ERROR,
                message_key="Configuration file is invalid.",
                action=SubsystemAction.OPEN_SETTINGS,
            )

        return SubsystemHealth(
            subsystem_key="Configuration",
            state=SubsystemState.WORKING,
            message_key="Preferences loaded (schema v{version}).",
            message_args={"version": preferences.version},
            action=SubsystemAction.OPEN_SETTINGS,
        )


system_health_checker = SystemHealthChecker()
