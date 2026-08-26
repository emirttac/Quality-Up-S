from __future__ import annotations

import os
import platform
import shutil
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageTk

from quality_ups.config import ICON_DIR


def apply_app_icon(window: Any) -> None:
    """Set the window / taskbar / dock icon from the bundled platform assets."""
    system = platform.system()
    platform_png = ICON_DIR / ("macos.png" if system == "Darwin" else "windows.png")
    small_png = ICON_DIR / "64.png"
    photos: list[Any] = []

    for source in (platform_png, small_png):
        if not source.exists():
            continue
        try:
            image = Image.open(source).convert("RGBA")
            if max(image.size) > 256:
                image.thumbnail((256, 256), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            photos.append(photo)
        except Exception:
            continue

    if photos:
        try:
            window.iconphoto(True, *photos)
        except Exception:
            try:
                window.iconphoto(True, photos[0])
            except Exception:
                pass

    if system == "Darwin":
        _macos_dock_icon(platform_png if platform_png.exists() else small_png)
    elif system == "Windows":
        _apply_windows_ico(window)

    window._app_icon_photos = photos


def _apply_windows_ico(window: Any) -> None:
    ico = ICON_DIR / "app.ico"
    if not ico.exists():
        return
    path = _windows_safe_ico(ico)
    try:
        window.iconbitmap(default=str(path))
    except Exception:
        try:
            window.iconbitmap(str(path))
        except Exception:
            pass


def _windows_safe_ico(source: Path) -> Path:
    # Tcl iconbitmap breaks on paths that contain an apostrophe (this project folder does).
    dest = Path(os.environ.get("TEMP") or tempfile.gettempdir()) / "quality-ups-app.ico"
    try:
        shutil.copyfile(source, dest)
        return dest
    except Exception:
        return source


def _macos_dock_icon(path: Path) -> None:
    if not path.exists():
        return
    try:
        from AppKit import NSApplication, NSImage
    except Exception:
        return
    try:
        image = NSImage.alloc().initByReferencingFile_(str(path))
        if image is None:
            return
        NSApplication.sharedApplication().setApplicationIconImage_(image)
    except Exception:
        pass
