from __future__ import annotations

import json
import locale
import platform
from dataclasses import asdict, dataclass
from pathlib import Path

from quality_ups.config import (
    DEFAULT_MODEL_ID,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_OUTPUT_QUALITY,
    DEFAULT_OVERLAP,
    DEFAULT_THEME,
    DEFAULT_TILE,
    MODEL_IDS,
    OUTPUT_FORMATS,
    OVERLAP_OPTIONS,
    THEME_OPTIONS,
    TILE_OPTIONS,
)
from quality_ups.i18n.catalog import LANGUAGES


def _prefs_path() -> Path:
    home = Path.home()
    system = platform.system()
    if system == "Darwin":
        root = home / "Library" / "Application Support" / "Quality Up'S"
    elif system == "Windows":
        root = home / "AppData" / "Roaming" / "Quality Up'S"
    else:
        root = home / ".config" / "quality-ups"
    return root / "prefs.json"


def detect_language() -> str:
    try:
        raw = locale.getlocale()[0] or locale.getdefaultlocale()[0] or ""
    except Exception:
        raw = ""
    code = raw.replace("-", "_").split("_")[0].lower()
    if code.startswith("zh"):
        return "zh"
    return code if code in LANGUAGES else "tr"


@dataclass
class Prefs:
    language: str = "tr"
    gpu_id: str = "auto"
    theme: str = DEFAULT_THEME
    model_id: str = DEFAULT_MODEL_ID
    tile: int = DEFAULT_TILE
    overlap: int = DEFAULT_OVERLAP
    output_format: str = DEFAULT_OUTPUT_FORMAT
    output_quality: int = DEFAULT_OUTPUT_QUALITY

    def normalized(self) -> Prefs:
        language = self.language if self.language in LANGUAGES else detect_language()
        gpu_id = self.gpu_id or "auto"
        theme = self.theme if self.theme in THEME_OPTIONS else DEFAULT_THEME
        model_id = self.model_id if self.model_id in MODEL_IDS else DEFAULT_MODEL_ID
        tile = self.tile if self.tile in TILE_OPTIONS else DEFAULT_TILE
        overlap = self.overlap if self.overlap in OVERLAP_OPTIONS else DEFAULT_OVERLAP
        output_format = (
            self.output_format.lower()
            if self.output_format.lower() in OUTPUT_FORMATS
            else DEFAULT_OUTPUT_FORMAT
        )
        quality = max(1, min(100, int(self.output_quality or DEFAULT_OUTPUT_QUALITY)))
        return Prefs(
            language=language,
            gpu_id=gpu_id,
            theme=theme,
            model_id=model_id,
            tile=tile,
            overlap=overlap,
            output_format=output_format,
            output_quality=quality,
        )


def load_prefs() -> Prefs:
    path = _prefs_path()
    if not path.exists():
        return Prefs(language=detect_language()).normalized()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Prefs(
            language=str(data.get("language") or detect_language()),
            gpu_id=str(data.get("gpu_id") or "auto"),
            theme=str(data.get("theme") or DEFAULT_THEME),
            model_id=str(data.get("model_id") or DEFAULT_MODEL_ID),
            tile=int(data.get("tile") or DEFAULT_TILE),
            overlap=int(data.get("overlap") or DEFAULT_OVERLAP),
            output_format=str(data.get("output_format") or DEFAULT_OUTPUT_FORMAT),
            output_quality=int(data.get("output_quality") or DEFAULT_OUTPUT_QUALITY),
        ).normalized()
    except Exception:
        return Prefs(language=detect_language()).normalized()


def save_prefs(prefs: Prefs) -> None:
    path = _prefs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(prefs.normalized()), indent=2), encoding="utf-8")
