# ============================================================================
# Project X
# Settings Page
# ============================================================================

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gui.settings.cameradiagnosticspanel import CameraDiagnosticsPanel
from gui.settings.playbacksettings import PlaybackSettingsPage
from i18n import language_manager, tr
from preferences import (
    SUPPORTED_LANGUAGES,
    SUPPORTED_VESSEL_CARD_LAYOUTS,
    preferences_manager,
)

_LANGUAGE_LABELS = {
    "en": "English",
    "hu": "Magyar",
}

_LAYOUT_LABELS = {
    "compact": "Compact",
    "standard": "Standard",
    "detailed": "Detailed",
    "media": "Media",
}


class SettingsPage(QWidget):

    personalization_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._build_ui()
        self._connect_signals()
        self.refresh()

    def refresh(self) -> None:

        preferences = preferences_manager.get()

        self._sync_language_combo(preferences.language)
        self._sync_layout_combo(preferences.vessel_card_layout)
        self.playback_settings.load_settings()
        self.camera_diagnostics.refresh()
        self._refresh_labels()

    def showEvent(self, event: QShowEvent) -> None:

        super().showEvent(event)
        self.camera_diagnostics.refresh()

    def _build_ui(self) -> None:

        self.setStyleSheet("background: #1d2127;")

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        outer_layout.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet("background: #1d2127;")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(
            "color: white; font-size: 26pt; font-weight: bold;"
        )
        layout.addWidget(self.title_label)

        personalization = QFrame()
        personalization.setStyleSheet("""
            QFrame {
                background: #252a31;
                border: 1px solid #3d4a5c;
                border-radius: 10px;
            }

            QLabel[role="section"] {
                color: #d5dbe3;
                font-size: 12pt;
                font-weight: 600;
            }

            QLabel[role="field"] {
                color: #9aa4af;
                font-size: 10pt;
                font-weight: 600;
            }

            QComboBox {
                background: #1d2127;
                color: white;
                border: 1px solid #3d4a5c;
                border-radius: 6px;
                padding: 6px 8px;
            }
        """)
        personalization_layout = QVBoxLayout(personalization)
        personalization_layout.setContentsMargins(16, 16, 16, 16)
        personalization_layout.setSpacing(12)

        self.section_label = QLabel()
        self.section_label.setProperty("role", "section")
        personalization_layout.addWidget(self.section_label)

        form = QFormLayout()
        form.setSpacing(12)

        self.language_label = QLabel()
        self.language_label.setProperty("role", "field")
        self.language_combo = QComboBox()
        for code in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(
                _LANGUAGE_LABELS.get(code, code),
                code,
            )
        form.addRow(self.language_label, self.language_combo)

        self.layout_label = QLabel()
        self.layout_label.setProperty("role", "field")
        self.layout_combo = QComboBox()
        for layout_name in SUPPORTED_VESSEL_CARD_LAYOUTS:
            self.layout_combo.addItem(
                _LAYOUT_LABELS.get(layout_name, layout_name),
                layout_name,
            )
        form.addRow(self.layout_label, self.layout_combo)

        personalization_layout.addLayout(form)
        layout.addWidget(personalization)

        self.playback_settings = PlaybackSettingsPage()
        self.playback_settings.setStyleSheet("""
            QFrame {
                background: #252a31;
                border: 1px solid #3d4a5c;
                border-radius: 10px;
                padding: 4px;
            }

            QLabel[role="section"] {
                color: #d5dbe3;
                font-size: 12pt;
                font-weight: 600;
            }

            QLabel[role="field"] {
                color: #9aa4af;
                font-size: 10pt;
                font-weight: 600;
            }

            QLabel[role="caption"] {
                color: #7d8794;
                font-size: 9pt;
            }

            QComboBox, QLineEdit {
                background: #1d2127;
                color: white;
                border: 1px solid #3d4a5c;
                border-radius: 6px;
                padding: 6px 8px;
            }

            QPushButton {
                background: #1976d2;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.playback_settings)

        self.camera_diagnostics = CameraDiagnosticsPanel()
        self.camera_diagnostics.setMinimumHeight(320)
        self.camera_diagnostics.setStyleSheet("""
            QFrame {
                background: #252a31;
                border: 1px solid #3d4a5c;
                border-radius: 10px;
                padding: 4px;
            }

            QLabel[role="section"] {
                color: #d5dbe3;
                font-size: 12pt;
                font-weight: 600;
            }

            QLabel[role="summary-title"] {
                color: #9aa4af;
                font-size: 9pt;
                font-weight: 600;
            }

            QLabel[role="summary-value"] {
                color: white;
                font-size: 16pt;
                font-weight: bold;
            }

            QComboBox, QPushButton {
                background: #1d2127;
                color: white;
                border: 1px solid #3d4a5c;
                border-radius: 6px;
                padding: 6px 8px;
            }

            QPushButton {
                background: #1976d2;
                border: none;
                padding: 8px 12px;
            }

            QTableWidget {
                background: #1d2127;
                color: white;
                border: 1px solid #3d4a5c;
                gridline-color: #3d4a5c;
            }

            QHeaderView::section {
                background: #2a3548;
                color: #d5dbe3;
                border: 1px solid #3d4a5c;
                padding: 6px;
            }
        """)
        layout.addWidget(self.camera_diagnostics)

        layout.addStretch()

    def _connect_signals(self) -> None:

        self.language_combo.currentIndexChanged.connect(
            self._on_language_changed
        )
        self.layout_combo.currentIndexChanged.connect(
            self._on_layout_changed
        )
        language_manager.language_changed.connect(
            lambda _code: self._refresh_labels()
        )

    def refresh_translations(self) -> None:

        self._refresh_labels()

    def _refresh_labels(self) -> None:

        self.title_label.setText(tr("Settings"))
        self.section_label.setText(tr("Personalization"))
        self.language_label.setText(tr("Language"))
        self.layout_label.setText(tr("Vessel Card"))

        playback_refresh = getattr(
            self.playback_settings,
            "refresh_translations",
            None,
        )

        if callable(playback_refresh):
            playback_refresh()

        diagnostics_refresh = getattr(
            self.camera_diagnostics,
            "refresh_translations",
            None,
        )

        if callable(diagnostics_refresh):
            diagnostics_refresh()

        current_language = self.language_combo.currentData()
        current_layout = self.layout_combo.currentData()

        self.language_combo.blockSignals(True)
        for index in range(self.language_combo.count()):
            code = self.language_combo.itemData(index)
            label_key = _LANGUAGE_LABELS.get(code, code)
            self.language_combo.setItemText(index, tr(label_key))
        self._sync_language_combo(current_language)
        self.language_combo.blockSignals(False)

        self.layout_combo.blockSignals(True)
        for index in range(self.layout_combo.count()):
            layout_name = self.layout_combo.itemData(index)
            label_key = _LAYOUT_LABELS.get(layout_name, layout_name)
            self.layout_combo.setItemText(index, tr(label_key))
        self._sync_layout_combo(current_layout)
        self.layout_combo.blockSignals(False)

    def _sync_language_combo(self, language: str) -> None:

        index = self.language_combo.findData(language)

        if index < 0:
            index = 0

        self.language_combo.setCurrentIndex(index)

    def _sync_layout_combo(self, layout_name: str) -> None:

        index = self.layout_combo.findData(layout_name)

        if index < 0:
            index = 0

        self.layout_combo.setCurrentIndex(index)

    def _on_language_changed(self, _index: int) -> None:

        code = self.language_combo.currentData()

        if not code:
            return

        if code == language_manager.current_language:
            return

        language_manager.set_language(code)
        self.personalization_changed.emit()

    def _on_layout_changed(self, _index: int) -> None:

        layout_name = self.layout_combo.currentData()

        if not layout_name:
            return

        preferences = preferences_manager.get()

        if layout_name == preferences.vessel_card_layout:
            return

        preferences_manager.set_vessel_card_layout(layout_name)
        self.personalization_changed.emit()
