#!/usr/bin/env python3
# ============================================================================
# Project X
# Generate branding raster assets from SVG master
# ============================================================================

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BRANDING_DIR = ROOT / "src" / "resources" / "branding"
PNG_PATH = BRANDING_DIR / "projectx-logo.png"
ICO_PATH = BRANDING_DIR / "projectx.ico"


def _draw_logo(size: int) -> Image.Image:

    image = Image.new("RGBA", (size, size), (29, 33, 39, 255))
    draw = ImageDraw.Draw(image)

    margin = int(size * 0.08)
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=int(size * 0.18),
        fill=(37, 42, 49, 255),
    )

    center = size // 2
    hull_length = int(size * 0.34)
    hull_width = int(size * 0.11)
    bow = int(size * 0.07)

    def draw_bow(angle_deg: float, light: str, dark: str) -> None:

        import math

        radians = math.radians(angle_deg)
        cos_a = math.cos(radians)
        sin_a = math.sin(radians)

        def rotate(x: float, y: float) -> tuple[float, float]:
            return (
                center + x * cos_a - y * sin_a,
                center + x * sin_a + y * cos_a,
            )

        outer = [
            rotate(-hull_length, -hull_width),
            rotate(hull_length, 0),
            rotate(-hull_length, hull_width),
            rotate(-hull_length + bow, 0),
        ]
        inner = [
            rotate(-hull_length + bow * 2, -hull_width * 0.55),
            rotate(hull_length - bow, 0),
            rotate(-hull_length + bow * 2, hull_width * 0.55),
            rotate(-hull_length + bow * 3, 0),
        ]

        draw.polygon(outer, fill=light)
        draw.polygon(inner, fill=dark)

    draw_bow(-45, "#4FC3F7", "#1976D2")
    draw_bow(45, "#4FC3F7", "#1976D2")

    r_outer = int(size * 0.045)
    r_inner = int(size * 0.02)
    draw.ellipse(
        (
            center - r_outer,
            center - r_outer,
            center + r_outer,
            center + r_outer,
        ),
        fill="#4FC3F7",
    )
    draw.ellipse(
        (
            center - r_inner,
            center - r_inner,
            center + r_inner,
            center + r_inner,
        ),
        fill="#E3F2FD",
    )

    return image


def _write_png(path: Path, image: Image.Image) -> None:

    image.save(path, format="PNG")


def _write_ico(path: Path, image: Image.Image) -> None:

    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    image.save(path, format="ICO", sizes=sizes)


def main() -> None:

    BRANDING_DIR.mkdir(parents=True, exist_ok=True)
    master = _draw_logo(512)
    _write_png(PNG_PATH, master)
    _write_ico(ICO_PATH, master)
    print(f"Wrote {PNG_PATH}")
    print(f"Wrote {ICO_PATH}")


if __name__ == "__main__":
    main()
