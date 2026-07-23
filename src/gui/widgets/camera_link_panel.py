# ============================================================================
# Project X
# Camera Link Panel (SAVE-217)
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from engines.camera.link_manager import (
    CameraLinkSnapshot,
    IntelligentCameraLinkManager,
    intelligent_camera_link_manager,
)
from engines.camera.link_states import CameraLinkMode
from engines.camera.scoring_engine import ScoredCamera
from gui.i18n_support import bind_language_refresh
from gui.theme import (
    ThemeColors,
    card_stylesheet,
    primary_button_stylesheet,
    secondary_button_stylesheet,
)
from i18n import tr


class CameraLinkPanel(QFrame):
    """Active camera, alternatives, score explanation, Auto/Manual mode."""

    modeChanged = Signal(str)
    overrideRequested = Signal(str)
    coverageToggled = Signal(bool)
    refreshRequested = Signal()

    def __init__(
        self,
        manager: IntelligentCameraLinkManager | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._manager = manager or intelligent_camera_link_manager
        self._alt_buttons: list[QPushButton] = []

        self.setObjectName("CameraLinkPanel")
        self.setMinimumWidth(300)
        self.setMaximumWidth(360)
        self.setStyleSheet(
            f"""
            QFrame#CameraLinkPanel {{
                background: {ThemeColors.Panel};
                border: 1px solid {ThemeColors.Border};
                border-radius: 10px;
            }}
            QLabel {{
                color: {ThemeColors.TextPrimary};
            }}
            """
        )

        self._build_ui()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self.apply_snapshot(self._manager.last_snapshot)

    def _build_ui(self) -> None:

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        self._title = QLabel()
        self._title.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 13pt; font-weight: 700;"
        )
        layout.addWidget(self._title)

        mode_row = QHBoxLayout()
        self._auto_btn = QPushButton()
        self._auto_btn.setCheckable(True)
        self._auto_btn.setStyleSheet(primary_button_stylesheet())
        self._manual_btn = QPushButton()
        self._manual_btn.setCheckable(True)
        self._manual_btn.setStyleSheet(secondary_button_stylesheet())
        mode_row.addWidget(self._auto_btn)
        mode_row.addWidget(self._manual_btn)
        layout.addLayout(mode_row)

        self._coverage_check = QCheckBox()
        self._coverage_check.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        layout.addWidget(self._coverage_check)

        active_card = QFrame()
        active_card.setStyleSheet(card_stylesheet(radius=8))
        active_layout = QVBoxLayout(active_card)
        active_layout.setContentsMargins(10, 8, 10, 8)
        active_layout.setSpacing(4)

        self._active_caption = QLabel()
        self._active_caption.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt; font-weight: 600;"
        )
        self._active_name = QLabel("—")
        self._active_name.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 11pt; font-weight: 600;"
        )
        self._active_meta = QLabel("")
        self._active_meta.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        self._active_meta.setWordWrap(True)
        active_layout.addWidget(self._active_caption)
        active_layout.addWidget(self._active_name)
        active_layout.addWidget(self._active_meta)
        layout.addWidget(active_card)

        self._why_caption = QLabel()
        self._why_caption.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt; font-weight: 600;"
        )
        layout.addWidget(self._why_caption)

        self._why = QLabel("")
        self._why.setWordWrap(True)
        self._why.setStyleSheet(
            f"color: {ThemeColors.text_body()}; font-size: 9pt;"
        )
        layout.addWidget(self._why)

        self._alts_caption = QLabel()
        self._alts_caption.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt; font-weight: 600;"
        )
        layout.addWidget(self._alts_caption)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMaximumHeight(120)
        scroll.setStyleSheet("background: transparent; border: none;")
        self._alts_host = QWidget()
        self._alts_layout = QVBoxLayout(self._alts_host)
        self._alts_layout.setContentsMargins(0, 0, 0, 0)
        self._alts_layout.setSpacing(4)
        scroll.setWidget(self._alts_host)
        layout.addWidget(scroll)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 8pt;"
        )
        layout.addWidget(self._status)

        self._auto_btn.clicked.connect(self._on_auto)
        self._manual_btn.clicked.connect(self._on_manual_hint)
        self._coverage_check.toggled.connect(self._on_coverage)

    def refresh_translations(self) -> None:

        self._title.setText(tr("Camera Link"))
        self._auto_btn.setText(tr("Auto"))
        self._manual_btn.setText(tr("Manual"))
        self._coverage_check.setText(tr("Show coverage zones"))
        self._active_caption.setText(tr("Active Camera"))
        self._why_caption.setText(tr("Why this camera"))
        self._alts_caption.setText(tr("Alternative Cameras"))

    def apply_snapshot(self, snapshot: CameraLinkSnapshot) -> None:

        is_auto = snapshot.mode == CameraLinkMode.AUTO
        self._auto_btn.blockSignals(True)
        self._manual_btn.blockSignals(True)
        self._auto_btn.setChecked(is_auto)
        self._manual_btn.setChecked(not is_auto)
        self._auto_btn.blockSignals(False)
        self._manual_btn.blockSignals(False)

        self._coverage_check.blockSignals(True)
        self._coverage_check.setChecked(snapshot.coverage_visible)
        self._coverage_check.blockSignals(False)

        active = snapshot.active
        if active is None:
            self._active_name.setText(tr("None"))
            self._active_meta.setText(tr("No camera in coverage"))
        else:
            self._active_name.setText(active.camera.name)
            self._active_meta.setText(
                f"{active.state.value} · {active.score * 100:.1f}% · "
                f"{active.match.distance_km:.2f} km · "
                f"Δ{active.match.bearing_difference_deg:.1f}°"
            )

        self._why.setText(snapshot.explanation or "—")
        status_bits = []
        if snapshot.reason:
            status_bits.append(snapshot.reason)
        if snapshot.switched:
            status_bits.append(tr("Camera switched"))
        status_bits.append(f"{tr('Mode')}: {snapshot.mode.value}")
        self._status.setText(" · ".join(status_bits))

        self._rebuild_alternatives(snapshot.alternatives)

    def _rebuild_alternatives(self, alternatives: list[ScoredCamera]) -> None:

        while self._alts_layout.count():
            item = self._alts_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._alt_buttons.clear()

        if not alternatives:
            empty = QLabel(tr("No alternatives"))
            empty.setStyleSheet(f"color: {ThemeColors.TextSecondary}; font-size: 9pt;")
            self._alts_layout.addWidget(empty)
            return

        for scored in alternatives:
            btn = QPushButton(
                f"{scored.camera.name}  ({scored.score * 100:.0f}% · {scored.state.value})"
            )
            btn.setStyleSheet(secondary_button_stylesheet())
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            camera_id = scored.camera.id
            btn.clicked.connect(
                lambda _checked=False, cid=camera_id: self._on_pick_alternative(cid)
            )
            self._alts_layout.addWidget(btn)
            self._alt_buttons.append(btn)

    def _on_auto(self) -> None:

        self._manager.clear_manual_override()
        self.modeChanged.emit(CameraLinkMode.AUTO.value)
        self.refreshRequested.emit()

    def _on_manual_hint(self) -> None:

        # Manual mode engages when an alternative is chosen; keep button state.
        self._manual_btn.setChecked(True)
        self._auto_btn.setChecked(False)

    def _on_pick_alternative(self, camera_id: str) -> None:

        self._manager.set_manual_override(camera_id)
        self.overrideRequested.emit(camera_id)
        self.modeChanged.emit(CameraLinkMode.MANUAL.value)
        self.refreshRequested.emit()

    def _on_coverage(self, checked: bool) -> None:

        self._manager.set_coverage_visible(checked)
        self.coverageToggled.emit(bool(checked))
