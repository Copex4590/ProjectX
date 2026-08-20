# -*- mode: python ; coding: utf-8 -*-
# ============================================================================
# Project X — PyInstaller spec (Linux + Windows one-dir bundle)
# ============================================================================
#
# Bundled runtime assets (via datas below):
#   - Qt WebEngine (collect_all hooks)
#   - Leaflet (src/resources/map/leaflet/)
#   - Translations (src/resources/translations/)
#   - Icons / flags / branding logos (src/resources/)
#   - Map HTML / CSS / JavaScript (src/resources/map/)
#   - Read-only config samples + camera packs
#
# Writable runtime data (DBs, logbooks, photos) use app.paths user-data dirs.
# The repo data/ tree is development-only and must not be bundled.

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

# SPECPATH is the directory containing this spec (installer/); repo root is one level up.
ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / "src"
BRANDING = SRC / "resources" / "branding"
CONFIG = SRC / "config"

# Read-only bundled configuration (exclude user runtime JSON files).
_config_datas = [
    (str(CONFIG / "cameras"), "config/cameras"),
    (str(CONFIG / "camera_packs"), "config/camera_packs"),
    (str(CONFIG / "playback.json"), "config"),
    (str(CONFIG / "preferences.json.example"), "config"),
    (str(CONFIG / "cameras.json.example"), "config"),
    (str(CONFIG / "observation_points.json.example"), "config"),
]

_resource_datas = [
    (str(SRC / "resources"), "resources"),
    *_config_datas,
    (str(BRANDING / "projectx.ico"), "."),
    (str(BRANDING / "projectx-logo.png"), "."),
]

_webengine_datas = []
_webengine_binaries = []
_webengine_hiddenimports = []

for _pkg in (
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebChannel",
):
    _datas, _binaries, _hiddenimports = collect_all(_pkg)
    _webengine_datas += _datas
    _webengine_binaries += _binaries
    _webengine_hiddenimports += _hiddenimports

# Vendored camera_hunter DiscoveryEngine import graph (not in PX src otherwise):
#   cdp_monitor → QtWebSockets
#   hls_player  → QtMultimedia + QtMultimediaWidgets
_hunter_qt_datas = []
_hunter_qt_binaries = []
_hunter_qt_hiddenimports = []

for _pkg in (
    "PySide6.QtWebSockets",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
):
    _datas, _binaries, _hiddenimports = collect_all(_pkg)
    _hunter_qt_datas += _datas
    _hunter_qt_binaries += _binaries
    _hunter_qt_hiddenimports += _hiddenimports

_camera_hunter_hiddenimports = [
    "camera_hunter",
    "camera_hunter.models",
    "camera_hunter.models.camera_result",
    "camera_hunter.models.camera_source",
    "camera_hunter.engine",
    "camera_hunter.engine.discovery",
    "camera_hunter.engine.classifier",
    "camera_hunter.engine.session",
    "camera_hunter.engine.hls_capture",
    "camera_hunter.engine.hls_diag",
    "camera_hunter.engine.hls_player",
    "camera_hunter.engine.hls_proxy",
    "camera_hunter.engine.jpg_player",
    "camera_hunter.engine.cdp_monitor",
    "camera_hunter.engine.earthcam_consent",
    "camera_hunter.engine.listing_catalog",
    "camera_hunter.engine.listing_store",
    "camera_hunter.engine.listing_scanner",
    "camera_hunter.engine.providers",
    "camera_hunter.engine.providers.earthcam",
    "camera_hunter.app",
    "camera_hunter.app.webengine_setup",
]

_hiddenimports = [
    *_webengine_hiddenimports,
    *_hunter_qt_hiddenimports,
    *_camera_hunter_hiddenimports,
    "openpyxl",
    "openpyxl.cell",
    "openpyxl.workbook",
    "websocket",
    "websocket._abnf",
    "websocket._core",
]

block_cipher = None

a = Analysis(
    [str(SRC / "main.py")],
    pathex=[str(SRC)],
    binaries=[*_webengine_binaries, *_hunter_qt_binaries],
    datas=[*_resource_datas, *_webengine_datas, *_hunter_qt_datas],
    hiddenimports=_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="projectx",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(BRANDING / "projectx.ico"),
    # PyInstaller 6+ defaults to _internal/ for onedir datas; legacy layout keeps
    # resources/ next to the executable (Inno Setup, AppImage, verify scripts).
    contents_directory=".",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="projectx",
)
