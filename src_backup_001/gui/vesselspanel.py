from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class VesselsPanel(QFrame):

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
                font-size:14pt;
                font-weight:bold;
            }

            QTableWidget{
                background:#252a31;
                color:white;
                border:1px solid #40444b;
                gridline-color:#40444b;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15,15,15,15)

        layout.addWidget(QLabel("Detected Vessels"))

        table = QTableWidget(5,4)

        table.setHorizontalHeaderLabels([
            "Name",
            "Distance",
            "Speed",
            "Source"
        ])

        for row in range(5):
            table.setItem(row,0,QTableWidgetItem("-"))
            table.setItem(row,1,QTableWidgetItem("-"))
            table.setItem(row,2,QTableWidgetItem("-"))
            table.setItem(row,3,QTableWidgetItem("-"))

        layout.addWidget(table)
