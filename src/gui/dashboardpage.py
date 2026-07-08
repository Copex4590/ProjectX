from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from database import registry
from ais import ais_manager
from camera import camera_manager
from gui.aiswizard import AISWizard
from gui.rtlsdrdiagnosticsdialog import RTLSdrDiagnosticsDialog
from gui.rtlsdrwizard import RTLSdrWizard
from gui.wizardhelp import show_wizard_help
from gui.camerawizard import CameraWizard
from gui.i18n_support import bind_language_refresh
from gui.observationwizard import ObservationWizard
from gui.settings.cameradiagnosticspanel import CameraDiagnosticsPanel
from gui.settings.playbacksettings import PlaybackSettingsPage
from i18n import language_manager, tr
from logbook import logbook_manager
from observation import observation_manager
from preferences import (
    SUPPORTED_LANGUAGES,
    SUPPORTED_VESSEL_CARD_LAYOUTS,
    preferences_manager,
)
from rtl import rtl_manager

_CARD_STYLE = """
    QFrame {
        background: #252a31;
        border: 1px solid #3d4a5c;
        border-radius: 10px;
    }
"""

_BUTTON_STYLE = """
    QPushButton {
        background: #243651;
        color: white;
        border: 1px solid #2d5a8e;
        border-radius: 6px;
        padding: 6px 12px;
    }
    QPushButton:hover {
        background: #2d4a6f;
    }
    QPushButton:disabled {
        color: #7a8494;
    }
"""

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


class InfoCard(QFrame):

    def __init__(self, title_key: str):

        super().__init__()

        self._title_key = title_key

        self.setStyleSheet("""
            QFrame{
                background:#252a31;
                border:1px solid #3d4a5c;
                border-radius:10px;
            }
        """)

        layout = QVBoxLayout(self)

        self.title = QLabel(tr(title_key))
        self.title.setAlignment(Qt.AlignCenter)

        self.title.setStyleSheet("""
            color:#bbbbbb;
            font-size:12pt;
        """)

        self.value = QLabel(tr("Not available"))
        self.value.setAlignment(Qt.AlignCenter)

        self.value.setStyleSheet("""
            color:white;
            font-size:28pt;
            font-weight:bold;
        """)

        layout.addWidget(self.title)
        layout.addWidget(self.value)


class _RenameDialog(QDialog):

    def __init__(self, current_name: str, parent=None):
        super().__init__(parent)

        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)

        self._label = QLabel()
        layout.addWidget(self._label)

        self._input = QLineEdit(current_name)
        layout.addWidget(self._input)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self._button_box)

        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("Rename"))
        self._label.setText(tr("Observation Point name"))
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            tr("Confirm")
        )
        self._button_box.button(
            QDialogButtonBox.StandardButton.Cancel
        ).setText(tr("Cancel"))

    def name(self) -> str:

        return self._input.text().strip()


