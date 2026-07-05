from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QPushButton, QFrame, QVBoxLayout


class Sidebar(QFrame):

    pageSelected = Signal(int)

    def __init__(self):
        super().__init__()

        self.setFixedWidth(260)

        self.setStyleSheet("""
            QFrame{
                background:#1d2127;
                border-right:1px solid #40444b;
            }

            QPushButton{
                color:white;
                background:transparent;
                border:none;
                text-align:left;
                padding:10px;
                font-size:12pt;
            }

            QPushButton:hover{
                background:#3b434d;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(8)

        buttons = [
            ("🏠 Dashboard",0),
            ("🗺 Live Map",1),
            ("🚢 Vessels",2),
            ("📷 Cameras",3),
            ("🗄 Vessel Database",4),
            ("🕓 Vessel Timeline",5),
            ("📊 Statistics",6),
            ("🔔 Alert Center",7),
            ("⚙ Alert Rules",8),
        ]

        for text,index in buttons:

            b = QPushButton(text)
            b.clicked.connect(
                lambda checked=False,i=index:
                self.pageSelected.emit(i)
            )

            layout.addWidget(b)

        layout.addStretch()
