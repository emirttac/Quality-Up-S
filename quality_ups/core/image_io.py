from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from quality_ups.config import DEFAULT_OUTPUT_FORMAT, DEFAULT_OUTPUT_QUALITY
from quality_ups.core.heif_support import ensure_heif_support

ensure_heif_support()


@dataclass(frozen=True)
class LoadedImage:
    """BGR(+A) contiguous array ready for the upscale pipeline."""

    bgr: np.ndarray
    alpha: np.ndarray | None
    mode: str  # RGB | RGBA | L …


def load_image(path: Path) -> LoadedImage:
    """Load an image while preserving an alpha channel when present."""
    pil = Image.open(path)
    if pil.mode in {"RGBA", "LA"} or (pil.mode == "P" and "transparency" in pil.info):
        rgba = pil.convert("RGBA")
        arr = np.array(rgba)
        rgb = arr[:, :, :3]
        alpha = arr[:, :, 3]
        bgr = np.ascontiguousarray(rgb[:, :, ::-1])
        return LoadedImage(bgr=bgr, alpha=np.ascontiguousarray(alpha), mode="RGBA")
    rgb = pil.convert("RGB")
    arr = np.array(rgb)
    bgr = np.ascontiguousarray(arr[:, :, ::-1])
    return LoadedImage(bgr=bgr, alpha=None, mode="RGB")


def merge_bgr_alpha(bgr: np.ndarray, alpha: np.ndarray | None) -> np.ndarray:
    """Return BGR or BGRA uint8 array."""
    if alpha is None:
        return bgr
    if alpha.shape[:2] != bgr.shape[:2]:
        alpha = cv2.resize(alpha, (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_NEAREST)
    return np.dstack([bgr, alpha])


def resize_alpha(alpha: np.ndarray, scale: int) -> np.ndarray:
    """Nearest-neighbor alpha upscale — keeps hard matte edges crisp."""
    h, w = alpha.shape[:2]
    return cv2.resize(alpha, (w * scale, h * scale), interpolation=cv2.INTER_NEAREST)


def save_image(
    path: Path,
    bgr_or_bgra: np.ndarray,
    *,
    fmt: str = DEFAULT_OUTPUT_FORMAT,
    quality: int = DEFAULT_OUTPUT_QUALITY,
) -> Path:
    """Write output in PNG / JPEG / WebP. Alpha is dropped for JPEG."""
    fmt = (fmt or "png").lower()
    if fmt == "jpg":
        fmt = "jpeg"
    quality = max(1, min(100, int(quality)))

    has_alpha = bgr_or_bgra.ndim == 3 and bgr_or_bgra.shape[2] == 4
    stem_path = path.with_suffix(_suffix_for(fmt))

    if fmt == "png":
        ok = cv2.imwrite(str(stem_path), bgr_or_bgra)
        if not ok:
            raise OSError(f"Failed to write {stem_path}")
        return stem_path

    if fmt == "webp":
        params = [int(cv2.IMWRITE_WEBP_QUALITY), quality]
        ok = cv2.imwrite(str(stem_path), bgr_or_bgra, params)
        if not ok:
            # Pillow fallback for environments without WebP encode in OpenCV.
            _pillow_save(stem_path, bgr_or_bgra, "WEBP", quality=quality, has_alpha=has_alpha)
        return stem_path

    # JPEG — flatten onto white if alpha exists.
    bgr = bgr_or_bgra[:, :, :3] if has_alpha else bgr_or_bgra
    if has_alpha:
        alpha = bgr_or_bgra[:, :, 3].astype(np.float32) / 255.0
        alpha3 = alpha[:, :, None]
        white = np.full_like(bgr, 255, dtype=np.float32)
        bgr = (bgr.astype(np.float32) * alpha3 + white * (1.0 - alpha3)).astype(np.uint8)
    params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    ok = cv2.imwrite(str(stem_path), bgr, params)
    if not ok:
        raise OSError(f"Failed to write {stem_path}")
    return stem_path


def _suffix_for(fmt: str) -> str:
    if fmt == "jpeg":
        return ".jpg"
    if fmt == "webp":
        return ".webp"
    return ".png"


def _pillow_save(
    path: Path,
    bgr_or_bgra: np.ndarray,
    pil_format: str,
    *,
    quality: int,
    has_alpha: bool,
) -> None:
    if has_alpha:
        rgba = cv2.cvtColor(bgr_or_bgra, cv2.COLOR_BGRA2RGBA)
        Image.fromarray(rgba, mode="RGBA").save(path, format=pil_format, quality=quality, method=6)
    else:
        rgb = cv2.cvtColor(bgr_or_bgra, cv2.COLOR_BGR2RGB)
        Image.fromarray(rgb, mode="RGB").save(path, format=pil_format, quality=quality, method=6)
