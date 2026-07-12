# ============================================================================
# First Run Wizard
# ============================================================================

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from debug.obs_freeze_trace import trace_block
from gui.i18n_support import bind_language_refresh
from gui.mapcontroller import MapController
from gui.observationwizard import ObservationSetupWidget, _SUBSTEP_MAP, _SUBSTEP_RADIUS
from gui.wizardhelp import add_wizard_back_button, add_wizard_next_button
from i18n import tr
from preferences import preferences_manager


class _FirstRunSuccessDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModal(True)
        self.setMinimumWidth(460)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self._title = QLabel()
        self._title.setWordWrap(True)
        self._title.setStyleSheet(
            "font-size: 14pt; font-weight: bold; color: #e8f5e9;"
        )
        layout.addWidget(self._title)

        self._body = QLabel()
        self._body.setWordWrap(True)
        self._body.setStyleSheet("color: #d5dbe3; font-size: 11pt;")
        layout.addWidget(self._body)

        layout.addSpacing(8)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self._continue_button = QPushButton()
        self._continue_button.setMinimumWidth(120)
        self._continue_button.clicked.connect(self.accept)
        button_row.addWidget(self._continue_button)
        layout.addLayout(button_row)

        self.setStyleSheet("""
            QDialog {
                background: #1d2127;
            }

            QPushButton {
                background: #243651;
                color: white;
                border: 1px solid #2d5a8e;
                border-radius: 6px;
                padding: 8px 20px;
            }

            QPushButton:hover {
                background: #2d4a6f;
            }
        """)

        self.refresh_translations()

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("Project X Setup"))
        self._title.setText(
            "✓ "
            + tr("You successfully created your first observation point.")
        )
        self._body.setText(
            tr(
                "To create additional observation points, choose Create new "
                "on the Dashboard."
            )
        )
        self._continue_button.setText(tr("Continue"))


class FirstRunWizard(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModal(False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumWidth(560)
        self.setMinimumHeight(420)

        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def start_setup(self) -> None:

        self._setup.begin_map_selection()

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("Project X Setup"))
        self._setup.refresh_translations()
        self._continue_button.setText(tr("Continue"))
        self._back_button.setText(tr("Back"))
        self._button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            tr("Cancel")
        )
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

        self._setup = ObservationSetupWidget(self)
        layout.addWidget(self._setup)

        button_row = QHBoxLayout()
        self._button_box = QDialogButtonBox()
        self._back_button = add_wizard_back_button(self._button_box)
        self._continue_button = add_wizard_next_button(self._button_box)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        button_row.addWidget(self._button_box)
        layout.addLayout(button_row)

    def _connect_signals(self) -> None:

        self._continue_button.clicked.connect(self._on_continue)
        self._back_button.clicked.connect(self._on_back)
        self._button_box.rejected.connect(self._on_cancel)

    def _sync_buttons(self) -> None:

        step = self._setup.substep_index()
        self._back_button.setEnabled(step > _SUBSTEP_MAP)
        self._back_button.setVisible(step > _SUBSTEP_MAP)
        self._continue_button.setVisible(True)

    def _on_continue(self) -> None:

        if self._setup.substep_index() == _SUBSTEP_RADIUS:
            self._complete_observation_setup()
            return

        self._setup.handle_next()

        if self._setup.substep_index() > _SUBSTEP_MAP:
            self.show()
            self.raise_()
            self.activateWindow()

        self._sync_buttons()

    def _on_back(self) -> None:

        if self._setup.handle_back():
            self._back_button.setEnabled(False)
        elif self._setup.substep_index() == _SUBSTEP_MAP:
            self.hide()

        self._sync_buttons()

    def _on_cancel(self) -> None:

        MapController.instance().cancel_pick_mode()
        self.reject()

    def _complete_observation_setup(self) -> None:

        with trace_block("FirstRunWizard._complete_observation_setup"):
            if not self._setup.handle_confirm():
                return

        if not self._show_success_dialog():
            return

        MapController.instance().cancel_pick_mode(restore_host=False)
        self._navigate_parent_to_dashboard()
        preferences_manager.set_first_run_completed(True)
        self.accept()

    def _navigate_parent_to_dashboard(self) -> None:

        parent = self.parent()

        if parent is not None and hasattr(parent, "pages"):
            parent.pages.setCurrentIndex(0)

    def _show_success_dialog(self) -> bool:

        dialog = _FirstRunSuccessDialog(self)
        bind_language_refresh(dialog.refresh_translations)
        return dialog.exec() == QDialog.DialogCode.Accepted

    def reject(self) -> None:

        self._setup.on_leave()
        super().reject()

    def accept(self) -> None:

        self._setup.on_leave()
        super().accept()
