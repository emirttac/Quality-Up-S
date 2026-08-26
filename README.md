# Quality Up'S

**Local AI image enhancement for desktop.**

Quality Up'S upscales and sharpens images entirely on your machine. Nothing is uploaded: models, processing, and output stay local. The app ships with a fast **FSRCNN** path (OpenCV DNN Super-Resolution) and an optional high-quality **Real-ESRGAN** path (ONNX Runtime), wrapped in a CustomTkinter UI with batch queue, themes, and multi-language support.

| | |
|---|---|
| **Version** | 1.0 |
| **Platforms** | macOS 12+ · Windows 10+ |
| **UI languages** | Türkçe · English · Deutsch · Français · Italiano · 中文 · Русский · Română |
| **Scales** | 2× · 4× |
| **Models** | FSRCNN (bundled) · Real-ESRGAN ONNX (optional weights) |
| **Output** | PNG · JPEG · WebP |
| **License** | [PolyForm Noncommercial 1.0.0](LICENSE) (no commercial use) |
| **Developer** | [emirttac](https://github.com/emirttac) |
| **Repository** | [emirttac/Quality-Up-S](https://github.com/emirttac/Quality-Up-S) |

<img width="1802" height="1460" alt="image" src="https://github.com/user-attachments/assets/edfe7194-e762-43e8-88ce-e82e729766de" />

## Table of contents

1. [What it does](#what-it-does)
2. [Features](#features)
3. [Models](#models)
4. [Architecture](#architecture)
5. [Processing pipeline](#processing-pipeline)
6. [Requirements](#requirements)
7. [Installation](#installation)
8. [Building installers](#building-installers)
9. [Usage](#usage)
10. [Settings reference](#settings-reference)
11. [Supported formats](#supported-formats)
12. [Project layout](#project-layout)
13. [Preferences](#preferences)
14. [Developer configuration](#developer-configuration)
15. [Platform notes](#platform-notes)
16. [Troubleshooting](#troubleshooting)
17. [Privacy](#privacy)
18. [Known limitations](#known-limitations)
19. [Acknowledgments](#acknowledgments)
20. [Author & links](#author--links)
21. [License](#license)

---

## What it does

1. **System gate** — probes CPU, GPU, cores, RAM, and OS; scores whether the machine is comfortable for local tiled super-resolution. Weaker hardware can still continue.
2. **Engine warm-up** — preloads FSRCNN 2× / 4× in the background and runs a short probe so **Enhance** unlocks only when the engine is ready.
3. **Queue** — drop or pick images; process one file at a time with live progress and ETA.
4. **Upscale** — overlapping tiles keep large photos stable; choose model, scale, tile size, and overlap.
5. **Export** — write PNG (alpha-safe), JPEG, or WebP with adjustable quality.
6. **Compare** — open a Before / After slider for the last successful result.

Typical flow:

```text
Drop images → choose Model + Scale + Format → Enhance → collect {name}_{scale}x.{ext}
```

Default output folder: `Desktop/QualityUps Output`.

---

## Features

### Enhancement

| Feature | Detail |
|---------|--------|
| **FSRCNN (Fast)** | Bundled `.pb` weights; OpenCV `dnn_superres`; low latency |
| **Real-ESRGAN (High quality)** | Optional ONNX weights; better text, line art, and faces |
| **Scales** | 2× and 4× |
| **Tiling** | Configurable tile size (256 / 512 / 1024) and overlap (8 / 16 / 32) |
| **Alpha / RGBA** | Transparency preserved; alpha resized with nearest-neighbor |
| **Batch queue** | Multi-file queue, per-file progress, overall ETA |
| **Cancel** | Stop mid-queue or mid-tile |
| **Output formats** | PNG, JPEG, WebP; JPEG/WebP quality 1–100% |

### Application

| Feature | Detail |
|---------|--------|
| **System gate** | Hardware score before the main UI |
| **Engine status** | Ready / may run slowly / unavailable |
| **Navigation** | Icon sidebar — Home · Settings · About |
| **Drag-and-drop** | Via `tkinterdnd2` |
| **Themes** | System · Light · Dark |
| **i18n** | Eight languages with natural phrasing (not stub lookups) |
| **GPU preference** | Automatic, detected adapters, or CPU only |
| **Acceleration** | OpenCV CPU (macOS-safe); ONNX CoreML / DirectML / CUDA when available |
| **Before / After** | Interactive reveal slider after a successful run |
| **Resizable window** | Flexible layout with HiDPI-friendly minimum size |
| **Updates** | Optional GitHub release/tag check from About |
| **Icons** | Platform app icon under `assets/icon/` |

### Privacy

- No cloud API for enhancement.
- Network use is limited to an optional, user-triggered GitHub update check and social links you open yourself.

---

## Models

| ID | UI label | Backend | Weights | When to use |
|----|----------|---------|---------|-------------|
| `fsrcnn` | FSRCNN (Fast) | OpenCV DNN SuperRes | `FSRCNN_x2.pb`, `FSRCNN_x4.pb` (required, in-repo) | Everyday photos, speed, batch jobs |
| `realesrgan` | Real-ESRGAN (High quality) | ONNX Runtime | `realesrgan-x2.onnx`, `realesrgan-x4.onnx` (optional) | Text, illustrations, faces, detail recovery |

### Real-ESRGAN setup

Place ONNX files in `assets/models/`:

```text
assets/models/realesrgan-x2.onnx
assets/models/realesrgan-x4.onnx
```

Expected tensor layout: **NCHW RGB float32** in `[0, 1]` (dynamic spatial size). Without these files the app still runs on FSRCNN; choosing Real-ESRGAN shows a clear prompt.

Also ensure `onnxruntime` is installed (included in `requirements.txt`). On Apple Silicon, CoreML EP is preferred automatically; on Windows, DirectML/CUDA providers are used when present.

See [`assets/models/README.md`](assets/models/README.md) for weight notes.

---

## Architecture

```text
┌──────────────┐     ┌────────────────┐     ┌──────────────────┐
│  SystemGate  │ ──► │ EngineRuntime  │ ──► │  Home / Queue    │
│  capability  │     │ preload + probe│     │ Enhance / Cancel │
└──────────────┘     └────────────────┘     └────────┬─────────┘
                                                     │
                                                     ▼
                                            ┌──────────────────┐
                                            │ SuperResolution  │
                                            │ Engine (tiled)   │
                                            │  ├─ FSRCNN       │
                                            │  └─ Real-ESRGAN  │
                                            └────────┬─────────┘
                                                     │
                                                     ▼
                                            Output folder
                                            name_2x.png|jpg|webp
```

| Layer | Module | Role |
|--------|--------|------|
| Entry | `main.py`, `host.py` | Path bootstrap, Windows DPI / AppUserModelID |
| UI shell | `quality_ups/ui/app.py` | Window, navigation, home queue, prefs wiring |
| Gate | `ui/gate.py` + `core/capability.py` | Hardware probe and continue path |
| Settings / About | `ui/settings_page.py`, `ui/about_page.py` | Preferences and update check |
| Compare | `ui/compare.py` | Before / After slider window |
| Theme | `ui/theme.py` | Light/dark palettes + CustomTkinter appearance |
| Queue | `core/processor.py` | Background one-file worker, cancel, callbacks |
| Engine | `core/engine.py` | Tile loop, RGBA merge, output naming |
| I/O | `core/image_io.py` | Load (keep alpha), save PNG/JPEG/WebP |
| Backends | `core/backends/` | Pluggable FSRCNN / Real-ESRGAN |
| Models | `core/models.py` | Catalog, paths, availability checks |
| Compute | `core/gpu.py` | Device discovery; OpenCV target + ONNX EP hints |
| Prefs | `core/prefs.py` | JSON persistence with normalization |
| i18n | `i18n/catalog.py` | Eight-language string catalog |
| Updates | `core/updates.py` | GitHub latest release / tags + OS notifications |

Backends are selected by `model_id`. The engine never hard-codes a single network; `create_backend()` builds the active implementation and the tile loop calls `upsample(patch, scale)`.

---

## Processing pipeline

Per file:

1. **Load** with Pillow — keep alpha when present (`RGBA` / palette transparency).
2. **Split** into BGR color + optional alpha.
3. **Tile** the BGR plane with configurable size and overlap.
4. **Upsample** each tile via the active backend (FSRCNN or Real-ESRGAN).
5. **Crop** overlap margins and stitch into the full-resolution BGR image.
6. **Scale alpha** with nearest-neighbor (hard edges stay crisp).
7. **Merge** BGR(+A) and **save** as PNG / JPEG / WebP.

JPEG flattens transparency onto white. WebP can keep alpha when the encoder supports it (OpenCV, with Pillow fallback).

Output name pattern: `{stem}_{scale}x.{ext}`  
Examples: `photo_2x.png`, `logo_4x.webp`.

---

## Requirements

### System

- **macOS** 12+ or **Windows** 10+
- Comfortable gate threshold (approximate): ≥ 4 CPU cores, ≥ 8 GB RAM, ≥ ~2 GB free — weaker machines can still continue
- Desktop environment with working **Tk** (CustomTkinter)

### Software

- **Python 3.10+** (developed and tested with 3.14 venv on macOS)
- `pip` + virtual environment
- **Tk-enabled Python**
  - macOS: prefer the [python.org](https://www.python.org/downloads/) installer (includes Tcl/Tk). Homebrew `python@3.x` often **lacks** `_tkinter` and will fail at startup.
  - Windows: python.org installer with **tcl/tk** enabled

### Python packages

See [`requirements.txt`](requirements.txt):

| Package | Purpose |
|---------|---------|
| `customtkinter` (≥5.2.2, &lt;6) | Application UI |
| `tkinterdnd2` | Drag-and-drop |
| `opencv-contrib-python` | `dnn_superres` / FSRCNN (**contrib** build required) |
| `Pillow` | Image load/save helpers, icons |
| `pillow-heif` | HEIC / HEIF decode for Pillow |
| `numpy` | Arrays and tiling |
| `psutil` | Memory / core probes for the gate |
| `onnxruntime` | Real-ESRGAN inference (CoreML / DirectML / CUDA / CPU) |

> Use **`opencv-contrib-python`**, not `opencv-python`. Super-resolution lives in the contrib package.  
> Do not install both OpenCV wheels in the same environment.

---

## Installation

Clone or copy the project, then create a virtual environment in the project root.

### macOS

```bash
cd "/path/to/Quality Up'S"

# Important: use a Tk-enabled Python (python.org), e.g.:
/usr/local/bin/python3 -m venv .venv

.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

Launch:

```bash
./run.command
# or
.venv/bin/python3 main.py
```

### Windows

Double-click **`run.bat`**. On first launch it will:

1. Create `.venv` if missing  
2. Install everything in `requirements.txt` (including `numpy`)  
3. Start the app  

Manual setup (optional):

```bat
cd path\to\Quality Up'S
py -3 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
run.bat
```

> Do **not** copy a macOS `.venv` folder to Windows. Virtual environments are platform-specific — delete `.venv` on Windows and let `run.bat` recreate it.

---

## Building installers

Release builds freeze the app with **PyInstaller**, then wrap it in a platform installer. Full details: [`packaging/README.md`](packaging/README.md).

| Platform | Build command | Artifact |
|----------|---------------|----------|
| **Windows** | `packaging\windows\build.bat` | `dist\installer\QualityUps-Setup-1.0.exe` (Inno Setup 6) |
| **macOS** | `./packaging/macos/build_dmg.sh` | `dist/QualityUps-1.0-macOS.dmg` |

### Windows (Inno Setup)

1. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php).
2. Ensure `.venv` has runtime deps (`run.bat` once).
3. Run `packaging\windows\build.bat` (or `build.ps1`).

The installer uses a modern wizard, LZMA2 compression, multi-language UI, Start Menu / optional desktop shortcuts, uninstaller, and the non-commercial license page. Publisher metadata points to [emirttac](https://github.com/emirttac).

### macOS (DMG)

```bash
chmod +x packaging/macos/build_dmg.sh
./packaging/macos/build_dmg.sh
```

Produces `Quality Up'S.app` plus a compressed DMG with an **Applications** symlink and Finder icon layout. The script applies an ad-hoc `codesign`. For distribution outside your Mac, notarize with an Apple Developer ID (commands in `packaging/README.md`).

### Optional GPU packages

| Platform | Optional package | Notes |
|----------|------------------|--------|
| Windows (DX12) | `onnxruntime-directml` | Alternative to stock `onnxruntime` |
| NVIDIA | `onnxruntime-gpu` | CUDA EP when drivers/CUDA match |
| macOS Apple Silicon | stock `onnxruntime` | CoreML EP is usually enough |

Only one ONNX Runtime wheel should be installed at a time.

---

## Usage

1. Start the app and wait for the **system check**; press Continue.
2. Wait until the engine status shows **Ready** (or Ready — may run slowly).
3. Drop images onto the home zone, or click to choose files.
4. Pick a **model** (FSRCNN or Real-ESRGAN) and **scale** (2× / 4×).
5. Choose **output format** (PNG / JPEG / WebP). Quality for JPEG/WebP is set in Settings.
6. Confirm the **Save to** folder.
7. Press **Enhance**. Use **Cancel** to stop; **Compare** opens Before / After for the last success.
8. Collect `{name}_{scale}x.*` files from the output folder.

### Keyboard

| Shortcut | Action |
|----------|--------|
| `⌘ ,` (macOS) / `Ctrl ,` (Windows) | Open Settings |

---

## Settings reference

| Setting | Options | Effect |
|---------|---------|--------|
| **Language** | 8 locales | Rewrites the full UI |
| **Appearance** | System / Light / Dark | CustomTkinter mode + app palette |
| **Active GPU** | Auto / adapters / CPU | Device preference for compute |
| **Tile size** | 256 · 512 · 1024 | Larger = faster on roomy VRAM/RAM; smaller = safer on limited memory |
| **Tile overlap** | 8 · 16 · 32 | Higher reduces seam artifacts; costs a little time |
| **Output format** | PNG · JPEG · WebP | Also selectable on Home |
| **JPEG / WebP quality** | 1–100% | Ignored for PNG |

About page: version, **Check for updates**, social links.

---

## Supported formats

### Input

| Format | Extensions | Notes |
|--------|------------|--------|
| PNG | `.png` | Alpha preserved |
| JPEG | `.jpg`, `.jpeg` | Fully supported |
| WebP | `.webp` | Alpha preserved when present |
| TIFF | `.tif`, `.tiff` | Fully supported |
| BMP | `.bmp` | Accepted |
| HEIC / HEIF | `.heic`, `.heif` | Decoded via `pillow-heif` (required) |

### Output

| Format | Alpha | Quality slider |
|--------|-------|----------------|
| PNG | Yes | N/A |
| JPEG | Flattened on white | Yes |
| WebP | Yes when encoder allows | Yes |

---

## Project layout

```text
Quality Up'S/
├── main.py                      # Entry: host prep + UI
├── run.command                  # macOS launcher (dev)
├── run.bat / setup.bat          # Windows launcher / setup (dev)
├── requirements.txt
├── requirements-build.txt       # PyInstaller
├── LICENSE                      # PolyForm Noncommercial 1.0.0
├── README.md
├── packaging/
│   ├── quality_ups.spec         # PyInstaller (Win + macOS)
│   ├── README.md
│   ├── windows/
│   │   ├── QualityUps.iss       # Inno Setup 6 script
│   │   ├── version_info.txt     # EXE file version resource
│   │   ├── build.bat
│   │   └── build.ps1
│   └── macos/
│       └── build_dmg.sh         # .app + professional DMG
├── assets/
│   ├── models/                  # FSRCNN (+ optional Real-ESRGAN ONNX)
│   ├── icon/                    # .png / .icns / .ico
│   └── social/
└── quality_ups/
    ├── config.py
    ├── host.py
    ├── core/
    ├── i18n/
    └── ui/
```

---

## Preferences

Stored as JSON (created on first save):

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/Quality Up'S/prefs.json` |
| Windows | `%AppData%\Roaming\Quality Up'S\prefs.json` |
| Other | `~/.config/quality-ups/prefs.json` |

| Key | Type | Default | Notes |
|-----|------|---------|--------|
| `language` | string | auto-detect → `tr` fallback | Must be a catalog code |
| `gpu_id` | string | `"auto"` | `"cpu"` or `"gpu:N"` |
| `theme` | string | `"system"` | `system` · `light` · `dark` |
| `model_id` | string | `"fsrcnn"` | `fsrcnn` · `realesrgan` |
| `tile` | int | `512` | `256` · `512` · `1024` |
| `overlap` | int | `16` | `8` · `16` · `32` |
| `output_format` | string | `"png"` | `png` · `jpeg` · `webp` |
| `output_quality` | int | `95` | Clamped to 1–100 |

Unknown or invalid values are normalized on load/save. Older prefs files with only `language` / `gpu_id` remain compatible.

---

## Developer configuration

Constants live in [`quality_ups/config.py`](quality_ups/config.py):

| Constant | Meaning |
|----------|---------|
| `APP_NAME` / `APP_VERSION` | `Quality Up'S` / `1.0` |
| `APP_PUBLISHER` / `APP_PUBLISHER_URL` | Emir Tuğra Ataç · https://github.com/emirttac |
| `SCALE_OPTIONS` | `(2, 4)` |
| `TILE_OPTIONS` / `OVERLAP_OPTIONS` | UI + prefs allow-lists |
| `DEFAULT_TILE` / `DEFAULT_OVERLAP` | `512` / `16` |
| `MODEL_FILES` / `REALESRGAN_FILES` | Scale → filename maps |
| `MODEL_IDS` | `("fsrcnn", "realesrgan")` |
| `OUTPUT_FORMATS` | `png` · `jpeg` · `webp` |
| `THEME_OPTIONS` | `system` · `light` · `dark` |
| `WINDOW_*` | Default and minimum window sizes |
| `GITHUB_REPO` | `emirttac/Quality-Up-S` |
| `SUPPORTED_EXTENSIONS` | Intake allow-list |

### Extending models

1. Add weight filenames to `config.py`.
2. Register a `ModelInfo` in `core/models.py`.
3. Implement a backend under `core/backends/` with `set_device`, `preload`, `upsample`.
4. Wire `create_backend()` in `core/backends/__init__.py`.
5. Add i18n keys (`model_<id>`) and include the id in `MODEL_IDS`.

### macOS OpenCV note

On Darwin, OpenCV DNN SuperRes is forced to **CPU**. OpenCL + Tk commonly deadlocks during warm-up on modern macOS. Real-ESRGAN still benefits from **CoreML** via ONNX Runtime.

---

## Platform notes

| Topic | macOS | Windows |
|--------|--------|---------|
| Launcher | `run.command` | `run.bat` |
| Fonts | SF Pro Text / Display | Segoe UI |
| Icons | `assets/icon/` (`.png`, `.icns`) | `.png`, `.ico` |
| Notifications | Notification Center (`osascript`) | Balloon tip (PowerShell) |
| Host setup | — | DPI awareness + App User Model ID |
| FSRCNN accel | CPU (by design) | OpenCL when available, else CPU |
| Real-ESRGAN accel | CoreML → CPU | DirectML / CUDA → CPU |

Linux code paths exist for prefs, fonts, and GPU probing, but there is **no** first-class Linux launcher in this tree.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `No module named 'numpy'` (Windows) | Empty/broken `.venv`, or macOS venv copied over | Delete `.venv`, run `run.bat` again (auto-installs deps) |
| Stuck on **Hazırlanıyor… / Getting ready…** | OpenCL + Tk deadlock (older builds) | Use current release (CPU DNN on macOS); restart app |
| `CTkLabel object is not callable` | Name clash on Settings scroll frame | Use current `settings_page.py` |
| Real-ESRGAN unavailable | Missing ONNX files or `onnxruntime` | Install deps; place `realesrgan-x*.onnx` in `assets/models/` |
| `Missing model files: FSRCNN_…` | Weights deleted from `assets/models/` | Restore bundled `.pb` files |
| Out of memory / crashes on huge images | Tile too large | Settings → tile **256** |
| Seam lines between tiles | Overlap too small | Settings → overlap **32** |
| Update check fails | No network or no GitHub releases/tags | Expected until releases exist; app still works offline |
| HEIC won’t open | `pillow-heif` missing or opener not registered | `pip install -r requirements.txt` (includes `pillow-heif`) |

---

## Privacy

- Enhancement never leaves the device.
- No analytics SDK is bundled.
- The only outbound HTTP call in-app is the optional **Check for updates** request to GitHub’s API, initiated by the user.
- Social buttons open URLs in the system browser only when clicked.

---

## Known limitations

- **Signed / notarized macOS builds** require an Apple Developer ID; the DMG script only ad-hoc signs by default.
- **Update checker** needs GitHub **releases or tags** newer than `APP_VERSION`; until then, the check may report failure or “up to date” depending on API response.
- **HEIC** requires `pillow-heif` (bundled in `requirements.txt` and registered at startup).
- **No automated test suite** in-repo today.
- **Large ONNX weights** (~64 MB each) increase installer size when bundled; omit them from `assets/models/` if you want a smaller FSRCNN-only package.
- Redistributed binaries must still respect **third-party** licenses (OpenCV, ONNX Runtime, etc.) in addition to this project’s non-commercial license.

---

## Acknowledgments

- **OpenCV** — DNN Super-Resolution (`dnn_superres`) and the FSRCNN model interface
- **Real-ESRGAN** (xinntao et al.) — high-quality restoration architecture; ONNX exports used optionally
- **ONNX Runtime** — portable inference (CoreML / DirectML / CUDA / CPU)
- **CustomTkinter** — modern Tk-based UI
- **tkinterdnd2** — drag-and-drop
- **Pillow** · **NumPy** · **psutil**

FSRCNN weights ship as `FSRCNN_x2.pb` / `FSRCNN_x4.pb` under `assets/models/`. Real-ESRGAN ONNX files are optional and documented alongside them.

---

## Author & links

- **Developer:** [emirttac](https://github.com/emirttac)
- GitHub (repo): [emirttac/Quality-Up-S](https://github.com/emirttac/Quality-Up-S)
- YouTube: [@BiAltTab](https://www.youtube.com/@BiAltTab)
- Instagram: [emirttac](https://www.instagram.com/emirttac/)
- LinkedIn: [Emir Tuğra Ataç](https://www.linkedin.com/in/emir-tu%C4%9Fra-ata%C3%A7-88b591394/)

---

## License

This project is licensed under the **PolyForm Noncommercial License 1.0.0** — personal, educational, and other non-commercial use only. Commercial use is not permitted without a separate written license from the copyright holder. See [`LICENSE`](LICENSE).

Copyright © 2026 Emir Tuğra Ataç ([https://github.com/emirttac](https://github.com/emirttac)).

Third-party dependencies (OpenCV, ONNX Runtime, CustomTkinter, and others) remain under their own licenses.
