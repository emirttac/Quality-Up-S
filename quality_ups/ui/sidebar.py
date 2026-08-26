from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk

from quality_ups.ui.icons import nav_icon
from quality_ups.ui.theme import COLORS

NAV_ITEMS = (
    ("home", "home", "nav_home"),
    ("settings", "settings", "nav_settings"),
    ("about", "info", "nav_about"),
)

PageCallback = Callable[[str], None]
TranslateFn = Callable[[str], str]


class IconSidebar(ctk.CTkFrame):
    """Narrow icon-only sidebar. Labels live in tooltips for accessibility."""

    WIDTH = 72

    def __init__(
        self,
        master: Any,
        *,
        on_select: PageCallback,
        translate: TranslateFn,
    ) -> None:
        super().__init__(master, fg_color=COLORS["surface"], width=self.WIDTH, corner_radius=0)
        self._on_select = on_select
        self._translate = translate
        self._active = "home"
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._tips: dict[str, str] = {}
        self._tip_window: ctk.CTkToplevel | None = None
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

    def _build(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, pady=(16, 8))
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, pady=(8, 16))

        groups = {
            "home": top,
            "settings": bottom,
            "about": bottom,
        }
        for key, icon, label_key in NAV_ITEMS:
            parent = groups[key]
            btn = ctk.CTkButton(
                parent,
                text="",
                image=nav_icon(icon, COLORS["secondary"]),
                width=44,
                height=44,
                corner_radius=10,
                fg_color="transparent",
                hover_color=COLORS["fill"],
                command=lambda k=key: self._on_select(k),
            )
            btn.pack(pady=4)
            btn.bind("<Enter>", lambda e, k=key: self._show_tip(k, e))
            btn.bind("<Leave>", lambda _e: self._hide_tip())
            self._buttons[key] = btn
            self._tips[key] = label_key
        self.set_active("home")

    def set_language(self, translate: TranslateFn) -> None:
        self._translate = translate

    def set_active(self, key: str) -> None:
        self._active = key
        for item, icon, _label in NAV_ITEMS:
            selected = item == key
            color = COLORS["blue"] if selected else COLORS["secondary"]
            self._buttons[item].configure(
                image=nav_icon(icon, color),
                fg_color=COLORS["blue_fill"] if selected else "transparent",
                hover_color=COLORS["blue_fill"] if selected else COLORS["fill"],
            )

    def _show_tip(self, key: str, event: Any) -> None:
        self._hide_tip()
        text = self._translate(self._tips[key])
        tip = ctk.CTkToplevel(self)
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        label = ctk.CTkLabel(
            tip,
            text=text,
            fg_color=COLORS["label"],
            text_color=COLORS["surface"],
            corner_radius=6,
        )
        label.pack(padx=8, pady=4)
        tip.update_idletasks()
        x = self.winfo_rootx() + self.WIDTH + 8
        y = event.widget.winfo_rooty() + 8
        tip.geometry(f"+{x}+{y}")
        self._tip_window = tip

    def _hide_tip(self) -> None:
        if self._tip_window is not None:
            self._tip_window.destroy()
            self._tip_window = None
