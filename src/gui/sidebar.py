from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QFrame, QVBoxLayout, QButtonGroup

from branding.assets import logo_pixmap
from i18n import language_manager, tr
from version import PROJECT_NAME


class Sidebar(QFrame):

    pageSelected = Signal(int)

    _PAGE_KEYS = (
        ("Dashboard", 0),
        ("Live Map", 1),
        ("Vessels", 2),
        ("Cameras", 3),
        ("Vessel Database", 4),
        ("Vessel Timeline", 5),
        ("Statistics", 6),
        ("Alert Center", 7),
        ("Alert Rules", 8),
        ("System Health", 9),
    )

    _PAGE_ICONS = (
        "🏠",
        "🗺",
        "🚢",
        "📷",
        "🗄",
        "🕓",
        "📊",
        "🔔",
        "⚙",
        "🩺",
    )

    def __init__(self):
        super().__init__()

        self.setFixedWidth(260)
        self._active_page = 0

        self.setStyleSheet("""
            QFrame {
                background: #1d2127;
                border-right: 1px solid #40444b;
            }

            QPushButton {
                color: white;
                background: transparent;
                border: none;
                text-align: left;
                padding: 10px;
                font-size: 12pt;
                border-radius: 6px;
            }

            QPushButton:hover {
                background: #3b434d;
            }

            QPushButton:checked {
                background: #1976d2;
                font-weight: 600;
            }
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(8)

        self._logo_label = QLabel()
        self._logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._logo_label)

        self._title_label = QLabel(PROJECT_NAME)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet(
            "color: white; font-size: 14pt; font-weight: bold; padding-bottom: 8px;"
        )
        self._layout.addWidget(self._title_label)

        self._buttons: list[QPushButton] = []
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        for index, (label_key, page_index) in enumerate(self._PAGE_KEYS):
            button = QPushButton()
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, i=page_index:
                self.pageSelected.emit(i)
            )
            self._button_group.addButton(button)
            self._buttons.append(button)
            self._layout.addWidget(button)

        self._layout.addStretch()

        language_manager.language_changed.connect(
            lambda _code: self.refresh_translations()
        )
        self.refresh_translations()
        self.set_active_page(0)

    def set_active_page(self, page_index: int) -> None:

        self._active_page = page_index

        for index, (_label_key, mapped_index) in enumerate(self._PAGE_KEYS):
            self._buttons[index].setChecked(mapped_index == page_index)

    def refresh_translations(self) -> None:

        pixmap = logo_pixmap(48)

        if pixmap.isNull():
            self._logo_label.clear()
        else:
            self._logo_label.setPixmap(pixmap)

        self._title_label.setText(PROJECT_NAME)

        for index, (label_key, _page_index) in enumerate(self._PAGE_KEYS):
            icon = self._PAGE_ICONS[index]
            self._buttons[index].setText(
                f"{icon} {tr(label_key)}"
            )

        self.set_active_page(self._active_page)
