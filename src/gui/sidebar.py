from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from branding.assets import logo_pixmap
from gui.theme import sidebar_stylesheet
from i18n import language_manager, tr
from version import PROJECT_NAME


class Sidebar(QFrame):

    pageSelected = Signal(int)

    _PAGE_KEYS = (
        ("Dashboard", 0),
        ("Map", 1),
        ("Vessels", 2),
        ("Cameras", 3),
        ("Vessel Database", 4),
        ("Vessel Timeline", 5),
        ("Statistics", 6),
        ("Alert Center", 7),
        ("Alert Rules", 8),
        ("System Health", 9),
        ("Database Manager", 10),
        ("Backup & Restore", 11),
        ("Settings", 12),
        ("Installed Plugins", 13),
        ("Analytics", 14),
        ("Session Recording", 15),
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
        "💾",
        "📦",
        "🛠",
        "🧩",
        "📈",
        "⏺",
    )

    def __init__(self):
        super().__init__()

        self.setFixedWidth(260)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._active_page = 0

        self.setStyleSheet(sidebar_stylesheet())

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(8)

        self._logo_label = QLabel()
        self._logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._logo_label)

        self._title_label = QLabel(PROJECT_NAME)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet(
            "color: white; font-size: 14pt; font-weight: bold; padding-bottom: 8px;"
        )
        root.addWidget(self._title_label)

        nav_host = QWidget()
        nav_host.setObjectName("sidebarNavHost")
        nav_layout = QVBoxLayout(nav_host)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)

        self._buttons: list[QPushButton] = []
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        for _index, (_label_key, page_index) in enumerate(self._PAGE_KEYS):
            button = QPushButton()
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, i=page_index: self.pageSelected.emit(i)
            )
            self._button_group.addButton(button)
            self._buttons.append(button)
            nav_layout.addWidget(button)

        nav_layout.addStretch()

        scroll = QScrollArea()
        scroll.setObjectName("sidebarNavScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        scroll.setWidget(nav_host)
        root.addWidget(scroll, 1)

        language_manager.language_changed.connect(
            lambda _code: self.refresh_translations()
        )
        self.refresh_translations()
        self.set_active_page(0)

    def minimumSizeHint(self) -> QSize:
        # Width stays fixed; height must not drive MainWindow minimum size.
        return QSize(260, 0)

    def sizeHint(self) -> QSize:
        return QSize(260, 400)

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
