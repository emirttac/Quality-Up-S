from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from quality_ups.config import MODEL_FILES, MODELS_DIR, REALESRGAN_FILES
from quality_ups.core.gpu import ComputeDevice


class UpscaleBackend(Protocol):
    id: str

    def set_device(self, device: ComputeDevice) -> None: ...

    def preload(self, scale: int) -> None: ...

    def upsample(self, patch_bgr: np.ndarray, scale: int) -> np.ndarray: ...


@dataclass(frozen=True)
class ModelInfo:
    id: str
    label_key: str
    backend: str  # opencv | onnx
    files: dict[int, str]
    required: bool = False

    def path_for(self, scale: int) -> Path:
        name = self.files.get(scale)
        if not name:
            raise ModelError(f"Unsupported scale for {self.id}: {scale}x")
        return MODELS_DIR / name

    def available_scales(self) -> list[int]:
        return [s for s, name in self.files.items() if (MODELS_DIR / name).exists()]

    def is_available(self) -> bool:
        return bool(self.available_scales())


class ModelError(RuntimeError):
    pass


MODEL_CATALOG: dict[str, ModelInfo] = {
    "fsrcnn": ModelInfo(
        id="fsrcnn",
        label_key="model_fsrcnn",
        backend="opencv",
        files=MODEL_FILES,
        required=True,
    ),
    "realesrgan": ModelInfo(
        id="realesrgan",
        label_key="model_realesrgan",
        backend="onnx",
        files=REALESRGAN_FILES,
        required=False,
    ),
}


def get_model_info(model_id: str) -> ModelInfo:
    info = MODEL_CATALOG.get(model_id)
    if info is None:
        raise ModelError(f"Unknown model: {model_id}")
    return info


def list_models() -> list[ModelInfo]:
    return list(MODEL_CATALOG.values())


def model_path_for_scale(scale: int, model_id: str = "fsrcnn") -> Path:
    info = get_model_info(model_id)
    path = info.path_for(scale)
    if not path.exists():
        raise ModelError(f"Model file missing: {path.name}")
    return path


def ensure_models(model_id: str = "fsrcnn") -> None:
    info = get_model_info(model_id)
    missing = [name for name in info.files.values() if not (MODELS_DIR / name).exists()]
    if missing:
        if info.required:
            raise ModelError(
                "Missing model files: "
                + ", ".join(missing)
                + f". Place them in {MODELS_DIR}"
            )
        raise ModelError(
            f"{info.id} weights missing: "
            + ", ".join(missing)
            + f". Place ONNX files in {MODELS_DIR} or switch to FSRCNN."
        )


def ensure_required_models() -> None:
    for info in MODEL_CATALOG.values():
        if info.required:
            ensure_models(info.id)
