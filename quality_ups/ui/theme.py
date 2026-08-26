from __future__ import annotations

import platform
from typing import Literal

import customtkinter as ctk

_SYSTEM = platform.system()
if _SYSTEM == "Windows":
    FONT = "Segoe UI"
    FONT_DISPLAY = "Segoe UI"
elif _SYSTEM == "Darwin":
    FONT = "SF Pro Text"
    FONT_DISPLAY = "SF Pro Display"
else:
    FONT = "Cantarell"
    FONT_DISPLAY = "Cantarell"

ThemeMode = Literal["system", "light", "dark"]

_LIGHT = {
    "window": "#F5F5F7",
    "surface": "#FFFFFF",
    "surface_secondary": "#EBEBED",
    "fill": "#F2F2F7",
    "separator": "#D8D8DC",
    "label": "#1D1D1F",
    "secondary": "#6E6E73",
    "tertiary": "#8E8E93",
    "blue": "#007AFF",
    "blue_pressed": "#0066D6",
    "blue_fill": "#E8F1FF",
    "green": "#248A3D",
    "orange": "#C93400",
    "red": "#D70015",
    "progress_track": "#E5E5EA",
    "drop_border": "#C7C7CC",
    "drop_active": "#E8F1FF",
    "checker_a": "#E8E8ED",
    "checker_b": "#FFFFFF",
}

_DARK = {
    "window": "#1C1C1E",
    "surface": "#2C2C2E",
    "surface_secondary": "#3A3A3C",
    "fill": "#3A3A3C",
    "separator": "#48484A",
    "label": "#F5F5F7",
    "secondary": "#A1A1A6",
    "tertiary": "#8E8E93",
    "blue": "#0A84FF",
    "blue_pressed": "#409CFF",
    "blue_fill": "#1A2A40",
    "green": "#30D158",
    "orange": "#FF9F0A",
    "red": "#FF453A",
    "progress_track": "#3A3A3C",
    "drop_border": "#48484A",
    "drop_active": "#1A2A40",
    "checker_a": "#3A3A3C",
    "checker_b": "#2C2C2E",
}

# Mutable palette used across the UI — always call apply_theme() at startup.
COLORS: dict[str, str] = dict(_LIGHT)
_CURRENT_MODE: ThemeMode = "light"


def resolved_appearance(mode: str) -> Literal["light", "dark"]:
    preferred = (mode or "system").lower()
    if preferred == "dark":
        return "dark"
    if preferred == "light":
        return "light"
    try:
        detected = ctk.get_appearance_mode()
        return "dark" if str(detected).lower() == "dark" else "light"
    except Exception:
        return "light"


def apply_theme(mode: str) -> Literal["light", "dark"]:
    """Apply CustomTkinter appearance + sync COLORS dict. Returns resolved mode."""
    global _CURRENT_MODE
    preferred = (mode or "system").lower()
    if preferred not in {"system", "light", "dark"}:
        preferred = "system"
    ctk.set_appearance_mode(preferred)
    resolved = resolved_appearance(preferred)
    COLORS.clear()
    COLORS.update(_DARK if resolved == "dark" else _LIGHT)
    _CURRENT_MODE = resolved
    return resolved


def current_theme() -> Literal["light", "dark"]:
    return _CURRENT_MODE
