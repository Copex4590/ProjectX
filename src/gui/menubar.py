from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QMenuBar,
    QMenu,
)

from gui.i18n_support import bind_language_refresh
from i18n import tr


class MenuBar(QMenuBar):

    about_requested = Signal()

    def __init__(self):
        super().__init__()

        self._file_menu = QMenu(self)
        self._new_profile_action = self._file_menu.addAction("")
        self._file_menu.addSeparator()
        self._exit_action = self._file_menu.addAction("")

        self._view_menu = QMenu(self)
        self._dashboard_action = self._view_menu.addAction("")
        self._map_action = self._view_menu.addAction("")

        self._tools_menu = QMenu(self)
        self._settings_action = self._tools_menu.addAction("")

        self._help_menu = QMenu(self)
        self._about_action = self._help_menu.addAction("")

        self._about_action.triggered.connect(self.about_requested.emit)

        self.addMenu(self._file_menu)
        self.addMenu(self._view_menu)
        self.addMenu(self._tools_menu)
        self.addMenu(self._help_menu)

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def refresh_translations(self) -> None:

        self._file_menu.setTitle(tr("File"))
        self._new_profile_action.setText(tr("New Profile"))
        self._exit_action.setText(tr("Exit"))

        self._view_menu.setTitle(tr("View"))
        self._dashboard_action.setText(tr("Dashboard"))
        self._map_action.setText(tr("Map"))

        self._tools_menu.setTitle(tr("Tools"))
        self._settings_action.setText(tr("Settings"))

        self._help_menu.setTitle(tr("Help"))
        self._about_action.setText(tr("About Project X"))
