# ============================================================================
# Project X
# Playback Settings Page
# ============================================================================

import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from engines.playback import BackendRegistry, backend_registry
from engines.playback.backend import PlaybackBackend
from gui.i18n_support import bind_language_refresh
from gui.theme import TEXT, TEXT_SOFT, ThemeColors
from i18n import tr
from playback.preferences import (
    PlaybackMode,
    PlaybackPreferences,
    load_playback_preferences,
    save_playback_preferences,
)

_BACKEND_ORDER = ("mpv", "vlc", "qt", "browser", "custom")

_BACKEND_LABELS = {
    "mpv": "MPV",
    "vlc": "VLC",
    "qt": "Qt",
    "browser": "Browser",
    "custom": "Custom",
}


def load_settings() -> PlaybackPreferences:

    return load_playback_preferences()


def save_settings(preferences: PlaybackPreferences) -> Path:

    return save_playback_preferences(preferences)


def restore_defaults() -> PlaybackPreferences:

    preferences = PlaybackPreferences.defaults()
    save_playback_preferences(preferences)
    return preferences


def available_backends(
    registry: BackendRegistry | None = None,
) -> list[PlaybackBackend]:

    installed = {
        backend.name.lower(): backend
        for backend in (registry or backend_registry).available_backends()
    }

    backends: list[PlaybackBackend] = []

    for backend_name in _BACKEND_ORDER:
        backend = installed.get(backend_name)

        if backend is None:
            continue

        if _is_backend_available(backend):
            backends.append(backend)

    return backends


def _is_backend_available(backend: PlaybackBackend) -> bool:

    name = backend.name.lower()

    if name == "mpv":
        return shutil.which("mpv") is not None

    if name == "vlc":
        return (
            shutil.which("vlc") is not None
            or shutil.which("cvlc") is not None
        )

    return True


def _backend_label(backend: PlaybackBackend) -> str:

    label = _BACKEND_LABELS.get(
        backend.name.lower(),
        backend.name.strip().title(),
    )
    return tr(label)


def _resolve_preferred_backend(
    preferred_backend: str,
    backends: list[PlaybackBackend],
) -> str:

    normalized = str(preferred_backend).strip().lower()
    available_names = {backend.name.lower() for backend in backends}

    if normalized in available_names:
        return normalized

    if backends:
        return backends[0].name.lower()

    return normalized


