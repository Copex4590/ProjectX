from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QGridLayout,
)


class StatisticsPanel(QFrame):

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

        layout.setContentsMargins(20, 20, 20, 20)
        layout.setHorizontalSpacing(25)
        layout.setVerticalSpacing(15)

        values = [
            ("AIS Targets", "0"),
            ("RTL Targets", "0"),
            ("Active Cameras", "0"),
            ("Alerts", "0"),
            ("CPU", "0 %"),
            ("Memory", "0 MB"),
        ]

        row = 0

        for title, value in values:

            layout.addWidget(QLabel(title), row, 0)

            number = QLabel(value)

            number.setStyleSheet("""
                font-size:18pt;
                font-weight:bold;
            """)

            layout.addWidget(number, row, 1)

            row += 1
