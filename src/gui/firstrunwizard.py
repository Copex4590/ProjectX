# ============================================================================
# First Run Wizard
# ============================================================================

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.aiswizard import AISSetupWidget
from gui.i18n_support import bind_language_refresh
from gui.observationwizard import ObservationSetupWidget
from gui.wizardhelp import add_wizard_back_button, add_wizard_next_button
from i18n import language_manager, tr
from preferences import SUPPORTED_LANGUAGES, preferences_manager

_LANGUAGE_LABELS = {
    "en": "English",
    "hu": "Magyar",
}

_STEP_LANGUAGE = 0
_STEP_WELCOME = 1
_STEP_OBSERVATION = 2
_STEP_AIS = 3
_STEP_CAMERA = 4
_STEP_FINISH = 5


class FirstRunWizard(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModal(False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumWidth(560)
        self.setMinimumHeight(520)

        self._add_camera_now = False

        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self._stack.setCurrentIndex(_STEP_LANGUAGE)
        self._sync_buttons()

    @property
    def open_camera_page(self) -> bool:

        return self._add_camera_now

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("Project X Setup"))
        self._welcome_title.setText(tr("Project X"))
        self._welcome_body.setText(tr("Welcome to Project X."))
        self._welcome_hint.setText(
            tr(
                "This wizard will help you configure "
                "your first Observation Point."
            )
        )
        self._language_title.setText(tr("Choose your language"))
        self._english_option.setText(tr("English"))
        self._hungarian_option.setText(tr("Magyar"))
        self._observation_setup.refresh_translations()
        self._ais_setup.refresh_translations()
        self._camera_title.setText(
            tr("Would you like to add your first camera now?")
        )
        self._camera_yes_option.setText(tr("Yes"))
        self._camera_skip_option.setText(
            tr("Skip (recommended if you only want AIS)")
        )
        self._finish_title.setText(tr("Configuration completed."))
        self._finish_body.setText(tr("Welcome to Project X."))

        self._continue_button.setText(tr("Continue"))
        self._back_button.setText(
            tr("Back")
        )
        self._next_button.setText(
            tr("Next")
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            tr("Cancel")
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            tr("Confirm")
        )
        self._open_dashboard_button.setText(tr("Open Dashboard"))

        self._sync_language_selection()
        self._sync_buttons()

    def _build_ui(self) -> None:

        self.setStyleSheet("""
            QDialog {
                background: #1d2127;
            }

            QLabel {
                color: #d5dbe3;
            }

            QLineEdit, QDoubleSpinBox {
                background: #252a31;
                color: white;
                border: 1px solid #3d4a5c;
                border-radius: 6px;
                padding: 6px 8px;
            }

            QRadioButton {
                color: #d5dbe3;
            }

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
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        language = QWidget()
        language_layout = QVBoxLayout(language)
        self._language_title = QLabel()
        self._language_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        language_layout.addWidget(self._language_title)

        self._english_option = QRadioButton()
        self._hungarian_option = QRadioButton()
        self._english_option.setChecked(True)

        language_layout.addWidget(self._english_option)
        language_layout.addWidget(self._hungarian_option)
        language_layout.addStretch()
        self._stack.addWidget(language)

        self._language_group = QButtonGroup(self)
        self._language_group.addButton(self._english_option, 0)
        self._language_group.addButton(self._hungarian_option, 1)

        welcome = QWidget()
        welcome_layout = QVBoxLayout(welcome)
        self._welcome_title = QLabel()
        self._welcome_title.setAlignment(Qt.AlignCenter)
        self._welcome_title.setStyleSheet(
            "font-size: 22pt; font-weight: bold; color: white;"
        )
        welcome_layout.addWidget(self._welcome_title)

        self._welcome_body = QLabel()
        self._welcome_body.setAlignment(Qt.AlignCenter)
        self._welcome_body.setStyleSheet("font-size: 13pt;")
        welcome_layout.addWidget(self._welcome_body)

        self._welcome_hint = QLabel()
        self._welcome_hint.setAlignment(Qt.AlignCenter)
        self._welcome_hint.setWordWrap(True)
        self._welcome_hint.setStyleSheet("color: #9aa4af; font-size: 10pt;")
        welcome_layout.addWidget(self._welcome_hint)
        welcome_layout.addStretch()

        self._continue_button = QPushButton()
        welcome_layout.addWidget(self._continue_button, alignment=Qt.AlignCenter)
        self._stack.addWidget(welcome)

        self._observation_setup = ObservationSetupWidget()
        self._stack.addWidget(self._observation_setup)

        self._ais_setup = AISSetupWidget()
        self._stack.addWidget(self._ais_setup)

        camera = QWidget()
        camera_layout = QVBoxLayout(camera)
        self._camera_title = QLabel()
        self._camera_title.setWordWrap(True)
        self._camera_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        camera_layout.addWidget(self._camera_title)

        self._camera_yes_option = QRadioButton()
        self._camera_skip_option = QRadioButton()
        self._camera_skip_option.setChecked(True)

        camera_layout.addWidget(self._camera_yes_option)
        camera_layout.addWidget(self._camera_skip_option)
        camera_layout.addStretch()
        self._stack.addWidget(camera)

        self._camera_group = QButtonGroup(self)
        self._camera_group.addButton(self._camera_yes_option, 0)
        self._camera_group.addButton(self._camera_skip_option, 1)

        finish = QWidget()
        finish_layout = QVBoxLayout(finish)
        self._finish_title = QLabel()
        self._finish_title.setAlignment(Qt.AlignCenter)
        self._finish_title.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: white;"
        )
        finish_layout.addWidget(self._finish_title)

        self._finish_body = QLabel()
        self._finish_body.setAlignment(Qt.AlignCenter)
        self._finish_body.setStyleSheet("font-size: 13pt;")
        finish_layout.addWidget(self._finish_body)
        finish_layout.addStretch()

        self._open_dashboard_button = QPushButton()
        finish_layout.addWidget(
            self._open_dashboard_button,
            alignment=Qt.AlignCenter,
        )
        self._stack.addWidget(finish)

        button_row = QHBoxLayout()
        self._button_box = QDialogButtonBox()
        self._back_button = add_wizard_back_button(self._button_box)
        self._next_button = add_wizard_next_button(self._button_box)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        button_row.addWidget(self._button_box)
        layout.addLayout(button_row)

    def _connect_signals(self) -> None:

        self._continue_button.clicked.connect(self._on_continue)
        self._open_dashboard_button.clicked.connect(self._on_finish)
        self._button_box.rejected.connect(self.reject)
        self._next_button.clicked.connect(
            self._on_next
        )
        self._back_button.clicked.connect(
            self._on_back
        )
        self._button_box.accepted.connect(self._on_confirm_or_ais)
        self._language_group.idClicked.connect(self._on_language_selected)
        self._camera_group.idClicked.connect(self._on_camera_selected)

    def _sync_language_selection(self) -> None:

        current = language_manager.current_language

        if current == "hu":
            self._hungarian_option.setChecked(True)
        else:
            self._english_option.setChecked(True)

    def _sync_buttons(self) -> None:

        step = self._stack.currentIndex()
        back_button = self._back_button
        next_button = self._next_button
        cancel_button = self._button_box.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        confirm_button = self._button_box.button(
            QDialogButtonBox.StandardButton.Ok
        )

        self._continue_button.setVisible(step == _STEP_WELCOME)
        self._open_dashboard_button.setVisible(step == _STEP_FINISH)

        back_button.setVisible(
            step not in (_STEP_LANGUAGE, _STEP_FINISH)
        )
        cancel_button.setVisible(
            step not in (_STEP_WELCOME, _STEP_FINISH)
        )

        if step == _STEP_OBSERVATION:
            self._observation_setup.update_outer_buttons(
                back_button,
                next_button,
                confirm_button,
            )
        elif step == _STEP_AIS:
            self._ais_setup.update_outer_buttons(
                back_button,
                next_button,
                confirm_button,
            )
        else:
            confirm_button.setVisible(False)
            next_button.setVisible(step in (_STEP_LANGUAGE, _STEP_CAMERA))

        if step == _STEP_LANGUAGE:
            back_button.setEnabled(False)
        elif step == _STEP_WELCOME:
            back_button.setEnabled(True)
        elif step == _STEP_CAMERA:
            back_button.setEnabled(True)
        elif step == _STEP_FINISH:
            back_button.setEnabled(False)

    def _on_continue(self) -> None:

        self._stack.setCurrentIndex(_STEP_OBSERVATION)
        self._observation_setup.on_enter()
        self._sync_buttons()

    def _persist_language_selection(self) -> None:

        button_id = self._language_group.checkedId()

        if button_id < 0:
            button_id = 0

        code = SUPPORTED_LANGUAGES[button_id]
        language_manager.set_language(code)

    def _on_language_selected(self, button_id: int) -> None:

        code = SUPPORTED_LANGUAGES[button_id]
        language_manager.set_language(code)

    def _on_camera_selected(self, button_id: int) -> None:

        self._add_camera_now = button_id == 0

    def _on_next(self) -> None:

        step = self._stack.currentIndex()

        if step == _STEP_LANGUAGE:
            self._persist_language_selection()
            self._stack.setCurrentIndex(_STEP_WELCOME)
        elif step == _STEP_OBSERVATION:
            self._observation_setup.handle_next()
        elif step == _STEP_AIS:
            if self._ais_setup.handle_next():
                self._ais_setup.on_leave()
                self._stack.setCurrentIndex(_STEP_CAMERA)
        elif step == _STEP_CAMERA:
            self._stack.setCurrentIndex(_STEP_FINISH)

        self._sync_buttons()

    def _on_back(self) -> None:

        step = self._stack.currentIndex()

        if step == _STEP_WELCOME:
            self._stack.setCurrentIndex(_STEP_LANGUAGE)
        elif step == _STEP_OBSERVATION:
            if self._observation_setup.handle_back():
                self._observation_setup.on_leave()
                self._stack.setCurrentIndex(_STEP_WELCOME)
        elif step == _STEP_AIS:
            if self._ais_setup.handle_back():
                self._ais_setup.on_leave()
                self._stack.setCurrentIndex(_STEP_OBSERVATION)
                self._observation_setup.on_enter()
        elif step == _STEP_CAMERA:
            self._stack.setCurrentIndex(_STEP_AIS)
            self._ais_setup.on_enter()

        self._sync_buttons()

    def _on_confirm_or_ais(self) -> None:

        if self._stack.currentIndex() == _STEP_AIS:
            self._on_ais_confirm()
            return

        self._on_confirm()

    def _on_confirm(self) -> None:

        if self._stack.currentIndex() != _STEP_OBSERVATION:
            return

        if not self._observation_setup.handle_confirm():
            return

        self._observation_setup.on_leave()
        self._stack.setCurrentIndex(_STEP_AIS)
        self._ais_setup.on_enter()
        self._sync_buttons()

    def _on_ais_confirm(self) -> None:

        if self._stack.currentIndex() != _STEP_AIS:
            return

        if not self._ais_setup.handle_confirm():
            return

        self._ais_setup.on_leave()
        self._stack.setCurrentIndex(_STEP_CAMERA)
        self._sync_buttons()

    def _on_finish(self) -> None:

        self._add_camera_now = self._camera_yes_option.isChecked()
        preferences_manager.set_first_run_completed(True)
        self.accept()