class PlaybackSettingsPage(QFrame):

    def __init__(
        self,
        registry: BackendRegistry | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._registry = registry or backend_registry

        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self.load_settings()

    def load_settings(self) -> PlaybackPreferences:

        preferences = load_settings()
        backends = available_backends(self._registry)

        self._populate_backend_combo(backends)

        if preferences.mode == PlaybackMode.USER_PREFERRED:
            self.mode_combo.setCurrentIndex(1)
        else:
            self.mode_combo.setCurrentIndex(0)

        preferred_backend = _resolve_preferred_backend(
            preferences.preferred_backend,
            backends,
        )
        self._select_backend(preferred_backend)

        self.executable_input.setText(preferences.custom_executable)
        self.arguments_input.setText(" ".join(preferences.custom_arguments))

        self._sync_mode_state()

        return preferences

    def save_settings(self) -> PlaybackPreferences:

        preferences = self._preferences_from_form()
        save_settings(preferences)
        return preferences

    def restore_defaults(self) -> PlaybackPreferences:

        preferences = restore_defaults()
        self.load_settings()
        return preferences

    def _build_ui(self) -> None:

        self.setStyleSheet(f"""
            QLabel[role="section"] {{
                color: white;
                font-size: 14pt;
                font-weight: bold;
            }}

            QLabel[role="field"] {{
                color: {TEXT};
                font-size: 10pt;
                font-weight: 600;
            }}

            QLineEdit {{
                background: {ThemeColors.Panel};
                color: white;
                border: 1px solid {ThemeColors.Border};
                border-radius: 6px;
                padding: 6px 8px;
            }}

            QLineEdit:disabled {{
                color: {TEXT_SOFT};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(10)

        self._title_label = QLabel(tr("Playback Settings"))
        self._title_label.setProperty("role", "section")
        layout.addWidget(self._title_label)

        self._mode_label = self._field_label(tr("Playback Mode"))
        layout.addWidget(self._mode_label)
        self.mode_combo = QComboBox()
        layout.addWidget(self.mode_combo)

        self._backend_label = self._field_label(tr("Preferred Backend"))
        layout.addWidget(self._backend_label)
        self.backend_combo = QComboBox()
        layout.addWidget(self.backend_combo)

        self._custom_backend_label = self._field_label(tr("Custom Backend"))
        layout.addWidget(self._custom_backend_label)
        self._executable_label = self._field_label(tr("Executable"), caption=True)
        layout.addWidget(self._executable_label)
        self.executable_input = QLineEdit()
        layout.addWidget(self.executable_input)

        self._arguments_label = self._field_label(tr("Arguments"), caption=True)
        layout.addWidget(self._arguments_label)
        self.arguments_input = QLineEdit()
        layout.addWidget(self.arguments_input)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self.save_button = QPushButton()
        self.restore_button = QPushButton()

        button_row.addWidget(self.save_button)
        button_row.addWidget(self.restore_button)
        button_row.addStretch()

        layout.addLayout(button_row)

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Playback Settings"))
        self._mode_label.setText(tr("Playback Mode"))
        self._backend_label.setText(tr("Preferred Backend"))
        self._custom_backend_label.setText(tr("Custom Backend"))
        self._executable_label.setText(tr("Executable"))
        self._arguments_label.setText(tr("Arguments"))

        mode_index = self.mode_combo.currentIndex()
        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        self.mode_combo.addItems([tr("Automatic"), tr("User Preferred")])
        if 0 <= mode_index < self.mode_combo.count():
            self.mode_combo.setCurrentIndex(mode_index)
        self.mode_combo.blockSignals(False)

        self.executable_input.setPlaceholderText(tr("Path to playback executable"))
        self.arguments_input.setPlaceholderText(tr("Optional launch arguments"))
        self.save_button.setText(tr("Save"))
        self.restore_button.setText(tr("Restore Defaults"))

        self._populate_backend_combo(available_backends(self._registry))

    def _field_label(self, text: str, *, caption: bool = False) -> QLabel:

        label = QLabel(text)
        label.setProperty("role", "caption" if caption else "field")
        return label

    def _connect_signals(self) -> None:

        self.mode_combo.currentIndexChanged.connect(self._sync_mode_state)
        self.save_button.clicked.connect(self._on_save_clicked)
        self.restore_button.clicked.connect(self._on_restore_clicked)

    def _populate_backend_combo(self, backends: list[PlaybackBackend]) -> None:

        current = self.backend_combo.currentData(Qt.ItemDataRole.UserRole)
        self.backend_combo.blockSignals(True)
        self.backend_combo.clear()

        for backend in backends:
            self.backend_combo.addItem(
                _backend_label(backend),
                backend.name.lower(),
            )

        if current:
            self._select_backend(str(current))

        self.backend_combo.blockSignals(False)

    def _select_backend(self, backend_name: str) -> None:

        target = backend_name.strip().lower()

        for index in range(self.backend_combo.count()):
            if self.backend_combo.itemData(index) == target:
                self.backend_combo.setCurrentIndex(index)
                return

        if self.backend_combo.count() > 0:
            self.backend_combo.setCurrentIndex(0)

    def _sync_mode_state(self) -> None:

        user_preferred = self.mode_combo.currentIndex() == 1
        self.backend_combo.setEnabled(user_preferred)

    def _preferences_from_form(self) -> PlaybackPreferences:

        mode = (
            PlaybackMode.USER_PREFERRED
            if self.mode_combo.currentIndex() == 1
            else PlaybackMode.AUTOMATIC
        )

        preferred_backend = ""

        if self.backend_combo.count() > 0:
            preferred_backend = str(
                self.backend_combo.currentData(Qt.ItemDataRole.UserRole) or ""
            ).strip().lower()

        arguments_text = self.arguments_input.text().strip()
        custom_arguments = (
            [part for part in arguments_text.split() if part]
            if arguments_text
            else []
        )

        return PlaybackPreferences(
            mode=mode,
            preferred_backend=preferred_backend,
            custom_executable=self.executable_input.text().strip(),
            custom_arguments=custom_arguments,
        )

    def _on_save_clicked(self) -> None:

        self.save_settings()

    def _on_restore_clicked(self) -> None:

        self.restore_defaults()
