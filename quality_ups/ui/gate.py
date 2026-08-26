from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from quality_ups.core.capability import CapabilityReport, HardwareProfile, assess_system
from quality_ups.ui.theme import COLORS, FONT, FONT_DISPLAY

ContinueCallback = Callable[[], None]
TranslateFn = Callable[..., str]


class SystemGate(ctk.CTkFrame):
    """Startup probe: hardware score, then continue into the main app."""

    def __init__(self, master: Any, *, on_continue: ContinueCallback, translate: TranslateFn) -> None:
        super().__init__(master, fg_color=COLORS["window"])
        self._on_continue = on_continue
        self._t = translate
        self._loading = True
        self._status_base = self._t("gate_checking")
        self._dots = 0
        self._pulse_id: str | None = None
        self._build()

    def begin(self) -> None:
        """Call after the window has painted so the loader is visible first."""
        self._show_loading("gate_checking")
        threading.Thread(target=self._probe, daemon=True, name="quality-ups-capability").start()

    def show_preparing(self) -> None:
        self._show_loading("gate_preparing")

    def _label(
        self,
        master: Any,
        text: str = "",
        *,
        size: int = 13,
        weight: str = "normal",
        color: str = COLORS["label"],
        display: bool = False,
        **kwargs: Any,
    ) -> ctk.CTkLabel:
        return ctk.CTkLabel(
            master,
            text=text,
            font=ctk.CTkFont(family=FONT_DISPLAY if display else FONT, size=size, weight=weight),
            text_color=color,
            **kwargs,
        )

    def _build(self) -> None:
        inner = ctk.CTkFrame(self, fg_color="transparent", width=400)
        inner.place(relx=0.5, rely=0.48, anchor="center")
        inner.grid_columnconfigure(0, weight=1)

        self.status = self._label(
            inner,
            f"{self._t('gate_checking')}…",
            size=15,
            wraplength=400,
            justify="center",
            anchor="center",
        )
        self.status.grid(row=0, column=0, sticky="ew")

        self.hint = self._label(
            inner,
            self._t("gate_wait"),
            size=12,
            color=COLORS["tertiary"],
            wraplength=400,
            justify="center",
            anchor="center",
        )
        self.hint.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        self.scan = ctk.CTkProgressBar(
            inner,
            width=400,
            height=8,
            corner_radius=4,
            mode="indeterminate",
            indeterminate_speed=1.4,
            progress_color=COLORS["blue"],
            fg_color=COLORS["progress_track"],
        )
        self.scan.grid(row=2, column=0, sticky="ew", pady=(20, 0))

        self.specs = ctk.CTkFrame(inner, fg_color="transparent")
        self.specs.grid(row=3, column=0, sticky="ew", pady=(18, 0))
        self.specs.grid_columnconfigure(1, weight=1)
        self.specs.grid_remove()

        self.continue_btn = ctk.CTkButton(
            inner,
            text=self._t("gate_continue"),
            width=200,
            height=32,
            corner_radius=6,
            fg_color=COLORS["blue"],
            hover_color=COLORS["blue_pressed"],
            text_color=COLORS["surface"],
            font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
            command=self._handle_continue,
        )
        self.continue_btn.grid(row=4, column=0, sticky="e", pady=(22, 0))
        self.continue_btn.grid_remove()

    def _show_loading(self, key: str) -> None:
        self._loading = True
        self._status_base = self._t(key)
        self.status.configure(text=f"{self._status_base}…", text_color=COLORS["label"])
        self.hint.configure(text=self._t("gate_wait"))
        self.hint.grid()
        self.specs.grid_remove()
        self.continue_btn.grid_remove()
        self.scan.grid()
        self.scan.start()
        self._start_pulse()

    def _start_pulse(self) -> None:
        self._stop_pulse()
        self._dots = 0
        self._pulse()

    def _stop_pulse(self) -> None:
        if self._pulse_id is not None:
            self.after_cancel(self._pulse_id)
            self._pulse_id = None

    def _pulse(self) -> None:
        if not self._loading:
            return
        self._dots = (self._dots + 1) % 4
        self.status.configure(text=f"{self._status_base}{'.' * self._dots}")
        self._pulse_id = self.after(400, self._pulse)

    def _handle_continue(self) -> None:
        self.continue_btn.configure(state="disabled")
        self._on_continue()

    def _probe(self) -> None:
        def on_progress(key: str, _frac: float) -> None:
            self.after(0, lambda k=key: self._set_step(k))

        report = assess_system(on_progress=on_progress)
        self.after(0, lambda: self._show_report(report))

    def _set_step(self, key: str) -> None:
        if not self._loading:
            return
        self._status_base = self._t(key)
        self.status.configure(text=f"{self._status_base}{'.' * self._dots}")

    def _show_report(self, report: CapabilityReport) -> None:
        self._loading = False
        self._stop_pulse()
        self.scan.stop()
        self.scan.grid_remove()
        self.hint.grid_remove()
        self.status.configure(
            text=self._t(report.message_key),
            text_color=COLORS["green"] if report.sufficient else COLORS["orange"],
        )
        self._fill_specs(report.profile)
        self.specs.grid()
        self.continue_btn.configure(text=self._t(report.button_key), state="normal")
        self.continue_btn.grid()

    def _fill_specs(self, profile: HardwareProfile) -> None:
        for child in self.specs.winfo_children():
            child.destroy()
        cores = (
            self._t("cores_split", physical=profile.cpu_physical, logical=profile.cpu_cores)
            if profile.cpu_physical and profile.cpu_physical != profile.cpu_cores
            else str(profile.cpu_cores)
        )
        rows = [
            (self._t("spec_cpu"), profile.cpu_name),
            (self._t("spec_gpu"), profile.gpu_name),
            (self._t("spec_cores"), cores),
            (self._t("spec_memory"), self._t("memory_line", ram=profile.ram_gb, free=profile.free_ram_gb)),
            (self._t("spec_os"), f"{profile.os_name} {profile.os_version}".strip()),
        ]
        for index, (label, value) in enumerate(rows):
            self._label(self.specs, label, size=12, color=COLORS["tertiary"], anchor="w").grid(
                row=index, column=0, sticky="w", padx=(0, 16), pady=3
            )
            self._label(self.specs, value, size=12, color=COLORS["secondary"], anchor="e").grid(
                row=index, column=1, sticky="e", pady=3
            )
