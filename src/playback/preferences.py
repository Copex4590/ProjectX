# ============================================================================
# Project X
# Playback Preferences
# ============================================================================

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from config.playback import (
    DEFAULT_CUSTOM_ARGUMENTS,
    DEFAULT_CUSTOM_EXECUTABLE,
    DEFAULT_PLAYBACK_MODE,
    DEFAULT_PREFERRED_BACKEND,
    PLAYBACK_PREFERENCES_FILE,
)
from engines.camera.providers.base_provider import ProviderSession
from engines.playback import BackendRegistry, backend_registry
from engines.playback.backend import PlaybackBackend


class PlaybackMode(Enum):

    AUTOMATIC = "automatic"
    USER_PREFERRED = "user_preferred"

    @classmethod
    def from_value(cls, value: str) -> "PlaybackMode":

        normalized = str(value).strip().lower().replace("-", "_")

        if normalized in {"user", "user_preferred", "preferred", "manual"}:
            return cls.USER_PREFERRED

        return cls.AUTOMATIC


def _parse_arguments(value) -> list[str]:

    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    text = str(value).strip()

    if not text:
        return []

    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return [text]

        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]

    return [part for part in text.split() if part]


@dataclass
class PlaybackPreferences:

    mode: PlaybackMode = PlaybackMode.AUTOMATIC
    preferred_backend: str = DEFAULT_PREFERRED_BACKEND
    custom_executable: str = ""
    custom_arguments: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:

        return {
            "mode": self.mode.value,
            "preferred_backend": self.preferred_backend,
            "custom_executable": self.custom_executable,
            "custom_arguments": list(self.custom_arguments),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlaybackPreferences":

        if not isinstance(data, dict):
            data = {}

        return cls(
            mode=PlaybackMode.from_value(data.get("mode", DEFAULT_PLAYBACK_MODE)),
            preferred_backend=str(
                data.get("preferred_backend", DEFAULT_PREFERRED_BACKEND)
            ).strip().lower(),
            custom_executable=str(
                data.get("custom_executable", DEFAULT_CUSTOM_EXECUTABLE)
            ).strip(),
            custom_arguments=_parse_arguments(
                data.get("custom_arguments", DEFAULT_CUSTOM_ARGUMENTS)
            ),
        )

    @classmethod
    def defaults(cls) -> "PlaybackPreferences":

        return cls(
            mode=PlaybackMode.from_value(DEFAULT_PLAYBACK_MODE),
            preferred_backend=DEFAULT_PREFERRED_BACKEND,
            custom_executable=DEFAULT_CUSTOM_EXECUTABLE,
            custom_arguments=_parse_arguments(DEFAULT_CUSTOM_ARGUMENTS),
        )


def load_playback_preferences(
    path: Path | None = None,
) -> PlaybackPreferences:

    preferences_file = Path(path or PLAYBACK_PREFERENCES_FILE)

    if not preferences_file.exists():
        return PlaybackPreferences.defaults()

    with preferences_file.open(encoding="utf-8") as handle:
        data = json.load(handle)

    return PlaybackPreferences.from_dict(data)


def save_playback_preferences(
    preferences: PlaybackPreferences,
    path: Path | None = None,
) -> Path:

    preferences_file = Path(path or PLAYBACK_PREFERENCES_FILE)
    preferences_file.parent.mkdir(parents=True, exist_ok=True)

    with preferences_file.open("w", encoding="utf-8") as handle:
        json.dump(preferences.to_dict(), handle, indent=2)
        handle.write("\n")

    return preferences_file


class PlaybackSelector:

    def __init__(
        self,
        preferences: PlaybackPreferences | None = None,
        registry: BackendRegistry | None = None,
    ):

        self._preferences = preferences or load_playback_preferences()
        self._registry = registry or backend_registry

    @property
    def preferences(self) -> PlaybackPreferences:

        return self._preferences

    def reload_preferences(
        self,
        path: Path | None = None,
    ) -> PlaybackPreferences:

        self._preferences = load_playback_preferences(path)
        return self._preferences

    def select_backend(
        self,
        provider_session: ProviderSession,
    ) -> PlaybackBackend | None:

        if self._preferences.mode == PlaybackMode.USER_PREFERRED:
            preferred = self._find_backend(
                self._preferences.preferred_backend,
            )

            if (
                preferred is not None
                and preferred.supports(provider_session)
            ):
                return preferred

        return self._registry.get_backend(provider_session)

    def available_backends(self) -> list[PlaybackBackend]:

        return self._registry.available_backends()

    def _find_backend(self, backend_name: str) -> PlaybackBackend | None:

        target = backend_name.strip().lower()

        if not target:
            return None

        for backend in self._registry.available_backends():
            if backend.name.lower() == target:
                return backend

        return None


playback_selector = PlaybackSelector()
