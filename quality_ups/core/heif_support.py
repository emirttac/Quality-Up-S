from __future__ import annotations

_registered = False


def ensure_heif_support() -> None:
    """Register Pillow HEIF/HEIC openers once (required dependency: pillow-heif)."""
    global _registered
    if _registered:
        return
    from pillow_heif import register_heif_opener

    register_heif_opener()
    _registered = True
