# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Quality Up'S (Windows + macOS).

Run from the repository root:
  pyinstaller packaging/quality_ups.spec --noconfirm --clean
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs

# Spec lives in packaging/ — project root is one level up.
ROOT = Path(SPECPATH).resolve().parent
ASSETS = ROOT / "assets"

APP_NAME = "Quality Up'S"
APP_VERSION = "1.0"
BUNDLE_ID = "com.emirttac.qualityups"

datas = [
    (str(ASSETS / "models"), "assets/models"),
    (str(ASSETS / "icon"), "assets/icon"),
    (str(ASSETS / "social"), "assets/social"),
]
binaries = []
hiddenimports = [
    "PIL._tkinter_finder",
    "tkinterdnd2",
    "customtkinter",
    "cv2",
    "onnxruntime",
    "pillow_heif",
    "darkdetect",
    "psutil",
]

for pkg in ("customtkinter", "tkinterdnd2", "onnxruntime", "pillow_heif"):
    try:
        pkg_datas, pkg_bins, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_bins
        hiddenimports += pkg_hidden
    except Exception:
        pass

try:
    datas += collect_data_files("cv2")
except Exception:
    pass

try:
    binaries += collect_dynamic_libs("onnxruntime")
except Exception:
    pass

icon_win = ASSETS / "icon" / "app.ico"
icon_mac = ASSETS / "icon" / "app.icns"
version_info = ROOT / "packaging" / "windows" / "version_info.txt"

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=True,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(icon_mac) if icon_mac.exists() else None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=APP_NAME,
    )
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=str(icon_mac) if icon_mac.exists() else None,
        bundle_identifier=BUNDLE_ID,
        version=APP_VERSION,
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
            "CFBundleIdentifier": BUNDLE_ID,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "12.0",
            "NSHumanReadableCopyright": (
                "Copyright © 2026 Emir Tuğra Ataç (https://github.com/emirttac)"
            ),
            "CFBundleDocumentTypes": [
                {
                    "CFBundleTypeName": "Image",
                    "CFBundleTypeRole": "Viewer",
                    "LSHandlerRank": "Alternate",
                    "LSItemContentTypes": [
                        "public.png",
                        "public.jpeg",
                        "public.tiff",
                        "public.heic",
                        "org.webmproject.webp",
                    ],
                }
            ],
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="QualityUps",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(icon_win) if icon_win.exists() else None,
        version=str(version_info) if version_info.exists() else None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="QualityUps",
    )
