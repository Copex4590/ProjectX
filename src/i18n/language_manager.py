# ============================================================================
# Project X
# Language Manager
# ============================================================================

import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from preferences.preferences import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from preferences.preferences_manager import preferences_manager

from app.paths import resource_path

_TRANSLATIONS_DIR = resource_path("translations")


class LanguageManager(QObject):

    language_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._current_language = DEFAULT_LANGUAGE
        self._catalogs: dict[str, dict[str, str]] = {}
        self._load_catalog(DEFAULT_LANGUAGE)

        preferences = preferences_manager.get()
        self.set_language(preferences.language, persist=False)

    @property
    def current_language(self) -> str:

        return self._current_language

    def set_language(self, language: str, persist: bool = True) -> str:

        normalized = str(language or DEFAULT_LANGUAGE).strip().lower()

        if normalized not in SUPPORTED_LANGUAGES:
            normalized = DEFAULT_LANGUAGE

        self._load_catalog(normalized)
        self._current_language = normalized

        if persist:
            preferences_manager.set_language(normalized)

        self.language_changed.emit(normalized)
        return normalized

    def translate(self, key: str) -> str:

        text = str(key or "").strip()

        if not text:
            return ""

        current = self._catalogs.get(self._current_language, {})
        fallback = self._catalogs.get(DEFAULT_LANGUAGE, {})

        if text in current:
            return current[text]

        if text in fallback:
            return fallback[text]

        return text

    def translations(self) -> dict[str, str]:

        current = self._catalogs.get(self._current_language, {})
        fallback = self._catalogs.get(DEFAULT_LANGUAGE, {})
        merged = dict(fallback)
        merged.update(current)
        return merged

    def _load_catalog(self, language: str) -> None:

        if language in self._catalogs:
            return

        path = _TRANSLATIONS_DIR / f"{language}.json"

        if not path.exists():
            self._catalogs[language] = {}
            return

        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)

        if isinstance(data, dict):
            self._catalogs[language] = {
                str(key): str(value)
                for key, value in data.items()
            }
        else:
            self._catalogs[language] = {}


language_manager = LanguageManager()
