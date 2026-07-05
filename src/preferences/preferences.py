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
    version: int = SCHEMA_VERSION

    def to_dict(self) -> dict:

        return {
            "version": SCHEMA_VERSION,
            "language": self.language,
            "vessel_card_layout": self.vessel_card_layout,
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

        return cls(
            language=language,
            vessel_card_layout=layout,
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

        return migrated
