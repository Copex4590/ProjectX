from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QLabel,
)
from PySide6.QtCore import Qt, Signal

from database import registry
from debug.obs_freeze_trace import trace_block
from gui.i18n_support import bind_language_refresh
from gui.theme import ThemeColors, BORDER
from gui.widgets.emptystate import EmptyStateWidget
from i18n import tr


def _ship_row_text(ship) -> str:

    return f"{ship.name:28} {ship.speed:5.1f} {tr('km/h')}"


class VesselsPage(QWidget):

    shipSelected = Signal(int)

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self._title_label = QLabel(tr("Vessels"))
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setStyleSheet("""
            font-size:26pt;
            font-weight:bold;
            color:white;
        """)

        layout.addWidget(self._title_label)

        self._stack = QStackedWidget()

        self.list = QListWidget()
        self.list.setStyleSheet(f"""
            QListWidget {{
                background: {ThemeColors.Panel};
                color: white;
                border: 1px solid {BORDER};
                font-size: 12pt;
            }}
        """)
        self._stack.addWidget(self.list)

        self._empty_state = EmptyStateWidget(
            "No vessels",
            help_title_key="Vessels help — title",
            help_body_key="Vessels help — body",
        )
        self._stack.addWidget(self._empty_state)

        layout.addWidget(self._stack)

        self.list.itemClicked.connect(self.item_clicked)

        self._last_count = -1

        bind_language_refresh(self.refresh_translations)

        self.refresh()

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Vessels"))
        self.refresh()

    def refresh(self):

        with trace_block("VesselsPage.refresh"):
            ships = sorted(
                registry.all(),
                key=lambda s: s.name.lower()
            )

            desired_mmsis = [ship.mmsi for ship in ships]
            current_mmsis = [
                self.list.item(index).data(Qt.UserRole)
                for index in range(self.list.count())
            ]

            if not ships:
                self._last_count = 0
                self.list.clear()
                self._stack.setCurrentWidget(self._empty_state)
                return

            self._stack.setCurrentWidget(self.list)

            # Full rebuild only when membership or sort order changes.
            if desired_mmsis != current_mmsis:
                self._rebuild_list(ships)
                return

            self._last_count = len(ships)
            ships_by_mmsi = {ship.mmsi: ship for ship in ships}

            for index in range(self.list.count()):
                item = self.list.item(index)
                mmsi = item.data(Qt.UserRole)
                ship = ships_by_mmsi.get(mmsi)

                if ship is None:
                    continue

                text = _ship_row_text(ship)

                if item.text() != text:
                    item.setText(text)

    def _rebuild_list(self, ships) -> None:

        self._last_count = len(ships)
        self.list.clear()

        for ship in ships:
            item = QListWidgetItem(_ship_row_text(ship))
            item.setData(Qt.UserRole, ship.mmsi)
            self.list.addItem(item)

    def item_clicked(self, item):

        mmsi = item.data(Qt.UserRole)

        if mmsi is not None:
            self.shipSelected.emit(mmsi)
