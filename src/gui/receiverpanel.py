from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QGridLayout,
)


class ReceiverPanel(QFrame):

    def __init__(self):
        super().__init__()

        self.setStyleSheet("""
            QFrame{
                background:#353b44;
                border:1px solid #4b535d;
                border-radius:10px;
            }

            QLabel{
                color:white;
            }
        """)

        layout = QGridLayout(self)
        layout.setContentsMargins(15,15,15,15)

        title = QLabel("Receivers")

        title.setStyleSheet("""
            font-size:14pt;
            font-weight:bold;
        """)

        layout.addWidget(title,0,0,1,2)

        data = [
            ("RTL-SDR","Offline"),
            ("AISStream","Offline"),
            ("GPS","Offline"),
            ("Internet","Online"),
        ]

        row = 1

        for name,state in data:

            layout.addWidget(QLabel(name),row,0)

            value = QLabel(state)

            value.setStyleSheet("""
                font-weight:bold;
            """)

            layout.addWidget(value,row,1)

            row += 1
