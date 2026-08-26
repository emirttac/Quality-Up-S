from quality_ups.core.capability import CapabilityReport, HardwareProfile, assess_system
from quality_ups.core.diagnostics import EngineStatus, Readiness

__all__ = [
    "CapabilityReport",
    "HardwareProfile",
    "assess_system",
    "EngineStatus",
    "Readiness",
    "SuperResolutionEngine",
    "UpscaleResult",
    "ModelError",
    "ensure_models",
    "ensure_required_models",
    "model_path_for_scale",
    "list_models",
    "get_model_info",
    "Processor",
    "ProgressUpdate",
    "QueueJob",
    "EngineRuntime",
]


def __getattr__(name: str):
    if name in {"SuperResolutionEngine", "UpscaleResult"}:
        from quality_ups.core.engine import SuperResolutionEngine, UpscaleResult

        return SuperResolutionEngine if name == "SuperResolutionEngine" else UpscaleResult
    if name in {"ModelError", "ensure_models", "model_path_for_scale", "ensure_required_models", "list_models", "get_model_info"}:
        from quality_ups.core import models as _models

        return getattr(_models, name)
    if name in {"Processor", "ProgressUpdate", "QueueJob"}:
        from quality_ups.core.processor import Processor, ProgressUpdate, QueueJob

        return {"Processor": Processor, "ProgressUpdate": ProgressUpdate, "QueueJob": QueueJob}[name]
    if name == "EngineRuntime":
        from quality_ups.core.runtime import EngineRuntime

        return EngineRuntime
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
