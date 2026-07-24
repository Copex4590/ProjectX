# ============================================================================
# Project X
# Session Recording & Replay Manager Page (SAVE-219)
# ============================================================================

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
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
from session.models import PLAYBACK_RATES, SESSION_FILE_EXTENSION, SessionState
from session.player import SessionPlayer, session_player
from session.recorder import SessionRecorder, session_recorder
from session.storage import (
    SessionStorage,
    format_bytes,
    format_duration,
    session_storage,
)

logger = logging.getLogger(__name__)


class _SectionCard(QFrame):

    def __init__(self, title_key: str, parent=None):
        super().__init__(parent)

        self._title_key = title_key
        self.setStyleSheet(card_stylesheet(radius=10))

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        self._title = QLabel()
        self._title.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 12pt; font-weight: 700;"
        )
        root.addWidget(self._title)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {ThemeColors.Border};")
        root.addWidget(divider)

        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        self.body.setContentsMargins(0, 4, 0, 0)
        root.addLayout(self.body)

    def refresh_translations(self) -> None:

        self._title.setText(tr(self._title_key))


class SessionRecordingPage(QWidget):
    """Record / Stop / Replay / list / import / export sessions."""

    navigateToMapRequested = Signal()

    def __init__(
        self,
        recorder: SessionRecorder | None = None,
        player: SessionPlayer | None = None,
        storage: SessionStorage | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._recorder = recorder or session_recorder
        self._player = player or session_player
        self._storage = storage or session_storage
        self._selected_path: Path | None = None

        self.setStyleSheet(f"background: {ThemeColors.Background};")
        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self.refresh_list()
        self._sync_controls()

    def _build_ui(self) -> None:

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {ThemeColors.Background}; border: none; }}"
        )
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet(f"background: {ThemeColors.Background};")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        self._title = QLabel()
        self._title.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 18pt; font-weight: 700;"
        )
        layout.addWidget(self._title)

        self._status = QLabel()
        self._status.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 10pt;"
        )
        layout.addWidget(self._status)

        record_card = _SectionCard("Recording")
        self._record_card = record_card
        record_row = QHBoxLayout()
        self._record_btn = QPushButton()
        self._record_btn.setStyleSheet(primary_button_stylesheet())
        self._stop_btn = QPushButton()
        self._stop_btn.setStyleSheet(secondary_button_stylesheet())
        record_row.addWidget(self._record_btn)
        record_row.addWidget(self._stop_btn)
        record_row.addStretch(1)
        record_card.body.addLayout(record_row)
        self._record_info = QLabel()
        self._record_info.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        record_card.body.addWidget(self._record_info)
        layout.addWidget(record_card)

        replay_card = _SectionCard("Replay")
        self._replay_card = replay_card
        replay_row = QHBoxLayout()
        self._play_btn = QPushButton()
        self._play_btn.setStyleSheet(primary_button_stylesheet())
        self._pause_btn = QPushButton()
        self._pause_btn.setStyleSheet(secondary_button_stylesheet())
        self._stop_replay_btn = QPushButton()
        self._stop_replay_btn.setStyleSheet(secondary_button_stylesheet())
        replay_row.addWidget(self._play_btn)
        replay_row.addWidget(self._pause_btn)
        replay_row.addWidget(self._stop_replay_btn)

        self._rate_label = QLabel()
        self._rate_label.setStyleSheet(f"color: {ThemeColors.TextSecondary};")
        replay_row.addWidget(self._rate_label)
        self._rate = QComboBox()
        self._rate.setStyleSheet(self._combo_style())
        for rate in PLAYBACK_RATES:
            self._rate.addItem(f"{rate}×", rate)
        replay_row.addWidget(self._rate)
        replay_row.addStretch(1)
        replay_card.body.addLayout(replay_row)

        seek_row = QHBoxLayout()
        self._elapsed_label = QLabel("0:00")
        self._elapsed_label.setStyleSheet(f"color: {ThemeColors.TextSecondary};")
        self._seek = QSlider(Qt.Orientation.Horizontal)
        self._seek.setRange(0, 1000)
        self._seek.setValue(0)
        self._duration_label = QLabel("0:00")
        self._duration_label.setStyleSheet(f"color: {ThemeColors.TextSecondary};")
        seek_row.addWidget(self._elapsed_label)
        seek_row.addWidget(self._seek, 1)
        seek_row.addWidget(self._duration_label)
        replay_card.body.addLayout(seek_row)
        layout.addWidget(replay_card)

        list_card = _SectionCard("Sessions")
        self._list_card = list_card
        actions = QHBoxLayout()
        self._refresh_btn = QPushButton()
        self._refresh_btn.setStyleSheet(secondary_button_stylesheet())
        self._import_btn = QPushButton()
        self._import_btn.setStyleSheet(secondary_button_stylesheet())
        self._export_btn = QPushButton()
        self._export_btn.setStyleSheet(secondary_button_stylesheet())
        self._delete_btn = QPushButton()
        self._delete_btn.setStyleSheet(secondary_button_stylesheet())
        self._load_btn = QPushButton()
        self._load_btn.setStyleSheet(primary_button_stylesheet())
        for btn in (
            self._refresh_btn,
            self._import_btn,
            self._export_btn,
            self._delete_btn,
            self._load_btn,
        ):
            actions.addWidget(btn)
        actions.addStretch(1)
        list_card.body.addLayout(actions)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Name", "Created", "Duration", "Size", "Events"]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setStyleSheet(
            f"""
            QTableWidget {{
                background: {ThemeColors.Panel};
                color: {ThemeColors.TextPrimary};
                gridline-color: {ThemeColors.Border};
                border: 1px solid {ThemeColors.Border};
                border-radius: 6px;
            }}
            QHeaderView::section {{
                background: {ThemeColors.panel_header()};
                color: {ThemeColors.TextSecondary};
                padding: 6px;
                border: none;
            }}
            """
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setMinimumHeight(220)
        list_card.body.addWidget(self._table)

        self._details = QLabel()
        self._details.setWordWrap(True)
        self._details.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        list_card.body.addWidget(self._details)
        layout.addWidget(list_card)
        layout.addStretch(1)

    def _connect_signals(self) -> None:

        self._record_btn.clicked.connect(self._on_record)
        self._stop_btn.clicked.connect(self._on_stop_record)
        self._play_btn.clicked.connect(self._on_play)
        self._pause_btn.clicked.connect(self._on_pause)
        self._stop_replay_btn.clicked.connect(self._on_stop_replay)
        self._rate.currentIndexChanged.connect(self._on_rate_changed)
        self._seek.sliderReleased.connect(self._on_seek_released)
        self._refresh_btn.clicked.connect(self.refresh_list)
        self._import_btn.clicked.connect(self._on_import)
        self._export_btn.clicked.connect(self._on_export)
        self._delete_btn.clicked.connect(self._on_delete)
        self._load_btn.clicked.connect(self._on_load)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

        self._player.state_changed.connect(lambda _s: self._sync_controls())
        self._player.progress_changed.connect(self._on_progress)
        self._player.finished.connect(self._sync_controls)

    def refresh_translations(self) -> None:

        self._title.setText(tr("Session Recording"))
        self._record_card.refresh_translations()
        self._replay_card.refresh_translations()
        self._list_card.refresh_translations()
        self._record_btn.setText(tr("Record"))
        self._stop_btn.setText(tr("Stop"))
        self._play_btn.setText(tr("Play"))
        self._pause_btn.setText(tr("Pause"))
        self._stop_replay_btn.setText(tr("Stop Replay"))
        self._rate_label.setText(tr("Speed"))
        self._refresh_btn.setText(tr("Refresh"))
        self._import_btn.setText(tr("Import"))
        self._export_btn.setText(tr("Export"))
        self._delete_btn.setText(tr("Delete"))
        self._load_btn.setText(tr("Load for Replay"))
        self._table.setHorizontalHeaderLabels(
            [
                tr("Name"),
                tr("Created"),
                tr("Duration"),
                tr("Size"),
                tr("Events"),
            ]
        )
        self._sync_controls()

    def refresh_list(self) -> None:

        entries = self._storage.list_sessions()
        self._table.setRowCount(0)
        for entry in entries:
            row = self._table.rowCount()
            self._table.insertRow(row)
            values = [
                entry.label,
                entry.manifest.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                format_duration(entry.manifest.duration_seconds),
                format_bytes(entry.size_bytes),
                str(entry.manifest.event_count),
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, str(entry.path))
                self._table.setItem(row, col, item)
        self._on_selection_changed()

    def _sync_controls(self) -> None:

        recording = self._recorder.is_recording
        active = self._player.is_active
        playing = self._player.is_playing

        self._record_btn.setEnabled(not recording and not active)
        self._stop_btn.setEnabled(recording)
        self._play_btn.setEnabled(self._player.manifest is not None and not recording)
        self._pause_btn.setEnabled(playing)
        self._stop_replay_btn.setEnabled(active)
        self._rate.setEnabled(self._player.manifest is not None)
        self._seek.setEnabled(self._player.manifest is not None)

        if recording:
            self._status.setText(
                tr("Recording… {count} events").format(
                    count=self._recorder.event_count
                )
            )
            self._status.setStyleSheet(f"color: {ThemeColors.Danger}; font-size: 10pt;")
        elif playing:
            self._status.setText(tr("Replaying session"))
            self._status.setStyleSheet(
                f"color: {ThemeColors.Success}; font-size: 10pt;"
            )
        elif active:
            self._status.setText(tr("Replay paused"))
            self._status.setStyleSheet(
                f"color: {ThemeColors.Warning}; font-size: 10pt;"
            )
        else:
            self._status.setText(tr("Idle"))
            self._status.setStyleSheet(
                f"color: {ThemeColors.TextSecondary}; font-size: 10pt;"
            )

        self._record_info.setText(
            tr("Captures AIS positions, camera links, alerts, and playback events.")
        )

    def _on_record(self) -> None:

        if self._player.is_active:
            self._player.stop()
        try:
            self._recorder.start()
        except Exception as exc:
            QMessageBox.warning(self, tr("Record"), str(exc))
            return
        self._sync_controls()

    def _on_stop_record(self) -> None:

        path = self._recorder.stop()
        self.refresh_list()
        self._sync_controls()
        if path is not None:
            QMessageBox.information(
                self,
                tr("Record"),
                tr("Session saved:\n{path}").format(path=str(path)),
            )

    def _on_load(self) -> None:

        if self._selected_path is None:
            QMessageBox.information(
                self, tr("Replay"), tr("Select a session first.")
            )
            return
        if self._recorder.is_recording:
            QMessageBox.warning(
                self, tr("Replay"), tr("Stop recording before replay.")
            )
            return
        try:
            self._player.load(self._selected_path)
        except Exception as exc:
            QMessageBox.warning(self, tr("Replay"), str(exc))
            return
        self._sync_controls()
        self._on_progress(0.0, self._player.duration_seconds)

    def _on_play(self) -> None:

        if self._player.manifest is None:
            self._on_load()
            if self._player.manifest is None:
                return
        self._player.set_rate(int(self._rate.currentData() or 1))
        self._player.play()
        self.navigateToMapRequested.emit()
        self._sync_controls()

    def _on_pause(self) -> None:

        self._player.pause()
        self._sync_controls()

    def _on_stop_replay(self) -> None:

        self._player.stop()
        self._sync_controls()

    def _on_rate_changed(self, _index: int = 0) -> None:

        self._player.set_rate(int(self._rate.currentData() or 1))

    def _on_seek_released(self) -> None:

        fraction = self._seek.value() / max(1, self._seek.maximum())
        self._player.seek_fraction(fraction)

    def _on_progress(self, elapsed: float, duration: float) -> None:

        self._elapsed_label.setText(format_duration(elapsed))
        self._duration_label.setText(format_duration(duration))
        if duration > 0 and not self._seek.isSliderDown():
            self._seek.blockSignals(True)
            self._seek.setValue(int((elapsed / duration) * self._seek.maximum()))
            self._seek.blockSignals(False)
        if self._recorder.is_recording:
            self._sync_controls()

    def _on_selection_changed(self) -> None:

        items = self._table.selectedItems()
        if not items:
            self._selected_path = None
            self._details.setText(tr("No session selected."))
            return
        path = Path(str(items[0].data(Qt.ItemDataRole.UserRole) or ""))
        self._selected_path = path if path.exists() else None
        if self._selected_path is None:
            self._details.setText(tr("No session selected."))
            return
        try:
            manifest = self._storage.read_manifest(self._selected_path)
            self._details.setText(
                tr(
                    "ID: {id}\nCreated: {created}\nDuration: {duration}\n"
                    "Events: {events}\nSize: {size}\nFile: {path}"
                ).format(
                    id=manifest.session_id,
                    created=manifest.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    duration=format_duration(manifest.duration_seconds),
                    events=manifest.event_count,
                    size=format_bytes(self._selected_path.stat().st_size),
                    path=str(self._selected_path),
                )
            )
        except Exception as exc:
            self._details.setText(str(exc))

    def _on_import(self) -> None:

        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Import"),
            str(Path.home()),
            f"Project X Session (*{SESSION_FILE_EXTENSION})",
        )
        if not path:
            return
        try:
            imported = self._storage.import_session(Path(path))
            self.refresh_list()
            QMessageBox.information(
                self,
                tr("Import"),
                tr("Imported:\n{path}").format(path=str(imported)),
            )
        except Exception as exc:
            QMessageBox.warning(self, tr("Import"), str(exc))

    def _on_export(self) -> None:

        if self._selected_path is None:
            QMessageBox.information(
                self, tr("Export"), tr("Select a session first.")
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Export"),
            str(Path.home() / self._selected_path.name),
            f"Project X Session (*{SESSION_FILE_EXTENSION})",
        )
        if not path:
            return
        try:
            exported = self._storage.export_session(self._selected_path, Path(path))
            QMessageBox.information(
                self,
                tr("Export"),
                tr("Exported:\n{path}").format(path=str(exported)),
            )
        except Exception as exc:
            QMessageBox.warning(self, tr("Export"), str(exc))

    def _on_delete(self) -> None:

        if self._selected_path is None:
            return
        answer = QMessageBox.question(
            self,
            tr("Delete"),
            tr("Delete session?\n{path}").format(path=str(self._selected_path)),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self._player.is_active and self._player.manifest:
            self._player.stop()
        self._storage.delete(self._selected_path)
        self.refresh_list()

    @staticmethod
    def _combo_style() -> str:

        return f"""
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
