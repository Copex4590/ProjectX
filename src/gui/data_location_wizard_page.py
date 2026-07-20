# ============================================================================
# First-run Data Location Wizard Page (SAVE-107-C1)
# ============================================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from gui.theme import DANGER, TEXT_MUTED, WARNING, ThemeColors
from i18n import tr
from storage import default_data_directory

_CUSTOM_PATH_INPUT_STYLE = f"""
    background: {ThemeColors.Panel};
    color: white;
    border: 1px solid {ThemeColors.Border};
    border-radius: 6px;
    padding: 6px 8px;
"""


def format_display_path(path: Path) -> str:
    """Format a path for display, using ~ when under the user home directory."""

    expanded = path.expanduser()

    try:
        resolved = expanded.resolve()
        home = Path.home().resolve()

        if resolved == home:
            return "~"

        if resolved.is_relative_to(home):
            return "~/" + str(resolved.relative_to(home))
    except (OSError, RuntimeError, ValueError):
        pass

    return str(expanded)


class DataLocationWizardPage(QWidget):
    """First-run page for choosing where Project X stores user data."""

    selection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._custom_directory: Path | None = None
        self._build_ui()
        self._connect_signals()
        self._sync_custom_controls()
        self.refresh_translations()

    def refresh_translations(self) -> None:

        self._title.setText(tr("Project X Data Location"))
        self._description.setText(
            tr(
                "Choose where Project X stores its data before the application "
                "is initialized."
            )
        )
        self._recommended_option.setText(tr("Recommended"))
        self._custom_option.setText(tr("Custom location..."))
        self._browse_button.setText(tr("Browse..."))
        self._update_recommended_path_label()
        self._update_custom_path_display()

    def uses_recommended(self) -> bool:

        return self._recommended_option.isChecked()

    def selected_directory(self) -> Path:

        if self.uses_recommended():
            return default_data_directory()

        if self._custom_directory is not None:
            return self._custom_directory.expanduser()

        return default_data_directory()

    def set_custom_directory(self, path: Path | str | None) -> None:

        if path is None or str(path).strip() == "":
            self._custom_directory = None
        else:
            self._custom_directory = Path(path).expanduser()

        self._update_custom_path_display()

    def custom_directory(self) -> Path | None:

        return self._custom_directory

    def set_validation_error(self, message: str | None) -> None:

        if message:
            self._clear_validation_warning()
            self._error_label.setText(message)
            self._error_label.setVisible(True)
            return

        self._error_label.clear()
        self._error_label.setVisible(False)

    def set_validation_warning(self, message: str | None) -> None:

        if message:
            self._clear_validation_error()
            self._warning_label.setText(f"⚠ {message}")
            self._warning_label.setVisible(True)
            return

        self._clear_validation_warning()

    def clear_validation_error(self) -> None:

        self.set_validation_error(None)

    def clear_validation_warning(self) -> None:

        self.set_validation_warning(None)

    def clear_validation_feedback(self) -> None:

        self._clear_validation_error()
        self._clear_validation_warning()

    def _clear_validation_error(self) -> None:

        self._error_label.clear()
        self._error_label.setVisible(False)

    def _clear_validation_warning(self) -> None:

        self._warning_label.clear()
        self._warning_label.setVisible(False)

    def _build_ui(self) -> None:

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._title = QLabel()
        self._title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(self._title)

        self._description = QLabel()
        self._description.setWordWrap(True)
        self._description.setStyleSheet(f"color: {TEXT_MUTED};")
        layout.addWidget(self._description)

        self._recommended_option = QRadioButton()
        self._recommended_option.setChecked(True)
        layout.addWidget(self._recommended_option)

        self._recommended_path_label = QLabel()
        self._recommended_path_label.setStyleSheet(
            f"color: {TEXT_MUTED}; padding-left: 28px;"
        )
        layout.addWidget(self._recommended_path_label)

        self._custom_option = QRadioButton()
        layout.addWidget(self._custom_option)

        custom_row = QHBoxLayout()
        custom_row.setContentsMargins(28, 0, 0, 0)
        custom_row.setSpacing(8)

        self._custom_path_input = QLineEdit()
        self._custom_path_input.setReadOnly(True)
        self._custom_path_input.setStyleSheet(_CUSTOM_PATH_INPUT_STYLE)
        custom_row.addWidget(self._custom_path_input, stretch=1)

        self._browse_button = QPushButton()
        custom_row.addWidget(self._browse_button)
        layout.addLayout(custom_row)

        self._error_label = QLabel()
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(f"color: {DANGER};")
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

        self._warning_label = QLabel()
        self._warning_label.setWordWrap(True)
        self._warning_label.setStyleSheet(f"color: {WARNING};")
        self._warning_label.setVisible(False)
        layout.addWidget(self._warning_label)

        layout.addStretch()

        self._location_group = QButtonGroup(self)
        self._location_group.addButton(self._recommended_option, 0)
        self._location_group.addButton(self._custom_option, 1)

    def _connect_signals(self) -> None:

        self._location_group.buttonClicked.connect(self._on_location_choice_changed)
        self._browse_button.clicked.connect(self._browse_custom_location)

    def _on_location_choice_changed(self) -> None:

        self.clear_validation_feedback()
        self._sync_custom_controls()
        self.selection_changed.emit()

    def _sync_custom_controls(self) -> None:

        custom_selected = self._custom_option.isChecked()
        self._custom_path_input.setEnabled(custom_selected)
        self._browse_button.setEnabled(custom_selected)

    def _browse_custom_location(self) -> None:

        start_dir = self._custom_directory or default_data_directory()
        selected = QFileDialog.getExistingDirectory(
            self,
            tr("Choose data location"),
            str(start_dir),
            QFileDialog.Option.ShowDirsOnly,
        )

        if not selected:
            return

        self._custom_option.setChecked(True)
        self.set_custom_directory(selected)
        self.clear_validation_feedback()
        self._sync_custom_controls()
        self.selection_changed.emit()

    def _update_recommended_path_label(self) -> None:

        self._recommended_path_label.setText(
            format_display_path(default_data_directory())
        )

    def _update_custom_path_display(self) -> None:

        if self._custom_directory is None:
            self._custom_path_input.clear()
            self._custom_path_input.setPlaceholderText(
                tr("No folder selected")
            )
            return

        self._custom_path_input.setPlaceholderText("")
        self._custom_path_input.setText(format_display_path(self._custom_directory))
