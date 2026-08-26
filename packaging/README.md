# Packaging Quality Up'S

Release artifacts are built with **PyInstaller** and wrapped in platform installers.

| Platform | Script | Output |
|----------|--------|--------|
| Windows | `packaging/windows/build.bat` or `build.ps1` | `dist/installer/QualityUps-Setup-1.0.exe` (Inno Setup) |
| macOS | `packaging/macos/build_dmg.sh` | `dist/QualityUps-1.0-macOS.dmg` |

Developer: [emirttac](https://github.com/emirttac) · License: PolyForm Noncommercial 1.0.0

## Prerequisites

### Both
- Project `.venv` with `requirements.txt` installed (`run.bat` / `run.command`)
- Build deps: `pip install -r requirements-build.txt` (scripts do this automatically)

### Windows
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) (for the Setup EXE)
- 64-bit Windows 10+

### macOS
- macOS 12+
- Xcode Command Line Tools (`xcode-select --install`) for `hdiutil` / optional `codesign`
- Tk-enabled Python (python.org) for the venv used to freeze the app

## Windows — Inno Setup installer

```bat
packaging\windows\build.bat
```

Or:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1
```

Steps performed:
1. Install PyInstaller into `.venv`
2. Freeze `main.py` → `dist\QualityUps\` (onedir, windowed, version resource + icon)
3. Compile `packaging\windows\QualityUps.iss` → `dist\installer\QualityUps-Setup-1.0.exe`

Installer features:
- Modern wizard, LZMA2 ultra compression
- Multi-language (EN / TR / DE / FR / IT / RU)
- Optional desktop icon
- Start Menu shortcuts + uninstaller
- Publisher / URL metadata pointing to https://github.com/emirttac
- Non-commercial license page from repo `LICENSE`

Manual compile only (after PyInstaller has produced `dist\QualityUps\`):

```bat
"%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" packaging\windows\QualityUps.iss
```

Do not compile `QualityUps.iss` in the Inno Setup IDE until step 2 has created `dist\QualityUps\QualityUps.exe`. Compiling earlier fails on the `[Files]` `Source` line (`dist\QualityUps\*`). The repo folder name `Quality Up'S` also contains an apostrophe; the script and build wrappers resolve an 8.3 short path (`QUALIT~1`) so Inno Setup does not treat `dist` as Pascal code.

## macOS — DMG

```bash
chmod +x packaging/macos/build_dmg.sh
./packaging/macos/build_dmg.sh
```

Steps performed:
1. Install PyInstaller
2. Freeze → `dist/Quality Up'S.app` (bundle id `com.emirttac.qualityups`)
3. Ad-hoc `codesign` (local Gatekeeper friendliness)
4. Create a professional DMG with Applications symlink + Finder icon layout
5. Compress to `dist/QualityUps-1.0-macOS.dmg`

Optional notarization (Apple Developer Program):

```bash
xcrun notarytool submit dist/QualityUps-1.0-macOS.dmg --keychain-profile <PROFILE> --wait
xcrun stapler staple dist/QualityUps-1.0-macOS.dmg
```

## Notes

- Real-ESRGAN `.onnx` weights under `assets/models/` are bundled when present (large).
- Frozen apps resolve assets via `sys._MEIPASS` (`quality_ups.config.APP_DIR`).
- Do not ship a development `.venv` inside the installer; only the PyInstaller output.
