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

    def set_vessel_card_layout(self, layout: str) -> Preferences:

        current = self.get()
        current.vessel_card_layout = str(layout).strip().lower()
        return self.save(Preferences.from_dict(current.to_dict()))

    def set_first_run_completed(self, completed: bool = True) -> Preferences:

        current = self.get()
        current.first_run_completed = bool(completed)
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
