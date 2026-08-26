from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk

from quality_ups.config import (
    OVERLAP_OPTIONS,
    OUTPUT_FORMATS,
    THEME_OPTIONS,
    TILE_OPTIONS,
)
from quality_ups.core.gpu import ComputeDevice
from quality_ups.core.prefs import Prefs
from quality_ups.i18n.catalog import LANGUAGES
from quality_ups.ui.theme import COLORS, FONT, FONT_DISPLAY

TranslateFn = Callable[..., str]


class SettingsPage(ctk.CTkScrollableFrame):
    def __init__(
        self,
        master: Any,
        *,
        translate: TranslateFn,
        prefs: Prefs,
        devices: list[ComputeDevice],
        on_language: Callable[[str], None],
        on_gpu: Callable[[str], None],
        on_theme: Callable[[str], None],
        on_tile: Callable[[int], None],
        on_overlap: Callable[[int], None],
        on_output_format: Callable[[str], None],
        on_output_quality: Callable[[int], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._t = translate
        self._prefs = prefs
        self._devices = devices
        self._on_language = on_language
        self._on_gpu = on_gpu
        self._on_theme = on_theme
        self._on_tile = on_tile
        self._on_overlap = on_overlap
        self._on_output_format = on_output_format
        self._on_output_quality = on_output_quality
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _make_label(self, master: Any, text: str, **kwargs: Any) -> ctk.CTkLabel:
        # Named _make_label — CTkScrollableFrame already owns self._label.
        size = kwargs.pop("size", 13)
        weight = kwargs.pop("weight", "normal")
        color = kwargs.pop("color", COLORS["label"])
        display = kwargs.pop("display", False)
        return ctk.CTkLabel(
            master,
            text=text,
            font=ctk.CTkFont(family=FONT_DISPLAY if display else FONT, size=size, weight=weight),
            text_color=color,
            **kwargs,
        )

    def _section(self, row: int, title_key: str, help_key: str) -> int:
        self._make_label(self, self._t(title_key), size=13, weight="bold", anchor="w").grid(
            row=row, column=0, sticky="w", pady=(22 if row else 0, 4)
        )
        self._make_label(
            self,
            self._t(help_key),
            size=12,
            color=COLORS["secondary"],
            wraplength=560,
            justify="left",
            anchor="w",
        ).grid(row=row + 1, column=0, sticky="ew")
        return row + 2

    def _menu(self, values: list[str], width: int, command: Any) -> ctk.CTkOptionMenu:
        return ctk.CTkOptionMenu(
            self,
            values=values,
            width=width,
            height=32,
            corner_radius=6,
            fg_color=COLORS["surface"],
            button_color=COLORS["surface_secondary"],
            button_hover_color=COLORS["separator"],
            text_color=COLORS["label"],
            dropdown_fg_color=COLORS["surface"],
            dropdown_hover_color=COLORS["fill"],
            font=ctk.CTkFont(family=FONT, size=13),
            command=command,
        )

    def _build(self) -> None:
        self._make_label(self, self._t("settings_title"), size=22, weight="bold", display=True, anchor="w").grid(
            row=0, column=0, sticky="w"
        )
        row = 1

        # Language
        row = self._section(row, "settings_language", "settings_language_help")
        names = [LANGUAGES[code] for code in LANGUAGES]
        codes = list(LANGUAGES.keys())
        current = LANGUAGES.get(self._prefs.language, LANGUAGES["tr"])
        lang_menu = self._menu(names, 220, lambda name: self._on_language(codes[names.index(name)]))
        lang_menu.set(current)
        lang_menu.grid(row=row, column=0, sticky="w", pady=(10, 0))
        row += 1

        # Theme
        row = self._section(row, "settings_theme", "settings_theme_help")
        theme_labels = [self._t(f"theme_{m}") for m in THEME_OPTIONS]
        theme_menu = self._menu(
            theme_labels,
            220,
            lambda name: self._on_theme(THEME_OPTIONS[theme_labels.index(name)]),
        )
        theme_menu.set(self._t(f"theme_{self._prefs.theme}"))
        theme_menu.grid(row=row, column=0, sticky="w", pady=(10, 0))
        row += 1

        # GPU
        row = self._section(row, "settings_gpu", "settings_gpu_help")
        labels: list[str] = []
        ids: list[str] = []
        for device in self._devices:
            if device.kind in {"auto", "cpu"}:
                label = self._t(device.label_key())
            else:
                kind = self._t(device.label_key())
                label = f"{device.name}  ·  {kind}"
            labels.append(label)
            ids.append(device.id)
        selected_index = ids.index(self._prefs.gpu_id) if self._prefs.gpu_id in ids else 0
        gpu_menu = self._menu(labels, 320, lambda name: self._on_gpu(ids[labels.index(name)]))
        gpu_menu.set(labels[selected_index])
        gpu_menu.grid(row=row, column=0, sticky="w", pady=(10, 0))
        row += 1

        # Tile
        row = self._section(row, "settings_tile", "settings_tile_help")
        tile_values = [str(v) for v in TILE_OPTIONS]
        tile_menu = self._menu(
            tile_values,
            160,
            lambda name: self._on_tile(int(name)),
        )
        tile_menu.set(str(self._prefs.tile))
        tile_menu.grid(row=row, column=0, sticky="w", pady=(10, 0))
        row += 1

        # Overlap
        row = self._section(row, "settings_overlap", "settings_overlap_help")
        overlap_values = [str(v) for v in OVERLAP_OPTIONS]
        overlap_menu = self._menu(
            overlap_values,
            160,
            lambda name: self._on_overlap(int(name)),
        )
        overlap_menu.set(str(self._prefs.overlap))
        overlap_menu.grid(row=row, column=0, sticky="w", pady=(10, 0))
        row += 1

        # Output format
        row = self._section(row, "settings_output_format", "settings_output_format_help")
        fmt_labels = [self._t(f"format_{f}") for f in OUTPUT_FORMATS]
        fmt_menu = self._menu(
            fmt_labels,
            220,
            lambda name: self._on_output_format(OUTPUT_FORMATS[fmt_labels.index(name)]),
        )
        fmt_menu.set(self._t(f"format_{self._prefs.output_format}"))
        fmt_menu.grid(row=row, column=0, sticky="w", pady=(10, 0))
        row += 1

        # Quality
        row = self._section(row, "settings_output_quality", "settings_output_quality_help")
        quality_row = ctk.CTkFrame(self, fg_color="transparent")
        quality_row.grid(row=row, column=0, sticky="ew", pady=(10, 24))
        quality_row.grid_columnconfigure(0, weight=1)
        self._quality_label = self._make_label(
            quality_row,
            f"{self._prefs.output_quality}%",
            size=12,
            color=COLORS["secondary"],
            anchor="e",
        )
        self._quality_label.grid(row=0, column=1, sticky="e", padx=(8, 0))
        slider = ctk.CTkSlider(
            quality_row,
            from_=1,
            to=100,
            number_of_steps=99,
            command=self._on_quality_slide,
            progress_color=COLORS["blue"],
            button_color=COLORS["blue"],
            button_hover_color=COLORS["blue_pressed"],
            fg_color=COLORS["progress_track"],
        )
        slider.set(self._prefs.output_quality)
        slider.grid(row=0, column=0, sticky="ew")

    def _on_quality_slide(self, value: float) -> None:
        q = int(round(value))
        self._quality_label.configure(text=f"{q}%")
        self._on_output_quality(q)
