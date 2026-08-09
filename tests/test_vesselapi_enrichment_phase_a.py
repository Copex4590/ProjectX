"""Phase A VesselAPI enrichment — unit + optional live tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from database.vessel_database import VesselDatabase
from database.vesselapi_client import (
    VesselApiResult,
    VesselApiVessel,
    load_api_key,
    parse_vessel_payload,
)
from database.vesselapi_provider import VesselAPIOnlineProvider
from models.vessel_record import VesselRecord


DE_VEERMAN = {
    "vessel": {
        "mmsi": 243042880,
        "call_sign": "HGD2880",
        "eni": "02321295",
        "name": "DE VEERMAN",
        "name_ais": "DE VEERMAN",
        "vessel_type": "Passenger",
        "vessel_subtype": "Passenger ship",
        "country": "Hungary",
        "country_code": "HU",
        "operating_status": "Active",
        "length": 38,
        "length_unit": "m",
        "breadth": 8,
        "breadth_unit": "m",
    }
}

PANNONIA = {
    "vessel": {
        "mmsi": 243070623,
        "call_sign": "HGFW",
        "eni": "08601505",
        "name": "PANNONIA",
        "name_ais": "PANNONIA",
        "vessel_type": "Not available",
        "country": "Hungary",
        "country_code": "HU",
        "operating_status": "Active",
        "length": 26,
        "length_unit": "m",
        "breadth": 7,
        "breadth_unit": "m",
        "draught_calculated_avg": 25.5,
        "draught_observed_max": 25.5,
    }
}


def test_parse_de_veerman_fields():
    vessel = parse_vessel_payload(DE_VEERMAN)
    assert vessel is not None
    assert vessel.mmsi == 243042880
    assert vessel.name == "DE VEERMAN"
    assert vessel.callsign == "HGD2880"
    assert vessel.country_code == "HU"
    assert vessel.length_m == 38
    assert vessel.width_m == 8
    assert "Passenger" in vessel.ship_type


def test_parse_pannonia_ignores_suspicious_draught_fields():
    vessel = parse_vessel_payload(PANNONIA)
    assert vessel is not None
    assert vessel.name == "PANNONIA"
    assert vessel.callsign == "HGFW"
    assert vessel.country_code == "HU"
    assert vessel.length_m == 26
    assert vessel.width_m == 7
    assert vessel.ship_type == ""  # Not available → empty
    assert not hasattr(vessel, "draught")


def test_fill_only_enrichment_and_no_draught_overwrite(tmp_path: Path):
    db_path = tmp_path / "vessels.db"
    db = VesselDatabase(db_path)
    # Pre-seed AIS/RTL draft that must not be replaced by VesselAPI 25.5
    db.upsert(
        VesselRecord(
            mmsi=243070623,
            name="",
            callsign="",
            draft=1.2,
            length=None,
            width=None,
        )
    )

    payloads = {
        243070623: PANNONIA,
        243042880: DE_VEERMAN,
    }

    def fake_fetch(mmsi, *, api_key, **kwargs):
        raw = payloads[int(mmsi)]
        vessel = parse_vessel_payload(raw)
        return VesselApiResult(ok=True, vessel=vessel, status_code=200)

    # Point provider at temp DB via monkeypatch of module singleton usage:
    import database.vesselapi_provider as provider_mod

    original_db = provider_mod.vessel_database
    provider_mod.vessel_database = db
    try:
        provider = VesselAPIOnlineProvider(
            enabled=True,
            fetch_fn=fake_fetch,
            key_file=tmp_path / "dummy.key",
        )
        (tmp_path / "dummy.key").write_text("test-key\n", encoding="utf-8")

        result = provider.enrich_mmsi(243070623, api_key="test-key", force=True)
        assert result.ok
        record = db.get(243070623)
        assert record is not None
        assert record.name == "PANNONIA"
        assert record.callsign == "HGFW"
        assert record.flag == "HU"
        assert record.length == 26
        assert record.width == 7
        assert record.draft == 1.2  # unchanged — no VesselAPI draught write
    finally:
        provider_mod.vessel_database = original_db


def test_does_not_overwrite_existing_ais_static_fields(tmp_path: Path):
    db_path = tmp_path / "vessels.db"
    db = VesselDatabase(db_path)
    db.upsert(
        VesselRecord(
            mmsi=243042880,
            name="AIS NAME",
            callsign="AISCS",
            flag="XX",
            length=99.0,
            width=11.0,
        )
    )

    def fake_fetch(mmsi, *, api_key, **kwargs):
        return VesselApiResult(
            ok=True,
            vessel=parse_vessel_payload(DE_VEERMAN),
            status_code=200,
        )

    import database.vesselapi_provider as provider_mod

    original_db = provider_mod.vessel_database
    provider_mod.vessel_database = db
    try:
        provider = VesselAPIOnlineProvider(enabled=True, fetch_fn=fake_fetch)
        provider.enrich_mmsi(243042880, api_key="x", force=True)
        record = db.get(243042880)
        assert record.name == "AIS NAME"
        assert record.callsign == "AISCS"
        assert record.flag == "XX"
        assert record.length == 99.0
        assert record.width == 11.0
    finally:
        provider_mod.vessel_database = original_db


def test_load_api_key_does_not_require_logging_value(tmp_path: Path):
    key_path = tmp_path / "vesselapi"
    key_path.write_text("secret-token-value\n", encoding="utf-8")
    loaded = load_api_key(key_file=key_path)
    assert loaded == "secret-token-value"


def test_vessel_sync_text_merge_keeps_enrichment():
    from database.vessel_sync import VesselObservation, _merge_observation

    existing = VesselRecord(
        mmsi=1,
        name="KEEP",
        callsign="CALL",
        flag="HU",
        length=26.0,
        width=7.0,
    )
    observation = VesselObservation(
        mmsi=1,
        imo="",
        name="",
        callsign="",
        ship_type="",
        flag="",
        length=None,
        width=None,
        draft=None,
        last_seen=existing.last_seen,
    )
    merged, changed = _merge_observation(existing, observation)
    assert merged.name == "KEEP"
    assert merged.callsign == "CALL"
    assert merged.flag == "HU"
    assert merged.length == 26.0


def test_live_vesselapi_enrichment_two_mmsis(tmp_path: Path):
    key = load_api_key()
    if not key:
        pytest.skip("Phase A VesselAPI key file missing")

    db = VesselDatabase(tmp_path / "live.db")
    import database.vesselapi_provider as provider_mod

    original = provider_mod.vessel_database
    provider_mod.vessel_database = db
    try:
        provider = VesselAPIOnlineProvider(enabled=True)
        for mmsi in (243042880, 243070623):
            result = provider.enrich_mmsi(mmsi, force=True)
            assert result.ok, result.error
        de = db.get(243042880)
        pa = db.get(243070623)
        assert de is not None
        assert de.name == "DE VEERMAN"
        assert de.callsign == "HGD2880"
        assert de.flag == "HU"
        assert de.length == 38
        assert de.width == 8
        assert pa is not None
        assert pa.name == "PANNONIA"
        assert pa.callsign == "HGFW"
        assert pa.flag == "HU"
        assert pa.length == 26
        assert pa.width == 7
        assert pa.draft != 25.5
    finally:
        provider_mod.vessel_database = original
