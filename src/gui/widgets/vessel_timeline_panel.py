# ============================================================================
# Project X
# Vessel Timeline Playback Panel (SAVE-214)
# ============================================================================

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from gui.i18n_support import bind_language_refresh
from gui.theme import (
    ThemeColors,
    card_stylesheet,
    primary_button_stylesheet,
    secondary_button_stylesheet,
)
from i18n import tr
from timeline.vessel_playback import (
    PLAYBACK_RATES,
    PlaybackMode,
    PlaybackSample,
    VesselPlaybackEngine,
)


class VesselTimelinePanel(QWidget):
    """Playback controls for the selected vessel trail."""

    playPauseRequested = Signal()
    liveRequested = Signal()
    rateChanged = Signal(int)
    seekFractionChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._updating = False
        self._mode = PlaybackMode.LIVE
        self._sample_count = 0

        self.setMinimumWidth(320)
        self.setMaximumWidth(420)
        self.setStyleSheet(f"background: {ThemeColors.Background};")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(0)

        card = QFrame()
        card.setStyleSheet(card_stylesheet(radius=10))
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        self._title = QLabel()
        self._title.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 11pt; font-weight: 700;"
        )
        card_layout.addWidget(self._title)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {ThemeColors.Border};")
        card_layout.addWidget(divider)

        self._status = QLabel()
        self._status.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        card_layout.addWidget(self._status)

        self._time_label = QLabel("—")
        self._time_label.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 10pt; font-weight: 600;"
        )
        card_layout.addWidget(self._time_label)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.setEnabled(False)
        self._slider.setStyleSheet(
            f"""
            QSlider::groove:horizontal {{
                height: 6px;
                background: {ThemeColors.Border};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {ThemeColors.Primary500};
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::sub-page:horizontal {{
                background: {ThemeColors.Primary300};
                border-radius: 3px;
            }}
            """
        )
        card_layout.addWidget(self._slider)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        self._play_button = QPushButton()
        self._play_button.setStyleSheet(primary_button_stylesheet())
        controls.addWidget(self._play_button)

        self._live_button = QPushButton()
        self._live_button.setStyleSheet(secondary_button_stylesheet())
        controls.addWidget(self._live_button)

        self._rate_combo = QComboBox()
        self._rate_combo.setStyleSheet(
            f"""
            QComboBox {{
                background: {ThemeColors.Panel};
                color: {ThemeColors.TextPrimary};
                border: 1px solid {ThemeColors.Border};
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 72px;
            }}
            QComboBox QAbstractItemView {{
                background: {ThemeColors.Panel};
                color: {ThemeColors.TextPrimary};
                selection-background-color: {ThemeColors.Primary700};
            }}
            """
        )
        for rate in PLAYBACK_RATES:
            self._rate_combo.addItem(f"{rate}×", rate)
        controls.addWidget(self._rate_combo)
        controls.addStretch(1)
        card_layout.addLayout(controls)

        root.addWidget(card)

        self._play_button.clicked.connect(self.playPauseRequested.emit)
        self._live_button.clicked.connect(self.liveRequested.emit)
        self._rate_combo.currentIndexChanged.connect(self._on_rate_changed)
        self._slider.valueChanged.connect(self._on_slider_changed)

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self.set_enabled_for_vessel(False)

    def refresh_translations(self) -> None:

        self._title.setText(tr("Vessel Timeline"))
        self._live_button.setText(tr("Live"))
        self._update_play_button()
        self._update_status_text()

    def set_enabled_for_vessel(self, enabled: bool) -> None:

        self._play_button.setEnabled(enabled and self._sample_count > 0)
        self._live_button.setEnabled(enabled)
        self._rate_combo.setEnabled(enabled)
        self._slider.setEnabled(enabled and self._sample_count > 1)
        if not enabled:
            self._status.setText(tr("Select a vessel to use timeline playback."))
            self._time_label.setText("—")
            self._updating = True
            self._slider.setRange(0, 0)
            self._slider.setValue(0)
            self._updating = False

    def bind_engine_state(
        self,
        *,
        mode: PlaybackMode | str,
        index: int,
        total: int,
        sample: PlaybackSample | None,
        rate: int,
    ) -> None:

        if isinstance(mode, PlaybackMode):
            self._mode = mode
        else:
            self._mode = PlaybackMode(str(mode))
        self._sample_count = max(0, int(total))
        self._updating = True
        try:
            if self._sample_count <= 1:
                self._slider.setRange(0, 0)
                self._slider.setValue(0)
            else:
                self._slider.setRange(0, self._sample_count - 1)
                self._slider.setValue(max(0, min(index, self._sample_count - 1)))
        finally:
            self._updating = False

        rate_index = self._rate_combo.findData(int(rate))
        if rate_index >= 0 and self._rate_combo.currentIndex() != rate_index:
            previous = self._updating
            self._updating = True
            self._rate_combo.setCurrentIndex(rate_index)
            self._updating = previous

        self._play_button.setEnabled(self._sample_count > 0)
        self._slider.setEnabled(self._sample_count > 1)
        self._update_play_button()
        self._update_status_text()
        self._update_time_label(sample, index, total)

    def _update_play_button(self) -> None:

        if self._mode == PlaybackMode.PLAYING:
            self._play_button.setText(tr("Pause"))
        else:
            self._play_button.setText(tr("Play"))

    def _update_status_text(self) -> None:

        if self._sample_count <= 0:
            self._status.setText(tr("No trail points available."))
            return

        if self._mode == PlaybackMode.LIVE:
            mode_text = tr("Live")
        elif self._mode == PlaybackMode.PLAYING:
            mode_text = tr("Playing")
        else:
            mode_text = tr("Paused")

        self._status.setText(
            f"{mode_text} · {self._sample_count} {tr('points')}"
        )

    def _update_time_label(
        self,
        sample: PlaybackSample | None,
        index: int,
        total: int,
    ) -> None:

        if sample is None or total <= 0:
            self._time_label.setText("—")
            return

        stamp = sample.timestamp
        if isinstance(stamp, datetime):
            stamp_text = stamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            stamp_text = str(stamp)
        self._time_label.setText(f"{stamp_text}  ({index + 1}/{total})")

    def _on_rate_changed(self, _index: int) -> None:

        if self._updating:
            return
        rate = self._rate_combo.currentData()
        if rate is not None:
            self.rateChanged.emit(int(rate))

    def _on_slider_changed(self, value: int) -> None:

        if self._updating or self._sample_count <= 1:
            return
        fraction = float(value) / float(self._sample_count - 1)
        self.seekFractionChanged.emit(fraction)


def sync_panel_from_engine(
    panel: VesselTimelinePanel,
    engine: VesselPlaybackEngine,
) -> None:

    panel.bind_engine_state(
        mode=engine.mode,
        index=engine.index,
        total=engine.sample_count,
        sample=engine.current_sample(),
        rate=engine.rate,
    )
