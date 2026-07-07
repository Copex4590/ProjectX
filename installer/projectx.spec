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

_hiddenimports = [
    *_webengine_hiddenimports,
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
    binaries=_webengine_binaries,
    datas=[*_resource_datas, *_webengine_datas],
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
