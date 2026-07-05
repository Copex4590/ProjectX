# -*- mode: python ; coding: utf-8 -*-
# ============================================================================
# Project X — PyInstaller spec
# ============================================================================

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent.parent
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

block_cipher = None

a = Analysis(
    [str(SRC / "main.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[
        (str(SRC / "resources"), "resources"),
        *_config_datas,
        (str(ROOT / "data"), "data"),
        (str(BRANDING / "projectx.ico"), "."),
        (str(BRANDING / "projectx-logo.png"), "."),
    ],
    hiddenimports=[
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebChannel",
        "openpyxl",
        "openpyxl.cell",
        "openpyxl.workbook",
        "websocket",
        "websocket._abnf",
        "websocket._core",
    ],
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
