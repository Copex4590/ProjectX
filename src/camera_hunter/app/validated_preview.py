"""Temporary standalone UI to check VALIDATED Hunter cameras on a map.

PX map-click chain (unchanged, documented here only):

  marker gmp-click / Leaflet click
  → MapWidget bridge.selectCamera(camera_id)
  → MapPage._on_catalog_camera_selected
  → camera.web_url
  → MapPage.start_hunter_camera_discovery
  → CameraPreviewPanel.start_hunter_discovery
  → HunterLiveSession.stop() + discover(url)  # interactive=True → HlsPlayer

This tool uses the same Hunter/HlsPlayer sequence after the URL is known.
The URL comes from hunter_catalog_validation.json (VALIDATED only), not from
camera_manager, so the overnight catalog validator is not touched.

A dedicated HunterLiveSession is used (not the PX GUI singleton and not the
catalog-validator session).
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from camera_hunter.app.catalog_validator import validation_store_path
from camera_hunter.engine.catalog_validation import ValidationRecord
from camera_hunter.engine.validation_map import validated_map_cameras
from camera_hunter.engine.validation_preview import (
    AUTO_REFRESH_MS,
    load_validated_records,
    preview_map_html_from_records,
    records_by_id,
    web_url_for_validated_camera,
)

logger = logging.getLogger(__name__)

PREVIEW_IDLE = "idle"
PREVIEW_LOADING = "loading"
PREVIEW_PLAYING = "playing"
PREVIEW_FAILED = "failed"


def create_preview_session():
    """Visible Hunter session for this tool only. Not the PX GUI singleton."""

    from cameras.hunter_session import HunterLiveSession

    return HunterLiveSession(headless=False)


def host_hunter_player(session, video_host) -> None:
    """Same hosting as CameraPreviewPanel._host_hunter_player."""

    widget = session.player_widget()
    if widget is None:
        return
    layout = video_host.layout()
    if layout is None:
        return
    if widget.parent() is not video_host:
        layout.addWidget(widget)
    widget.show()


def start_hunter_preview(session, page_url: str, video_host) -> bool:
    """Mirror CameraPreviewPanel.start_hunter_discovery for a known page URL."""

    session.ensure()
    session.stop()
    host_hunter_player(session, video_host)
    return session.discover(page_url)


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        prog="validated-preview",
        description=(
            "Temporary map of VALIDATED Hunter cameras. Click a marker to run "
            "the existing Hunter discovery + HlsPlayer preview. Reads "
            "hunter_catalog_validation.json only; does not start catalog scan."
        ),
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=None,
        help="Validation JSON (default: data/cache/hunter_catalog_validation.json).",
    )
    parser.add_argument(
        "--refresh-interval",
        type=float,
        default=AUTO_REFRESH_MS / 1000.0,
        metavar="SECONDS",
        help="Auto-refresh interval (default: 30).",
    )
    parser.add_argument(
        "--no-auto-refresh",
        action="store_true",
        help="Do not reload the JSON on a timer.",
    )
    return parser


def load_preview_cameras(path: Path) -> tuple[list[ValidationRecord], str | None]:
    """Read VALIDATED cameras. On a bad/missing file keep going with a message."""

    target = Path(path)
    if not target.exists():
        return [], f"Validation JSON not found: {target}"
    try:
        records = load_validated_records(target)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read validation JSON %s: %s", target, exc)
        return [], f"Could not read validation JSON: {exc}"
    return records, None


def create_window(args: argparse.Namespace, session=None):
    """Build the Qt window. Call only after QApplication exists."""

    from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal, Slot
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtWebEngineCore import QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWidgets import (
        QCheckBox,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QPushButton,
        QSizePolicy,
        QSplitter,
        QVBoxLayout,
        QWidget,
    )

    class MapBridge(QObject):

        cameraSelected = Signal(str)

        @Slot(str)
        def selectCamera(self, camera_id: str) -> None:

            self.cameraSelected.emit(str(camera_id or ""))

    class ValidatedPreviewWindow(QMainWindow):

        def __init__(self, store_path: Path, session, *, auto_refresh: bool, interval_ms: int):

            super().__init__()
            self.setWindowTitle("Project X — validated camera check (temporary)")
            self.resize(1280, 720)

            self._store_path = Path(store_path)
            self._session = session
            self._index: dict[str, ValidationRecord] = {}
            self._state = PREVIEW_IDLE
            self._selected_id = ""

            toolbar = QWidget()
            toolbar_layout = QHBoxLayout(toolbar)
            toolbar_layout.setContentsMargins(8, 8, 8, 8)
            self._refresh_btn = QPushButton("Refresh")
            self._refresh_btn.clicked.connect(self.refresh)
            refresh_s = max(int(interval_ms / 1000), 1)
            self._auto = QCheckBox(f"Auto-refresh {refresh_s}s")
            self._auto.setChecked(bool(auto_refresh))
            self._auto.toggled.connect(self._on_auto_toggled)
            self._count_label = QLabel("VALIDATED: 0")
            self._file_label = QLabel(str(self._store_path))
            self._file_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            toolbar_layout.addWidget(self._refresh_btn)
            toolbar_layout.addWidget(self._auto)
            toolbar_layout.addWidget(self._count_label)
            toolbar_layout.addStretch(1)
            toolbar_layout.addWidget(self._file_label)

            self._map = QWebEngineView()
            settings = self._map.settings()
            settings.setAttribute(
                QWebEngineSettings.LocalContentCanAccessRemoteUrls,
                True,
            )
            settings.setAttribute(
                QWebEngineSettings.JavascriptEnabled,
                True,
            )
            self._bridge = MapBridge()
            self._bridge.cameraSelected.connect(self._on_camera_selected)
            channel = QWebChannel(self._map.page())
            channel.registerObject("bridge", self._bridge)
            self._map.page().setWebChannel(channel)
            self._map_loaded = False
            self._map.loadFinished.connect(self._on_map_loaded)

            preview = QWidget()
            preview.setMinimumWidth(380)
            preview_layout = QVBoxLayout(preview)
            self._name_label = QLabel("No camera selected")
            self._name_label.setWordWrap(True)
            self._name_label.setStyleSheet("font-size: 16px; font-weight: 600;")
            self._id_label = QLabel("")
            self._id_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self._url_label = QLabel("")
            self._url_label.setWordWrap(True)
            self._url_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self._state_label = QLabel(PREVIEW_IDLE)
            self._state_label.setObjectName("previewState")
            self._detail_label = QLabel("")
            self._detail_label.setWordWrap(True)

            self._video_host = QWidget()
            self._video_host.setObjectName("videoHost")
            self._video_host.setMinimumHeight(220)
            self._video_host.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            video_layout = QVBoxLayout(self._video_host)
            video_layout.setContentsMargins(0, 0, 0, 0)

            preview_layout.addWidget(self._name_label)
            preview_layout.addWidget(self._id_label)
            preview_layout.addWidget(self._url_label)
            preview_layout.addWidget(self._state_label)
            preview_layout.addWidget(self._detail_label)
            preview_layout.addWidget(self._video_host, 1)

            splitter = QSplitter(Qt.Orientation.Horizontal)
            splitter.addWidget(self._map)
            splitter.addWidget(preview)
            splitter.setStretchFactor(0, 3)
            splitter.setStretchFactor(1, 2)

            root = QWidget()
            root_layout = QVBoxLayout(root)
            root_layout.setContentsMargins(0, 0, 0, 0)
            root_layout.addWidget(toolbar)
            root_layout.addWidget(splitter, 1)
            self.setCentralWidget(root)
            self.setStyleSheet(
                """
                QLabel#previewState[state="loading"] { color: #c9a227; font-weight: 700; }
                QLabel#previewState[state="playing"] { color: #2e9e57; font-weight: 700; }
                QLabel#previewState[state="failed"] { color: #c0392b; font-weight: 700; }
                QLabel#previewState[state="idle"] { color: #666; font-weight: 700; }
                QWidget#videoHost { background: #111; }
                """
            )

            self._session.live_ready.connect(self._on_live_ready)
            self._session.status.connect(self._on_status)
            self._session.failed.connect(self._on_failed)

            self._timer = QTimer(self)
            self._timer.timeout.connect(self.refresh)
            interval = max(int(interval_ms), 1000)
            self._timer.setInterval(interval)
            if auto_refresh:
                self._timer.start()

            self.refresh()

        def _set_state(self, state: str, detail: str = "") -> None:

            self._state = state
            self._state_label.setText(state.upper())
            self._state_label.setProperty("state", state)
            self._state_label.style().unpolish(self._state_label)
            self._state_label.style().polish(self._state_label)
            self._detail_label.setText(detail)

        def _on_map_loaded(self, ok: bool) -> None:

            self._map_loaded = bool(ok)

        def refresh(self) -> None:

            records, error = load_preview_cameras(self._store_path)
            if error:
                if self._index:
                    self._count_label.setText(
                        f"VALIDATED: {len(self._index)} ({error})"
                    )
                    return
                self._count_label.setText(f"VALIDATED: 0 ({error})")
            else:
                self._index = records_by_id(records)
            markers = validated_map_cameras(list(self._index.values()))
            if not error:
                self._count_label.setText(f"VALIDATED: {len(markers)}")
            if not self._map_loaded:
                html = preview_map_html_from_records(list(self._index.values()))
                self._map.setHtml(html, QUrl("https://unpkg.com/"))
                return
            payload = json.dumps(markers, ensure_ascii=True)
            self._map.page().runJavaScript(f"updateCameras({payload})")

        def _on_auto_toggled(self, checked: bool) -> None:

            if checked:
                self._timer.start()
            else:
                self._timer.stop()

        def _on_camera_selected(self, camera_id: str) -> None:

            camera_id = str(camera_id or "").strip()
            record = self._index.get(camera_id)
            if record is None:
                self._set_state(PREVIEW_FAILED, f"Unknown camera: {camera_id}")
                return
            page_url = web_url_for_validated_camera(self._index, camera_id)
            self._selected_id = camera_id
            self._name_label.setText(record.name or camera_id)
            self._id_label.setText(camera_id)
            self._url_label.setText(page_url)
            if not page_url:
                self._set_state(PREVIEW_FAILED, "Camera has no web_url")
                return
            self._set_state(PREVIEW_LOADING, "Hunter discovery…")
            started = start_hunter_preview(self._session, page_url, self._video_host)
            if not started:
                self._set_state(PREVIEW_FAILED, "Discovery did not start")

        def _on_live_ready(self, result: object) -> None:

            if self._state != PREVIEW_LOADING:
                return
            host_hunter_player(self._session, self._video_host)
            source = str(getattr(result, "source_page", "") or "").strip()
            self._set_state(PREVIEW_PLAYING, source or "LIVE")

        def _on_status(self, message: str) -> None:

            if self._state != PREVIEW_LOADING:
                return
            text = str(message or "").strip()
            if text:
                self._detail_label.setText(text)

        def _on_failed(self, message: str) -> None:

            if self._state not in {PREVIEW_LOADING, PREVIEW_PLAYING}:
                return
            self._set_state(PREVIEW_FAILED, str(message or "").strip() or "failed")

        def closeEvent(self, event) -> None:  # noqa: N802

            try:
                self._timer.stop()
                self._session.stop()
            except Exception:
                logger.exception("Failed stopping preview Hunter session")
            super().closeEvent(event)

    if session is None:
        session = create_preview_session()
    store_path = Path(args.store) if args.store is not None else validation_store_path()
    interval_ms = int(float(getattr(args, "refresh_interval", 30.0)) * 1000)
    auto = not bool(getattr(args, "no_auto_refresh", False))
    return ValidatedPreviewWindow(
        store_path,
        session,
        auto_refresh=auto,
        interval_ms=interval_ms,
    )


def main(argv: list[str] | None = None) -> int:

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = build_parser().parse_args(argv)

    from camera_hunter.app.webengine_setup import configure_remote_debugging
    from PySide6.QtWidgets import QApplication

    configure_remote_debugging()
    app = QApplication.instance()
    if app is None:
        app = QApplication(["projectx-validated-preview"])
    window = create_window(args)
    window.show()
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
