from __future__ import annotations

import sys


def prepare_host() -> None:
    """Windows-only process setup. Must run before the Tk window is created."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("emirttac.QualityUps")
    except Exception:
        pass
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
