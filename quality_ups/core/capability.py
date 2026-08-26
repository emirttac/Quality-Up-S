from __future__ import annotations

import os
import platform
import re
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass

# Keep the loading screen on screen long enough to read.
_MIN_PROBE_SECONDS = 1.4

# Internal comfort threshold for tiled FSRCNN on CPU.
_PASS_SCORE = 62

ProgressCallback = Callable[[str, float], None]


@dataclass(frozen=True)
class HardwareProfile:
    os_name: str
    os_version: str
    os_supported: bool
    cpu_name: str
    cpu_cores: int
    cpu_physical: int
    gpu_name: str
    gpu_capable: bool
    gpu_dedicated: bool
    apple_silicon: bool
    ram_gb: float
    free_ram_gb: float


@dataclass(frozen=True)
class CapabilityReport:
    sufficient: bool
    score: int
    profile: HardwareProfile
    message_key: str
    button_key: str


def memory_gb() -> tuple[float, float]:
    """Return (total_gb, available_gb)."""
    try:
        import psutil

        vm = psutil.virtual_memory()
        return vm.total / (1024**3), vm.available / (1024**3)
    except Exception:
        total = 0.0
        try:
            pagesize = os.sysconf("SC_PAGE_SIZE")
            total = (os.sysconf("SC_PHYS_PAGES") * pagesize) / (1024**3)
        except (ValueError, OSError, AttributeError):
            total = 8.0
        free = max(total * 0.35, 2.0)
        return total, free


def assess_system(on_progress: ProgressCallback | None = None) -> CapabilityReport:
    """Probe CPU, GPU, cores, memory, and OS, then score local-AI readiness."""

    def emit(message: str, fraction: float) -> None:
        if on_progress:
            on_progress(message, fraction)

    started = time.perf_counter()
    emit("gate_checking", 0.08)
    try:
        emit("gate_os", 0.18)
        system = platform.system()
        os_name, os_version, os_supported = _os_info(system)

        emit("gate_memory", 0.36)
        ram_total, ram_free = memory_gb()

        emit("gate_cpu", 0.54)
        logical, physical = _cpu_counts()
        apple_silicon = system == "Darwin" and platform.machine().lower() in {"arm64", "aarch64"}
        cpu_name = _cpu_name(system)

        emit("gate_gpu", 0.74)
        gpu_name, gpu_capable, gpu_dedicated = _gpu_info(system, apple_silicon, cpu_name)

        emit("gate_scoring", 0.9)
        profile = HardwareProfile(
            os_name=os_name,
            os_version=os_version,
            os_supported=os_supported,
            cpu_name=cpu_name,
            cpu_cores=logical,
            cpu_physical=physical,
            gpu_name=gpu_name,
            gpu_capable=gpu_capable,
            gpu_dedicated=gpu_dedicated,
            apple_silicon=apple_silicon,
            ram_gb=ram_total,
            free_ram_gb=ram_free,
        )
        score, sufficient = _score(profile)
    except Exception:
        ram_total, ram_free = memory_gb()
        cores = os.cpu_count() or 1
        profile = HardwareProfile(
            os_name=platform.system() or "Unknown",
            os_version=platform.release(),
            os_supported=False,
            cpu_name="Unknown CPU",
            cpu_cores=cores,
            cpu_physical=cores,
            gpu_name="Unknown GPU",
            gpu_capable=False,
            gpu_dedicated=False,
            apple_silicon=False,
            ram_gb=ram_total,
            free_ram_gb=ram_free,
        )
        score, sufficient = _score(profile)
    remaining = _MIN_PROBE_SECONDS - (time.perf_counter() - started)
    if remaining > 0:
        time.sleep(remaining)
    emit("gate_finishing", 1.0)
    return CapabilityReport(
        sufficient=sufficient,
        score=score,
        profile=profile,
        message_key="gate_ok" if sufficient else "gate_weak",
        button_key="gate_continue" if sufficient else "gate_continue_anyway",
    )


def _cpu_counts() -> tuple[int, int]:
    logical = os.cpu_count() or 1
    physical = logical
    try:
        import psutil

        phys = psutil.cpu_count(logical=False)
        if phys:
            physical = phys
    except Exception:
        pass
    return logical, physical


def _score(profile: HardwareProfile) -> tuple[int, bool]:
    score = 0

    cores = profile.cpu_cores
    if cores >= 8:
        score += 24
    elif cores >= 6:
        score += 20
    elif cores >= 4:
        score += 16
    elif cores >= 2:
        score += 8
    else:
        score += 2

    ram = profile.ram_gb
    if ram >= 16:
        score += 24
    elif ram >= 8:
        score += 18
    elif ram >= 4:
        score += 8
    else:
        score += 2

    free = profile.free_ram_gb
    if free >= 4:
        score += 12
    elif free >= 2:
        score += 6

    if profile.gpu_capable:
        if profile.apple_silicon or profile.gpu_dedicated:
            score += 24
        else:
            score += 14
    else:
        score += 4

    if profile.os_supported:
        score += 16
    else:
        score += 4

    score = min(100, score)
    sufficient = (
        score >= _PASS_SCORE
        and cores >= 4
        and ram >= 8
        and free >= 2.0
        and profile.os_supported
    )
    return score, sufficient