class DashboardPage(QWidget):

    personalization_changed = Signal()

    def __init__(self):
        super().__init__()

        root_layout = QVBoxLayout(self)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )

        self._observation_wizard: ObservationWizard | None = None

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._title_label = QLabel(tr("Dashboard"))
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setStyleSheet("""
            font-size:26pt;
            font-weight:bold;
            color:white;
        """)
        layout.addWidget(self._title_label)

        self._subtitle_label = QLabel()
        self._subtitle_label.setAlignment(Qt.AlignCenter)
        self._subtitle_label.setStyleSheet(
            "color: #9aa4af; font-size: 11pt; padding-bottom: 4px;"
        )
        layout.addWidget(self._subtitle_label)

        summary_grid = QGridLayout()
        summary_grid.setSpacing(12)

        self.ships = InfoCard("Ships")
        self.ais = InfoCard("AIS")
        self.last = InfoCard("Last Ship")

        self.ais.value.setText(tr("Disconnected"))

        summary_grid.addWidget(self.ships, 0, 0)
        summary_grid.addWidget(self.ais, 0, 1)
        summary_grid.addWidget(self.last, 0, 2)
        layout.addLayout(summary_grid)

        columns = QHBoxLayout()
        columns.setSpacing(12)

        left_column = QVBoxLayout()
        left_column.setSpacing(12)
        right_column = QVBoxLayout()
        right_column.setSpacing(12)

        self._observation_card = QFrame()
        self._observation_card.setStyleSheet(_CARD_STYLE)
        observation_layout = QVBoxLayout(self._observation_card)
        observation_layout.setContentsMargins(16, 16, 16, 16)
        observation_layout.setSpacing(10)

        self._observation_title = QLabel()
        self._observation_title.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: white;"
        )
        observation_layout.addWidget(self._observation_title)

        self._observation_map_hint = QLabel()
        self._observation_map_hint.setWordWrap(True)
        self._observation_map_hint.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        observation_layout.addWidget(self._observation_map_hint)

        info_grid = QGridLayout()
        info_grid.setColumnStretch(1, 1)

        self._name_caption = QLabel()
        self._name_value = QLabel()
        self._coords_caption = QLabel()
        self._coords_value = QLabel()
        self._status_caption = QLabel()
        self._status_value = QLabel()

        for caption in (
            self._name_caption,
            self._coords_caption,
            self._status_caption,
        ):
            caption.setStyleSheet("color: #9aa4af;")

        for value in (
            self._name_value,
            self._coords_value,
            self._status_value,
        ):
            value.setStyleSheet("color: white; font-weight: 600;")
            value.setWordWrap(True)

        info_grid.addWidget(self._name_caption, 0, 0)
        info_grid.addWidget(self._name_value, 0, 1)
        info_grid.addWidget(self._coords_caption, 1, 0)
        info_grid.addWidget(self._coords_value, 1, 1)
        info_grid.addWidget(self._status_caption, 2, 0)
        info_grid.addWidget(self._status_value, 2, 1)
        observation_layout.addLayout(info_grid)

        selector_row = QHBoxLayout()
        self._point_selector_label = QLabel()
        self._point_selector = QComboBox()
        selector_row.addWidget(self._point_selector_label)
        selector_row.addWidget(self._point_selector, 1)
        self._selector_panel = QWidget()
        self._selector_panel.setLayout(selector_row)
        self._selector_panel.setVisible(False)
        observation_layout.addWidget(self._selector_panel)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self._rename_button = QPushButton()
        self._create_button = QPushButton()
        self._delete_button = QPushButton()
        self._set_active_button = QPushButton()

        for button in (
            self._rename_button,
            self._create_button,
            self._delete_button,
            self._set_active_button,
        ):
            button.setStyleSheet(_BUTTON_STYLE)

        button_row.addWidget(self._rename_button)
        button_row.addWidget(self._create_button)
        button_row.addWidget(self._delete_button)
        button_row.addWidget(self._set_active_button)
        button_row.addStretch()
        observation_layout.addLayout(button_row)

        self._cameras_card = QFrame()
        self._cameras_card.setStyleSheet(_CARD_STYLE)
        cameras_layout = QVBoxLayout(self._cameras_card)
        cameras_layout.setContentsMargins(16, 16, 16, 16)
        cameras_layout.setSpacing(10)

        self._cameras_title = QLabel()
        self._cameras_title.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: white;"
        )
        cameras_layout.addWidget(self._cameras_title)

        self._cameras_list = QVBoxLayout()
        self._cameras_list.setSpacing(6)
        cameras_layout.addLayout(self._cameras_list)

        self._no_cameras_label = QLabel()
        self._no_cameras_label.setStyleSheet("color: #9aa4af;")
        self._no_cameras_label.setVisible(False)
        cameras_layout.addWidget(self._no_cameras_label)

        self._cameras_help_button = QPushButton()
        self._cameras_help_button.setStyleSheet(_BUTTON_STYLE)
        self._cameras_help_button.setVisible(False)
        cameras_layout.addWidget(self._cameras_help_button)

        self._add_camera_button = QPushButton()
        self._add_camera_button.setStyleSheet(_BUTTON_STYLE)
        cameras_layout.addWidget(self._add_camera_button)

        self._logbook_card = QFrame()
        self._logbook_card.setStyleSheet(_CARD_STYLE)
        logbook_layout = QVBoxLayout(self._logbook_card)
        logbook_layout.setContentsMargins(16, 16, 16, 16)
        logbook_layout.setSpacing(10)

        self._logbook_title = QLabel()
        self._logbook_title.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: white;"
        )
        logbook_layout.addWidget(self._logbook_title)

        self._import_logbook_button = QPushButton()
        self._import_logbook_button.setStyleSheet(_BUTTON_STYLE)
        logbook_layout.addWidget(self._import_logbook_button)

        self._ais_card = QFrame()
        self._ais_card.setStyleSheet(_CARD_STYLE)
        ais_layout = QVBoxLayout(self._ais_card)
        ais_layout.setContentsMargins(16, 16, 16, 16)
        ais_layout.setSpacing(10)

        self._ais_title = QLabel()
        self._ais_title.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: white;"
        )
        ais_layout.addWidget(self._ais_title)

        ais_grid = QGridLayout()
        self._ais_provider_caption = QLabel()
        self._ais_provider_value = QLabel()
        self._ais_config_caption = QLabel()
        self._ais_config_value = QLabel()
        self._ais_connection_caption = QLabel()
        self._ais_connection_value = QLabel()

        for caption in (
            self._ais_provider_caption,
            self._ais_config_caption,
            self._ais_connection_caption,
        ):
            caption.setStyleSheet("color: #9aa4af;")

        for value in (
            self._ais_provider_value,
            self._ais_config_value,
            self._ais_connection_value,
        ):
            value.setStyleSheet("color: white; font-weight: 600;")
            value.setWordWrap(True)

        ais_grid.addWidget(self._ais_provider_caption, 0, 0)
        ais_grid.addWidget(self._ais_provider_value, 0, 1)
        ais_grid.addWidget(self._ais_config_caption, 1, 0)
        ais_grid.addWidget(self._ais_config_value, 1, 1)
        ais_grid.addWidget(self._ais_connection_caption, 2, 0)
        ais_grid.addWidget(self._ais_connection_value, 2, 1)
        ais_layout.addLayout(ais_grid)

        ais_button_row = QHBoxLayout()
        ais_button_row.setSpacing(8)

        self._ais_configure_button = QPushButton()
        self._ais_test_button = QPushButton()
        self._ais_change_button = QPushButton()

        for button in (
            self._ais_configure_button,
            self._ais_test_button,
            self._ais_change_button,
        ):
            button.setStyleSheet(_BUTTON_STYLE)

        ais_button_row.addWidget(self._ais_configure_button)
        ais_button_row.addWidget(self._ais_test_button)
        ais_button_row.addWidget(self._ais_change_button)
        ais_button_row.addStretch()
        ais_layout.addLayout(ais_button_row)

        self._rtl_card = QFrame()
        self._rtl_card.setStyleSheet(_CARD_STYLE)
        rtl_layout = QVBoxLayout(self._rtl_card)
        rtl_layout.setContentsMargins(16, 16, 16, 16)
        rtl_layout.setSpacing(10)

        self._rtl_title = QLabel()
        self._rtl_title.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: white;"
        )
        rtl_layout.addWidget(self._rtl_title)

        rtl_grid = QGridLayout()
        self._rtl_status_caption = QLabel()
        self._rtl_status_value = QLabel()
        self._rtl_connection_caption = QLabel()
        self._rtl_connection_value = QLabel()
        self._rtl_messages_caption = QLabel()
        self._rtl_messages_value = QLabel()

        for caption in (
            self._rtl_status_caption,
            self._rtl_connection_caption,
            self._rtl_messages_caption,
        ):
            caption.setStyleSheet("color: #9aa4af;")

        for value in (
            self._rtl_status_value,
            self._rtl_connection_value,
            self._rtl_messages_value,
        ):
            value.setStyleSheet("color: white; font-weight: 600;")

        rtl_grid.addWidget(self._rtl_status_caption, 0, 0)
        rtl_grid.addWidget(self._rtl_status_value, 0, 1)
        rtl_grid.addWidget(self._rtl_connection_caption, 1, 0)
        rtl_grid.addWidget(self._rtl_connection_value, 1, 1)
        rtl_grid.addWidget(self._rtl_messages_caption, 2, 0)
        rtl_grid.addWidget(self._rtl_messages_value, 2, 1)
        rtl_layout.addLayout(rtl_grid)

        rtl_button_row = QHBoxLayout()
        rtl_button_row.setSpacing(8)
        self._rtl_setup_button = QPushButton()
        self._rtl_test_button = QPushButton()
        self._rtl_diagnostics_button = QPushButton()

        for button in (
            self._rtl_setup_button,
            self._rtl_test_button,
            self._rtl_diagnostics_button,
        ):
            button.setStyleSheet(_BUTTON_STYLE)

        rtl_button_row.addWidget(self._rtl_setup_button)
        rtl_button_row.addWidget(self._rtl_test_button)
        rtl_button_row.addWidget(self._rtl_diagnostics_button)
        rtl_button_row.addStretch()
        rtl_layout.addLayout(rtl_button_row)

        left_column.addWidget(self._ais_card)
        left_column.addWidget(self._rtl_card)
        left_column.addWidget(self._logbook_card)
        right_column.addWidget(self._observation_card)
        right_column.addWidget(self._cameras_card)
        columns.addLayout(left_column, 1)
        columns.addLayout(right_column, 1)
        layout.addLayout(columns)

        self._configuration_card = QFrame()
        self._configuration_card.setStyleSheet(_CARD_STYLE)
        configuration_layout = QVBoxLayout(self._configuration_card)
        configuration_layout.setContentsMargins(16, 16, 16, 16)
        configuration_layout.setSpacing(16)

        self._configuration_title = QLabel()
        self._configuration_title.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: white;"
        )
        configuration_layout.addWidget(self._configuration_title)

        personalization = QFrame()
        personalization.setStyleSheet("""
            QFrame {
                background: #1d2127;
                border: 1px solid #3d4a5c;
                border-radius: 8px;
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
                background: #252a31;
                color: white;
                border: 1px solid #3d4a5c;
                border-radius: 6px;
                padding: 6px 8px;
            }
        """)
        personalization_layout = QVBoxLayout(personalization)
        personalization_layout.setContentsMargins(16, 16, 16, 16)
        personalization_layout.setSpacing(12)

        self._personalization_title = QLabel()
        self._personalization_title.setProperty("role", "section")
        personalization_layout.addWidget(self._personalization_title)

        form = QFormLayout()
        form.setSpacing(12)

        self._language_label = QLabel()
        self._language_label.setProperty("role", "field")
        self._language_combo = QComboBox()
        for code in SUPPORTED_LANGUAGES:
            self._language_combo.addItem(
                _LANGUAGE_LABELS.get(code, code),
                code,
            )
        form.addRow(self._language_label, self._language_combo)

        self._layout_label = QLabel()
        self._layout_label.setProperty("role", "field")
        self._layout_combo = QComboBox()
        for layout_name in SUPPORTED_VESSEL_CARD_LAYOUTS:
            self._layout_combo.addItem(
                _LAYOUT_LABELS.get(layout_name, layout_name),
                layout_name,
            )
        form.addRow(self._layout_label, self._layout_combo)

        personalization_layout.addLayout(form)
        configuration_layout.addWidget(personalization)

        self.playback_settings = PlaybackSettingsPage()
        self.playback_settings.setStyleSheet("""
            QFrame {
                background: #1d2127;
                border: 1px solid #3d4a5c;
                border-radius: 8px;
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
                background: #252a31;
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
        configuration_layout.addWidget(self.playback_settings)

        self.camera_diagnostics = CameraDiagnosticsPanel()
        self.camera_diagnostics.setMinimumHeight(320)
        self.camera_diagnostics.setStyleSheet("""
            QFrame {
                background: #1d2127;
                border: 1px solid #3d4a5c;
                border-radius: 8px;
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
                background: #252a31;
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
                background: #252a31;
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
        configuration_layout.addWidget(self.camera_diagnostics)
        layout.addWidget(self._configuration_card)

        layout.addStretch()

        self._scroll.setWidget(content)
        root_layout.addWidget(self._scroll)

        self._rename_button.clicked.connect(self._rename_active)
        self._create_button.clicked.connect(self._create_new)
        self._delete_button.clicked.connect(self._delete_active)
        self._set_active_button.clicked.connect(self._set_selected_active)
        self._point_selector.currentIndexChanged.connect(
            self._on_selector_changed
        )
        self._language_combo.currentIndexChanged.connect(
            self._on_language_changed
        )
        self._layout_combo.currentIndexChanged.connect(
            self._on_layout_changed
        )
        language_manager.language_changed.connect(
            lambda _code: self._refresh_configuration_labels()
        )
        self._add_camera_button.clicked.connect(self._add_camera)
        self._import_logbook_button.clicked.connect(self._import_legacy_logbook)
        self._cameras_help_button.clicked.connect(
            lambda: show_wizard_help(
                self,
                "Cameras help — title",
                "Cameras help — body",
            )
        )
        self._ais_configure_button.clicked.connect(self._configure_ais)
        self._ais_test_button.clicked.connect(self._test_ais)
        self._ais_change_button.clicked.connect(self._change_ais)
        self._rtl_setup_button.clicked.connect(self._setup_rtl)
        self._rtl_test_button.clicked.connect(self._test_rtl)
        self._rtl_diagnostics_button.clicked.connect(self._rtl_diagnostics)

        bind_language_refresh(self.refresh_translations)

        self.refresh_translations()
        self.refresh_configuration()
        self.update_dashboard()
        self.refresh_observation()
        self.refresh_cameras()

    def showEvent(self, event: QShowEvent) -> None:

        super().showEvent(event)
        self.camera_diagnostics.refresh()

    def open_configuration_section(self, *, focus_diagnostics: bool = False) -> None:

        self.refresh_configuration()

        if focus_diagnostics:
            self._scroll.ensureWidgetVisible(self.camera_diagnostics)

    def refresh_configuration(self) -> None:

        preferences = preferences_manager.get()

        self._sync_language_combo(preferences.language)
        self._sync_layout_combo(preferences.vessel_card_layout)
        self.playback_settings.load_settings()
        self.camera_diagnostics.refresh()
        self._refresh_configuration_labels()

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Dashboard"))
        self._subtitle_label.setText(tr("Operational control center"))
        self.ships.title.setText(tr("Ships"))
        self.ais.title.setText(tr("AIS"))
        self.last.title.setText(tr("Last Ship"))

        self._observation_title.setText(tr("Observation Point"))
        self._observation_map_hint.setText(
            tr("Geographic editing is available on the Map.")
        )
        self._name_caption.setText(tr("Name"))
        self._coords_caption.setText(tr("Coordinates"))
        self._status_caption.setText(tr("Status"))
        self._point_selector_label.setText(tr("Observation Point"))

        self._rename_button.setText(tr("Rename"))
        self._create_button.setText(tr("Create new"))
        self._delete_button.setText(tr("Delete"))
        self._set_active_button.setText(tr("Set active"))
        self._cameras_title.setText(tr("Attached Cameras"))
        self._no_cameras_label.setText(tr("No cameras"))
        self._cameras_help_button.setText(tr("Help"))
        self._add_camera_button.setText(tr("Add Camera"))
        self._logbook_title.setText(tr("Vessel Logbook"))
        self._import_logbook_button.setText(tr("Import Legacy Logbook"))
        self._ais_title.setText(tr("AIS Source"))
        self._ais_provider_caption.setText(tr("Provider"))
        self._ais_config_caption.setText(tr("Status"))
        self._ais_connection_caption.setText(tr("Connection"))
        self._ais_configure_button.setText(tr("Configure"))
        self._ais_test_button.setText(tr("Test"))
        self._ais_change_button.setText(tr("Change"))
        self._rtl_title.setText(tr("RTL-SDR"))
        self._rtl_status_caption.setText(tr("Status"))
        self._rtl_connection_caption.setText(tr("RTL Status"))
        self._rtl_messages_caption.setText(tr("AIS Messages"))
        self._rtl_setup_button.setText(tr("Setup"))
        self._rtl_test_button.setText(tr("Test"))
        self._rtl_diagnostics_button.setText(tr("Diagnostics"))
        self._configuration_title.setText(tr("Configuration"))

        self._create_button.setToolTip(tr("Create a new observation point"))
        self._add_camera_button.setToolTip(
            tr("Add a camera to the active observation point")
        )
        self._ais_configure_button.setToolTip(tr("Configure AIS data source"))
        self._ais_test_button.setToolTip(tr("Test AIS connection"))
        self._rtl_setup_button.setToolTip(tr("Open RTL-SDR setup wizard"))
        self._rtl_test_button.setToolTip(tr("Run a short RTL reception test"))
        self._rtl_diagnostics_button.setToolTip(tr("View RTL-SDR diagnostics"))

        self._refresh_configuration_labels()
        self.refresh_observation()
        self.refresh_cameras()
        self.refresh_ais()
        self.refresh_rtl()

    def refresh_observation(self) -> None:

        points = observation_manager.all()
        active = observation_manager.active()

        self._populate_selector(points, active)

        if active is not None:
            self._name_value.setText(active.name)
            self._coords_value.setText(
                f"{active.latitude:.5f}, {active.longitude:.5f}"
            )
            self._status_value.setText(tr("Active"))
            self._status_value.setStyleSheet("color: #66bb6a; font-weight: 600;")
            has_point = True
        else:
            self._name_value.setText(tr("No observation point"))
            self._coords_value.setText(tr("Not available"))
            self._status_value.setText(tr("Not configured"))
            self._status_value.setStyleSheet("color: #9aa4af; font-weight: 600;")
            has_point = False

        self._rename_button.setEnabled(has_point)
        self._delete_button.setEnabled(has_point)
        self._set_active_button.setEnabled(
            has_point and len(points) > 1
        )
        self._selector_panel.setVisible(len(points) > 1)
        self.refresh_cameras()

    def refresh_cameras(self) -> None:

        while self._cameras_list.count():
            item = self._cameras_list.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

        active = observation_manager.active()
        has_point = active is not None
        self._add_camera_button.setEnabled(has_point)

        if not has_point:
            self._no_cameras_label.setVisible(True)
            self._cameras_help_button.setVisible(True)
            return

        cameras = camera_manager.by_observation(active.id)
        self._no_cameras_label.setVisible(not cameras)
        self._cameras_help_button.setVisible(not cameras)

        for camera in cameras:
            row = QHBoxLayout()
            row_widget = QWidget()
            row_widget.setLayout(row)

            name_label = QLabel(camera.name)
            name_label.setStyleSheet("color: white; font-weight: 600;")
            row.addWidget(name_label, 1)

            status_text = tr("Enabled") if camera.enabled else tr("Disabled")
            status_label = QLabel(status_text)
            status_label.setStyleSheet(
                "color: #66bb6a;" if camera.enabled else "color: #9aa4af;"
            )
            row.addWidget(status_label)

            edit_button = QPushButton(tr("Edit"))
            delete_button = QPushButton(tr("Delete"))

            for button in (edit_button, delete_button):
                button.setStyleSheet("""
                    QPushButton {
                        background: #243651;
                        color: white;
                        border: 1px solid #2d5a8e;
                        border-radius: 6px;
                        padding: 4px 10px;
                    }
                    QPushButton:hover {
                        background: #2d4a6f;
                    }
                """)

            edit_button.clicked.connect(
                lambda _checked=False, item=camera: self._edit_camera(item)
            )
            delete_button.clicked.connect(
                lambda _checked=False, item=camera: self._delete_camera(item)
            )

            row.addWidget(edit_button)
            row.addWidget(delete_button)
            self._cameras_list.addWidget(row_widget)

    def refresh_ais(self) -> None:

        self._ais_provider_value.setText(ais_manager.provider_name())

        if ais_manager.is_configured():
            self._ais_config_value.setText(tr("Configured"))
            self._ais_config_value.setStyleSheet("color: #66bb6a; font-weight: 600;")
        else:
            self._ais_config_value.setText(tr("Not configured"))
            self._ais_config_value.setStyleSheet("color: #9aa4af; font-weight: 600;")

        if ais_manager.is_connected():
            self._ais_connection_value.setText(tr("Connected"))
            self._ais_connection_value.setStyleSheet("color: #66bb6a; font-weight: 600;")
            self.ais.value.setText(tr("Connected"))
        else:
            self._ais_connection_value.setText(tr("Disconnected"))
            self._ais_connection_value.setStyleSheet("color: #9aa4af; font-weight: 600;")
            self.ais.value.setText(tr("Disconnected"))

    def _configure_ais(self) -> None:

        wizard = AISWizard(self)

        if wizard.exec() == QDialog.DialogCode.Accepted:
            self.refresh_ais()
        self.refresh_rtl()

    def _change_ais(self) -> None:

        self._configure_ais()

    def _test_ais(self) -> None:

        if not ais_manager.is_configured():
            QMessageBox.information(
                self,
                tr("AIS Source"),
                tr("AIS source is not configured yet."),
            )
            return

        result = ais_manager.test_current()

        if result.success:
            QMessageBox.information(
                self,
                tr("AIS Source"),
                f"✓ {tr(result.message)}",
            )
            return

        QMessageBox.warning(
            self,
            tr("AIS Source"),
            tr(result.message),
        )

    def refresh_rtl(self) -> None:

        status = rtl_manager.status_label()

        if status == "connected":
            self._rtl_status_value.setText(tr("Connected"))
            self._rtl_status_value.setStyleSheet("color: #66bb6a; font-weight: 600;")
            self._rtl_connection_value.setText("🟢 " + tr("Connected"))
        elif status == "configured":
            self._rtl_status_value.setText(tr("Configured"))
            self._rtl_status_value.setStyleSheet("color: #bbbbbb; font-weight: 600;")
            self._rtl_connection_value.setText("⚪ " + tr("Disconnected"))
        else:
            self._rtl_status_value.setText(tr("Not configured"))
            self._rtl_status_value.setStyleSheet("color: #9aa4af; font-weight: 600;")
            self._rtl_connection_value.setText("⚪ " + tr("Disconnected"))

        stats = rtl_manager.reception_stats()
        self._rtl_messages_value.setText(str(stats.message_count))

    def _setup_rtl(self) -> None:

        wizard = RTLSdrWizard(self)

        if wizard.exec() == QDialog.DialogCode.Accepted:
            self.refresh_rtl()
            self.refresh_ais()
        else:
            self.refresh_rtl()

    def _test_rtl(self) -> None:

        result = rtl_manager.test_reception(duration_seconds=8.0)

        if result.success:
            QMessageBox.information(
                self,
                tr("RTL-SDR"),
                f"✓ {tr('Reception test successful')}\n"
                f"{tr('AIS messages received')}: {result.message_count}\n"
                f"{tr('Ships detected')}: {result.ships_detected}",
            )
        else:
            QMessageBox.warning(
                self,
                tr("RTL-SDR"),
                result.message or tr("No AIS messages received yet."),
            )

        self.refresh_rtl()

    def _rtl_diagnostics(self) -> None:

        dialog = RTLSdrDiagnosticsDialog(self)
        dialog.exec()
        self.refresh_rtl()

    def _import_legacy_logbook(self) -> None:

        source = QFileDialog.getExistingDirectory(
            self,
            tr("Import Legacy Logbook"),
            "",
            QFileDialog.Option.ShowDirsOnly,
        )

        if not source:
            return

        try:
            result = logbook_manager.import_legacy(source)
        except FileNotFoundError:
            QMessageBox.warning(
                self,
                tr("Import Legacy Logbook"),
                tr("The selected folder does not contain a legacy logbook."),
            )
            return

        QMessageBox.information(
            self,
            tr("Import Legacy Logbook"),
            tr(
                "Legacy logbook import complete. "
                "Imported: {imported}, skipped: {skipped}."
            ).format(
                imported=result.imported_folders,
                skipped=result.skipped_folders,
            ),
        )

    def _add_camera(self) -> None:

        point_id = self._active_point_id()

        if point_id is None:
            return

        wizard = CameraWizard(point_id, self)

        if wizard.exec() == QDialog.DialogCode.Accepted:
            self.refresh_cameras()

    def _edit_camera(self, camera) -> None:

        point_id = self._active_point_id()

        if point_id is None:
            return

        wizard = CameraWizard(point_id, self, camera=camera)

        if wizard.exec() == QDialog.DialogCode.Accepted:
            self.refresh_cameras()

    def _delete_camera(self, camera) -> None:

        answer = QMessageBox.question(
            self,
            tr("Delete"),
            tr("Delete camera '{name}'?").format(name=camera.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        camera_manager.remove(camera.id)
        self.refresh_cameras()

    def _populate_selector(self, points, active) -> None:

        self._point_selector.blockSignals(True)
        self._point_selector.clear()

        for point in points:
            label = point.name

            if point.active:
                label = f"{label} ({tr('Active')})"

            self._point_selector.addItem(label, point.id)

        if active is not None:
            for index in range(self._point_selector.count()):
                if self._point_selector.itemData(index) == active.id:
                    self._point_selector.setCurrentIndex(index)
                    break

        self._point_selector.blockSignals(False)

    def _active_point_id(self) -> str | None:

        active = observation_manager.active()
        return active.id if active else None

    def _rename_active(self) -> None:

        active = observation_manager.active()

        if active is None:
            return

        dialog = _RenameDialog(active.name, self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        new_name = dialog.name()

        if not new_name:
            return

        observation_manager.rename(active.id, new_name)

    def _create_new(self) -> None:

        if (
            self._observation_wizard is not None
            and self._observation_wizard.isVisible()
        ):
            self._observation_wizard.raise_()
            self._observation_wizard.activateWindow()
            return

        wizard = ObservationWizard(self)
        wizard.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        wizard.finished.connect(self._on_observation_wizard_finished)
        self._observation_wizard = wizard
        wizard.show()

    def _on_observation_wizard_finished(self, result: int) -> None:

        self._observation_wizard = None

        if result == QDialog.DialogCode.Accepted:
            self.refresh_observation()

    def _delete_active(self) -> None:

        active = observation_manager.active()

        if active is None:
            return

        answer = QMessageBox.question(
            self,
            tr("Delete"),
            tr("Delete observation point '{name}'?").format(
                name=active.name
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        observation_manager.delete(active.id)

    def _set_selected_active(self) -> None:

        point_id = self._point_selector.currentData()

        if not point_id:
            return

        observation_manager.set_active(str(point_id))

    def _on_selector_changed(self, _index: int) -> None:

        point_id = self._point_selector.currentData()

        if not point_id:
            return

        active = observation_manager.active()

        if active is not None and active.id == point_id:
            return

        observation_manager.set_active(str(point_id))

    def _refresh_configuration_labels(self) -> None:

        self._personalization_title.setText(tr("Personalization"))
        self._language_label.setText(tr("Language"))
        self._layout_label.setText(tr("Vessel Card"))

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

        current_language = self._language_combo.currentData()
        current_layout = self._layout_combo.currentData()

        self._language_combo.blockSignals(True)
        for index in range(self._language_combo.count()):
            code = self._language_combo.itemData(index)
            label_key = _LANGUAGE_LABELS.get(code, code)
            self._language_combo.setItemText(index, tr(label_key))
        self._sync_language_combo(current_language)
        self._language_combo.blockSignals(False)

        self._layout_combo.blockSignals(True)
        for index in range(self._layout_combo.count()):
            layout_name = self._layout_combo.itemData(index)
            label_key = _LAYOUT_LABELS.get(layout_name, layout_name)
            self._layout_combo.setItemText(index, tr(label_key))
        self._sync_layout_combo(current_layout)
        self._layout_combo.blockSignals(False)

    def _sync_language_combo(self, language: str) -> None:

        index = self._language_combo.findData(language)

        if index < 0:
            index = 0

        self._language_combo.setCurrentIndex(index)

    def _sync_layout_combo(self, layout_name: str) -> None:

        index = self._layout_combo.findData(layout_name)

        if index < 0:
            index = 0

        self._layout_combo.setCurrentIndex(index)

    def _on_language_changed(self, _index: int) -> None:

        code = self._language_combo.currentData()

        if not code:
            return

        if code == language_manager.current_language:
            return

        language_manager.set_language(code)
        self.personalization_changed.emit()

    def _on_layout_changed(self, _index: int) -> None:

        layout_name = self._layout_combo.currentData()

        if not layout_name:
            return

        preferences = preferences_manager.get()

        if layout_name == preferences.vessel_card_layout:
            return

        preferences_manager.set_vessel_card_layout(layout_name)
        self.personalization_changed.emit()

    def update_dashboard(self):

        ships = registry.all()

        self.ships.value.setText(str(len(ships)))

        if ships:
            self.last.value.setText(ships[-1].name)
        else:
            self.last.value.setText(tr("Not available"))

    def on_ship_updated(self):

        ships = registry.all()

        self.ships.value.setText(str(len(ships)))

        if ships:
            self.last.value.setText(ships[-1].name)
        else:
            self.last.value.setText(tr("Not available"))

        self.refresh_ais()
        self.refresh_rtl()
