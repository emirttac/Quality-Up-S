from __future__ import annotations

import webbrowser
from typing import Any, Callable

import customtkinter as ctk

from quality_ups.config import APP_NAME, APP_VERSION, SOCIAL_LINKS
from quality_ups.ui.icons import social_icon
from quality_ups.ui.theme import COLORS, FONT, FONT_DISPLAY

TranslateFn = Callable[..., str]


class AboutPage(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        *,
        translate: TranslateFn,
        on_check_updates: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._t = translate
        self._on_check_updates = on_check_updates
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _label(self, master: Any, text: str, **kwargs: Any) -> ctk.CTkLabel:
        size = kwargs.pop("size", 13)
        weight = kwargs.pop("weight", "normal")
        color = kwargs.pop("color", COLORS["label"])
        display = kwargs.pop("display", False)
        variable = kwargs.pop("variable", None)
        return ctk.CTkLabel(
            master,
            text=text,
            textvariable=variable,
            font=ctk.CTkFont(family=FONT_DISPLAY if display else FONT, size=size, weight=weight),
            text_color=color,
            **kwargs,
        )

    def _build(self) -> None:
        self._label(self, self._t("about_title"), size=22, weight="bold", display=True, anchor="w").grid(
            row=0, column=0, sticky="w"
        )
        self._label(self, APP_NAME, size=15, weight="bold", anchor="w").grid(
            row=1, column=0, sticky="w", pady=(18, 0)
        )
        self.version = self._label(
            self,
            self._t("about_version", version=APP_VERSION),
            size=13,
            color=COLORS["secondary"],
            anchor="w",
        )
        self.version.grid(row=2, column=0, sticky="w", pady=(4, 0))
        self._label(
            self,
            self._t("about_tagline"),
            size=13,
            color=COLORS["secondary"],
            anchor="w",
        ).grid(row=3, column=0, sticky="w", pady=(6, 0))

        self.check_btn = ctk.CTkButton(
            self,
            text=self._t("check_updates"),
            width=200,
            height=32,
            corner_radius=6,
            fg_color=COLORS["blue"],
            hover_color=COLORS["blue_pressed"],
            text_color=COLORS["surface"],
            font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
            command=self._on_check_updates,
        )
        self.check_btn.grid(row=4, column=0, sticky="w", pady=(16, 0))

        self.status = self._label(self, "", size=12, color=COLORS["secondary"], anchor="w", wraplength=520)
        self.status.grid(row=5, column=0, sticky="w", pady=(8, 0))

        self._label(self, self._t("social_title"), size=13, weight="bold", anchor="w").grid(
            row=6, column=0, sticky="w", pady=(32, 10)
        )

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=7, column=0, sticky="w")
        self._social_images: list[ctk.CTkImage] = []
        for key, name, url in SOCIAL_LINKS:
            icon = social_icon(key, 32)
            self._social_images.append(icon)
            chip = ctk.CTkFrame(row, fg_color=COLORS["surface"], corner_radius=10, border_width=1, border_color=COLORS["separator"])
            chip.pack(side="left", padx=(0, 10))
            inner = ctk.CTkFrame(chip, fg_color="transparent")
            inner.pack(padx=10, pady=8)
            logo = ctk.CTkLabel(inner, text="", image=icon)
            logo.pack(side="left")
            caption = ctk.CTkLabel(
                inner,
                text=name,
                font=ctk.CTkFont(family=FONT, size=12),
                text_color=COLORS["label"],
            )
            caption.pack(side="left", padx=(8, 2))
            for widget in (chip, inner, logo, caption):
                widget.bind("<Button-1>", lambda _e, link=url: webbrowser.open(link))

    def set_status(self, text: str, *, checking: bool = False, alert: bool = False) -> None:
        color = COLORS["orange"] if alert else COLORS["secondary"]
        self.status.configure(text=text, text_color=color)
        self.check_btn.configure(state="disabled" if checking else "normal")
