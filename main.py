#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

# Allow running without installing the package.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quality_ups.host import prepare_host
from quality_ups.core.heif_support import ensure_heif_support

prepare_host()
ensure_heif_support()

from quality_ups.ui.app import run


if __name__ == "__main__":
    run()
