from __future__ import annotations

from cv2 import dnn_superres

from quality_ups.core.gpu import ComputeDevice, apply_compute_device
from quality_ups.core.models import model_path_for_scale


class FsrcnnBackend:
    """OpenCV DNN SuperRes FSRCNN — fast, bundled weights."""

    id = "fsrcnn"

    def __init__(self) -> None:
        self._cache: dict[int, object] = {}
        self._device: ComputeDevice | None = None

    def set_device(self, device: ComputeDevice) -> None:
        self._device = device
        for sr in self._cache.values():
            apply_compute_device(sr, device)

    def preload(self, scale: int) -> None:
        self._ensure(scale)

    def _ensure(self, scale: int):
        if scale in self._cache:
            return self._cache[scale]
        path = model_path_for_scale(scale, "fsrcnn")
        sr = dnn_superres.DnnSuperResImpl_create()
        sr.readModel(str(path))
        sr.setModel("fsrcnn", scale)
        if self._device is not None:
            apply_compute_device(sr, self._device)
        self._cache[scale] = sr
        return sr

    def upsample(self, patch_bgr, scale: int):
        sr = self._ensure(scale)
        return sr.upsample(patch_bgr)
