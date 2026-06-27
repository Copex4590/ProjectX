from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QHBoxLayout,
)


class ToolBar(QFrame):

    def __init__(self):
        super().__init__()

        self.setFixedHeight(54)

        self.setStyleSheet("""
            QFrame{
                background:#20242a;
                border-bottom:1px solid #40444b;
            }

            QLabel{
                color:white;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15,0,15,0)

        title = QLabel("PROJECT X")

        title.setStyleSheet("""
            font-size:15pt;
            font-weight:bold;
        """)

        layout.addWidget(title)

        layout.addStretch()

        layout.addWidget(QLabel("Profile: Default"))
        layout.addSpacing(20)
        layout.addWidget(QLabel("Linux Mint"))
        layout.addSpacing(20)
        layout.addWidget(QLabel("v0.3 Alpha"))
        layout.addSpacing(20)

        state = QLabel("🟢 READY")

        state.setAlignment(Qt.AlignRight)

        layout.addWidget(state)
