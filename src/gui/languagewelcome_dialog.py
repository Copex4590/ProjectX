# ============================================================================
# Language Welcome Dialog — first launch language selection
# ============================================================================

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from gui.i18n_support import bind_language_refresh
from gui.theme import wizard_shell_stylesheet
from i18n import language_manager, tr
from preferences import SUPPORTED_LANGUAGES, preferences_manager


class LanguageWelcomeDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModal(True)
        self.setMinimumWidth(480)
        self.setMinimumHeight(320)
        self.setWindowTitle("Project X")

        self._build_ui()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("Project X Setup"))
        self._welcome_title.setText(tr("Welcome to Project X"))
        self._language_title.setText(tr("Choose your language"))
        self._english_option.setText(tr("English"))
        self._hungarian_option.setText(tr("Magyar"))
        self._next_button.setText(tr("Next"))

    def _build_ui(self) -> None:

        self.setStyleSheet(wizard_shell_stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self._welcome_title = QLabel()
        self._welcome_title.setStyleSheet(
            "font-size: 18pt; font-weight: bold; color: white;"
        )
        layout.addWidget(self._welcome_title)

        self._language_title = QLabel()
        self._language_title.setStyleSheet("font-size: 13pt; font-weight: bold;")
        layout.addWidget(self._language_title)

        self._english_option = QRadioButton()
        self._hungarian_option = QRadioButton()
        self._english_option.setChecked(True)
        layout.addWidget(self._english_option)
        layout.addWidget(self._hungarian_option)

        layout.addStretch()

        button_row = QHBoxLayout()
        button_row.addStretch()
        self._next_button = QPushButton()
        self._next_button.setMinimumWidth(120)
        self._next_button.clicked.connect(self._on_next)
        button_row.addWidget(self._next_button)
        layout.addLayout(button_row)

        self._language_group = QButtonGroup(self)
        self._language_group.addButton(self._english_option, 0)
        self._language_group.addButton(self._hungarian_option, 1)

    def _selected_language(self) -> str:

        button_id = self._language_group.checkedId()

        if button_id < 0:
            button_id = 0

        return SUPPORTED_LANGUAGES[button_id]

    def _on_next(self) -> None:

        language_manager.set_language(self._selected_language())
        preferences_manager.set_language_selected(True)
        self.accept()


def run_language_welcome_if_needed(parent=None) -> bool:

    if preferences_manager.get().language_selected:
        return True

    dialog = LanguageWelcomeDialog(parent)
    return dialog.exec() == QDialog.DialogCode.Accepted
