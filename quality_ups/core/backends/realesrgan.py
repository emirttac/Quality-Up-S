from __future__ import annotations

import platform
from typing import Any

import cv2
import numpy as np

from quality_ups.core.gpu import ComputeDevice
from quality_ups.core.models import model_path_for_scale


def onnx_available() -> bool:
    try:
        import onnxruntime  # noqa: F401

        return True
    except ImportError:
        return False


def preferred_onnx_providers(device: ComputeDevice | None = None) -> list[str]:
    """Pick ONNX Runtime EP order for the active compute preference."""
    try:
        import onnxruntime as ort
    except ImportError:
        return ["CPUExecutionProvider"]

    available = set(ort.get_available_providers())
    ordered: list[str] = []

    prefer_cpu = device is not None and device.kind == "cpu"
    system = platform.system()

    if not prefer_cpu:
        # Windows DirectML (AMD/Intel/NVIDIA via DX12)
        if "DmlExecutionProvider" in available and system == "Windows":
            ordered.append("DmlExecutionProvider")
        # NVIDIA CUDA
        if "CUDAExecutionProvider" in available:
            ordered.append("CUDAExecutionProvider")
        # Apple CoreML / Metal path
        if "CoreMLExecutionProvider" in available and system == "Darwin":
            ordered.append("CoreMLExecutionProvider")
        # Generic OpenVINO / ROCm when present
        for name in ("ROCMExecutionProvider", "OpenVINOExecutionProvider"):
            if name in available:
                ordered.append(name)

    if "CPUExecutionProvider" in available:
        ordered.append("CPUExecutionProvider")
    return ordered or ["CPUExecutionProvider"]


class RealesrganBackend:
    """Real-ESRGAN via ONNX Runtime (optional high-quality path).

    Expects `realesrgan-x2.onnx` / `realesrgan-x4.onnx` under assets/models.
    Input/output tensors are NCHW RGB float32 in [0, 1].
    """

    id = "realesrgan"

    def __init__(self) -> None:
        self._sessions: dict[int, Any] = {}
        self._device: ComputeDevice | None = None
        self._input_names: dict[int, str] = {}
        self._output_names: dict[int, str] = {}

    def set_device(self, device: ComputeDevice) -> None:
        # Provider list is fixed at session creation — rebuild on device change.
        if self._device != device:
            self._sessions.clear()
            self._input_names.clear()
            self._output_names.clear()
        self._device = device

    def preload(self, scale: int) -> None:
        self._ensure(scale)

    def _ensure(self, scale: int):
        if scale in self._sessions:
            return self._sessions[scale]
        import onnxruntime as ort

        path = model_path_for_scale(scale, "realesrgan")
        providers = preferred_onnx_providers(self._device)
        session = ort.InferenceSession(str(path), providers=providers)
        inputs = session.get_inputs()
        outputs = session.get_outputs()
        self._input_names[scale] = inputs[0].name
        self._output_names[scale] = outputs[0].name
        self._sessions[scale] = session
        return session

    def upsample(self, patch_bgr: np.ndarray, scale: int) -> np.ndarray:
        session = self._ensure(scale)
        rgb = cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        # NCHW
        tensor = np.transpose(rgb, (2, 0, 1))[None, ...]
        out = session.run(
            [self._output_names[scale]],
            {self._input_names[scale]: tensor},
        )[0]
        # Handle NCHW or NHWC outputs
        if out.ndim == 4 and out.shape[1] in (3, 4):
            out_rgb = np.transpose(out[0], (1, 2, 0))
        else:
            out_rgb = out[0]
        out_rgb = np.clip(out_rgb[..., :3] * 255.0, 0, 255).astype(np.uint8)
        return cv2.cvtColor(out_rgb, cv2.COLOR_RGB2BGR)
