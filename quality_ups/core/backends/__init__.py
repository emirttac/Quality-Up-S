from __future__ import annotations

from quality_ups.core.backends.fsrcnn import FsrcnnBackend
from quality_ups.core.backends.realesrgan import RealesrganBackend, onnx_available
from quality_ups.core.models import ModelError, get_model_info


def create_backend(model_id: str):
    info = get_model_info(model_id)
    if info.backend == "opencv":
        return FsrcnnBackend()
    if info.backend == "onnx":
        if not onnx_available():
            raise ModelError(
                "Real-ESRGAN requires the optional onnxruntime package. "
                "Install with: pip install onnxruntime"
            )
        return RealesrganBackend()
    raise ModelError(f"Unsupported backend: {info.backend}")
