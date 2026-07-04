from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from cameras import camera_manager
from engines.camera import camera_selection_engine
from models.ship import Ship


class CameraPreviewPanel(QFrame):

    def __init__(self):
        super().__init__()

        camera_manager.load()

        self.setMinimumWidth(300)
        self.setMaximumWidth(360)

        self.setStyleSheet("""
            QFrame#CameraPreviewPanel {
                background: #353b44;
                border: 1px solid #4b535d;
                border-radius: 10px;
            }

            QLabel {
                color: white;
            }

            QLabel[role="title"] {
                font-size: 14pt;
                font-weight: bold;
            }

            QLabel[role="caption"] {
                color: #9aa4af;
                font-size: 9pt;
                font-weight: 600;
            }

            QLabel[role="value"] {
                font-size: 11pt;
                font-weight: 500;
            }

            QLabel[role="empty"] {
                color: #9aa4af;
                font-size: 12pt;
                font-weight: 600;
            }

            QFrame#videoHost {
                background: #252a31;
                border: 1px solid #40444b;
                border-radius: 6px;
                min-height: 180px;
            }
        """)

        self.setObjectName("CameraPreviewPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.title = QLabel("Camera Preview")
        self.title.setProperty("role", "title")
        layout.addWidget(self.title)

        self.video_host = QFrame()
        self.video_host.setObjectName("videoHost")
        layout.addWidget(self.video_host)

        self.details = QWidget()
        details_layout = QVBoxLayout(self.details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(8)

        self._value_labels = {
            "name": self._add_row(details_layout, "Camera"),
            "country": self._add_row(details_layout, "Country"),
            "distance": self._add_row(details_layout, "Distance"),
            "confidence": self._add_row(details_layout, "Confidence"),
            "direction": self._add_row(details_layout, "Viewing Direction"),
            "radius": self._add_row(details_layout, "Visibility Radius"),
            "status": self._add_row(details_layout, "Camera Status"),
        }

        layout.addWidget(self.details)

        self.empty_label = QLabel("No camera available")
        self.empty_label.setProperty("role", "empty")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setWordWrap(True)
        layout.addWidget(self.empty_label)

        self.show_empty()

    def _add_row(self, layout, caption: str) -> QLabel:

        row = QWidget()
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(2)

        label = QLabel(caption)
        label.setProperty("role", "caption")

        value = QLabel("—")
        value.setProperty("role", "value")
        value.setWordWrap(True)

        row_layout.addWidget(label)
        row_layout.addWidget(value)
        layout.addWidget(row)

        return value

    def show_for_ship(self, ship: Ship | None):

        if ship is None:
            self.show_empty()
            return

        match = camera_selection_engine.get_best_camera(ship)

        if match is None:
            self.show_empty()
            return

        camera = match.camera

        self.details.setVisible(True)
        self.empty_label.setVisible(False)

        self._value_labels["name"].setText(camera.name)
        self._value_labels["country"].setText(camera.country)
        self._value_labels["distance"].setText(
            f"{match.distance_km:.2f} km"
        )
        self._value_labels["confidence"].setText(
            f"{match.confidence * 100:.1f}%"
        )
        self._value_labels["direction"].setText(
            f"{camera.direction_deg:.1f}°"
        )
        self._value_labels["radius"].setText(
            f"{camera.visibility_radius_km:.2f} km"
        )
        self._value_labels["status"].setText(
            "Enabled" if camera.enabled else "Disabled"
        )

    def show_empty(self):

        self.details.setVisible(False)
        self.empty_label.setVisible(True)

    def video_container(self) -> QFrame:

        return self.video_host
