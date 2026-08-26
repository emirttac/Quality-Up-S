from __future__ import annotations

import os
import threading
import time
from typing import Callable

import numpy as np

from quality_ups.core.capability import memory_gb
from quality_ups.core.diagnostics import EngineStatus, Readiness
from quality_ups.core.engine import SuperResolutionEngine
from quality_ups.core.models import ensure_required_models


StatusCallback = Callable[[str], None]
ReadyCallback = Callable[[EngineStatus], None]


class EngineRuntime:
    """Keeps the SR engine warm in the background for the app lifetime."""

    def __init__(self) -> None:
        self.engine = SuperResolutionEngine()
        self.status: EngineStatus | None = None
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_ready(self) -> bool:
        return self._ready.is_set() and self.status is not None and self.status.readiness != Readiness.BLOCKED

    def start(
        self,
        *,
        on_status: StatusCallback | None = None,
        on_ready: ReadyCallback | None = None,
    ) -> None:
        if self._thread and self._thread.is_alive():
            return

        def worker() -> None:
            def emit(msg: str) -> None:
                if on_status:
                    on_status(msg)

            cpu = os.cpu_count() or 1
            ram_total, ram_free = memory_gb()
            bench_ms: float | None = None
            models_ok = False

            try:
                emit("Checking models…")
                ensure_required_models()
                models_ok = True

                # Keep OpenCL off for OpenCV DNN (see gpu.apply_compute_device).
                try:
                    import cv2

                    cv2.ocl.setUseOpenCL(False)
                except Exception:
                    pass

                emit("Loading 2×…")
                self.engine.preload(2, model_id="fsrcnn")

                emit("Loading 4×…")
                self.engine.preload(4, model_id="fsrcnn")

                emit("Measuring performance…")
                probe = np.ascontiguousarray(
                    np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8)
                )
                t0 = time.perf_counter()
                _ = self.engine.upscale_array(probe, 2)
                bench_ms = (time.perf_counter() - t0) * 1000.0

                # Rough comfort heuristic for local tiled FSRCNN.
                if ram_free < 2.0:
                    readiness = Readiness.BLOCKED
                    title = "Not enough memory"
                    detail = (
                        f"Only {ram_free:.1f} GB of memory is free. "
                        "Quit other apps, then reopen Quality Up'S."
                    )
                elif ram_free < 4.0 or cpu < 4 or (bench_ms and bench_ms > 1200):
                    readiness = Readiness.LIMITED
                    title = "Ready — may run slowly"
                    detail = (
                        f"{cpu} cores, {ram_free:.1f} GB free of {ram_total:.1f} GB. "
                        f"Probe {bench_ms:.0f} ms. Prefer 2× for large batches."
                    )
                else:
                    readiness = Readiness.READY
                    title = "Ready"
                    detail = (
                        f"{cpu} cores, {ram_free:.1f} GB free of {ram_total:.1f} GB. "
                        f"Probe {bench_ms:.0f} ms."
                    )

                status = EngineStatus(
                    readiness=readiness,
                    title=title,
                    detail=detail,
                    cpu_cores=cpu,
                    ram_gb=ram_total,
                    free_ram_gb=ram_free,
                    bench_ms=bench_ms,
                    models_ok=models_ok,
                )
            except Exception as exc:  # noqa: BLE001
                status = EngineStatus(
                    readiness=Readiness.BLOCKED,
                    title="Unavailable",
                    detail=str(exc),
                    cpu_cores=cpu,
                    ram_gb=ram_total,
                    free_ram_gb=ram_free,
                    bench_ms=bench_ms,
                    models_ok=models_ok,
                )

            with self._lock:
                self.status = status
            self._ready.set()
            emit(status.title)
            if on_ready:
                on_ready(status)

        self._thread = threading.Thread(target=worker, daemon=True, name="quality-ups-engine")
        self._thread.start()
