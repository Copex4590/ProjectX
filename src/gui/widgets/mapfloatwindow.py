# ============================================================================
# Project X — Detached map host (single MapWidget reparent target)
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.i18n_support import bind_language_refresh
from gui.theme import ThemeColors, secondary_button_stylesheet
from i18n import tr


_WINDOW_STYLE = f"""
    QMainWindow {{
        background: {ThemeColors.Background};
    }}
    QWidget#MapFloatCentral {{
        background: {ThemeColors.Background};
    }}
    QWidget#MapFloatHost {{
        background: transparent;
        border: none;
        margin: 0;
        padding: 0;
    }}
    {secondary_button_stylesheet(padding="6px 12px")}
"""


class MapFloatWindow(QMainWindow):
    """Thin standalone host for the single live MapWidget."""

    redockRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MapFloatWindow")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
        )
        self.resize(1100, 800)
        self.setMinimumSize(640, 480)
        self.setStyleSheet(_WINDOW_STYLE)

        self._map_widget: QWidget | None = None

        central = QWidget()
        central.setObjectName("MapFloatCentral")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)

        self._redock_button = QPushButton()
        self._redock_button.setObjectName("MapFloatRedockButton")
        self._redock_button.clicked.connect(self.redockRequested.emit)
        toolbar.addWidget(self._redock_button)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        host = QWidget()
        host.setObjectName("MapFloatHost")
        self._map_host_layout = QVBoxLayout(host)
        self._map_host_layout.setContentsMargins(0, 0, 0, 0)
        self._map_host_layout.setSpacing(0)
        root.addWidget(host, 1)

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def refresh_translations(self) -> None:
        self.setWindowTitle(tr("Map"))
        self._redock_button.setText(tr("Redock Map"))

    def attach_map(self, widget: QWidget) -> None:
        if self._map_widget is widget:
            return
        if self._map_widget is not None:
            self.release_map()
        self._map_widget = widget
        self._map_host_layout.addWidget(widget)

    def release_map(self) -> None:
        widget = self._map_widget
        self._map_widget = None
        if widget is None:
            return
        self._map_host_layout.removeWidget(widget)
        widget.setParent(None)

    def has_map(self) -> bool:
        return self._map_widget is not None

    def closeEvent(self, event: QCloseEvent) -> None:
        # Closing the shell must redock the MapWidget, never destroy it.
        if self._map_widget is not None:
            event.ignore()
            self.redockRequested.emit()
            return
        event.accept()
