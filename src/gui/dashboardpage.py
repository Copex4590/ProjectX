from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from database import registry
from gui.i18n_support import bind_language_refresh
from i18n import tr


class InfoCard(QFrame):

    def __init__(self, title_key: str):

        super().__init__()

        self._title_key = title_key

        self.setStyleSheet("""
            QFrame{
                background:#252a31;
                border:1px solid #40444b;
                border-radius:10px;
            }
        """)

        layout = QVBoxLayout(self)

        self.title = QLabel(tr(title_key))
        self.title.setAlignment(Qt.AlignCenter)

        self.title.setStyleSheet("""
            color:#bbbbbb;
            font-size:12pt;
        """)

        self.value = QLabel("--")
        self.value.setAlignment(Qt.AlignCenter)

        self.value.setStyleSheet("""
            color:white;
            font-size:28pt;
            font-weight:bold;
        """)

        layout.addWidget(self.title)
        layout.addWidget(self.value)


class DashboardPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self._title_label = QLabel(tr("Dashboard"))
        self._title_label.setAlignment(Qt.AlignCenter)

        self._title_label.setStyleSheet("""
            font-size:26pt;
            font-weight:bold;
            color:white;
        """)

        layout.addWidget(self._title_label)

        grid = QGridLayout()

        self.ships = InfoCard("Ships")
        self.ais = InfoCard("AIS")
        self.last = InfoCard("Last Ship")

        self.ais.value.setText(tr("CONNECTED"))

        grid.addWidget(self.ships, 0, 0)
        grid.addWidget(self.ais, 0, 1)
        grid.addWidget(self.last, 0, 2)

        layout.addLayout(grid)
        layout.addStretch()

        bind_language_refresh(self.refresh_translations)

        self.update_dashboard()

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Dashboard"))
        self.ships.title.setText(tr("Ships"))
        self.ais.title.setText(tr("AIS"))
        self.last.title.setText(tr("Last Ship"))
        self.ais.value.setText(tr("CONNECTED"))

    def update_dashboard(self):

        ships = registry.all()

        self.ships.value.setText(str(len(ships)))

        if ships:
            self.last.value.setText(ships[-1].name)
        else:
            self.last.value.setText("--")

    def on_ship_updated(self):

        ships = registry.all()

        self.ships.value.setText(str(len(ships)))

        if ships:
            self.last.value.setText(ships[-1].name)
        else:
            self.last.value.setText("--")
