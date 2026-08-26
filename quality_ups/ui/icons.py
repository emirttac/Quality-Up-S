from __future__ import annotations

from functools import lru_cache

from PIL import Image, ImageDraw
import customtkinter as ctk

from quality_ups.config import APP_DIR

SOCIAL_DIR = APP_DIR / "assets" / "social"


def _hex(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _blank(size: int) -> Image.Image:
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def _line(draw: ImageDraw.ImageDraw, xy, color: str, width: int) -> None:
    draw.line(xy, fill=_hex(color) + (255,), width=width, joint="curve")


@lru_cache(maxsize=64)
def nav_icon(name: str, color: str, size: int = 22) -> ctk.CTkImage:
    img = _blank(size * 2)
    draw = ImageDraw.Draw(img)
    s = size * 2
    w = max(3, s // 12)
    c = color
    if name == "home":
        _line(draw, [(s * 0.18, s * 0.52), (s * 0.50, s * 0.22), (s * 0.82, s * 0.52)], c, w)
        _line(draw, [(s * 0.28, s * 0.50), (s * 0.28, s * 0.82), (s * 0.72, s * 0.82), (s * 0.72, s * 0.50)], c, w)
        _line(draw, [(s * 0.44, s * 0.82), (s * 0.44, s * 0.62), (s * 0.56, s * 0.62), (s * 0.56, s * 0.82)], c, w)
    elif name == "settings":
        cx, cy, r = s / 2, s / 2, s * 0.16
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=_hex(c) + (255,), width=w)
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0), (0.72, 0.72), (-0.72, 0.72), (0.72, -0.72), (-0.72, -0.72)):
            x0, y0 = cx + dx * s * 0.22, cy + dy * s * 0.22
            x1, y1 = cx + dx * s * 0.40, cy + dy * s * 0.40
            _line(draw, [(x0, y0), (x1, y1)], c, w + 1)
    else:
        draw.ellipse((s * 0.16, s * 0.16, s * 0.84, s * 0.84), outline=_hex(c) + (255,), width=w)
        _line(draw, [(s * 0.50, s * 0.42), (s * 0.50, s * 0.70)], c, w + 1)
        dot = s * 0.05
        draw.ellipse((s * 0.50 - dot, s * 0.30 - dot, s * 0.50 + dot, s * 0.30 + dot), fill=_hex(c) + (255,))
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


@lru_cache(maxsize=16)
def social_icon(name: str, size: int = 32) -> ctk.CTkImage:
    path = SOCIAL_DIR / f"{name}.png"
    img = Image.open(path).convert("RGBA")
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
