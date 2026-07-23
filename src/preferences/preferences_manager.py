# ============================================================================
# Project X
# Preferences Manager
# ============================================================================

import json
from copy import deepcopy
from threading import Lock

from preferences.preferences import (
    PREFERENCES_FILE,
    Preferences,
)


class PreferencesManager:

    def __init__(self, path=None):

        self._path = path or PREFERENCES_FILE
        self._lock = Lock()
        self._preferences = self._load()

    def get(self) -> Preferences:

        with self._lock:
            return deepcopy(self._preferences)

    def reload(self) -> Preferences:

        with self._lock:
            self._preferences = self._load()
            return deepcopy(self._preferences)

    def save(self, preferences: Preferences) -> Preferences:

        payload = Preferences.from_dict(preferences.to_dict())

        with self._lock:
            self._preferences = payload
            self._write(payload)

        return deepcopy(payload)

    def set_language(self, language: str) -> Preferences:

        current = self.get()
        current.language = str(language).strip().lower()
        return self.save(Preferences.from_dict(current.to_dict()))

    def set_language_selected(self, selected: bool = True) -> Preferences:

        current = self.get()
        current.language_selected = bool(selected)
        return self.save(Preferences.from_dict(current.to_dict()))

    def set_vessel_card_layout(self, layout: str) -> Preferences:

        current = self.get()
        current.vessel_card_layout = str(layout).strip().lower()
        return self.save(Preferences.from_dict(current.to_dict()))

    def set_first_run_completed(self, completed: bool = True) -> Preferences:

        current = self.get()
        current.first_run_completed = bool(completed)
        return self.save(Preferences.from_dict(current.to_dict()))

    def set_ais_provider_coverage_notice_dismissed(
        self,
        dismissed: bool = True,
    ) -> Preferences:

        current = self.get()
        current.ais_provider_coverage_notice_dismissed = bool(dismissed)
        return self.save(Preferences.from_dict(current.to_dict()))

    def set_observation_point_workflow_notice_dismissed(
        self,
        dismissed: bool = True,
    ) -> Preferences:

        current = self.get()
        current.observation_point_workflow_notice_dismissed = bool(dismissed)
        return self.save(Preferences.from_dict(current.to_dict()))

    def set_ais_configuration(
        self,
        *,
        provider_type: str,
        api_key: str = "",
        host: str = "",
        port: int = 0,
        configured: bool = True,
    ) -> Preferences:

        current = self.get()
        current.ais_provider = str(provider_type).strip().lower()
        current.aisstream_api_key = str(api_key).strip()
        current.ais_local_host = str(host).strip() or current.ais_local_host
        current.ais_local_port = int(port or current.ais_local_port)
        current.ais_configured = bool(configured)
        return self.save(Preferences.from_dict(current.to_dict()))

    def set_ais_enabled_providers(
        self,
        providers: list[str],
        *,
        legacy_provider: str | None = None,
    ) -> Preferences:

        current = self.get()
        current.ais_enabled_providers = [
            str(item).strip().lower()
            for item in providers
            if str(item).strip()
        ]

        if legacy_provider is not None:
            current.ais_provider = str(legacy_provider).strip().lower()

        return self.save(Preferences.from_dict(current.to_dict()))

    def set_rtl_configuration(
        self,
        *,
        owned: bool | None = None,
        configured: bool | None = None,
        auto_start_ais_catcher: bool | None = None,
        setup_os: str | None = None,
        setup_completed: bool | None = None,
    ) -> Preferences:

        current = self.get()

        if owned is not None:
            current.rtl_sdr_owned = bool(owned)

        if configured is not None:
            current.rtl_sdr_configured = bool(configured)

        if auto_start_ais_catcher is not None:
            current.rtl_auto_start_ais_catcher = bool(auto_start_ais_catcher)

        if setup_os is not None:
            current.rtl_setup_os = str(setup_os).strip().lower()

        if setup_completed is not None:
            current.rtl_setup_completed = bool(setup_completed)

        return self.save(Preferences.from_dict(current.to_dict()))

    def update_application_settings(self, **changes) -> Preferences:
        """Persist SAVE-211 application settings keys without touching AIS secrets."""

        current = self.get()
        payload = current.to_dict()

        allowed = {
            "language",
            "theme",
            "startup_page",
            "startup_maximized",
            "startup_restore_session",
            "ais_auto_connect",
            "ais_reconnect_enabled",
            "ais_reconnect_min_s",
            "ais_reconnect_max_s",
            "ais_connection_timeout_s",
            "camera_default_provider",
            "camera_auto_selection",
            "camera_preview_quality",
            "database_backup_frequency",
            "database_cleanup_policy",
            "notifications_desktop",
            "notifications_sounds",
            "log_level",
            "developer_mode",
            "diagnostics_enabled",
            "rtl_auto_start_ais_catcher",
        }

        for key, value in changes.items():
            if key in allowed:
                payload[key] = value

        return self.save(Preferences.from_dict(payload))

    def reset_application_settings(self) -> Preferences:
        """Reset SAVE-211 settings to defaults; keep AIS credentials and setup state."""

        current = self.get()
        defaults = Preferences.defaults()

        current.theme = defaults.theme
        current.startup_page = defaults.startup_page
        current.startup_maximized = defaults.startup_maximized
        current.startup_restore_session = defaults.startup_restore_session
        current.ais_auto_connect = defaults.ais_auto_connect
        current.ais_reconnect_enabled = defaults.ais_reconnect_enabled
        current.ais_reconnect_min_s = defaults.ais_reconnect_min_s
        current.ais_reconnect_max_s = defaults.ais_reconnect_max_s
        current.ais_connection_timeout_s = defaults.ais_connection_timeout_s
        current.camera_default_provider = defaults.camera_default_provider
        current.camera_auto_selection = defaults.camera_auto_selection
        current.camera_preview_quality = defaults.camera_preview_quality
        current.database_backup_frequency = defaults.database_backup_frequency
        current.database_cleanup_policy = defaults.database_cleanup_policy
        current.notifications_desktop = defaults.notifications_desktop
        current.notifications_sounds = defaults.notifications_sounds
        current.log_level = defaults.log_level
        current.developer_mode = defaults.developer_mode
        current.diagnostics_enabled = defaults.diagnostics_enabled
        current.language = defaults.language
        current.vessel_card_layout = defaults.vessel_card_layout

        return self.save(Preferences.from_dict(current.to_dict()))

    def _load(self) -> Preferences:

        if not self._path.exists():
            defaults = Preferences.defaults()
            self._write(defaults)
            return defaults

        with self._path.open(encoding="utf-8") as handle:
            data = json.load(handle)

        migrated = Preferences.migrate(data)
        preferences = Preferences.from_dict(migrated)

        if data != migrated:
            self._write(preferences)

        return preferences

    def _write(self, preferences: Preferences) -> None:

        self._path.parent.mkdir(parents=True, exist_ok=True)

        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(preferences.to_dict(), handle, indent=2)
            handle.write("\n")


preferences_manager = PreferencesManager()
