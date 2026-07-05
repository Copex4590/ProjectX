# ============================================================================
# Project X
# Diagnostic Report
# ============================================================================

from __future__ import annotations

import platform
import sys
from datetime import datetime

from PySide6 import __version__ as QT_VERSION

from ais import ais_manager
from observation import observation_manager
from preferences import preferences_manager
from system_health.checker import SystemHealthChecker
from system_health.subsystem_status import SubsystemState
from version import PROJECT_BUILD, PROJECT_VERSION


def _format_message(item) -> str:

    message = item.message_key

    if item.message_args:
        try:
            message = message.format(**item.message_args)
        except (KeyError, ValueError):
            pass

    if item.detail:
        message = f"{message} ({item.detail})"

    return message


def generate_diagnostic_report(
    *,
    hybrid_engine=None,
    run_live_tests: bool = True,
) -> str:

    checker = SystemHealthChecker(hybrid_engine=hybrid_engine)
    report = checker.run_full_check(run_live_tests=run_live_tests)
    preferences = preferences_manager.get()
    active = observation_manager.active()
    lines: list[str] = []

    lines.append("Project X Diagnostic Report")
    lines.append("=" * 40)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Version: {PROJECT_VERSION}")
    lines.append(f"Build: {PROJECT_BUILD}")
    lines.append(f"Operating system: {platform.system()} {platform.release()}")
    lines.append(f"Qt version: {QT_VERSION}")

    if PROJECT_BUILD == "dev":
        lines.append(f"Python version: {sys.version.split()[0]}")

    lines.append("")
    lines.append("Subsystem Status")
    lines.append("-" * 40)

    for item in report.subsystems:
        lines.append(f"{item.subsystem_key}: {item.state.value}")
        lines.append(f"  {_format_message(item)}")

    lines.append("")
    lines.append("AIS Status")
    lines.append("-" * 40)
    lines.append(f"Provider: {preferences.ais_provider}")
    lines.append(f"Configured: {preferences.ais_configured}")
    lines.append(f"AIS connection: {ais_manager.ais_connection_status()}")
    lines.append(f"RTL connection: {ais_manager.rtl_connection_status()}")
    lines.append("API key: [redacted]")

    lines.append("")
    lines.append("RTL Status")
    lines.append("-" * 40)
    lines.append(f"RTL configured: {preferences.rtl_sdr_configured}")
    lines.append(f"Auto-start AIS-Catcher: {preferences.rtl_auto_start_ais_catcher}")
    lines.append(f"Local AIS host: {preferences.ais_local_host}")
    lines.append(f"Local AIS port: {preferences.ais_local_port}")

    lines.append("")
    lines.append("Observation Point")
    lines.append("-" * 40)

    if active is None:
        lines.append("Active point: none")
    else:
        lines.append(f"Active point: {active.name}")
        lines.append(f"Coordinates: {active.latitude:.5f}, {active.longitude:.5f}")

    lines.append("")
    lines.append("Camera Status")
    lines.append("-" * 40)

    try:
        from camera import camera_manager

        lines.append(f"Cameras loaded: {len(camera_manager.all())}")
    except OSError:
        lines.append("Cameras loaded: unavailable")

    lines.append("")
    lines.append("Logbook Status")
    lines.append("-" * 40)

    try:
        from logbook import logbook_manager

        lines.append(f"Storage path: {logbook_manager.base_dir}")
    except OSError:
        lines.append("Storage path: unavailable")

    lines.append("")
    lines.append("Configuration Summary")
    lines.append("-" * 40)
    lines.append(f"Language: {preferences.language}")
    lines.append(f"Vessel card layout: {preferences.vessel_card_layout}")
    lines.append(f"First run completed: {preferences.first_run_completed}")
    lines.append(f"RTL setup completed: {preferences.rtl_setup_completed}")

    lines.append("")
    lines.append("Summary")
    lines.append("-" * 40)

    if report.has_errors:
        lines.append("Overall: errors detected")
    elif report.has_warnings:
        lines.append("Overall: warnings detected")
    else:
        lines.append("Overall: all checked subsystems operational")

    error_count = sum(
        1 for item in report.subsystems if item.state == SubsystemState.ERROR
    )
    warning_count = sum(
        1 for item in report.subsystems if item.state == SubsystemState.WARNING
    )
    lines.append(f"Errors: {error_count}")
    lines.append(f"Warnings: {warning_count}")

    return "\n".join(lines) + "\n"
