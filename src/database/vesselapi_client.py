# ============================================================================
# Project X
# VesselAPI HTTP client (Phase A)
# ============================================================================

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

VESSELAPI_BASE_URL = "https://api.vesselapi.com/v1"
DEFAULT_TIMEOUT_S = 15.0
# Phase A temporary key location (never logged / never committed).
PHASE_A_KEY_FILE = Path.home() / "Asztal" / "vesselapi"


@dataclass(frozen=True)
class VesselApiVessel:
    """Normalized subset of VesselAPI vessel payload used for enrichment."""

    mmsi: int
    name: str = ""
    callsign: str = ""
    imo: str = ""
    ship_type: str = ""
    country: str = ""
    country_code: str = ""
    operating_status: str = ""
    length_m: float | None = None
    width_m: float | None = None
    # Draught intentionally omitted from trusted Phase A mapping.


@dataclass(frozen=True)
class VesselApiResult:
    ok: bool
    vessel: VesselApiVessel | None = None
    error: str = ""
    status_code: int | None = None


def load_api_key(*, key_file: Path | None = None) -> str:
    """Load Bearer token from Phase A key file. Never logs the value."""

    path = Path(key_file or PHASE_A_KEY_FILE)
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning("VesselAPI key file unreadable (%s)", type(exc).__name__)
        return ""
    if not text:
        logger.warning("VesselAPI key file is empty")
        return ""
    # Allow "KEY=..." style without logging content.
    if "=" in text and not text.startswith("ey") and " " not in text.split("=", 1)[0]:
        _name, _, value = text.partition("=")
        text = value.strip()
    return text


def resolve_api_key(*, key_file: Path | None = None) -> str:
    """Preferences key first; Phase A file is compatibility fallback only."""

    try:
        from preferences.preferences_manager import preferences_manager

        prefs_key = str(preferences_manager.get().vesselapi_api_key or "").strip()
        if prefs_key:
            return prefs_key
    except Exception:
        logger.debug("VesselAPI preferences key unavailable", exc_info=True)

    return load_api_key(key_file=key_file)


def validate_api_key(
    api_key: str,
    *,
    test_mmsi: int = 243042880,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> VesselApiResult:
    """Live GET probe for Settings Test Connection. Never logs the key."""

    key = (api_key or "").strip()
    if not key:
        return VesselApiResult(ok=False, error="missing_api_key")
    return fetch_vessel_by_mmsi(test_mmsi, api_key=key, timeout_s=timeout_s)


def _optional_float(value: Any) -> float | None:

    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return number


def _safe_text(value: Any) -> str:

    if value is None:
        return ""
    return str(value).strip()


def parse_vessel_payload(payload: dict[str, Any]) -> VesselApiVessel | None:
    """Extract enrichment fields; draught is intentionally ignored in Phase A."""

    if not isinstance(payload, dict):
        return None

    vessel = payload.get("vessel")
    if not isinstance(vessel, dict):
        # Some responses may be the vessel object itself.
        if "mmsi" in payload:
            vessel = payload
        else:
            return None

    try:
        mmsi = int(vessel.get("mmsi"))
    except (TypeError, ValueError):
        return None
    if mmsi <= 0:
        return None

    vessel_type = _safe_text(vessel.get("vessel_type"))
    subtype = _safe_text(vessel.get("vessel_subtype"))
    if vessel_type.lower() in {"", "not available", "unknown", "n/a"}:
        ship_type = subtype
    elif subtype and subtype.lower() not in vessel_type.lower():
        ship_type = f"{vessel_type} / {subtype}"
    else:
        ship_type = vessel_type

    imo = _safe_text(vessel.get("imo") or vessel.get("IMO") or vessel.get("imo_number"))
    # Reject non-IMO placeholders.
    if imo.lower() in {"0", "none", "null", "n/a", "not available"}:
        imo = ""

    return VesselApiVessel(
        mmsi=mmsi,
        name=_safe_text(vessel.get("name") or vessel.get("name_ais")),
        callsign=_safe_text(vessel.get("call_sign") or vessel.get("callsign")),
        imo=imo,
        ship_type=ship_type,
        country=_safe_text(vessel.get("country")),
        country_code=_safe_text(vessel.get("country_code")).upper(),
        operating_status=_safe_text(vessel.get("operating_status")),
        length_m=_optional_float(vessel.get("length")),
        width_m=_optional_float(vessel.get("breadth") or vessel.get("width")),
    )


def fetch_vessel_by_mmsi(
    mmsi: int,
    *,
    api_key: str,
    base_url: str = VESSELAPI_BASE_URL,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> VesselApiResult:
    """GET /vessel/{mmsi}?filter.idType=mmsi with Bearer auth."""

    key = (api_key or "").strip()
    if not key:
        return VesselApiResult(ok=False, error="missing_api_key")

    try:
        mmsi_int = int(mmsi)
    except (TypeError, ValueError):
        return VesselApiResult(ok=False, error="invalid_mmsi")
    if mmsi_int <= 0:
        return VesselApiResult(ok=False, error="invalid_mmsi")

    url = f"{base_url.rstrip('/')}/vessel/{mmsi_int}?filter.idType=mmsi"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": "ProjectX-VesselAPI/phase-a",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=float(timeout_s)) as response:
            status = int(getattr(response, "status", 200) or 200)
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        # Do not include body (may echo secrets in some gateways).
        logger.warning(
            "VesselAPI HTTP error for MMSI %s: status=%s",
            mmsi_int,
            exc.code,
        )
        return VesselApiResult(
            ok=False,
            error=f"http_{exc.code}",
            status_code=int(exc.code),
        )
    except urllib.error.URLError as exc:
        logger.warning(
            "VesselAPI network error for MMSI %s: %s",
            mmsi_int,
            type(exc.reason).__name__ if exc.reason else type(exc).__name__,
        )
        return VesselApiResult(ok=False, error="network_error")
    except TimeoutError:
        logger.warning("VesselAPI timeout for MMSI %s", mmsi_int)
        return VesselApiResult(ok=False, error="timeout")
    except OSError as exc:
        logger.warning(
            "VesselAPI OS error for MMSI %s: %s",
            mmsi_int,
            type(exc).__name__,
        )
        return VesselApiResult(ok=False, error="os_error")

    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        logger.warning("VesselAPI invalid JSON for MMSI %s", mmsi_int)
        return VesselApiResult(ok=False, error="invalid_json", status_code=status)

    if not isinstance(payload, dict):
        return VesselApiResult(ok=False, error="invalid_payload", status_code=status)

    if payload.get("error") or payload.get("errors"):
        logger.warning("VesselAPI error payload for MMSI %s", mmsi_int)
        return VesselApiResult(ok=False, error="api_error", status_code=status)

    vessel = parse_vessel_payload(payload)
    if vessel is None:
        return VesselApiResult(ok=False, error="missing_vessel", status_code=status)

    return VesselApiResult(ok=True, vessel=vessel, status_code=status)
