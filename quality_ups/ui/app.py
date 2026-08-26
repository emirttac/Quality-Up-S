from __future__ import annotations

import platform
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from quality_ups.config import (
    APP_NAME,
    APP_VERSION,
    MODEL_IDS,
    OUTPUT_FORMATS,
    SCALE_OPTIONS,
    SUPPORTED_EXTENSIONS,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from quality_ups.core.prefs import Prefs, load_prefs, save_prefs
from quality_ups.host import prepare_host
from quality_ups.i18n.catalog import translate
from quality_ups.ui.about_page import AboutPage
from quality_ups.ui.app_icon import apply_app_icon
from quality_ups.ui.compare import CompareWindow
from quality_ups.ui.gate import SystemGate
from quality_ups.ui.settings_page import SettingsPage
from quality_ups.ui.sidebar import IconSidebar
from quality_ups.ui.theme import COLORS, FONT, FONT_DISPLAY, apply_theme


def _parse_drop_paths(data: str) -> list[Path]:
    paths: list[Path] = []
    token = ""
    in_brace = False
    for ch in data:
        if ch == "{":
            in_brace = True
            token = ""
            continue
        if ch == "}":
            in_brace = False
            if token:
                paths.append(Path(token))
            token = ""
            continue
        if ch == " " and not in_brace:
            if token:
                paths.append(Path(token))
                token = ""
            continue
        token += ch
    if token:
        paths.append(Path(token))
    return paths


def _is_supported(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def _short_path(path: str, max_len: int = 42) -> str:
    if len(path) <= max_len:
        return path
    return "…" + path[-(max_len - 1) :]


class QualityUpsApp(ctk.CTk, TkinterDnD.DnDWrapper):
    """macOS-HIG oriented layout: icon sidebar, one content pane at a time."""

    def __init__(self) -> None:
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        ctk.set_default_color_theme("blue")

        self.title(APP_NAME)
        apply_app_icon(self)

        self.prefs = load_prefs()
        apply_theme(self.prefs.theme)
        self.configure(fg_color=COLORS["window"])

        self.runtime: Any = None
        self.processor: Any = None
        self.queue: list[Path] = []
        self.scale = tk.IntVar(value=2)
        self.model_id = tk.StringVar(value=self.prefs.model_id)
        self.output_format = tk.StringVar(value=self.prefs.output_format)
        self.output_dir = tk.StringVar(value=str(Path.home() / "Desktop" / "QualityUps Output"))
        self.engine_label = tk.StringVar(value=self.t("engine_checking"))
        self.progress_detail = tk.StringVar(value="")
        self.progress_percent = tk.StringVar(value="")
        self._done_count = 0
        self._fail_count = 0
        self._engine_ready = False
        self._engine_state = "checking"
        self._queue_rows: list[Any] = []
        self._gate: SystemGate | None = None
        self._entering_main = False
        self._page = "home"
        self._sidebar: IconSidebar | None = None
        self._pages: dict[str, Any] = {}
        self._content: ctk.CTkFrame | None = None
        self._shell: ctk.CTkFrame | None = None
        self._home_labels: dict[str, Any] = {}
        self._devices: list[Any] | None = None
        self._last_compare: tuple[Path, Path] | None = None
        self._compare_btn: ctk.CTkButton | None = None
        self._model_buttons: dict[str, ctk.CTkButton] = {}
        self._format_menu: ctk.CTkOptionMenu | None = None
        self._scale_buttons: dict[int, ctk.CTkButton] = {}

        self.bind("<Command-comma>", lambda _e: self._show_page("settings"))
        self.bind("<Control-comma>", lambda _e: self._show_page("settings"))
        self.bind("<Command-Control-f>", lambda _e: "break")
        self.bind("<F11>", lambda _e: "break")
        # macOS keeps the window out of the Dock; Windows must still minimize to the taskbar.
        if platform.system() == "Darwin":
            self.bind("<Unmap>", self._on_unmap)

        self.withdraw()
        self._show_gate()
        self.deiconify()
        self.lift()
        if self._gate is not None:
            self._gate.begin()
        self.update_idletasks()
        self.update()

    def t(self, key: str, **kwargs: object) -> str:
        return translate(self.prefs.language, key, **kwargs)

    def _label(
        self,
        master: Any,
        text: str = "",
        *,
        size: int = 13,
        weight: str = "normal",
        color: str = COLORS["label"],
        variable: tk.Variable | None = None,
        display: bool = False,
        **kwargs: Any,
    ) -> ctk.CTkLabel:
        return ctk.CTkLabel(
            master,
            text=text,
            textvariable=variable,
            font=ctk.CTkFont(family=FONT_DISPLAY if display else FONT, size=size, weight=weight),
            text_color=color,
            **kwargs,
        )

    def _hairline(self, master: Any) -> ctk.CTkFrame:
        return ctk.CTkFrame(master, fg_color=COLORS["separator"], height=1, corner_radius=0)

    def _center(self, width: int, height: int) -> None:
        self.update_idletasks()
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 3)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _lock_window(self, width: int, height: int) -> None:
        """Fixed size (gate screen)."""
        self.resizable(False, False)
        self.minsize(width, height)
        self.maxsize(width, height)
        try:
            self.attributes("-fullscreen", False)
        except tk.TclError:
            pass
        self._center(width, height)

    def _flex_window(self, width: int, height: int) -> None:
        """Resizable main window with sensible minimums for HiDPI."""
        self.resizable(True, True)
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        try:
            self.maxsize(self.winfo_screenwidth(), self.winfo_screenheight())
        except tk.TclError:
            pass
        try:
            self.attributes("-fullscreen", False)
        except tk.TclError:
            pass
        self._center(width, height)

    def _on_unmap(self, event: Any) -> None:
        if event.widget is not self:
            return
        try:
            if str(self.state()) == "iconic":
                self.after(10, self._restore_window)
        except tk.TclError:
            pass

    def _restore_window(self) -> None:
        try:
            self.attributes("-fullscreen", False)
        except tk.TclError:
            pass
        self.deiconify()
        self.lift()

    def _show_gate(self) -> None:
        self._lock_window(520, 460)
        self._gate = SystemGate(self, on_continue=self._enter_main, translate=self.t)
        self._gate.pack(fill="both", expand=True)

    def _enter_main(self) -> None:
        if self._gate is None or self._entering_main:
            return
        self._entering_main = True
        self._gate.show_preparing()
        threading.Thread(target=self._prepare_main, daemon=True, name="quality-ups-boot").start()

    def _prepare_main(self) -> None:
        try:
            from quality_ups.core.processor import Processor
            from quality_ups.core.runtime import EngineRuntime
            from quality_ups.core.gpu import list_compute_devices

            # Disable OpenCL early — before any DNN load — to avoid Tk deadlocks on macOS.
            try:
                import cv2

                cv2.ocl.setUseOpenCL(False)
            except Exception:
                pass

            runtime = EngineRuntime()
            runtime.engine.set_device(self.prefs.gpu_id)
            processor = Processor(engine=runtime.engine)
            devices = list_compute_devices()
            self.after(0, lambda: self._reveal_main(runtime, processor, devices))
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda e=exc: self._boot_failed(e))

    def _boot_failed(self, exc: BaseException) -> None:
        self._entering_main = False
        messagebox.showerror(APP_NAME, str(exc))
        if self._gate is None:
            return
        try:
            self._gate._loading = False
            self._gate._stop_pulse()
            self._gate.scan.stop()
            self._gate.scan.grid_remove()
            self._gate.status.configure(text=str(exc), text_color=COLORS["red"])
            self._gate.continue_btn.configure(state="normal")
            self._gate.continue_btn.grid()
        except Exception:
            pass

    def _reveal_main(self, runtime: Any, processor: Any, devices: list[Any] | None = None) -> None:
        if devices is not None:
            self._devices = devices
        if self._gate is not None:
            self._gate.destroy()
            self._gate = None
        self.runtime = runtime
        self.processor = processor
        runtime.engine.configure(tile=self.prefs.tile, overlap=self.prefs.overlap, model_id=self.prefs.model_id)
        self._flex_window(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)
        self._build()
        self._start_engine()

    def _build(self) -> None:
        if self._shell is not None:
            self._shell.destroy()
        shell = ctk.CTkFrame(self, fg_color=COLORS["window"])
        shell.pack(fill="both", expand=True)
        shell.grid_columnconfigure(1, weight=1)
        shell.grid_rowconfigure(0, weight=1)
        self._shell = shell

        self._sidebar = IconSidebar(shell, on_select=self._show_page, translate=self.t)
        self._sidebar.grid(row=0, column=0, sticky="nsw")

        self._content = ctk.CTkFrame(shell, fg_color=COLORS["window"])
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        home = ctk.CTkFrame(self._content, fg_color=COLORS["window"])
        home.grid(row=0, column=0, sticky="nsew")
        self._pages = {"home": home}
        self._build_home(home)
        self._rebuild_aux_pages()
        self._show_page("home")

    def _gpu_devices(self) -> list[Any]:
        if self._devices is None:
            from quality_ups.core.gpu import list_compute_devices

            self._devices = list_compute_devices()
        return self._devices

    def _rebuild_aux_pages(self) -> None:
        for key in ("settings", "about"):
            page = self._pages.get(key)
            if page is not None:
                page.destroy()
        assert self._content is not None
        settings = SettingsPage(
            self._content,
            translate=self.t,
            prefs=self.prefs,
            devices=self._gpu_devices(),
            on_language=self._set_language,
            on_gpu=self._set_gpu,
            on_theme=self._set_theme,
            on_tile=self._set_tile,
            on_overlap=self._set_overlap,
            on_output_format=self._set_output_format,
            on_output_quality=self._set_output_quality,
        )
        about = AboutPage(self._content, translate=self.t, on_check_updates=self._check_updates)
        settings.grid(row=0, column=0, sticky="nsew", padx=28, pady=24)
        about.grid(row=0, column=0, sticky="nsew", padx=28, pady=24)
        self._pages["settings"] = settings
        self._pages["about"] = about
        self._show_page(self._page)

    def _persist_prefs(self, **kwargs: Any) -> None:
        data = {
            "language": self.prefs.language,
            "gpu_id": self.prefs.gpu_id,
            "theme": self.prefs.theme,
            "model_id": self.prefs.model_id,
            "tile": self.prefs.tile,
            "overlap": self.prefs.overlap,
            "output_format": self.prefs.output_format,
            "output_quality": self.prefs.output_quality,
        }
        data.update(kwargs)
        self.prefs = Prefs(**data).normalized()
        save_prefs(self.prefs)

    def _set_language(self, code: str) -> None:
        self._persist_prefs(language=code)
        if self._sidebar is not None:
            self._sidebar.set_language(self.t)
            self._sidebar.set_active(self._page)
        self._apply_home_language()
        self._rebuild_aux_pages()

    def _set_gpu(self, gpu_id: str) -> None:
        self._persist_prefs(gpu_id=gpu_id)
        if self.runtime is not None:
            self.runtime.engine.set_device(gpu_id)

    def _set_theme(self, theme: str) -> None:
        self._persist_prefs(theme=theme)
        apply_theme(theme)
        self.configure(fg_color=COLORS["window"])
        page = self._page
        self._build()
        self._show_page(page)
        # Restore engine status styling after a full shell rebuild.
        if self._engine_state == "ready":
            self.engine_status.configure(text_color=COLORS["green"])
            self.start_btn.configure(state="normal")
        elif self._engine_state == "slow":
            self.engine_status.configure(text_color=COLORS["orange"])
            self.start_btn.configure(state="normal")
        elif self._engine_state == "unavailable":
            self.engine_status.configure(text_color=COLORS["red"])
            self.start_btn.configure(state="disabled")
        self._refresh_engine_label()
        if self._last_compare is not None and self._compare_btn is not None:
            self._compare_btn.configure(state="normal")
        if self.queue:
            self._refresh_queue_list()

    def _set_tile(self, tile: int) -> None:
        self._persist_prefs(tile=tile)
        if self.runtime is not None:
            self.runtime.engine.configure(tile=tile)

    def _set_overlap(self, overlap: int) -> None:
        self._persist_prefs(overlap=overlap)
        if self.runtime is not None:
            self.runtime.engine.configure(overlap=overlap)

    def _set_output_format(self, fmt: str) -> None:
        self._persist_prefs(output_format=fmt)
        self.output_format.set(fmt)
        if self._format_menu is not None:
            self._format_menu.set(self.t(f"format_{fmt}"))

    def _on_format_menu(self, name: str) -> None:
        for fmt in OUTPUT_FORMATS:
            if self.t(f"format_{fmt}") == name:
                self._set_output_format(fmt)
                return

    def _set_output_quality(self, quality: int) -> None:
        self._persist_prefs(output_quality=quality)

    def _show_page(self, key: str) -> None:
        if key not in self._pages:
            return
        self._page = key
        for name, frame in self._pages.items():
            if name == key:
                frame.tkraise()
                frame.grid()
            else:
                frame.grid_remove()
        if self._sidebar is not None:
            self._sidebar.set_active(key)

    def _build_home(self, root: ctk.CTkFrame) -> None:
        inner = ctk.CTkFrame(root, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=20)
        inner.grid_columnconfigure(0, weight=1)
        inner.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title = self._label(header, APP_NAME, size=22, weight="bold", display=True, anchor="w")
        title.grid(row=0, column=0, sticky="w")
        self.engine_status = self._label(
            header, variable=self.engine_label, size=12, color=COLORS["secondary"], anchor="e"
        )
        self.engine_status.grid(row=0, column=1, sticky="e", padx=(12, 0))

        self._hairline(inner).grid(row=1, column=0, sticky="ew", pady=(14, 16))

        self.drop = ctk.CTkFrame(
            inner,
            fg_color=COLORS["surface"],
            border_width=1,
            border_color=COLORS["drop_border"],
            corner_radius=10,
            height=120,
        )
        self.drop.grid(row=2, column=0, sticky="ew")
        self.drop.grid_propagate(False)

        drop_copy = ctk.CTkFrame(self.drop, fg_color="transparent")
        drop_copy.place(relx=0.5, rely=0.5, anchor="center")
        drop_title = self._label(drop_copy, self.t("drop_title"), size=15, weight="bold")
        drop_title.pack()
        drop_hint = self._label(drop_copy, self.t("drop_hint"), size=12, color=COLORS["tertiary"])
        drop_hint.pack(pady=(4, 0))
        self._home_labels["drop_title"] = drop_title
        self._home_labels["drop_hint"] = drop_hint

        self.drop.drop_target_register(DND_FILES)
        self.drop.dnd_bind("<<Drop>>", self._on_drop)
        self.drop.dnd_bind("<<DragEnter>>", self._on_drag_enter)
        self.drop.dnd_bind("<<DragLeave>>", self._on_drag_leave)
        self.drop.bind("<Button-1>", lambda _e: self._browse())
        for child in drop_copy.winfo_children():
            child.bind("<Button-1>", lambda _e: self._browse())

        queue_wrap = ctk.CTkFrame(inner, fg_color="transparent")
        queue_wrap.grid(row=3, column=0, sticky="nsew", pady=(20, 0))
        queue_wrap.grid_columnconfigure(0, weight=1)
        queue_wrap.grid_rowconfigure(1, weight=1)

        q_head = ctk.CTkFrame(queue_wrap, fg_color="transparent")
        q_head.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        q_head.grid_columnconfigure(0, weight=1)

        queue_title = self._label(q_head, self.t("queue"), size=13, weight="bold", anchor="w")
        queue_title.grid(row=0, column=0, sticky="w")
        self.queue_count = self._label(q_head, self.t("queue_none"), size=12, color=COLORS["secondary"], anchor="e")
        self.queue_count.grid(row=0, column=1, sticky="e")
        self._home_labels["queue"] = queue_title

        self.queue_box = ctk.CTkScrollableFrame(
            queue_wrap,
            fg_color=COLORS["surface"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["separator"],
        )
        self.queue_box.grid(row=1, column=0, sticky="nsew")
        self.queue_box.grid_columnconfigure(0, weight=1)
        self._render_empty_queue()

        settings = ctk.CTkFrame(inner, fg_color="transparent")
        settings.grid(row=4, column=0, sticky="ew", pady=(20, 0))
        settings.grid_columnconfigure(1, weight=1)

        model_label = self._label(settings, self.t("model"), size=13, color=COLORS["secondary"], anchor="w", width=88)
        model_label.grid(row=0, column=0, sticky="w", pady=(0, 10))
        self._home_labels["model"] = model_label
        model_row = ctk.CTkFrame(settings, fg_color=COLORS["surface_secondary"], corner_radius=7, height=28)
        model_row.grid(row=0, column=1, sticky="w", pady=(0, 10))
        self._model_buttons = {}
        for mid in MODEL_IDS:
            btn = ctk.CTkButton(
                model_row,
                text=self.t(f"model_{mid}"),
                width=168,
                height=26,
                corner_radius=6,
                font=ctk.CTkFont(family=FONT, size=12),
                command=lambda m=mid: self._set_model(m),
            )
            btn.pack(side="left", padx=1, pady=1)
            self._model_buttons[mid] = btn
        self._set_model(self.prefs.model_id, notify=False)

        scale_label = self._label(settings, self.t("scale"), size=13, color=COLORS["secondary"], anchor="w", width=88)
        scale_label.grid(row=1, column=0, sticky="w", pady=(0, 10))
        self._home_labels["scale"] = scale_label
        scale_row = ctk.CTkFrame(settings, fg_color=COLORS["surface_secondary"], corner_radius=7, height=28)
        scale_row.grid(row=1, column=1, sticky="w", pady=(0, 10))
        self._scale_buttons = {}
        for scale in SCALE_OPTIONS:
            btn = ctk.CTkButton(
                scale_row,
                text=f"{scale}×",
                width=56,
                height=26,
                corner_radius=6,
                font=ctk.CTkFont(family=FONT, size=13),
                command=lambda s=scale: self._set_scale(s),
            )
            btn.pack(side="left", padx=1, pady=1)
            self._scale_buttons[scale] = btn
        self._set_scale(2)

        fmt_label = self._label(settings, self.t("format"), size=13, color=COLORS["secondary"], anchor="w", width=88)
        fmt_label.grid(row=2, column=0, sticky="w", pady=(0, 10))
        self._home_labels["format"] = fmt_label
        fmt_labels = [self.t(f"format_{f}") for f in OUTPUT_FORMATS]
        self._format_menu = ctk.CTkOptionMenu(
            settings,
            values=fmt_labels,
            width=160,
            height=28,
            corner_radius=6,
            fg_color=COLORS["surface"],
            button_color=COLORS["surface_secondary"],
            button_hover_color=COLORS["separator"],
            text_color=COLORS["label"],
            dropdown_fg_color=COLORS["surface"],
            dropdown_hover_color=COLORS["fill"],
            font=ctk.CTkFont(family=FONT, size=12),
            command=self._on_format_menu,
        )
        self._format_menu.set(self.t(f"format_{self.prefs.output_format}"))
        self._format_menu.grid(row=2, column=1, sticky="w", pady=(0, 10))

        save_label = self._label(settings, self.t("save_to"), size=13, color=COLORS["secondary"], anchor="w", width=88)
        save_label.grid(row=3, column=0, sticky="w")
        self._home_labels["save_to"] = save_label
        out_row = ctk.CTkFrame(settings, fg_color="transparent")
        out_row.grid(row=3, column=1, sticky="ew")
        out_row.grid_columnconfigure(0, weight=1)

        self.output_entry = ctk.CTkEntry(
            out_row,
            textvariable=self.output_dir,
            height=28,
            corner_radius=6,
            border_width=1,
            border_color=COLORS["separator"],
            fg_color=COLORS["surface"],
            text_color=COLORS["label"],
            font=ctk.CTkFont(family=FONT, size=12),
        )
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.choose_btn = ctk.CTkButton(
            out_row,
            text=self.t("choose"),
            width=88,
            height=28,
            corner_radius=6,
            fg_color=COLORS["surface_secondary"],
            hover_color=COLORS["separator"],
            text_color=COLORS["label"],
            font=ctk.CTkFont(family=FONT, size=12),
            command=self._choose_output,
        )
        self.choose_btn.grid(row=0, column=1)

        self.progress_block = ctk.CTkFrame(inner, fg_color="transparent")
        self.progress_block.grid(row=5, column=0, sticky="ew", pady=(18, 0))
        self.progress_block.grid_columnconfigure(0, weight=1)

        prog_head = ctk.CTkFrame(self.progress_block, fg_color="transparent")
        prog_head.grid(row=0, column=0, sticky="ew")
        prog_head.grid_columnconfigure(0, weight=1)
        self._label(prog_head, variable=self.progress_detail, size=12, color=COLORS["secondary"], anchor="w").grid(
            row=0, column=0, sticky="w"
        )
        self._label(prog_head, variable=self.progress_percent, size=12, color=COLORS["secondary"], anchor="e").grid(
            row=0, column=1, sticky="e"
        )
        self.progress = ctk.CTkProgressBar(
            self.progress_block,
            height=4,
            corner_radius=2,
            progress_color=COLORS["blue"],
            fg_color=COLORS["progress_track"],
        )
        self.progress.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.progress.set(0)
        self.progress_block.grid_remove()

        self._hairline(inner).grid(row=6, column=0, sticky="ew", pady=(18, 14))

        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.grid(row=7, column=0, sticky="ew")
        actions.grid_columnconfigure(1, weight=1)

        self.clear_btn = ctk.CTkButton(
            actions,
            text=self.t("clear"),
            width=84,
            height=28,
            corner_radius=6,
            fg_color=COLORS["surface_secondary"],
            hover_color=COLORS["separator"],
            text_color=COLORS["label"],
            font=ctk.CTkFont(family=FONT, size=13),
            command=self._clear_queue,
        )
        self.clear_btn.grid(row=0, column=0, sticky="w")

        self._compare_btn = ctk.CTkButton(
            actions,
            text=self.t("compare"),
            width=100,
            height=28,
            corner_radius=6,
            fg_color=COLORS["surface_secondary"],
            hover_color=COLORS["separator"],
            text_color=COLORS["label"],
            font=ctk.CTkFont(family=FONT, size=13),
            command=self._open_compare,
            state="disabled",
        )
        self._compare_btn.grid(row=0, column=1, sticky="w", padx=(8, 0))

        self.cancel_btn = ctk.CTkButton(
            actions,
            text=self.t("cancel"),
            width=84,
            height=28,
            corner_radius=6,
            fg_color=COLORS["surface_secondary"],
            hover_color=COLORS["separator"],
            text_color=COLORS["label"],
            font=ctk.CTkFont(family=FONT, size=13),
            command=self._cancel,
            state="disabled",
        )
        self.cancel_btn.grid(row=0, column=2, sticky="e", padx=(0, 8))

        self.start_btn = ctk.CTkButton(
            actions,
            text=self.t("enhance"),
            width=110,
            height=28,
            corner_radius=6,
            fg_color=COLORS["blue"],
            hover_color=COLORS["blue_pressed"],
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
            command=self._start,
            state="disabled",
        )
        self.start_btn.grid(row=0, column=3, sticky="e")

    def _apply_home_language(self) -> None:
        mapping = {
            "drop_title": "drop_title",
            "drop_hint": "drop_hint",
            "queue": "queue",
            "scale": "scale",
            "save_to": "save_to",
            "model": "model",
            "format": "format",
        }
        for attr, key in mapping.items():
            widget = self._home_labels.get(attr)
            if widget is not None:
                widget.configure(text=self.t(key))
        self.choose_btn.configure(text=self.t("choose"))
        self.clear_btn.configure(text=self.t("clear"))
        self.cancel_btn.configure(text=self.t("cancel"))
        self.start_btn.configure(text=self.t("enhance"))
        if self._compare_btn is not None:
            self._compare_btn.configure(text=self.t("compare"))
        for mid, btn in self._model_buttons.items():
            btn.configure(text=self.t(f"model_{mid}"))
        if self._format_menu is not None:
            fmt_labels = [self.t(f"format_{f}") for f in OUTPUT_FORMATS]
            self._format_menu.configure(values=fmt_labels)
            self._format_menu.set(self.t(f"format_{self.prefs.output_format}"))
        self._refresh_engine_label()
        if self.queue:
            self._refresh_queue_list()
        else:
            self._render_empty_queue()

    def _refresh_engine_label(self) -> None:
        keys = {
            "checking": "engine_checking",
            "ready": "engine_ready",
            "slow": "engine_slow",
            "unavailable": "engine_unavailable",
        }
        self.engine_label.set(self.t(keys.get(self._engine_state, "engine_checking")))

    def _start_engine(self) -> None:
        self.runtime.start(
            on_status=lambda _msg: self.after(0, lambda: None),
            on_ready=lambda status: self.after(0, lambda s=status: self._on_engine_ready(s)),
        )

    def _on_engine_ready(self, status: Any) -> None:
        from quality_ups.core.diagnostics import Readiness

        if status.readiness == Readiness.READY:
            self._engine_state = "ready"
            self.engine_status.configure(text_color=COLORS["green"])
            self._engine_ready = True
            self.start_btn.configure(state="normal")
        elif status.readiness == Readiness.LIMITED:
            self._engine_state = "slow"
            self.engine_status.configure(text_color=COLORS["orange"])
            self._engine_ready = True
            self.start_btn.configure(state="normal")
        else:
            self._engine_state = "unavailable"
            self.engine_status.configure(text_color=COLORS["red"])
            self._engine_ready = False
            self.start_btn.configure(state="disabled")
            messagebox.showerror(APP_NAME, status.detail)
        self._refresh_engine_label()

    def _set_scale(self, scale: int) -> None:
        self.scale.set(scale)
        for value, btn in self._scale_buttons.items():
            selected = value == scale
            btn.configure(
                fg_color=COLORS["blue"] if selected else "transparent",
                hover_color=COLORS["blue_pressed"] if selected else COLORS["fill"],
                text_color="#FFFFFF" if selected else COLORS["label"],
            )

    def _set_model(self, model_id: str, *, notify: bool = True) -> None:
        from quality_ups.core.models import get_model_info

        info = get_model_info(model_id)
        if model_id != "fsrcnn" and not info.is_available():
            if notify:
                messagebox.showinfo(APP_NAME, self.t("model_unavailable"))
            model_id = "fsrcnn"
        self.model_id.set(model_id)
        self._persist_prefs(model_id=model_id)
        if self.runtime is not None:
            try:
                self.runtime.engine.configure(model_id=model_id)
            except Exception as exc:  # noqa: BLE001
                if notify:
                    messagebox.showwarning(APP_NAME, str(exc))
                self.model_id.set("fsrcnn")
                self._persist_prefs(model_id="fsrcnn")
                model_id = "fsrcnn"
                self.runtime.engine.configure(model_id="fsrcnn")
        for mid, btn in self._model_buttons.items():
            selected = mid == model_id
            btn.configure(
                fg_color=COLORS["blue"] if selected else "transparent",
                hover_color=COLORS["blue_pressed"] if selected else COLORS["fill"],
                text_color="#FFFFFF" if selected else COLORS["label"],
            )

    def _set_scale_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for btn in self._scale_buttons.values():
            btn.configure(state=state)
        for btn in self._model_buttons.values():
            btn.configure(state=state)
        if self._format_menu is not None:
            self._format_menu.configure(state=state)

    def _open_compare(self) -> None:
        if self._last_compare is None:
            return
        before, after = self._last_compare
        CompareWindow(self, before=before, after=after, translate=self.t)

    def _queue_count_text(self) -> str:
        count = len(self.queue)
        if count == 0:
            return self.t("queue_none")
        if count == 1:
            return self.t("queue_one")
        return self.t("queue_many", n=count)

    def _render_empty_queue(self) -> None:
        for row in self._queue_rows:
            row.destroy()
        self._queue_rows.clear()
        empty = self._label(
            self.queue_box,
            self.t("queue_empty"),
            size=13,
            color=COLORS["tertiary"],
            anchor="center",
        )
        empty.grid(row=0, column=0, sticky="ew", pady=28)
        self._queue_rows.append(empty)
        self.queue_count.configure(text=self._queue_count_text())

    def _refresh_queue_list(self) -> None:
        for row in self._queue_rows:
            row.destroy()
        self._queue_rows.clear()
        if not self.queue:
            self._render_empty_queue()
            return
        for index, path in enumerate(self.queue):
            row = ctk.CTkFrame(self.queue_box, fg_color="transparent")
            row.grid(row=index, column=0, sticky="ew")
            row.grid_columnconfigure(0, weight=1)
            last = index == len(self.queue) - 1
            self._label(row, path.name, size=13, anchor="w").grid(
                row=0, column=0, sticky="ew", padx=12, pady=(10, 10 if last else 0)
            )
            self._label(
                row,
                path.suffix.upper().lstrip(".") or "FILE",
                size=11,
                color=COLORS["tertiary"],
                anchor="e",
            ).grid(row=0, column=1, sticky="e", padx=(8, 12), pady=(10, 10 if last else 0))
            if not last:
                self._hairline(row).grid(row=1, column=0, columnspan=2, sticky="ew", padx=12)
            self._queue_rows.append(row)
        self.queue_count.configure(text=self._queue_count_text())

    def _on_drag_enter(self, _event: Any) -> None:
        self.drop.configure(fg_color=COLORS["drop_active"], border_color=COLORS["blue"])

    def _on_drag_leave(self, _event: Any) -> None:
        self.drop.configure(fg_color=COLORS["surface"], border_color=COLORS["drop_border"])

    def _on_drop(self, event: Any) -> None:
        self._on_drag_leave(event)
        self._add_paths(_parse_drop_paths(event.data))

    def _browse(self) -> None:
        files = filedialog.askopenfilenames(
            title=self.t("browse_title"),
            filetypes=[
                (self.t("images_filter"), "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.heic *.heif"),
                (self.t("all_files"), "*.*"),
            ],
        )
        if files:
            self._add_paths([Path(f) for f in files])

    def _choose_output(self) -> None:
        path = filedialog.askdirectory(title=self.t("output_title"))
        if path:
            self.output_dir.set(path)

    def _add_paths(self, paths: list[Path]) -> None:
        added = 0
        for path in paths:
            path = path.expanduser().resolve()
            if not _is_supported(path) or path in self.queue:
                continue
            self.queue.append(path)
            added += 1
        if added:
            self._refresh_queue_list()
        elif paths:
            messagebox.showinfo(APP_NAME, self.t("unsupported_files"))

    def _show_progress(self) -> None:
        self.progress_block.grid()

    def _hide_progress(self) -> None:
        self.progress.set(0)
        self.progress_detail.set("")
        self.progress_percent.set("")
        self.progress_block.grid_remove()

    def _clear_queue(self) -> None:
        if self.processor is None or self.processor.is_busy:
            return
        self.queue.clear()
        self._render_empty_queue()
        self._hide_progress()

    def _cancel(self) -> None:
        if self.processor is None:
            return
        self.processor.cancel()
        self.progress_detail.set(self.t("stopping"))

    def _fmt_eta(self, seconds: float | None) -> str:
        if seconds is None:
            return self.t("eta_estimating")
        seconds = max(0, int(seconds))
        m, s = divmod(seconds, 60)
        if m:
            return self.t("eta_min_sec", m=m, s=s)
        return self.t("eta_sec", s=s)

    def _start(self) -> None:
        if self.processor is None or self.processor.is_busy:
            return
        if not self._engine_ready:
            messagebox.showwarning(APP_NAME, self.t("engine_not_ready"))
            return
        if not self.queue:
            messagebox.showinfo(APP_NAME, self.t("add_one_image"))
            return
        out = Path(self.output_dir.get()).expanduser()
        try:
            out.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(APP_NAME, self.t("create_folder_error", error=exc))
            return

        self._done_count = 0
        self._fail_count = 0
        self._last_compare = None
        if self._compare_btn is not None:
            self._compare_btn.configure(state="disabled")
        self.start_btn.configure(state="disabled")
        self.clear_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self._set_scale_enabled(False)
        self.progress.set(0)
        self.progress_detail.set(self.t("starting"))
        self.progress_percent.set("0%")
        self._show_progress()

        from quality_ups.core.processor import QueueJob

        job = QueueJob(
            paths=list(self.queue),
            scale=int(self.scale.get()),
            output_dir=out,
            model_id=self.model_id.get(),
            output_format=self.prefs.output_format,
            output_quality=self.prefs.output_quality,
            tile=self.prefs.tile,
            overlap=self.prefs.overlap,
        )
        self.processor.start(
            job,
            on_progress=lambda update: self.after(0, lambda u=update: self._on_progress(u)),
            on_item_done=lambda result: self.after(0, lambda r=result: self._on_item_done(r)),
            on_item_fail=lambda path, err: self.after(0, lambda p=path, e=err: self._on_item_fail(p, e)),
            on_finished=lambda: self.after(0, self._on_finished),
        )

    def _on_progress(self, update: Any) -> None:
        self.progress.set(max(0.0, min(1.0, update.overall)))
        self.progress_percent.set(f"{int(update.overall * 100)}%")
        self.progress_detail.set(
            self.t(
                "progress_file",
                index=update.file_index,
                total=update.file_total,
                name=update.filename,
                eta=self._fmt_eta(update.eta_seconds),
            )
        )

    def _on_item_done(self, result: Any) -> None:
        self._done_count += 1
        self._last_compare = (Path(result.source), Path(result.output))
        if self._compare_btn is not None:
            self._compare_btn.configure(state="normal")

    def _on_item_fail(self, path: Path, err: str) -> None:
        self._fail_count += 1
        messagebox.showwarning(APP_NAME, self.t("process_fail", name=path.name, error=err))

    def _on_finished(self) -> None:
        self.start_btn.configure(state="normal" if self._engine_ready else "disabled")
        self.clear_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self._set_scale_enabled(True)
        if self._done_count and not self._fail_count:
            self.progress.set(1)
            self.progress_percent.set("100%")
            self.progress_detail.set(self.t("finished", path=_short_path(self.output_dir.get())))
        elif self.progress_detail.get() in {self.t("stopping"), "Stopping…"}:
            self.progress_detail.set(self.t("canceled"))
        else:
            key = "finished_errors" if self._fail_count == 1 else "finished_errors_many"
            self.progress_detail.set(self.t(key, n=self._fail_count))

    def _check_updates(self) -> None:
        about = self._pages.get("about")
        if isinstance(about, AboutPage):
            about.set_status(self.t("checking_updates"), checking=True)
        threading.Thread(target=self._check_updates_worker, daemon=True, name="quality-ups-update").start()

    def _check_updates_worker(self) -> None:
        from quality_ups.core.updates import check_for_updates, notify_update

        result = check_for_updates()
        self.after(0, lambda: self._on_update_result(result, notify_update))

    def _on_update_result(self, result: Any, notify_update: Any) -> None:
        about = self._pages.get("about")
        if result.update_available:
            text = self.t("update_available", version=result.latest or "")
            if isinstance(about, AboutPage):
                about.set_status(text, alert=True)
            notify_update(self.t("notify_update_title"), self.t("notify_update_body", version=result.latest or APP_VERSION))
            messagebox.showinfo(APP_NAME, f"{text}\n{result.url}")
            return
        if result.ok:
            text = self.t("up_to_date")
            if isinstance(about, AboutPage):
                about.set_status(text)
            return
        if isinstance(about, AboutPage):
            about.set_status(self.t("update_failed"), alert=True)


def run() -> None:
    prepare_host()
    app = QualityUpsApp()
    app.mainloop()