def _cpu_name(system: str) -> str:
    if system == "Darwin":
        return _sysctl("machdep.cpu.brand_string") or platform.processor() or "Unknown CPU"
    if system == "Linux":
        try:
            for line in open("/proc/cpuinfo", encoding="utf-8", errors="ignore"):
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
        except OSError:
            pass
        return platform.processor() or "Unknown CPU"
    if system == "Windows":
        name = _powershell("(Get-CimInstance Win32_Processor).Name")
        if name:
            return name.splitlines()[0].strip()
        return platform.processor() or "Unknown CPU"
    return platform.processor() or "Unknown CPU"


def _gpu_info(system: str, apple_silicon: bool, cpu_name: str) -> tuple[str, bool, bool]:
    if apple_silicon:
        chip = cpu_name.strip() or "Apple Silicon"
        if "GPU" not in chip:
            chip = f"{chip} GPU"
        return chip, True, True

    if system == "Darwin":
        return _macos_intel_gpu()
    if system == "Windows":
        return _windows_gpu()
    if system == "Linux":
        return _linux_gpu()
    return "Unknown GPU", False, False


def _macos_intel_gpu() -> tuple[str, bool, bool]:
    try:
        out = _run(["system_profiler", "SPDisplaysDataType"], timeout=10)
    except Exception:
        return "Unknown GPU", False, False
    names: list[str] = []
    dedicated = False
    current = ""
    for raw in out.splitlines():
        line = raw.strip()
        if line.startswith("Chipset Model:"):
            current = line.split(":", 1)[1].strip()
            if current:
                names.append(current)
        if "VRAM" in line or line.startswith("Total Number of Cores:"):
            dedicated = dedicated or bool(current)
        lower = current.lower()
        if any(token in lower for token in ("amd", "radeon", "nvidia", "geforce")):
            dedicated = True
    if not names:
        return "Unknown GPU", False, False
    integrated_only = all(
        any(token in n.lower() for token in ("intel", "iris", "uhd", "hd graphics"))
        for n in names
    )
    return ", ".join(names), True, dedicated and not integrated_only


def _windows_gpu() -> tuple[str, bool, bool]:
    out = _powershell(
        "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"
    )
    names = [line.strip() for line in (out or "").splitlines() if line.strip()]
    if not names:
        return "Unknown GPU", False, False
    joined = ", ".join(names)
    lower = joined.lower()
    dedicated = any(
        token in lower
        for token in ("nvidia", "geforce", "rtx", "radeon", "amd", "arc")
    )
    return joined, True, dedicated


def _linux_gpu() -> tuple[str, bool, bool]:
    try:
        out = _run(["lspci"], timeout=5)
    except Exception:
        return "Unknown GPU", False, False
    names: list[str] = []
    dedicated = False
    for line in out.splitlines():
        if not re.search(r"VGA|3D|Display", line, re.I):
            continue
        name = line.split(":", 2)[-1].strip() if ":" in line else line.strip()
        names.append(name)
        lower = name.lower()
        if any(token in lower for token in ("nvidia", "geforce", "radeon", "amd", "arc")):
            dedicated = True
    if not names:
        return "Unknown GPU", False, False
    return ", ".join(names), True, dedicated


def _os_info(system: str) -> tuple[str, str, bool]:
    if system == "Darwin":
        ver = platform.mac_ver()[0] or ""
        major = _major(ver)
        return "macOS", ver or "unknown", major >= 12
    if system == "Windows":
        ver = platform.win32_ver()[0] or platform.release()
        major = _major(ver) or (10 if ver.lower() in {"10", "11", "server"} else 0)
        if ver in {"10", "11"}:
            major = int(ver)
        pretty = ver if ver else platform.release()
        return "Windows", pretty, major >= 10
    if system == "Linux":
        dist = ""
        try:
            dist = " ".join(platform.freedesktop_os_release().get("PRETTY_NAME", "").split())
        except Exception:
            dist = platform.release()
        return "Linux", dist or platform.release(), True
    return system or "Unknown", platform.release(), True


def _major(version: str) -> int:
    try:
        return int(version.split(".")[0])
    except (ValueError, AttributeError):
        return 0


def _sysctl(key: str) -> str:
    try:
        return _run(["sysctl", "-n", key], timeout=3).strip()
    except Exception:
        return ""


def _powershell(command: str) -> str:
    creationflags = 0
    if platform.system() == "Windows":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        return _run(
            ["powershell", "-NoProfile", "-Command", command],
            timeout=8,
            creationflags=creationflags,
        )
    except Exception:
        return ""


def _run(args: list[str], timeout: int, creationflags: int = 0) -> str:
    result = subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=creationflags,
    )
    return result.stdout or ""
