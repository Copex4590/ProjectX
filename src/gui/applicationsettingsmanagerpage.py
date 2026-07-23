# ============================================================================
# Project X
# Application Settings Manager Page (SAVE-211)
# ============================================================================

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ais.providers import AISProviderType, normalize_provider_type
from ais.user_provider_service import (
    get_enabled_provider_ids,
    set_enabled_providers,
)
from database.vessel_database_manager import vessel_database_manager
from gui.i18n_support import bind_language_refresh
from gui.theme import (
    ThemeColors,
    card_stylesheet,
    primary_button_stylesheet,
    secondary_button_stylesheet,
)
from i18n import language_manager, tr
from playback.preferences import (
    PlaybackMode,
    load_playback_preferences,
    save_playback_preferences,
)
from preferences.application_settings import apply_runtime_settings
from preferences.preferences import (
    SUPPORTED_BACKUP_FREQUENCIES,
    SUPPORTED_CAMERA_PREVIEW_QUALITIES,
    SUPPORTED_CAMERA_PROVIDERS,
    SUPPORTED_CLEANUP_POLICIES,
    SUPPORTED_LANGUAGES,
    SUPPORTED_LOG_LEVELS,
    SUPPORTED_STARTUP_PAGES,
    SUPPORTED_THEMES,
)
from preferences.preferences_manager import preferences_manager

logger = logging.getLogger(__name__)

_LANGUAGE_LABELS = {
    "en": "English",
    "hu": "Magyar",
}

_THEME_LABELS = {
    "dark": "Project X Dark",
}

_STARTUP_LABELS = {
    "dashboard": "Dashboard",
    "map": "Map",
    "vessels": "Vessels",
    "cameras": "Cameras",
    "system_health": "System Health",
    "settings": "Settings",
}

_PROVIDER_LABELS = {
    "mpv": "MPV",
    "vlc": "VLC",
    "qt": "Qt",
    "browser": "Browser",
    "custom": "Custom",
}

_QUALITY_LABELS = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
}

_BACKUP_LABELS = {
    "never": "Never",
    "daily": "Daily",
    "weekly": "Weekly",
    "manual": "Manual only",
}

_CLEANUP_LABELS = {
    "never": "Never",
    "30d": "After 30 days",
    "90d": "After 90 days",
    "365d": "After 1 year",
}


class _SectionCard(QFrame):

    def __init__(self, title_key: str, parent=None):
        super().__init__(parent)

        self._title_key = title_key
        self.setStyleSheet(card_stylesheet(radius=10))

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        self._title = QLabel()
        self._title.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 12pt; font-weight: 700;"
        )
        root.addWidget(self._title)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {ThemeColors.Border};")
        root.addWidget(divider)

        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        self.body.setContentsMargins(0, 4, 0, 0)
        root.addLayout(self.body)

    def refresh_translations(self) -> None:

        self._title.setText(tr(self._title_key))


class ApplicationSettingsManagerPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._loading = False
        self._ais_provider_checks: dict[AISProviderType, QCheckBox] = {}
        self._labeled_widgets: list[tuple[QLabel | QCheckBox, str]] = []

        self.setStyleSheet(f"background: {ThemeColors.Background};")
        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self.reload_from_preferences()

    def _build_ui(self) -> None:

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {ThemeColors.Background}; border: none; }}"
        )
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet(f"background: {ThemeColors.Background};")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        self._title_label = QLabel()
        self._title_label.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 18pt; font-weight: 700;"
        )
        header.addWidget(self._title_label)
        header.addStretch(1)

        self._status_label = QLabel()
        self._status_label.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        header.addWidget(self._status_label, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(header)

        self._sections: list[_SectionCard] = []

        self._general_card = self._add_section(layout, "General")
        self._language_combo = self._add_combo_row(
            self._general_card,
            "Language",
            SUPPORTED_LANGUAGES,
            _LANGUAGE_LABELS,
        )
        self._theme_combo = self._add_combo_row(
            self._general_card,
            "Theme",
            SUPPORTED_THEMES,
            _THEME_LABELS,
        )
        self._startup_page_combo = self._add_combo_row(
            self._general_card,
            "Startup page",
            SUPPORTED_STARTUP_PAGES,
            _STARTUP_LABELS,
        )
        self._startup_maximized = self._add_checkbox(
            self._general_card,
            "Start maximized",
        )
        self._startup_restore = self._add_checkbox(
            self._general_card,
            "Restore previous session layout",
        )

        self._ais_card = self._add_section(layout, "AIS")
        providers_label = QLabel()
        providers_label.setObjectName("aisProvidersLabel")
        providers_label.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 10pt;"
        )
        self._ais_providers_label = providers_label
        self._ais_card.body.addWidget(providers_label)

        for provider, label in (
            (AISProviderType.AISSTREAM, "AISStream"),
            (AISProviderType.LOCAL, "RTL-SDR"),
        ):
            checkbox = QCheckBox(label)
            checkbox.setStyleSheet(self._checkbox_style())
            self._ais_provider_checks[provider] = checkbox
            self._ais_card.body.addWidget(checkbox)

        future = QLabel()
        future.setObjectName("aisFutureLabel")
        future.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        self._ais_future_label = future
        self._ais_card.body.addWidget(future)

        self._ais_auto_connect = self._add_checkbox(self._ais_card, "Auto connect")
        self._ais_reconnect = self._add_checkbox(self._ais_card, "Reconnect")
        self._ais_timeout = self._add_double_row(
            self._ais_card,
            "Connection timeout (s)",
            minimum=1.0,
            maximum=120.0,
            step=1.0,
        )
        self._ais_reconnect_min = self._add_double_row(
            self._ais_card,
            "Reconnect min delay (s)",
            minimum=0.5,
            maximum=60.0,
            step=0.5,
        )
        self._ais_reconnect_max = self._add_double_row(
            self._ais_card,
            "Reconnect max delay (s)",
            minimum=1.0,
            maximum=600.0,
            step=1.0,
        )

        self._cameras_card = self._add_section(layout, "Cameras")
        self._camera_provider_combo = self._add_combo_row(
            self._cameras_card,
            "Default provider",
            SUPPORTED_CAMERA_PROVIDERS,
            _PROVIDER_LABELS,
        )
        self._camera_auto_selection = self._add_checkbox(
            self._cameras_card,
            "Auto selection",
        )
        self._camera_quality_combo = self._add_combo_row(
            self._cameras_card,
            "Preview quality",
            SUPPORTED_CAMERA_PREVIEW_QUALITIES,
            _QUALITY_LABELS,
        )

        self._database_card = self._add_section(layout, "Database")
        self._db_auto_sync = self._add_checkbox(self._database_card, "Auto Sync")
        self._db_sync_interval = self._add_spin_row(
            self._database_card,
            "Sync interval (seconds)",
            minimum=30,
            maximum=86400,
            step=30,
        )
        self._db_backup_combo = self._add_combo_row(
            self._database_card,
            "Backup frequency",
            SUPPORTED_BACKUP_FREQUENCIES,
            _BACKUP_LABELS,
        )
        self._db_cleanup_combo = self._add_combo_row(
            self._database_card,
            "Cleanup policy",
            SUPPORTED_CLEANUP_POLICIES,
            _CLEANUP_LABELS,
        )

        self._notifications_card = self._add_section(layout, "Notifications")
        self._notify_desktop = self._add_checkbox(
            self._notifications_card,
            "Desktop notifications",
        )
        self._notify_sounds = self._add_checkbox(
            self._notifications_card,
            "Sounds",
        )
        self._log_level_combo = self._add_combo_row(
            self._notifications_card,
            "Log level",
            SUPPORTED_LOG_LEVELS,
            {level: level for level in SUPPORTED_LOG_LEVELS},
            preserve_case=True,
        )

        self._advanced_card = self._add_section(layout, "Advanced")
        self._developer_mode = self._add_checkbox(
            self._advanced_card,
            "Developer mode",
        )
        self._diagnostics = self._add_checkbox(
            self._advanced_card,
            "Diagnostics",
        )

        actions = QHBoxLayout()
        actions.setSpacing(10)

        self._save_button = QPushButton()
        self._save_button.setStyleSheet(primary_button_stylesheet())
        actions.addWidget(self._save_button)

        self._reload_button = QPushButton()
        self._reload_button.setStyleSheet(secondary_button_stylesheet())
        actions.addWidget(self._reload_button)

        self._reset_button = QPushButton()
        self._reset_button.setStyleSheet(secondary_button_stylesheet())
        actions.addWidget(self._reset_button)

        actions.addStretch(1)
        self._advanced_card.body.addLayout(actions)

        layout.addStretch(1)

    def _add_section(self, layout: QVBoxLayout, title_key: str) -> _SectionCard:

        card = _SectionCard(title_key)
        self._sections.append(card)
        layout.addWidget(card)
        return card

    def _label_style(self) -> str:

        return f"color: {ThemeColors.TextSecondary}; font-size: 10pt;"

    def _checkbox_style(self) -> str:

        return (
            f"color: {ThemeColors.TextPrimary}; font-size: 10pt;"
            f"spacing: 8px;"
        )

    def _combo_style(self) -> str:

        return f"""
            QComboBox {{
                background: {ThemeColors.Panel};
                color: {ThemeColors.TextPrimary};
                border: 1px solid {ThemeColors.Border};
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 220px;
            }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{
                background: {ThemeColors.Panel};
                color: {ThemeColors.TextPrimary};
                selection-background-color: {ThemeColors.Primary700};
            }}
        """

    def _spin_style(self) -> str:

        return f"""
            QSpinBox, QDoubleSpinBox {{
                background: {ThemeColors.Panel};
                color: {ThemeColors.TextPrimary};
                border: 1px solid {ThemeColors.Border};
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 120px;
            }}
        """

    def _add_checkbox(self, card: _SectionCard, label_key: str) -> QCheckBox:

        checkbox = QCheckBox()
        checkbox.setProperty("label_key", label_key)
        checkbox.setStyleSheet(self._checkbox_style())
        card.body.addWidget(checkbox)
        return checkbox

    def _add_combo_row(
        self,
        card: _SectionCard,
        label_key: str,
        values: tuple[str, ...],
        labels: dict[str, str],
        *,
        preserve_case: bool = False,
    ) -> QComboBox:

        row = QHBoxLayout()
        label = QLabel()
        label.setProperty("label_key", label_key)
        label.setStyleSheet(self._label_style())
        row.addWidget(label)

        combo = QComboBox()
        combo.setStyleSheet(self._combo_style())

        for value in values:
            display = labels.get(value, value)
            combo.addItem(display, value if not preserve_case else value)

        row.addWidget(combo, 1)
        card.body.addLayout(row)
        self._labeled_widgets.append((label, label_key))
        return combo

    def _add_spin_row(
        self,
        card: _SectionCard,
        label_key: str,
        *,
        minimum: int,
        maximum: int,
        step: int,
    ) -> QSpinBox:

        row = QHBoxLayout()
        label = QLabel()
        label.setProperty("label_key", label_key)
        label.setStyleSheet(self._label_style())
        row.addWidget(label)

        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setStyleSheet(self._spin_style())
        row.addWidget(spin)
        row.addStretch(1)
        card.body.addLayout(row)
        self._labeled_widgets.append((label, label_key))
        return spin

    def _add_double_row(
        self,
        card: _SectionCard,
        label_key: str,
        *,
        minimum: float,
        maximum: float,
        step: float,
    ) -> QDoubleSpinBox:

        row = QHBoxLayout()
        label = QLabel()
        label.setProperty("label_key", label_key)
        label.setStyleSheet(self._label_style())
        row.addWidget(label)

        spin = QDoubleSpinBox()
        spin.setDecimals(1)
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setStyleSheet(self._spin_style())
        row.addWidget(spin)
        row.addStretch(1)
        card.body.addLayout(row)
        self._labeled_widgets.append((label, label_key))
        return spin

    def _connect_signals(self) -> None:

        self._save_button.clicked.connect(self.save_settings)
        self._reload_button.clicked.connect(self.reload_from_preferences)
        self._reset_button.clicked.connect(self.reset_settings)

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Settings"))
        self._status_label.setText(tr("All settings are saved to preferences.json"))

        for section in self._sections:
            section.refresh_translations()

        for widget in (
            self._startup_maximized,
            self._startup_restore,
            self._ais_auto_connect,
            self._ais_reconnect,
            self._camera_auto_selection,
            self._db_auto_sync,
            self._notify_desktop,
            self._notify_sounds,
            self._developer_mode,
            self._diagnostics,
        ):
            key = widget.property("label_key")
            if key:
                widget.setText(tr(str(key)))

        for label, key in getattr(self, "_labeled_widgets", []):
            label.setText(tr(key))

        self._ais_providers_label.setText(tr("Providers"))
        self._ais_future_label.setText(
            tr("MarineTraffic / AISHub — Coming Soon")
        )

        self._save_button.setText(tr("Save Settings"))
        self._reload_button.setText(tr("Reload"))
        self._reset_button.setText(tr("Reset settings"))

        self._refresh_combo_labels(self._language_combo, _LANGUAGE_LABELS)
        self._refresh_combo_labels(self._theme_combo, _THEME_LABELS)
        self._refresh_combo_labels(self._startup_page_combo, _STARTUP_LABELS)
        self._refresh_combo_labels(self._camera_provider_combo, _PROVIDER_LABELS)
        self._refresh_combo_labels(self._camera_quality_combo, _QUALITY_LABELS)
        self._refresh_combo_labels(self._db_backup_combo, _BACKUP_LABELS)
        self._refresh_combo_labels(self._db_cleanup_combo, _CLEANUP_LABELS)

        for level in SUPPORTED_LOG_LEVELS:
            index = self._log_level_combo.findData(level)
            if index >= 0:
                self._log_level_combo.setItemText(index, level)

    def _refresh_combo_labels(
        self,
        combo: QComboBox,
        labels: dict[str, str],
    ) -> None:

        current = combo.currentData()
        for index in range(combo.count()):
            value = combo.itemData(index)
            combo.setItemText(index, tr(labels.get(value, str(value))))
        if current is not None:
            index = combo.findData(current)
            if index >= 0:
                combo.setCurrentIndex(index)

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:

        index = combo.findData(value)
        if index < 0:
            index = 0
        combo.setCurrentIndex(index)

    def reload_from_preferences(self) -> None:

        self._loading = True
        try:
            preferences = preferences_manager.reload()
            snapshot = vessel_database_manager.collect_snapshot()

            self._set_combo_value(self._language_combo, preferences.language)
            self._set_combo_value(self._theme_combo, preferences.theme)
            self._set_combo_value(self._startup_page_combo, preferences.startup_page)
            self._startup_maximized.setChecked(preferences.startup_maximized)
            self._startup_restore.setChecked(preferences.startup_restore_session)

            enabled = {
                normalize_provider_type(value)
                for value in get_enabled_provider_ids()
            }
            for provider, checkbox in self._ais_provider_checks.items():
                checkbox.setChecked(provider in enabled)

            self._ais_auto_connect.setChecked(preferences.ais_auto_connect)
            self._ais_reconnect.setChecked(preferences.ais_reconnect_enabled)
            self._ais_timeout.setValue(preferences.ais_connection_timeout_s)
            self._ais_reconnect_min.setValue(preferences.ais_reconnect_min_s)
            self._ais_reconnect_max.setValue(preferences.ais_reconnect_max_s)

            self._set_combo_value(
                self._camera_provider_combo,
                preferences.camera_default_provider,
            )
            self._camera_auto_selection.setChecked(preferences.camera_auto_selection)
            self._set_combo_value(
                self._camera_quality_combo,
                preferences.camera_preview_quality,
            )

            self._db_auto_sync.setChecked(snapshot.synchronization.auto_sync_enabled)
            self._db_sync_interval.setValue(
                int(snapshot.synchronization.sync_interval_seconds)
            )
            self._set_combo_value(
                self._db_backup_combo,
                preferences.database_backup_frequency,
            )
            self._set_combo_value(
                self._db_cleanup_combo,
                preferences.database_cleanup_policy,
            )

            self._notify_desktop.setChecked(preferences.notifications_desktop)
            self._notify_sounds.setChecked(preferences.notifications_sounds)
            self._set_combo_value(self._log_level_combo, preferences.log_level)

            self._developer_mode.setChecked(preferences.developer_mode)
            self._diagnostics.setChecked(preferences.diagnostics_enabled)

            self._status_label.setText(tr("Loaded from preferences.json"))
            self._status_label.setStyleSheet(
                f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
            )
        finally:
            self._loading = False

    def save_settings(self) -> None:

        if self._loading:
            return

        language = str(self._language_combo.currentData() or "en")
        theme = str(self._theme_combo.currentData() or "dark")
        startup_page = str(self._startup_page_combo.currentData() or "dashboard")
        camera_provider = str(
            self._camera_provider_combo.currentData() or "mpv"
        )
        camera_quality = str(
            self._camera_quality_combo.currentData() or "medium"
        )
        backup_frequency = str(
            self._db_backup_combo.currentData() or "weekly"
        )
        cleanup_policy = str(
            self._db_cleanup_combo.currentData() or "90d"
        )
        log_level = str(self._log_level_combo.currentData() or "WARNING")

        reconnect_min = float(self._ais_reconnect_min.value())
        reconnect_max = float(self._ais_reconnect_max.value())
        if reconnect_max < reconnect_min:
            reconnect_max = reconnect_min

        preferences_manager.update_application_settings(
            language=language,
            theme=theme,
            startup_page=startup_page,
            startup_maximized=self._startup_maximized.isChecked(),
            startup_restore_session=self._startup_restore.isChecked(),
            ais_auto_connect=self._ais_auto_connect.isChecked(),
            ais_reconnect_enabled=self._ais_reconnect.isChecked(),
            ais_reconnect_min_s=reconnect_min,
            ais_reconnect_max_s=reconnect_max,
            ais_connection_timeout_s=float(self._ais_timeout.value()),
            camera_default_provider=camera_provider,
            camera_auto_selection=self._camera_auto_selection.isChecked(),
            camera_preview_quality=camera_quality,
            database_backup_frequency=backup_frequency,
            database_cleanup_policy=cleanup_policy,
            notifications_desktop=self._notify_desktop.isChecked(),
            notifications_sounds=self._notify_sounds.isChecked(),
            log_level=log_level,
            developer_mode=self._developer_mode.isChecked(),
            diagnostics_enabled=self._diagnostics.isChecked(),
            rtl_auto_start_ais_catcher=self._ais_auto_connect.isChecked(),
        )

        language_manager.set_language(language)

        enabled = {
            provider
            for provider, checkbox in self._ais_provider_checks.items()
            if checkbox.isChecked()
        }
        set_enabled_providers(enabled)

        vessel_database_manager.set_auto_sync(self._db_auto_sync.isChecked())
        vessel_database_manager.set_sync_interval(
            float(self._db_sync_interval.value())
        )

        try:
            playback = load_playback_preferences()
            playback.preferred_backend = camera_provider
            if playback.mode == PlaybackMode.AUTOMATIC and self._camera_auto_selection.isChecked():
                pass
            elif self._camera_auto_selection.isChecked():
                playback.mode = PlaybackMode.AUTOMATIC
            else:
                playback.mode = PlaybackMode.USER_PREFERRED
            save_playback_preferences(playback)
        except Exception:
            logger.exception("Failed to sync camera provider to playback preferences")

        apply_runtime_settings()

        self._status_label.setText(tr("Settings saved"))
        self._status_label.setStyleSheet(
            f"color: {ThemeColors.Success}; font-size: 9pt;"
        )

    def reset_settings(self) -> None:

        answer = QMessageBox.question(
            self,
            tr("Reset settings"),
            tr(
                "Reset application settings to defaults?\n"
                "AIS API keys and provider setup are kept."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        preferences_manager.reset_application_settings()
        language_manager.set_language(preferences_manager.get().language)
        vessel_database_manager.set_auto_sync(False)
        vessel_database_manager.set_sync_interval(300.0)
        apply_runtime_settings()
        self.reload_from_preferences()
        self._status_label.setText(tr("Settings reset to defaults"))
        self._status_label.setStyleSheet(
            f"color: {ThemeColors.Warning}; font-size: 9pt;"
        )
