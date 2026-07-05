# ============================================================================
# Project X
# Branding Assets
# ============================================================================

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

_BRANDING_DIR = Path(__file__).resolve().parent.parent / "resources" / "branding"


def branding_dir() -> Path:

    return _BRANDING_DIR


def logo_svg_path() -> Path:

    return _BRANDING_DIR / "projectx-logo.svg"


def logo_png_path() -> Path:

    return _BRANDING_DIR / "projectx-logo.png"


def window_icon_path() -> Path:

    if sys.platform == "win32":
        ico = _BRANDING_DIR / "projectx.ico"

        if ico.exists():
            return ico

    return logo_png_path()


def app_icon() -> QIcon:

    icon_path = window_icon_path()

    if icon_path.exists():
        return QIcon(str(icon_path))

    return QIcon()


def logo_pixmap(size: int = 128) -> QPixmap:

    png = logo_png_path()

    if png.exists():
        pixmap = QPixmap(str(png))

        if not pixmap.isNull():
            return pixmap.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

    return QPixmap()
