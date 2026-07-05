# -*- mode: python ; coding: utf-8 -*-
# ============================================================================
# Project X — PyInstaller spec
# ============================================================================

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent.parent
SRC = ROOT / "src"
BRANDING = SRC / "resources" / "branding"

block_cipher = None

a = Analysis(
    [str(SRC / "main.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[
        (str(SRC / "resources"), "resources"),
        (str(SRC / "config"), "config"),
        (str(ROOT / "data"), "data"),
        (str(BRANDING / "projectx.ico"), "."),
        (str(BRANDING / "projectx-logo.png"), "."),
    ],
    hiddenimports=[],
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
    disable_windowed_traceback=False,
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
