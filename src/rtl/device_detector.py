# ============================================================================
# Project X
# RTL-SDR Device Detection
# ============================================================================

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class RTLDeviceInfo:

    detected: bool
    manufacturer: str = ""
    serial: str = ""
    tuner: str = ""
    sample_rate: str = ""
    source: str = ""


def _run_command(command: list[str], timeout: float = 8.0) -> str:

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""

    return (completed.stdout or "") + (completed.stderr or "")


def _parse_rtl_test_output(output: str) -> RTLDeviceInfo:

    if not output.strip():
        return RTLDeviceInfo(detected=False)

    lowered = output.lower()

    if "no supported devices found" in lowered:
        return RTLDeviceInfo(detected=False, source="rtl_test")

    manufacturer = _extract_field(output, r"Manufacturer:\s*(.+)")
    serial = _extract_field(output, r"Serial number:\s*(.+)")
    tuner = _extract_field(output, r"Tuner type:\s*(.+)")
    sample_rate = _extract_field(output, r"Sampling at:\s*(.+)")

    if not manufacturer and "realtek" in lowered:
        manufacturer = "Realtek"

    detected = bool(manufacturer or serial or tuner or "found" in lowered)

    return RTLDeviceInfo(
        detected=detected,
        manufacturer=manufacturer,
        serial=serial,
        tuner=tuner,
        sample_rate=sample_rate,
        source="rtl_test",
    )


def _extract_field(text: str, pattern: str) -> str:

    match = re.search(pattern, text, flags=re.IGNORECASE)

    if not match:
        return ""

    return match.group(1).strip()


def _detect_via_lsusb() -> RTLDeviceInfo:

    if shutil.which("lsusb") is None:
        return RTLDeviceInfo(detected=False)

    output = _run_command(["lsusb"])

    if not output:
        return RTLDeviceInfo(detected=False)

    for line in output.splitlines():
        lowered = line.lower()

        if "rtl" not in lowered and "2838" not in lowered and "realtek" not in lowered:
            continue

        return RTLDeviceInfo(
            detected=True,
            manufacturer="Realtek",
            serial="",
            tuner="",
            sample_rate="",
            source="lsusb",
        )

    return RTLDeviceInfo(detected=False)


def detect_rtl_device() -> RTLDeviceInfo:

    rtl_test = shutil.which("rtl_test")

    if rtl_test:
        output = _run_command([rtl_test, "-t"])
        result = _parse_rtl_test_output(output)

        if result.detected:
            return result

    return _detect_via_lsusb()
