from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageDraw, ImageTk
import customtkinter as ctk
import tkinter as tk

from quality_ups.ui.theme import COLORS, FONT, FONT_DISPLAY

TranslateFn = Callable[..., str]


def _checkerboard(size: tuple[int, int], cell: int = 12) -> Image.Image:
    w, h = size
    img = Image.new("RGB", (w, h), COLORS.get("checker_b", "#FFFFFF"))
    draw = ImageDraw.Draw(img)
    a = COLORS.get("checker_a", "#E8E8ED")
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            if ((x // cell) + (y // cell)) % 2 == 0:
                draw.rectangle([x, y, x + cell - 1, y + cell - 1], fill=a)
    return img


def _fit(pil: Image.Image, box: tuple[int, int]) -> Image.Image:
    bw, bh = box
    if bw < 8 or bh < 8:
        return pil
    src = pil.convert("RGBA") if pil.mode in {"RGBA", "LA", "P"} else pil.convert("RGB")
    src.thumbnail((bw, bh), Image.Resampling.LANCZOS)
    return src


class BeforeAfterView(ctk.CTkFrame):
    """Interactive before/after reveal slider over a shared preview canvas."""

    def __init__(
        self,
        master: Any,
        *,
        before: Path,
        after: Path,
        translate: TranslateFn,
        height: int = 280,
    ) -> None:
        super().__init__(master, fg_color=COLORS["surface"], corner_radius=10)
        self._t = translate
        self._before_path = Path(before)
        self._after_path = Path(after)
        self._ratio = 0.5
        self._photo: ImageTk.PhotoImage | None = None
        self._before_img: Image.Image | None = None
        self._after_img: Image.Image | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        head.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            head,
            text=self._t("compare_before"),
            font=ctk.CTkFont(family=FONT, size=12),
            text_color=COLORS["secondary"],
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            head,
            text=self._t("compare_after"),
            font=ctk.CTkFont(family=FONT, size=12),
            text_color=COLORS["secondary"],
        ).grid(row=0, column=2, sticky="e")

        self._canvas = tk.Canvas(
            self,
            height=height,
            highlightthickness=0,
            bg=COLORS["fill"],
            bd=0,
        )
        self._canvas.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        self._canvas.bind("<Configure>", self._redraw)
        self._canvas.bind("<B1-Motion>", self._drag)
        self._canvas.bind("<Button-1>", self._drag)

        self._slider = ctk.CTkSlider(
            self,
            from_=0,
            to=1,
            number_of_steps=100,
            command=self._on_slider,
            progress_color=COLORS["blue"],
            button_color=COLORS["blue"],
            button_hover_color=COLORS["blue_pressed"],
            fg_color=COLORS["progress_track"],
        )
        self._slider.set(0.5)
        self._slider.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))

        self.after(50, self._load)

    def _load(self) -> None:
        try:
            self._before_img = Image.open(self._before_path)
            self._after_img = Image.open(self._after_path)
        except Exception:
            self._before_img = None
            self._after_img = None
        self._redraw()

    def _on_slider(self, value: float) -> None:
        self._ratio = float(value)
        self._redraw()

    def _drag(self, event: Any) -> None:
        w = max(self._canvas.winfo_width(), 1)
        self._ratio = max(0.0, min(1.0, event.x / w))
        self._slider.set(self._ratio)
        self._redraw()

    def _redraw(self, _event: Any = None) -> None:
        if self._before_img is None or self._after_img is None:
            return
        cw = max(self._canvas.winfo_width(), 40)
        ch = max(self._canvas.winfo_height(), 40)
        before = _fit(self._before_img, (cw, ch))
        after = _fit(self._after_img, (cw, ch))
        base = _checkerboard((cw, ch))
        composed = base.convert("RGBA")
        # Draw after fully, then overlay left portion of before.
        after_rgba = after.convert("RGBA")
        before_rgba = before.convert("RGBA")
        layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        ax = (cw - after_rgba.width) // 2
        ay = (ch - after_rgba.height) // 2
        layer.paste(after_rgba, (ax, ay), after_rgba if after_rgba.mode == "RGBA" else None)

        split = int(cw * self._ratio)
        left = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        bx = (cw - before_rgba.width) // 2
        by = (ch - before_rgba.height) // 2
        left.paste(before_rgba, (bx, by), before_rgba if before_rgba.mode == "RGBA" else None)
        left = left.crop((0, 0, split, ch))
        layer.paste(left, (0, 0), left)

        final = Image.alpha_composite(composed, layer).convert("RGB")
        self._photo = ImageTk.PhotoImage(final)
        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor="nw", image=self._photo)
        self._canvas.create_line(split, 0, split, ch, fill=COLORS["blue"], width=2)
        self._canvas.create_oval(split - 6, ch // 2 - 6, split + 6, ch // 2 + 6, fill=COLORS["blue"], outline="")


class CompareWindow(ctk.CTkToplevel):
    def __init__(
        self,
        master: Any,
        *,
        before: Path,
        after: Path,
        translate: TranslateFn,
    ) -> None:
        super().__init__(master)
        self.title(translate("compare_title"))
        self.geometry("720x460")
        self.minsize(480, 320)
        self.configure(fg_color=COLORS["window"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text=translate("compare_title"),
            font=ctk.CTkFont(family=FONT_DISPLAY, size=18, weight="bold"),
            text_color=COLORS["label"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))

        view = BeforeAfterView(self, before=before, after=after, translate=translate, height=320)
        view.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
