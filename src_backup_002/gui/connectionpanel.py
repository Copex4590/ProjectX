from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
)


class ConnectionPanel(QFrame):

    def __init__(self):
        super().__init__()

        self.setFixedWidth(240)

        self.setStyleSheet("""
            QFrame{
                background:#252a31;
                border-left:1px solid #40444b;
            }

            QLabel{
                color:white;
                padding:6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15,15,15,15)

        title = QLabel("Connections")

        title.setStyleSheet("""
            font-size:14pt;
            font-weight:bold;
        """)

        layout.addWidget(title)

        for item in [
            "🟢 Internet",
            "⚪ AISStream",
            "⚪ RTL Receiver",
            "⚪ GPS",
            "⚪ Camera",
            "⚪ Database",
            "⚪ API",
        ]:
            layout.addWidget(QLabel(item))

        layout.addStretch()
