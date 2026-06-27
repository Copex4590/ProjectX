# ============================================================================
# Project X
# File    : mainwindow.py
# Version : 0.2.4-alpha
# ============================================================================

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QWidget,
)

from gui.sidebar import Sidebar
from gui.dashboard import Dashboard
from gui.connectionpanel import ConnectionPanel
from gui.statuspanel import StatusPanel
from gui.menubar import MenuBar


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Project X")
        self.resize(1600, 900)

        self.build_ui()

    def build_ui(self):

        self.setStyleSheet("""
            QMainWindow{
                background:#2b2f36;
            }

            QWidget{
                background:#2b2f36;
                color:white;
                font-family:Segoe UI;
                font-size:11pt;
            }

            QStatusBar{
                background:#20242a;
                color:#d0d0d0;
            }
        """)

        self.setMenuBar(MenuBar())

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(Sidebar())
        root.addWidget(Dashboard())
        root.addWidget(ConnectionPanel())

        self.setStatusBar(StatusPanel())
