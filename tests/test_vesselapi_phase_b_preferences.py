"""Phase B — VesselAPI Preferences key resolution and storage."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from database.vesselapi_client import load_api_key, resolve_api_key
from preferences.preferences import Preferences
from preferences.preferences_manager import PreferencesManager


@pytest.fixture()
def prefs_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> PreferencesManager:
    path = tmp_path / "preferences.json"
    manager = PreferencesManager(path)
    # Package __init__ exports preferences_manager instance; import the submodule.
    pm_mod = importlib.import_module("preferences.preferences_manager")
    monkeypatch.setattr(pm_mod, "preferences_manager", manager, raising=True)
    return manager


def test_resolve_prefers_preferences_over_phase_a_file(
    tmp_path: Path,
    prefs_manager: PreferencesManager,
):
    key_file = tmp_path / "vesselapi"
    key_file.write_text("file-key-value\n", encoding="utf-8")
    prefs_manager.set_vesselapi_configuration(
        api_key="prefs-key-value",
        enabled=True,
    )

    assert resolve_api_key(key_file=key_file) == "prefs-key-value"
    assert load_api_key(key_file=key_file) == "file-key-value"


def test_resolve_falls_back_to_phase_a_file(
    tmp_path: Path,
    prefs_manager: PreferencesManager,
):
    key_file = tmp_path / "vesselapi"
    key_file.write_text("fallback-key\n", encoding="utf-8")
    prefs_manager.set_vesselapi_configuration(api_key="", enabled=False)

    assert resolve_api_key(key_file=key_file) == "fallback-key"


def test_set_vesselapi_configuration_persists(prefs_manager: PreferencesManager):
    prefs_manager.set_vesselapi_configuration(
        api_key="  stored-key  ",
        enabled=True,
    )
    loaded = prefs_manager.reload()
    assert loaded.vesselapi_api_key == "stored-key"
    assert loaded.vesselapi_enabled is True


def test_reset_keeps_vesselapi_credentials(prefs_manager: PreferencesManager):
    prefs_manager.set_vesselapi_configuration(api_key="keep-me", enabled=True)
    prefs_manager.update_application_settings(theme="dark", log_level="DEBUG")
    prefs_manager.reset_application_settings()
    prefs = prefs_manager.get()
    assert prefs.vesselapi_api_key == "keep-me"
    assert prefs.vesselapi_enabled is True


def test_preferences_roundtrip_includes_vesselapi_fields():
    prefs = Preferences(
        vesselapi_api_key="abc",
        vesselapi_enabled=True,
    )
    restored = Preferences.from_dict(prefs.to_dict())
    assert restored.vesselapi_api_key == "abc"
    assert restored.vesselapi_enabled is True


def test_provider_enabled_follows_preferences(
    tmp_path: Path,
    prefs_manager: PreferencesManager,
):
    from database.vesselapi_provider import VesselAPIOnlineProvider

    prefs_manager.set_vesselapi_configuration(api_key="prefs-key", enabled=False)
    provider = VesselAPIOnlineProvider(key_file=tmp_path / "missing.key")
    assert provider.enabled is False

    prefs_manager.set_vesselapi_configuration(api_key="prefs-key", enabled=True)
    provider.apply_preferences()
    assert provider.enabled is True
