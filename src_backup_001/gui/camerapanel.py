from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
)


class CameraPanel(QFrame):

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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15,15,15,15)

        title = QLabel("Camera")

        title.setStyleSheet("""
            font-size:14pt;
            font-weight:bold;
        """)

        preview = QLabel("Camera Preview")

        preview.setMinimumHeight(220)

        preview.setStyleSheet("""
            background:#252a31;
            border:1px solid #40444b;
            border-radius:6px;
        """)

        layout.addWidget(title)
        layout.addWidget(preview)
