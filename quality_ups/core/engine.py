from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from quality_ups.config import (
    DEFAULT_MODEL_ID,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_OUTPUT_QUALITY,
    DEFAULT_OVERLAP,
    DEFAULT_TILE,
)
from quality_ups.core.backends import create_backend
from quality_ups.core.gpu import ComputeDevice, resolve_device
from quality_ups.core.image_io import load_image, merge_bgr_alpha, resize_alpha, save_image
from quality_ups.core.models import ensure_models, get_model_info


TileProgressCallback = Callable[[float], None]
CancelCheck = Callable[[], bool]


@dataclass(frozen=True)
class UpscaleResult:
    source: Path
    output: Path
    scale: int
    width: int
    height: int
    seconds: float
    model_id: str = DEFAULT_MODEL_ID


class SuperResolutionEngine:
    """Tiled super-resolution with pluggable backends and RGBA preservation."""

    def __init__(
        self,
        tile: int = DEFAULT_TILE,
        overlap: int = DEFAULT_OVERLAP,
        model_id: str = DEFAULT_MODEL_ID,
    ) -> None:
        self.tile = tile
        self.overlap = overlap
        self.model_id = model_id
        self._device: ComputeDevice = resolve_device("auto")
        self._backend = create_backend(model_id)
        self._backend.set_device(self._device)

    def configure(
        self,
        *,
        tile: int | None = None,
        overlap: int | None = None,
        model_id: str | None = None,
    ) -> None:
        if tile is not None:
            self.tile = max(64, int(tile))
        if overlap is not None:
            self.overlap = max(0, int(overlap))
        if model_id is not None and model_id != self.model_id:
            self.model_id = model_id
            self._backend = create_backend(model_id)
            self._backend.set_device(self._device)

    def set_device(self, gpu_id: str) -> None:
        self._device = resolve_device(gpu_id)
        self._backend.set_device(self._device)

    def preload(self, scale: int, model_id: str | None = None) -> None:
        mid = model_id or self.model_id
        if mid != self.model_id:
            self.configure(model_id=mid)
        ensure_models(self.model_id)
        self._backend.preload(scale)

    def upscale_array(
        self,
        arr_bgr: np.ndarray,
        scale: int,
        *,
        on_tile_progress: TileProgressCallback | None = None,
        should_cancel: CancelCheck | None = None,
    ) -> np.ndarray:
        ensure_models(self.model_id)
        get_model_info(self.model_id)  # validate id
        return self._upscale_tiled(
            arr_bgr,
            scale,
            on_tile_progress=on_tile_progress,
            should_cancel=should_cancel,
        )

    def _upscale_tiled(
        self,
        arr: np.ndarray,
        scale: int,
        *,
        on_tile_progress: TileProgressCallback | None = None,
        should_cancel: CancelCheck | None = None,
    ) -> np.ndarray:
        h, w = arr.shape[:2]
        out = np.empty((h * scale, w * scale, 3), dtype=np.uint8)
        tile = self.tile
        overlap = self.overlap

        tiles_y = max(1, (h + tile - 1) // tile)
        tiles_x = max(1, (w + tile - 1) // tile)
        total_tiles = tiles_y * tiles_x
        done_tiles = 0

        y = 0
        while y < h:
            x = 0
            y0 = max(0, y - overlap)
            y1 = min(h, y + tile + overlap)
            while x < w:
                if should_cancel and should_cancel():
                    raise RuntimeError("Cancelled")
                x0 = max(0, x - overlap)
                x1 = min(w, x + tile + overlap)
                patch = np.ascontiguousarray(arr[y0:y1, x0:x1])
                up = self._backend.upsample(patch, scale)
                crop_top = (y - y0) * scale
                crop_left = (x - x0) * scale
                out_h = min(tile, h - y) * scale
                out_w = min(tile, w - x) * scale
                out_y0 = y * scale
                out_x0 = x * scale
                # Guard against backends that return slightly different sizes.
                src = up[crop_top : crop_top + out_h, crop_left : crop_left + out_w]
                if src.shape[0] != out_h or src.shape[1] != out_w:
                    import cv2

                    src = cv2.resize(src, (out_w, out_h), interpolation=cv2.INTER_CUBIC)
                out[out_y0 : out_y0 + out_h, out_x0 : out_x0 + out_w] = src
                done_tiles += 1
                if on_tile_progress:
                    on_tile_progress(done_tiles / total_tiles)
                x += tile
            y += tile
        return out

    def process_file(
        self,
        source: Path,
        output_dir: Path,
        scale: int,
        *,
        on_tile_progress: TileProgressCallback | None = None,
        should_cancel: CancelCheck | None = None,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
        output_quality: int = DEFAULT_OUTPUT_QUALITY,
    ) -> UpscaleResult:
        import time

        source = Path(source)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        started = time.perf_counter()
        loaded = load_image(source)
        result_bgr = self.upscale_array(
            loaded.bgr,
            scale,
            on_tile_progress=on_tile_progress,
            should_cancel=should_cancel,
        )
        if should_cancel and should_cancel():
            raise RuntimeError("Cancelled")

        alpha_out = resize_alpha(loaded.alpha, scale) if loaded.alpha is not None else None
        combined = merge_bgr_alpha(result_bgr, alpha_out)

        tentative = output_dir / f"{source.stem}_{scale}x.png"
        output = save_image(
            tentative,
            combined,
            fmt=output_format,
            quality=output_quality,
        )
        seconds = time.perf_counter() - started
        height, width = result_bgr.shape[:2]
        return UpscaleResult(
            source=source,
            output=output,
            scale=scale,
            width=width,
            height=height,
            seconds=seconds,
            model_id=self.model_id,
        )
