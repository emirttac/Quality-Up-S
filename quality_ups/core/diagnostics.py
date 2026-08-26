from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Readiness(str, Enum):
    READY = "ready"
    LIMITED = "limited"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class EngineStatus:
    readiness: Readiness
    title: str
    detail: str
    cpu_cores: int
    ram_gb: float
    free_ram_gb: float
    bench_ms: float | None
    models_ok: bool
