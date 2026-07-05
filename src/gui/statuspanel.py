from PySide6.QtWidgets import QStatusBar

from gui.i18n_support import bind_language_refresh
from i18n import tr


class StatusPanel(QStatusBar):

    def __init__(self):
        super().__init__()

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def refresh_translations(self) -> None:

        self.showMessage(
            f"🟢 {tr('Internet')}    "
            f"⚪ {tr('AIS')}    "
            f"⚪ {tr('RTL')}    "
            f"⚪ {tr('Camera')}    "
            f"{tr('Ready')}"
        )
