from __future__ import annotations

import sys
from pathlib import Path


def _resolve_app_dir() -> Path:
    """Project root in source; PyInstaller bundle root when frozen."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


APP_NAME = "Quality Up'S"
APP_VERSION = "1.0"
APP_PUBLISHER = "Emir Tuğra Ataç"
APP_PUBLISHER_URL = "https://github.com/emirttac"
APP_DIR = _resolve_app_dir()
MODELS_DIR = APP_DIR / "assets" / "models"
ICON_DIR = APP_DIR / "assets" / "icon"
GITHUB_REPO = "emirttac/Quality-Up-S"
GITHUB_URL = f"https://github.com/{GITHUB_REPO}"

SOCIAL_LINKS = (
    ("youtube", "YouTube", "https://www.youtube.com/@BiAltTab"),
    ("instagram", "Instagram", "https://www.instagram.com/emirttac/"),
    ("github", "GitHub", "https://github.com/emirttac"),
    ("linkedin", "LinkedIn", "https://www.linkedin.com/in/emir-tu%C4%9Fra-ata%C3%A7-88b591394/"),
)

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}

# Tile size keeps large photos stable in OpenCV DNN / ONNX SuperRes.
DEFAULT_TILE = 512
DEFAULT_OVERLAP = 16
TILE_OPTIONS = (256, 512, 1024)
OVERLAP_OPTIONS = (8, 16, 32)

SCALE_OPTIONS = (2, 4)

# Built-in OpenCV FSRCNN weights (always required).
MODEL_FILES = {
    2: "FSRCNN_x2.pb",
    4: "FSRCNN_x4.pb",
}

# Optional Real-ESRGAN ONNX weights (high quality path).
REALESRGAN_FILES = {
    2: "realesrgan-x2.onnx",
    4: "realesrgan-x4.onnx",
}

MODEL_IDS = ("fsrcnn", "realesrgan")
DEFAULT_MODEL_ID = "fsrcnn"

OUTPUT_FORMATS = ("png", "jpeg", "webp")
DEFAULT_OUTPUT_FORMAT = "png"
DEFAULT_OUTPUT_QUALITY = 95  # JPEG / WebP quality 1–100

THEME_OPTIONS = ("system", "light", "dark")
DEFAULT_THEME = "system"

WINDOW_MIN_WIDTH = 760
WINDOW_MIN_HEIGHT = 580
WINDOW_DEFAULT_WIDTH = 900
WINDOW_DEFAULT_HEIGHT = 700
