from __future__ import annotations

import json
import os
import platform
import re
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ComputeDevice:
    id: str
    name: str
    kind: str  # auto | cpu | apple | discrete | integrated

    def label_key(self) -> str:
        if self.kind == "auto":
            return "gpu_auto"
        if self.kind == "cpu":
            return "gpu_cpu"
        if self.kind == "apple":
            return "gpu_apple"
        if self.kind == "discrete":
            return "gpu_discrete"
        if self.kind == "integrated":
            return "gpu_integrated"
        return "gpu_auto"


def list_compute_devices() -> list[ComputeDevice]:
    devices = [ComputeDevice(id="auto", name="Automatic", kind="auto")]
    devices.extend(_detect_gpus())
    devices.append(ComputeDevice(id="cpu", name="CPU", kind="cpu"))
    # Keep unique ids while preserving order.
    seen: set[str] = set()
    unique: list[ComputeDevice] = []
    for device in devices:
        if device.id in seen:
            continue
        seen.add(device.id)
        unique.append(device)
    return unique


def resolve_device(gpu_id: str) -> ComputeDevice:
    devices = list_compute_devices()
    for device in devices:
        if device.id == gpu_id:
            if device.kind == "auto":
                return _best_device(devices)
            return device
    return _best_device(devices)


def apply_compute_device(sr, device: ComputeDevice) -> None:
    """Configure an OpenCV DNN SuperRes impl for the chosen device."""
    import cv2

    # OpenCV OpenCL is deprecated/broken on modern macOS and commonly deadlocks
    # when the Tk event loop is already running (engine warm-up hangs on
    # "Hazırlanıyor…"). Prefer CPU for FSRCNN there; Real-ESRGAN still uses
    # ONNX CoreML separately.
    force_cpu = device.kind == "cpu" or platform.system() == "Darwin"
    if force_cpu:
        try:
            cv2.ocl.setUseOpenCL(False)
        except Exception:
            pass
        sr.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        sr.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        return

    index = _gpu_index(device.id)
    if index is not None:
        os.environ["OPENCV_OPENCL_DEVICE"] = f":GPU:{index}"
    try:
        cv2.ocl.setUseOpenCL(True)
    except Exception:
        pass
    sr.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    try:
        sr.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)
    except Exception:
        sr.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)



def describe_accelerators() -> list[str]:
    """Human-readable list of available acceleration backends."""
    names: list[str] = ["OpenCV OpenCL/CPU"]
    try:
        from quality_ups.core.backends.realesrgan import onnx_available, preferred_onnx_providers

        if onnx_available():
            names.append("ONNX Runtime (" + ", ".join(preferred_onnx_providers()) + ")")
    except Exception:
        pass
    try:
        import torch

        if torch.cuda.is_available():
            names.append("PyTorch CUDA")
        elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            names.append("PyTorch MPS (Metal)")
        else:
            names.append("PyTorch CPU")
    except Exception:
        pass
    return names


def _best_device(devices: list[ComputeDevice]) -> ComputeDevice:
    for kind in ("discrete", "apple", "integrated"):
        for device in devices:
            if device.kind == kind:
                return device
    for device in devices:
        if device.kind == "cpu":
            return device
    return devices[0]


def _gpu_index(device_id: str) -> int | None:
    if not device_id.startswith("gpu:"):
        return None
    try:
        return int(device_id.split(":", 1)[1])
    except ValueError:
        return None


def _detect_gpus() -> list[ComputeDevice]:
    system = platform.system()
    if system == "Darwin":
        return _macos_gpus()
    if system == "Windows":
        return _windows_gpus()
    if system == "Linux":
        return _linux_gpus()
    return []


def _macos_gpus() -> list[ComputeDevice]:
    names: list[str] = []
    try:
        raw = subprocess.run(
            ["system_profiler", "SPDisplaysDataType", "-json"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
        payload = json.loads(raw)
        for item in payload.get("SPDisplaysDataType", []):
            name = item.get("sppci_model") or item.get("_name")
            if name:
                names.append(str(name))
    except Exception:
        if platform.machine().lower() in {"arm64", "aarch64"}:
            names = ["Apple GPU"]
    return [_classify_gpu(index, name) for index, name in enumerate(names)]


def _windows_gpus() -> list[ComputeDevice]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        raw = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=creationflags,
        ).stdout
    except Exception:
        return []
    names = [line.strip() for line in raw.splitlines() if line.strip()]
    return [_classify_gpu(index, name) for index, name in enumerate(names)]


def _linux_gpus() -> list[ComputeDevice]:
    try:
        raw = subprocess.run(
            ["lspci"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
    except Exception:
        return []
    names: list[str] = []
    for line in raw.splitlines():
        if not re.search(r"VGA|3D|Display", line, re.I):
            continue
        name = line.split(":", 2)[-1].strip() if ":" in line else line.strip()
        names.append(name)
    return [_classify_gpu(index, name) for index, name in enumerate(names)]


def _classify_gpu(index: int, name: str) -> ComputeDevice:
    lower = name.lower()
    if "apple" in lower:
        kind = "apple"
    elif any(token in lower for token in ("nvidia", "geforce", "rtx", "radeon", "amd", "arc")):
        kind = "discrete"
    elif any(token in lower for token in ("intel", "iris", "uhd", "hd graphics", "vega")):
        kind = "integrated"
    else:
        kind = "discrete" if index == 0 else "integrated"
    return ComputeDevice(id=f"gpu:{index}", name=name, kind=kind)
