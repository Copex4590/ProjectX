# ============================================================================
# Project X
# Application Preferences
# ============================================================================

import os
from dataclasses import dataclass
from pathlib import Path

from storage.bootstrap import bootstrap_config_path

PREFERENCES_FILE = Path(
    os.environ.get(
        "PROJECTX_PREFERENCES_FILE",
        str(bootstrap_config_path("preferences.json")),
    )
)

# Data directory migration (SAVE-107-B4) updates `data_directory` only after the
# standalone storage migration service verifies a successful copy into a marked
# data root. Legacy source data is never modified or deleted by that process.

SCHEMA_VERSION = 2

DEFAULT_LANGUAGE = "en"
DEFAULT_VESSEL_CARD_LAYOUT = "standard"
DEFAULT_AIS_PROVIDER = "later"
DEFAULT_AIS_LOCAL_HOST = "localhost"
DEFAULT_AIS_LOCAL_PORT = 10110

SUPPORTED_LANGUAGES = ("en", "hu")

SUPPORTED_VESSEL_CARD_LAYOUTS = (
    "compact",
    "standard",
    "detailed",
    "media",
)


@dataclass
class Preferences:

    language: str = DEFAULT_LANGUAGE
    language_selected: bool = False
    vessel_card_layout: str = DEFAULT_VESSEL_CARD_LAYOUT
    first_run_completed: bool = False
    ais_provider: str = DEFAULT_AIS_PROVIDER
    ais_enabled_providers: list[str] | None = None
    aisstream_api_key: str = ""
    ais_local_host: str = DEFAULT_AIS_LOCAL_HOST
    ais_local_port: int = DEFAULT_AIS_LOCAL_PORT
    ais_configured: bool = False
    rtl_sdr_owned: bool | None = None
    rtl_sdr_configured: bool = False
    rtl_auto_start_ais_catcher: bool = True
    rtl_setup_os: str = ""
    rtl_setup_completed: bool = False
    ais_provider_coverage_notice_dismissed: bool = False
    observation_point_workflow_notice_dismissed: bool = False
    legacy_migration_deferred: bool = False
    storage_activation_deferred_until_restart: bool = False
    data_directory: str | None = None
    version: int = SCHEMA_VERSION

    def to_dict(self) -> dict:

        return {
            "version": SCHEMA_VERSION,
            "language": self.language,
            "language_selected": self.language_selected,
            "vessel_card_layout": self.vessel_card_layout,
            "first_run_completed": self.first_run_completed,
            "ais_provider": self.ais_provider,
            "ais_enabled_providers": list(self.ais_enabled_providers or []),
            "aisstream_api_key": self.aisstream_api_key,
            "ais_local_host": self.ais_local_host,
            "ais_local_port": self.ais_local_port,
            "ais_configured": self.ais_configured,
            "rtl_sdr_owned": self.rtl_sdr_owned,
            "rtl_sdr_configured": self.rtl_sdr_configured,
            "rtl_auto_start_ais_catcher": self.rtl_auto_start_ais_catcher,
            "rtl_setup_os": self.rtl_setup_os,
            "rtl_setup_completed": self.rtl_setup_completed,
            "ais_provider_coverage_notice_dismissed": (
                self.ais_provider_coverage_notice_dismissed
            ),
            "observation_point_workflow_notice_dismissed": (
                self.observation_point_workflow_notice_dismissed
            ),
            "legacy_migration_deferred": self.legacy_migration_deferred,
            "storage_activation_deferred_until_restart": (
                self.storage_activation_deferred_until_restart
            ),
            "data_directory": self.data_directory,
        }

    @classmethod
    def defaults(cls) -> "Preferences":

        return cls()

    @classmethod
    def from_dict(cls, data: dict) -> "Preferences":

        if not isinstance(data, dict):
            data = {}

        language = str(data.get("language", DEFAULT_LANGUAGE)).strip().lower()

        if language not in SUPPORTED_LANGUAGES:
            language = DEFAULT_LANGUAGE

        layout = str(
            data.get("vessel_card_layout", DEFAULT_VESSEL_CARD_LAYOUT)
        ).strip().lower()

        if layout not in SUPPORTED_VESSEL_CARD_LAYOUTS:
            layout = DEFAULT_VESSEL_CARD_LAYOUT

        first_run_completed = bool(data.get("first_run_completed", False))
        language_selected = bool(data.get("language_selected", False))
        ais_provider = str(
            data.get("ais_provider", DEFAULT_AIS_PROVIDER)
        ).strip().lower() or DEFAULT_AIS_PROVIDER

        raw_enabled = data.get("ais_enabled_providers")
        if isinstance(raw_enabled, list):
            ais_enabled_providers = [
                str(item).strip().lower()
                for item in raw_enabled
                if str(item).strip()
            ]
        else:
            ais_enabled_providers = None

        try:
            ais_local_port = int(data.get("ais_local_port", DEFAULT_AIS_LOCAL_PORT))
        except (TypeError, ValueError):
            ais_local_port = DEFAULT_AIS_LOCAL_PORT

        owned_value = data.get("rtl_sdr_owned", None)

        if owned_value is None:
            rtl_sdr_owned = None
        else:
            rtl_sdr_owned = bool(owned_value)

        raw_data_directory = data.get("data_directory")

        if raw_data_directory is None:
            data_directory = None
        else:
            data_directory = str(raw_data_directory).strip() or None

        return cls(
            language=language,
            language_selected=language_selected,
            vessel_card_layout=layout,
            first_run_completed=first_run_completed,
            ais_provider=ais_provider,
            ais_enabled_providers=ais_enabled_providers,
            aisstream_api_key=str(data.get("aisstream_api_key", "")).strip(),
            ais_local_host=str(
                data.get("ais_local_host", DEFAULT_AIS_LOCAL_HOST)
            ).strip() or DEFAULT_AIS_LOCAL_HOST,
            ais_local_port=ais_local_port,
            ais_configured=bool(data.get("ais_configured", False)),
            rtl_sdr_owned=rtl_sdr_owned,
            rtl_sdr_configured=bool(data.get("rtl_sdr_configured", False)),
            rtl_auto_start_ais_catcher=bool(
                data.get("rtl_auto_start_ais_catcher", True)
            ),
            rtl_setup_os=str(data.get("rtl_setup_os", "")).strip().lower(),
            rtl_setup_completed=bool(data.get("rtl_setup_completed", False)),
            ais_provider_coverage_notice_dismissed=bool(
                data.get("ais_provider_coverage_notice_dismissed", False)
            ),
            observation_point_workflow_notice_dismissed=bool(
                data.get("observation_point_workflow_notice_dismissed", False)
            ),
            legacy_migration_deferred=bool(
                data.get("legacy_migration_deferred", False)
            ),
            storage_activation_deferred_until_restart=bool(
                data.get("storage_activation_deferred_until_restart", False)
            ),
            data_directory=data_directory,
            version=int(data.get("version", SCHEMA_VERSION)),
        )

    def has_data_directory(self) -> bool:
        """Return True when a user data directory has been configured."""

        return bool((self.data_directory or "").strip())

    @classmethod
    def migrate(cls, data: dict) -> dict:

        if not isinstance(data, dict):
            data = {}

        defaults = cls.defaults().to_dict()
        migrated = dict(defaults)

        for key, value in data.items():
            migrated[key] = value

        migrated["version"] = SCHEMA_VERSION

        language = str(migrated.get("language", DEFAULT_LANGUAGE)).strip().lower()

        if language not in SUPPORTED_LANGUAGES:
            migrated["language"] = DEFAULT_LANGUAGE

        layout = str(
            migrated.get("vessel_card_layout", DEFAULT_VESSEL_CARD_LAYOUT)
        ).strip().lower()

        if layout not in SUPPORTED_VESSEL_CARD_LAYOUTS:
            migrated["vessel_card_layout"] = DEFAULT_VESSEL_CARD_LAYOUT

        migrated["first_run_completed"] = (
            False
            if "first_run_completed" not in data
            else bool(migrated.get("first_run_completed", False))
        )

        migrated["language_selected"] = (
            False
            if "language_selected" not in data
            else bool(migrated.get("language_selected", False))
        )
        migrated.setdefault("ais_provider", DEFAULT_AIS_PROVIDER)
        migrated.setdefault("ais_enabled_providers", None)
        migrated.setdefault("aisstream_api_key", "")
        migrated.setdefault("ais_local_host", DEFAULT_AIS_LOCAL_HOST)

        try:
            migrated["ais_local_port"] = int(
                migrated.get("ais_local_port", DEFAULT_AIS_LOCAL_PORT)
            )
        except (TypeError, ValueError):
            migrated["ais_local_port"] = DEFAULT_AIS_LOCAL_PORT

        migrated["ais_configured"] = bool(migrated.get("ais_configured", False))

        if "rtl_sdr_owned" not in data:
            migrated["rtl_sdr_owned"] = None
        else:
            migrated["rtl_sdr_owned"] = bool(migrated.get("rtl_sdr_owned"))

        migrated.setdefault("rtl_sdr_configured", False)
        migrated.setdefault("rtl_auto_start_ais_catcher", True)
        migrated.setdefault("rtl_setup_os", "")
        migrated["rtl_setup_completed"] = (
            False
            if "rtl_setup_completed" not in data
            else bool(migrated.get("rtl_setup_completed", False))
        )
        migrated.setdefault("ais_provider_coverage_notice_dismissed", False)
        migrated.setdefault("observation_point_workflow_notice_dismissed", False)
        migrated.setdefault("legacy_migration_deferred", False)
        migrated.setdefault("storage_activation_deferred_until_restart", False)

        if "data_directory" not in data:
            migrated["data_directory"] = None
        else:
            raw_data_directory = migrated.get("data_directory")

            if raw_data_directory is None:
                migrated["data_directory"] = None
            else:
                migrated["data_directory"] = (
                    str(raw_data_directory).strip() or None
                )

        migrated["version"] = SCHEMA_VERSION

        return migrated
