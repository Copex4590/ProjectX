from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QGridLayout,
)


class SystemPanel(QFrame):

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

        data = [
            ("CPU","0 %"),
            ("RAM","0 MB"),
            ("AIS","Offline"),
            ("RTL","Offline"),
            ("Camera","Offline"),
            ("Internet","Online"),
        ]

        row = 0

        for name,value in data:

            layout.addWidget(QLabel(name),row,0)

            label = QLabel(value)

            label.setStyleSheet("""
                font-weight:bold;
            """)

            layout.addWidget(label,row,1)

            row += 1
