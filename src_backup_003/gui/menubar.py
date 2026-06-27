from PySide6.QtWidgets import (
    QMenuBar,
    QMenu,
)


class MenuBar(QMenuBar):

    def __init__(self):
        super().__init__()

        file_menu = QMenu("File", self)
        file_menu.addAction("New Profile")
        file_menu.addSeparator()
        file_menu.addAction("Exit")

        view_menu = QMenu("View", self)
        view_menu.addAction("Dashboard")
        view_menu.addAction("Map")

        tools_menu = QMenu("Tools", self)
        tools_menu.addAction("Settings")

        help_menu = QMenu("Help", self)
        help_menu.addAction("About Project X")

        self.addMenu(file_menu)
        self.addMenu(view_menu)
        self.addMenu(tools_menu)
        self.addMenu(help_menu)
