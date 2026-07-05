# ============================================================================
# Project X
# Application Preferences
# ============================================================================

import os
from dataclasses import dataclass
from pathlib import Path

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

PREFERENCES_FILE = Path(
    os.environ.get(
        "PROJECTX_PREFERENCES_FILE",
        str(_CONFIG_DIR / "preferences.json"),
    )
)

SCHEMA_VERSION = 1

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
    vessel_card_layout: str = DEFAULT_VESSEL_CARD_LAYOUT
    first_run_completed: bool = False
    ais_provider: str = DEFAULT_AIS_PROVIDER
    aisstream_api_key: str = ""
    ais_local_host: str = DEFAULT_AIS_LOCAL_HOST
    ais_local_port: int = DEFAULT_AIS_LOCAL_PORT
    ais_configured: bool = False
    version: int = SCHEMA_VERSION

    def to_dict(self) -> dict:

        return {
            "version": SCHEMA_VERSION,
            "language": self.language,
            "vessel_card_layout": self.vessel_card_layout,
            "first_run_completed": self.first_run_completed,
            "ais_provider": self.ais_provider,
            "aisstream_api_key": self.aisstream_api_key,
            "ais_local_host": self.ais_local_host,
            "ais_local_port": self.ais_local_port,
            "ais_configured": self.ais_configured,
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
        ais_provider = str(
            data.get("ais_provider", DEFAULT_AIS_PROVIDER)
        ).strip().lower() or DEFAULT_AIS_PROVIDER

        try:
            ais_local_port = int(data.get("ais_local_port", DEFAULT_AIS_LOCAL_PORT))
        except (TypeError, ValueError):
            ais_local_port = DEFAULT_AIS_LOCAL_PORT

        return cls(
            language=language,
            vessel_card_layout=layout,
            first_run_completed=first_run_completed,
            ais_provider=ais_provider,
            aisstream_api_key=str(data.get("aisstream_api_key", "")).strip(),
            ais_local_host=str(
                data.get("ais_local_host", DEFAULT_AIS_LOCAL_HOST)
            ).strip() or DEFAULT_AIS_LOCAL_HOST,
            ais_local_port=ais_local_port,
            ais_configured=bool(data.get("ais_configured", False)),
            version=int(data.get("version", SCHEMA_VERSION)),
        )

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

        migrated["first_run_completed"] = bool(
            migrated.get("first_run_completed", False)
        )
        migrated.setdefault("ais_provider", DEFAULT_AIS_PROVIDER)
        migrated.setdefault("aisstream_api_key", "")
        migrated.setdefault("ais_local_host", DEFAULT_AIS_LOCAL_HOST)

        try:
            migrated["ais_local_port"] = int(
                migrated.get("ais_local_port", DEFAULT_AIS_LOCAL_PORT)
            )
        except (TypeError, ValueError):
            migrated["ais_local_port"] = DEFAULT_AIS_LOCAL_PORT

        migrated["ais_configured"] = bool(migrated.get("ais_configured", False))

        return migrated
