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
    BG_HEADER,
    BORDER,
    TEXT,
    TEXT_MUTED,
    card_stylesheet,
    secondary_button_stylesheet,
)
from i18n import tr

_WINDOW_STYLE = f"""
    QWidget#ProviderWindow {{
        background: {BG_DEEP};
    }}
    QLabel {{
        color: {TEXT};
    }}
    {secondary_button_stylesheet()}
"""

_SECTION_STYLE = card_stylesheet(radius=8)

_CLOSE_BUTTON_STYLE = f"""
    QPushButton {{
        background: transparent;
        color: {TEXT_MUTED};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 4px 12px;
        min-width: 72px;
    }}
    QPushButton:hover {{
        background: {BG_HEADER};
        color: white;
    }}
"""


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
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(12)

        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setFixedSize(40, 40)
        self._icon_label.setStyleSheet("font-size: 24pt;")
        header.addWidget(self._icon_label)

        self._title_label = QLabel()
        self._title_label.setStyleSheet(
            "font-size: 18pt; font-weight: bold; color: white;"
        )
        header.addWidget(self._title_label, 1)

        self._close_button = QPushButton()
        self._close_button.setStyleSheet(_CLOSE_BUTTON_STYLE)
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
        content_layout.setSpacing(12)

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
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(tr(title_key))
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: white;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        for caption_key, value_key in rows:
            caption = QLabel(tr(caption_key))
            caption.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: 600;")
            value = QLabel(tr(value_key))
            value.setStyleSheet("color: white; font-weight: 600;")
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
