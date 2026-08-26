from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from quality_ups.config import DEFAULT_OUTPUT_FORMAT, DEFAULT_OUTPUT_QUALITY
from quality_ups.core.engine import SuperResolutionEngine, UpscaleResult


@dataclass(frozen=True)
class ProgressUpdate:
    overall: float
    file_index: int
    file_total: int
    file_fraction: float
    filename: str
    message: str
    eta_seconds: float | None = None


ProgressCallback = Callable[[ProgressUpdate], None]
ItemDoneCallback = Callable[[UpscaleResult], None]
ItemFailCallback = Callable[[Path, str], None]
FinishedCallback = Callable[[], None]


@dataclass
class QueueJob:
    paths: list[Path]
    scale: int
    output_dir: Path
    model_id: str = "fsrcnn"
    output_format: str = DEFAULT_OUTPUT_FORMAT
    output_quality: int = DEFAULT_OUTPUT_QUALITY
    tile: int | None = None
    overlap: int | None = None


@dataclass
class Processor:
    """Runs jobs one image at a time on a background thread."""

    engine: SuperResolutionEngine
    _thread: threading.Thread | None = field(default=None, init=False, repr=False)
    _cancel: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _busy: bool = field(default=False, init=False)

    @property
    def is_busy(self) -> bool:
        return self._busy

    def cancel(self) -> None:
        self._cancel.set()

    def start(
        self,
        job: QueueJob,
        *,
        on_progress: ProgressCallback | None = None,
        on_item_done: ItemDoneCallback | None = None,
        on_item_fail: ItemFailCallback | None = None,
        on_finished: FinishedCallback | None = None,
    ) -> None:
        if self._busy:
            raise RuntimeError("Already processing")

        self._cancel.clear()
        self._busy = True

        def worker() -> None:
            total = len(job.paths)
            started = time.perf_counter()
            completed = 0
            try:
                self.engine.configure(
                    tile=job.tile,
                    overlap=job.overlap,
                    model_id=job.model_id,
                )
                for index, path in enumerate(job.paths, start=1):
                    if self._cancel.is_set():
                        if on_progress:
                            on_progress(
                                ProgressUpdate(
                                    overall=completed / max(total, 1),
                                    file_index=index,
                                    file_total=total,
                                    file_fraction=0.0,
                                    filename=path.name,
                                    message="Cancelled",
                                    eta_seconds=0.0,
                                )
                            )
                        break

                    def emit_file(frac: float, name: str = path.name, idx: int = index) -> None:
                        if not on_progress:
                            return
                        overall = ((idx - 1) + max(0.0, min(1.0, frac))) / max(total, 1)
                        elapsed = time.perf_counter() - started
                        eta = None
                        if overall > 0.02:
                            eta = max(0.0, (elapsed / overall) - elapsed)
                        on_progress(
                            ProgressUpdate(
                                overall=overall,
                                file_index=idx,
                                file_total=total,
                                file_fraction=frac,
                                filename=name,
                                message=f"{idx}/{total} · {name}",
                                eta_seconds=eta,
                            )
                        )

                    emit_file(0.0)
                    try:
                        result = self.engine.process_file(
                            path,
                            job.output_dir,
                            job.scale,
                            on_tile_progress=emit_file,
                            should_cancel=self._cancel.is_set,
                            output_format=job.output_format,
                            output_quality=job.output_quality,
                        )
                        completed += 1
                        emit_file(1.0)
                        if on_item_done:
                            on_item_done(result)
                    except Exception as exc:  # noqa: BLE001
                        if str(exc) == "Cancelled" or self._cancel.is_set():
                            if on_progress:
                                on_progress(
                                    ProgressUpdate(
                                        overall=completed / max(total, 1),
                                        file_index=index,
                                        file_total=total,
                                        file_fraction=0.0,
                                        filename=path.name,
                                        message="Cancelled",
                                        eta_seconds=0.0,
                                    )
                                )
                            break
                        if on_item_fail:
                            on_item_fail(path, str(exc))
                        completed += 1
            finally:
                self._busy = False
                if on_finished:
                    on_finished()

        self._thread = threading.Thread(target=worker, daemon=True, name="quality-ups-queue")
        self._thread.start()
