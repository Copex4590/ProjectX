# ============================================================================
# Project X
# Application Preferences
# ============================================================================

import os
from dataclasses import dataclass
from pathlib import Path

from app.paths import runtime_config_path

PREFERENCES_FILE = Path(
    os.environ.get(
        "PROJECTX_PREFERENCES_FILE",
        str(runtime_config_path("preferences.json")),
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

# SAVE-211 — Application Settings Manager
DEFAULT_THEME = "dark"
SUPPORTED_THEMES = ("dark",)

DEFAULT_STARTUP_PAGE = "dashboard"
SUPPORTED_STARTUP_PAGES = (
    "dashboard",
    "map",
    "vessels",
    "cameras",
    "system_health",
    "settings",
)

DEFAULT_CAMERA_DEFAULT_PROVIDER = "mpv"
SUPPORTED_CAMERA_PROVIDERS = ("mpv", "vlc", "qt", "browser", "custom")

DEFAULT_CAMERA_PREVIEW_QUALITY = "medium"
SUPPORTED_CAMERA_PREVIEW_QUALITIES = ("low", "medium", "high")

DEFAULT_BACKUP_FREQUENCY = "weekly"
SUPPORTED_BACKUP_FREQUENCIES = ("never", "daily", "weekly", "manual")

DEFAULT_CLEANUP_POLICY = "90d"
SUPPORTED_CLEANUP_POLICIES = ("never", "30d", "90d", "365d")

DEFAULT_LOG_LEVEL = "WARNING"
SUPPORTED_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

DEFAULT_AIS_RECONNECT_MIN_S = 1.0
DEFAULT_AIS_RECONNECT_MAX_S = 60.0
DEFAULT_AIS_CONNECTION_TIMEOUT_S = 10.0


def _normalize_choice(value: object, allowed: tuple[str, ...], default: str) -> str:

    normalized = str(value or default).strip().lower()
    allowed_lower = {item.lower(): item for item in allowed}

    if normalized in allowed_lower:
        return allowed_lower[normalized]

    return default


def _normalize_log_level(value: object) -> str:

    normalized = str(value or DEFAULT_LOG_LEVEL).strip().upper()

    if normalized in SUPPORTED_LOG_LEVELS:
        return normalized

    return DEFAULT_LOG_LEVEL


def _safe_float(value: object, default: float, *, minimum: float = 0.1) -> float:

    try:
        resolved = float(value)
    except (TypeError, ValueError):
        return default

    return max(minimum, resolved)


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

    # SAVE-211 General
    theme: str = DEFAULT_THEME
    startup_page: str = DEFAULT_STARTUP_PAGE
    startup_maximized: bool = False
    startup_restore_session: bool = True

    # SAVE-211 AIS
    ais_auto_connect: bool = True
    ais_reconnect_enabled: bool = True
    ais_reconnect_min_s: float = DEFAULT_AIS_RECONNECT_MIN_S
    ais_reconnect_max_s: float = DEFAULT_AIS_RECONNECT_MAX_S
    ais_connection_timeout_s: float = DEFAULT_AIS_CONNECTION_TIMEOUT_S

    # SAVE-211 Cameras
    camera_default_provider: str = DEFAULT_CAMERA_DEFAULT_PROVIDER
    camera_auto_selection: bool = True
    camera_preview_quality: str = DEFAULT_CAMERA_PREVIEW_QUALITY

    # SAVE-211 Database (auto-sync lives in vessel DB manager state)
    database_backup_frequency: str = DEFAULT_BACKUP_FREQUENCY
    database_cleanup_policy: str = DEFAULT_CLEANUP_POLICY

    # SAVE-211 Notifications
    notifications_desktop: bool = True
    notifications_sounds: bool = False
    log_level: str = DEFAULT_LOG_LEVEL

    # SAVE-211 Advanced
    developer_mode: bool = False
    diagnostics_enabled: bool = False

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
            "theme": self.theme,
            "startup_page": self.startup_page,
            "startup_maximized": self.startup_maximized,
            "startup_restore_session": self.startup_restore_session,
            "ais_auto_connect": self.ais_auto_connect,
            "ais_reconnect_enabled": self.ais_reconnect_enabled,
            "ais_reconnect_min_s": self.ais_reconnect_min_s,
            "ais_reconnect_max_s": self.ais_reconnect_max_s,
            "ais_connection_timeout_s": self.ais_connection_timeout_s,
            "camera_default_provider": self.camera_default_provider,
            "camera_auto_selection": self.camera_auto_selection,
            "camera_preview_quality": self.camera_preview_quality,
            "database_backup_frequency": self.database_backup_frequency,
            "database_cleanup_policy": self.database_cleanup_policy,
            "notifications_desktop": self.notifications_desktop,
            "notifications_sounds": self.notifications_sounds,
            "log_level": self.log_level,
            "developer_mode": self.developer_mode,
            "diagnostics_enabled": self.diagnostics_enabled,
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

        reconnect_min = _safe_float(
            data.get("ais_reconnect_min_s", DEFAULT_AIS_RECONNECT_MIN_S),
            DEFAULT_AIS_RECONNECT_MIN_S,
        )
        reconnect_max = _safe_float(
            data.get("ais_reconnect_max_s", DEFAULT_AIS_RECONNECT_MAX_S),
            DEFAULT_AIS_RECONNECT_MAX_S,
        )
        if reconnect_max < reconnect_min:
            reconnect_max = reconnect_min

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
            theme=_normalize_choice(
                data.get("theme", DEFAULT_THEME),
                SUPPORTED_THEMES,
                DEFAULT_THEME,
            ),
            startup_page=_normalize_choice(
                data.get("startup_page", DEFAULT_STARTUP_PAGE),
                SUPPORTED_STARTUP_PAGES,
                DEFAULT_STARTUP_PAGE,
            ),
            startup_maximized=bool(data.get("startup_maximized", False)),
            startup_restore_session=bool(data.get("startup_restore_session", True)),
            ais_auto_connect=bool(data.get("ais_auto_connect", True)),
            ais_reconnect_enabled=bool(data.get("ais_reconnect_enabled", True)),
            ais_reconnect_min_s=reconnect_min,
            ais_reconnect_max_s=reconnect_max,
            ais_connection_timeout_s=_safe_float(
                data.get(
                    "ais_connection_timeout_s",
                    DEFAULT_AIS_CONNECTION_TIMEOUT_S,
                ),
                DEFAULT_AIS_CONNECTION_TIMEOUT_S,
            ),
            camera_default_provider=_normalize_choice(
                data.get(
                    "camera_default_provider",
                    DEFAULT_CAMERA_DEFAULT_PROVIDER,
                ),
                SUPPORTED_CAMERA_PROVIDERS,
                DEFAULT_CAMERA_DEFAULT_PROVIDER,
            ),
            camera_auto_selection=bool(data.get("camera_auto_selection", True)),
            camera_preview_quality=_normalize_choice(
                data.get(
                    "camera_preview_quality",
                    DEFAULT_CAMERA_PREVIEW_QUALITY,
                ),
                SUPPORTED_CAMERA_PREVIEW_QUALITIES,
                DEFAULT_CAMERA_PREVIEW_QUALITY,
            ),
            database_backup_frequency=_normalize_choice(
                data.get(
                    "database_backup_frequency",
                    DEFAULT_BACKUP_FREQUENCY,
                ),
                SUPPORTED_BACKUP_FREQUENCIES,
                DEFAULT_BACKUP_FREQUENCY,
            ),
            database_cleanup_policy=_normalize_choice(
                data.get(
                    "database_cleanup_policy",
                    DEFAULT_CLEANUP_POLICY,
                ),
                SUPPORTED_CLEANUP_POLICIES,
                DEFAULT_CLEANUP_POLICY,
            ),
            notifications_desktop=bool(data.get("notifications_desktop", True)),
            notifications_sounds=bool(data.get("notifications_sounds", False)),
            log_level=_normalize_log_level(data.get("log_level", DEFAULT_LOG_LEVEL)),
            developer_mode=bool(data.get("developer_mode", False)),
            diagnostics_enabled=bool(data.get("diagnostics_enabled", False)),
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

        if "language_selected" not in data:
            migrated["language_selected"] = bool(data)
        else:
            migrated["language_selected"] = bool(
                migrated.get("language_selected", False)
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
        migrated.setdefault("rtl_setup_completed", False)
        migrated.setdefault("ais_provider_coverage_notice_dismissed", False)
        migrated.setdefault("observation_point_workflow_notice_dismissed", False)

        # SAVE-211 defaults for existing preference files
        migrated["theme"] = _normalize_choice(
            migrated.get("theme", DEFAULT_THEME),
            SUPPORTED_THEMES,
            DEFAULT_THEME,
        )
        migrated["startup_page"] = _normalize_choice(
            migrated.get("startup_page", DEFAULT_STARTUP_PAGE),
            SUPPORTED_STARTUP_PAGES,
            DEFAULT_STARTUP_PAGE,
        )
        migrated["startup_maximized"] = bool(migrated.get("startup_maximized", False))
        migrated["startup_restore_session"] = bool(
            migrated.get("startup_restore_session", True)
        )
        migrated["ais_auto_connect"] = bool(migrated.get("ais_auto_connect", True))
        migrated["ais_reconnect_enabled"] = bool(
            migrated.get("ais_reconnect_enabled", True)
        )
        migrated["ais_reconnect_min_s"] = _safe_float(
            migrated.get("ais_reconnect_min_s", DEFAULT_AIS_RECONNECT_MIN_S),
            DEFAULT_AIS_RECONNECT_MIN_S,
        )
        migrated["ais_reconnect_max_s"] = _safe_float(
            migrated.get("ais_reconnect_max_s", DEFAULT_AIS_RECONNECT_MAX_S),
            DEFAULT_AIS_RECONNECT_MAX_S,
        )
        if migrated["ais_reconnect_max_s"] < migrated["ais_reconnect_min_s"]:
            migrated["ais_reconnect_max_s"] = migrated["ais_reconnect_min_s"]
        migrated["ais_connection_timeout_s"] = _safe_float(
            migrated.get(
                "ais_connection_timeout_s",
                DEFAULT_AIS_CONNECTION_TIMEOUT_S,
            ),
            DEFAULT_AIS_CONNECTION_TIMEOUT_S,
        )
        migrated["camera_default_provider"] = _normalize_choice(
            migrated.get(
                "camera_default_provider",
                DEFAULT_CAMERA_DEFAULT_PROVIDER,
            ),
            SUPPORTED_CAMERA_PROVIDERS,
            DEFAULT_CAMERA_DEFAULT_PROVIDER,
        )
        migrated["camera_auto_selection"] = bool(
            migrated.get("camera_auto_selection", True)
        )
        migrated["camera_preview_quality"] = _normalize_choice(
            migrated.get(
                "camera_preview_quality",
                DEFAULT_CAMERA_PREVIEW_QUALITY,
            ),
            SUPPORTED_CAMERA_PREVIEW_QUALITIES,
            DEFAULT_CAMERA_PREVIEW_QUALITY,
        )
        migrated["database_backup_frequency"] = _normalize_choice(
            migrated.get(
                "database_backup_frequency",
                DEFAULT_BACKUP_FREQUENCY,
            ),
            SUPPORTED_BACKUP_FREQUENCIES,
            DEFAULT_BACKUP_FREQUENCY,
        )
        migrated["database_cleanup_policy"] = _normalize_choice(
            migrated.get(
                "database_cleanup_policy",
                DEFAULT_CLEANUP_POLICY,
            ),
            SUPPORTED_CLEANUP_POLICIES,
            DEFAULT_CLEANUP_POLICY,
        )
        migrated["notifications_desktop"] = bool(
            migrated.get("notifications_desktop", True)
        )
        migrated["notifications_sounds"] = bool(
            migrated.get("notifications_sounds", False)
        )
        migrated["log_level"] = _normalize_log_level(
            migrated.get("log_level", DEFAULT_LOG_LEVEL)
        )
        migrated["developer_mode"] = bool(migrated.get("developer_mode", False))
        migrated["diagnostics_enabled"] = bool(
            migrated.get("diagnostics_enabled", False)
        )

        return migrated
