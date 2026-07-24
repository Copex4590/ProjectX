from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

import logging

from cameras import camera_manager
from engines.camera import camera_selection_engine
from gui.i18n_support import bind_language_refresh
from gui.theme import ThemeColors
from i18n import tr
from models.ship import Ship
from playback.live_camera_workflow import live_camera_workflow

logger = logging.getLogger(__name__)


class CameraPreviewPanel(QFrame):

    _DETAIL_KEYS = (
        "name",
        "country",
        "distance",
        "confidence",
        "direction",
        "radius",
        "status",
        "playback",
    )

    _CAPTION_KEYS = {
        "name": "Camera",
        "country": "Country",
        "distance": "Distance",
        "confidence": "Confidence",
        "direction": "Viewing Direction",
        "radius": "Visibility Radius",
        "status": "Camera Status",
        "playback": "Playback",
    }

    def __init__(self):
        super().__init__()

        camera_manager.load()

        self._last_mmsi = None
        self._last_camera_id = None
        self._workflow = live_camera_workflow
        self._empty_message_key = "No camera available"
        self._error_message_key = None
        self._error_message_raw = None
        self._camera_enabled = None
        self._playback_key = None
        self._playback_backend = None

        self.setMinimumWidth(300)
        self.setMaximumWidth(360)

        self.setStyleSheet(f"""
            QFrame#CameraPreviewPanel {{
                background: {ThemeColors.panel_elevated()};
                border: 1px solid {ThemeColors.Primary700};
                border-radius: 10px;
            }}

            QLabel {{
                color: {ThemeColors.TextPrimary};
            }}

            QLabel[role="title"] {{
                font-size: 14pt;
                font-weight: bold;
            }}

            QLabel[role="caption"] {{
                color: {ThemeColors.TextSecondary};
                font-size: 9pt;
                font-weight: 600;
            }}

            QLabel[role="value"] {{
                font-size: 11pt;
                font-weight: 500;
            }}

            QLabel[role="empty"] {{
                color: {ThemeColors.TextSecondary};
                font-size: 12pt;
                font-weight: 600;
            }}

            QLabel[role="error"] {{
                color: {ThemeColors.Danger};
                font-size: 10pt;
                font-weight: 500;
            }}

            QFrame#videoHost {{
                background: {ThemeColors.Panel};
                border: 1px solid {ThemeColors.Border};
                border-radius: 6px;
                min-height: 180px;
            }}
        """)

        self.setObjectName("CameraPreviewPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self._title_label = QLabel(tr("Camera Preview"))
        self._title_label.setProperty("role", "title")
        layout.addWidget(self._title_label)

        self.video_host = QFrame()
        self.video_host.setObjectName("videoHost")
        layout.addWidget(self.video_host)

        self.details = QWidget()
        details_layout = QVBoxLayout(self.details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(8)

        self._caption_labels = {}
        self._value_labels = {}

        for field in self._DETAIL_KEYS:
            caption_key = self._CAPTION_KEYS[field]
            self._value_labels[field] = self._add_row(
                details_layout,
                caption_key,
            )

        layout.addWidget(self.details)

        self.error_label = QLabel("")
        self.error_label.setProperty("role", "error")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        self.empty_label = QLabel(tr("No camera available"))
        self.empty_label.setProperty("role", "empty")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setWordWrap(True)
        layout.addWidget(self.empty_label)

        bind_language_refresh(self.refresh_translations)

        self.show_empty()

    def _add_row(self, layout, caption_key: str) -> QLabel:

        row = QWidget()
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(2)

        label = QLabel(tr(caption_key))
        label.setProperty("role", "caption")
        self._caption_labels[caption_key] = label

        value = QLabel("—")
        value.setProperty("role", "value")
        value.setWordWrap(True)

        row_layout.addWidget(label)
        row_layout.addWidget(value)
        layout.addWidget(row)

        return value

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Camera Preview"))

        for caption_key, caption_label in self._caption_labels.items():
            caption_label.setText(tr(caption_key))

        if self.empty_label.isVisible():
            self.empty_label.setText(tr(self._empty_message_key))

        if self._camera_enabled is not None:
            self._value_labels["status"].setText(
                tr("Enabled")
                if self._camera_enabled
                else tr("Disabled")
            )

        if self._playback_backend:
            self._value_labels["playback"].setText(self._playback_backend)
        elif self._playback_key:
            self._value_labels["playback"].setText(tr(self._playback_key))

        if self.error_label.isVisible():
            if self._error_message_key:
                self.error_label.setText(tr(self._error_message_key))
            elif self._error_message_raw:
                self.error_label.setText(self._error_message_raw)

    def show_for_ship(self, ship: Ship | None):

        try:
            self._show_for_ship(ship)
        except Exception:
            logger.exception("Camera preview failed for ship")
            self._workflow.stop()
            self._last_mmsi = None
            self.show_empty("An unexpected camera error occurred.")

    def show_for_match(self, ship: Ship | None, match) -> None:
        """Show a specific camera match (manual override). Does not change show_for_ship."""

        try:
            self._show_for_match(ship, match)
        except Exception:
            logger.exception("Camera preview failed for explicit match")
            self._workflow.stop()
            self._last_mmsi = None
            self.show_empty("An unexpected camera error occurred.")

    def _show_for_match(self, ship: Ship | None, match) -> None:

        if ship is None or match is None:
            self._workflow.stop()
            self._last_mmsi = None
            self.show_empty()
            return

        vessel_changed = self._last_mmsi != ship.mmsi
        camera_changed = (
            self._last_camera_id != getattr(match.camera, "id", None)
        )

        self.details.setVisible(True)
        self.empty_label.setVisible(False)
        self._update_camera_details(match)
        self._last_camera_id = getattr(match.camera, "id", None)

        if vessel_changed or camera_changed:
            self._workflow.stop()
            self._last_mmsi = ship.mmsi
            result = self._workflow.start_for_match(match)
            self._update_playback_state(result)

    def _show_for_ship(self, ship: Ship | None):

        if ship is None:
            self._workflow.stop()
            self._last_mmsi = None
            self._last_camera_id = None
            self.show_empty()
            return

        match = camera_selection_engine.get_best_camera(ship)

        if match is None:
            self._workflow.stop()
            self._last_mmsi = ship.mmsi
            self._last_camera_id = None
            self.show_empty()
            return

        vessel_changed = self._last_mmsi != ship.mmsi

        self.details.setVisible(True)
        self.empty_label.setVisible(False)
        self._update_camera_details(match)
        self._last_camera_id = match.camera.id

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
        self._camera_enabled = camera.enabled
        self._value_labels["status"].setText(
            tr("Enabled") if camera.enabled else tr("Disabled")
        )

    def _update_playback_state(self, result):

        if result.success:
            self.error_label.setVisible(False)
            self._error_message_key = None
            self._error_message_raw = None
            self._playback_key = "Active"
            self._playback_backend = result.backend_name
            self._value_labels["playback"].setText(
                result.backend_name or tr("Active")
            )
            return

        self._playback_key = "Unavailable"
        self._playback_backend = None
        self._value_labels["playback"].setText(tr("Unavailable"))
        self._error_message_key = "Camera playback failed"
        self._error_message_raw = None
        self.error_label.setText(tr("Camera playback failed"))
        self.error_label.setVisible(True)

    def show_empty(self, message_key: str = "No camera available"):

        self._workflow.stop()
        self._last_mmsi = None
        self._last_camera_id = None
        self._camera_enabled = None
        self._playback_key = None
        self._playback_backend = None
        self._error_message_key = None
        self._error_message_raw = None
        self._empty_message_key = message_key
        self.details.setVisible(False)
        self.error_label.setVisible(False)
        self.empty_label.setText(tr(message_key))
        self.empty_label.setVisible(True)

    def video_container(self) -> QFrame:

        return self.video_host
