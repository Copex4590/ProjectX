from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from cameras import camera_manager
from engines.camera import camera_selection_engine
from models.ship import Ship
from playback.live_camera_workflow import live_camera_workflow


class CameraPreviewPanel(QFrame):

    def __init__(self):
        super().__init__()

        camera_manager.load()

        self._last_mmsi = None
        self._workflow = live_camera_workflow

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

            QLabel[role="error"] {
                color: #f0a8a8;
                font-size: 10pt;
                font-weight: 500;
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
            "playback": self._add_row(details_layout, "Playback"),
        }

        layout.addWidget(self.details)

        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

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

        try:
            self._show_for_ship(ship)
        except Exception:
            self._workflow.stop()
            self._last_mmsi = None
            self.show_empty("An unexpected camera error occurred.")

    def _show_for_ship(self, ship: Ship | None):

        if ship is None:
            self._workflow.stop()
            self._last_mmsi = None
            self.show_empty()
            return

        match = camera_selection_engine.get_best_camera(ship)

        if match is None:
            self._workflow.stop()
            self._last_mmsi = ship.mmsi
            self.show_empty()
            return

        vessel_changed = self._last_mmsi != ship.mmsi

        self.details.setVisible(True)
        self.empty_label.setVisible(False)
        self._update_camera_details(match)

        if vessel_changed:
            self._workflow.stop()
            self._last_mmsi = ship.mmsi
            result = self._workflow.start_for_ship(ship)
            self._update_playback_state(result)
            return

        self._update_camera_details(match)

    def _update_camera_details(self, match):

        camera = match.camera

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

    def _update_playback_state(self, result):

        if result.success:
            self.error_label.setVisible(False)
            self._value_labels["playback"].setText(
                result.backend_name or "Active"
            )
            return

        self._value_labels["playback"].setText("Unavailable")
        self.error_label.setText(result.message)
        self.error_label.setVisible(True)

    def show_empty(self, message: str = "No camera available"):

        self._workflow.stop()
        self._last_mmsi = None
        self.details.setVisible(False)
        self.error_label.setVisible(False)
        self.empty_label.setText(message)
        self.empty_label.setVisible(True)

    def video_container(self) -> QFrame:

        return self.video_host
