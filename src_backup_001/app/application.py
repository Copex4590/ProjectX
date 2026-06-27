# ============================================================================
# Project X
# File    : application.py
# Module  : Application
# Version : 0.1.0-alpha
# ============================================================================

import sys

from PySide6.QtWidgets import QApplication

from app.mainwindow import MainWindow


class Application:
    """
    Main application controller.
    Responsible for creating and running the GUI.
    """

    def __init__(self):

        self.qt = QApplication(sys.argv)

        self.window = MainWindow()

    def run(self):

        self.window.show()

        return self.qt.exec()
