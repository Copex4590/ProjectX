# ============================================================================
# Project X
# Provider Window Base
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ais.providers import normalize_provider_type
from ais.user_provider_service import (
    get_provider_snapshot,
    remove_provider,
)
from gui.i18n_support import bind_language_refresh
from gui.theme import (
    BG_DEEP,
    DASHBOARD_BUTTON_ROW_SPACING,
    DASHBOARD_CARD_PADDING,
    DASHBOARD_MARGIN,
    DASHBOARD_SECTION_SPACING,
    DASHBOARD_SPACING,
    TEXT_PRIMARY,
    dashboard_button_stylesheet,
    dashboard_caption_stylesheet,
    dashboard_card_stylesheet,
    dashboard_section_title_stylesheet,
    dashboard_value_stylesheet,
)
from i18n import tr

_WINDOW_STYLE = f"""
    QWidget#ProviderWindow {{
        background: {BG_DEEP};
    }}
    QLabel {{
        color: {TEXT_PRIMARY};
    }}
    {dashboard_button_stylesheet()}
"""

_SECTION_STYLE = dashboard_card_stylesheet()
_BUTTON_STYLE = dashboard_button_stylesheet()


class ProviderWindow(QWidget):
    def __init__(self, provider_id: str, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.Window | Qt.WindowType.Tool,
        )

        self._provider_id = normalize_provider_type(provider_id).value
        self._configuration_edited = False
        self._applying_snapshot = False

        self.setObjectName("ProviderWindow")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumWidth(560)
        self.setMinimumHeight(480)
        self.setStyleSheet(_WINDOW_STYLE)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(
            DASHBOARD_MARGIN,
            DASHBOARD_MARGIN,
            DASHBOARD_MARGIN,
            DASHBOARD_MARGIN,
        )
        root_layout.setSpacing(DASHBOARD_SPACING)

        header = QHBoxLayout()
        header.setSpacing(DASHBOARD_SPACING)

        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setFixedSize(40, 40)
        self._icon_label.setStyleSheet("font-size: 24pt;")
        header.addWidget(self._icon_label)

        self._title_label = QLabel()
        self._title_label.setStyleSheet(dashboard_section_title_stylesheet())
        header.addWidget(self._title_label, 1)

        root_layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(DASHBOARD_SPACING)

        self._status_section, self._connection_status_value = self._build_status_section()
        content_layout.addWidget(self._status_section)

        self._configuration_section = QFrame()
        self._configuration_section.setStyleSheet(_SECTION_STYLE)
        configuration_layout = QVBoxLayout(self._configuration_section)
        configuration_layout.setContentsMargins(
            DASHBOARD_CARD_PADDING,
            DASHBOARD_CARD_PADDING,
            DASHBOARD_CARD_PADDING,
            DASHBOARD_CARD_PADDING,
        )
        configuration_layout.setSpacing(DASHBOARD_SECTION_SPACING)

        self._configuration_title = QLabel()
        self._configuration_title.setStyleSheet(dashboard_section_title_stylesheet())
        configuration_layout.addWidget(self._configuration_title)

        self._configuration_form = QFormLayout()
        self._configuration_form.setSpacing(DASHBOARD_SECTION_SPACING)
        configuration_layout.addLayout(self._configuration_form)

        self._build_configuration_fields(self._configuration_form)
        content_layout.addWidget(self._configuration_section)

        content_layout.addStretch()
        scroll.setWidget(content)
        root_layout.addWidget(scroll, 1)

        footer = QHBoxLayout()
        footer.setSpacing(DASHBOARD_BUTTON_ROW_SPACING)

        self._save_button = QPushButton()
        self._save_button.setStyleSheet(_BUTTON_STYLE)
        self._save_button.clicked.connect(self._on_save)
        footer.addWidget(self._save_button)

        self._delete_button = QPushButton()
        self._delete_button.setStyleSheet(_BUTTON_STYLE)
        self._delete_button.clicked.connect(self._on_delete)
        footer.addWidget(self._delete_button)

        footer.addStretch()

        self._close_button = QPushButton()
        self._close_button.setStyleSheet(_BUTTON_STYLE)
        self._close_button.clicked.connect(self.close)
        footer.addWidget(self._close_button)

        root_layout.addLayout(footer)

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self.refresh_state()

    def provider_icon(self) -> str:

        raise NotImplementedError

    def provider_title_key(self) -> str:

        raise NotImplementedError

    def _build_configuration_fields(self, form: QFormLayout) -> None:

        raise NotImplementedError

    def _apply_snapshot(self, snapshot) -> None:

        raise NotImplementedError

    def _collect_configuration(self) -> bool:

        raise NotImplementedError

    def _register_configuration_widget(self, widget: QWidget) -> None:

        if hasattr(widget, "textChanged"):
            widget.textChanged.connect(self._mark_configuration_edited)

        if hasattr(widget, "valueChanged"):
            widget.valueChanged.connect(self._mark_configuration_edited)

        if isinstance(widget, QCheckBox):
            widget.stateChanged.connect(self._mark_configuration_edited)

    def _mark_configuration_edited(self, *_args) -> None:

        if self._applying_snapshot:
            return

        self._configuration_edited = True

    def _configuration_has_focus(self) -> bool:

        focused = self.focusWidget()

        if focused is None:
            return False

        return self._configuration_section.isAncestorOf(focused)

    def _should_refresh_configuration(self) -> bool:

        if self._configuration_edited:
            return False

        return not self._configuration_has_focus()

    def refresh_state(self) -> None:

        snapshot = get_provider_snapshot(self._provider_id)
        status = snapshot.status
        self._connection_status_value.setText(f"{status.icon}   {status.text}")

        if self._should_refresh_configuration():
            self._applying_snapshot = True

            try:
                self._apply_snapshot(snapshot)
            finally:
                self._applying_snapshot = False

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr(self.provider_title_key()))
        self._icon_label.setText(self.provider_icon())
        self._title_label.setText(tr(self.provider_title_key()))
        self._configuration_title.setText(tr("Configuration"))
        self._save_button.setText(tr("Save"))
        self._delete_button.setText(tr("Delete"))
        self._close_button.setText(tr("Close"))
        self.refresh_state()

    def _reset_configuration_edited(self) -> None:

        self._configuration_edited = False

    def _build_status_section(self) -> tuple[QFrame, QLabel]:

        frame = QFrame()
        frame.setStyleSheet(_SECTION_STYLE)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(
            DASHBOARD_CARD_PADDING,
            DASHBOARD_CARD_PADDING,
            DASHBOARD_CARD_PADDING,
            DASHBOARD_CARD_PADDING,
        )
        layout.setSpacing(DASHBOARD_SECTION_SPACING)

        title = QLabel(tr("Connection status"))
        title.setStyleSheet(dashboard_section_title_stylesheet())
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(DASHBOARD_SECTION_SPACING)

        status_caption = QLabel(tr("Status"))
        status_caption.setStyleSheet(dashboard_caption_stylesheet())
        status_value = QLabel()
        status_value.setStyleSheet(dashboard_value_stylesheet())
        status_value.setWordWrap(True)
        form.addRow(status_caption, status_value)

        layout.addLayout(form)
        return frame, status_value

    def _on_save(self) -> None:

        if not self._collect_configuration():
            return

        self._reset_configuration_edited()
        self.close()

    def _on_delete(self) -> None:

        snapshot = get_provider_snapshot(self._provider_id)
        answer = QMessageBox.question(
            self,
            tr("Delete"),
            tr("Delete provider '{name}'?").format(name=tr(snapshot.label_key)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        remove_provider(self._provider_id)
        self.close()
