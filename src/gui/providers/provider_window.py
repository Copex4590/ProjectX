# ============================================================================
# Project X
# Provider Window Base
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
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


class ProviderWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.Window | Qt.WindowType.Tool,
        )

        self.setObjectName("ProviderWindow")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumWidth(560)
        self.setMinimumHeight(480)
        self.setStyleSheet(_WINDOW_STYLE)

        self._section_forms: list[QFormLayout] = []
        self._section_rows: list[list[tuple[str, str]]] = []

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

        self._close_button = QPushButton()
        self._close_button.setStyleSheet(dashboard_button_stylesheet())
        self._close_button.clicked.connect(self.close)
        header.addWidget(self._close_button)

        root_layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(DASHBOARD_SPACING)

        for title_key, rows in self._sections():
            section, form = self._build_section(title_key, rows)
            self._section_forms.append(form)
            self._section_rows.append(rows)
            content_layout.addWidget(section)

        content_layout.addStretch()
        scroll.setWidget(content)
        root_layout.addWidget(scroll, 1)

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def provider_icon(self) -> str:

        raise NotImplementedError

    def provider_title_key(self) -> str:

        raise NotImplementedError

    def _sections(self) -> list[tuple[str, list[tuple[str, str]]]]:

        raise NotImplementedError

    def _build_section(
        self,
        title_key: str,
        rows: list[tuple[str, str]],
    ) -> tuple[QFrame, QFormLayout]:

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

        title = QLabel(tr(title_key))
        title.setStyleSheet(dashboard_section_title_stylesheet())
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(DASHBOARD_SECTION_SPACING)

        for caption_key, value_key in rows:
            caption = QLabel(tr(caption_key))
            caption.setStyleSheet(dashboard_caption_stylesheet())
            value = QLabel(tr(value_key))
            value.setStyleSheet(dashboard_value_stylesheet())
            value.setWordWrap(True)
            form.addRow(caption, value)

        layout.addLayout(form)
        return frame, form

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr(self.provider_title_key()))
        self._icon_label.setText(self.provider_icon())
        self._title_label.setText(tr(self.provider_title_key()))
        self._close_button.setText(tr("Close"))

        for form, rows in zip(self._section_forms, self._section_rows):
            for row_index, (caption_key, value_key) in enumerate(rows):
                caption_item = form.itemAt(row_index, QFormLayout.ItemRole.LabelRole)
                value_item = form.itemAt(row_index, QFormLayout.ItemRole.FieldRole)

                if caption_item and caption_item.widget():
                    caption_item.widget().setText(tr(caption_key))

                if value_item and value_item.widget():
                    value_item.widget().setText(tr(value_key))
