#!/usr/bin/env bash
# Quality Up'S — macOS .app + professional .dmg builder
# Developer: https://github.com/emirttac
#
# Usage (from repo root):
#   chmod +x packaging/macos/build_dmg.sh
#   ./packaging/macos/build_dmg.sh
#
# Output:
#   dist/Quality Up'S.app
#   dist/QualityUps-1.0-macOS.dmg

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

APP_NAME="Quality Up'S"
APP_VERSION="1.0"
DMG_NAME="QualityUps-${APP_VERSION}-macOS"
VOLUME_NAME="Quality Up'S"
BUNDLE_ID="com.emirttac.qualityups"

PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "Missing .venv. Create it with ./run.command first (Tk-enabled Python)."
  exit 1
fi

echo "=== Quality Up'S macOS build ==="
echo

echo "[1/4] Installing build dependencies…"
"$PY" -m pip install -r requirements-build.txt

echo "[2/4] PyInstaller .app bundle…"
rm -rf "dist/${APP_NAME}.app" "dist/${APP_NAME}" "build/pyinstaller"
"$PY" -m PyInstaller packaging/quality_ups.spec \
  --noconfirm --clean \
  --distpath dist \
  --workpath build/pyinstaller

APP_PATH="dist/${APP_NAME}.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "PyInstaller did not produce ${APP_PATH}"
  exit 1
fi

# Ensure Finder shows the custom icon
if [[ -f "assets/icon/app.icns" ]]; then
  mkdir -p "${APP_PATH}/Contents/Resources"
  cp -f "assets/icon/app.icns" "${APP_PATH}/Contents/Resources/icon.icns" || true
fi

# Ad-hoc sign so Gatekeeper is less angry on local machines (optional identity override)
if command -v codesign >/dev/null 2>&1; then
  echo "[3/4] Ad-hoc code signing…"
  codesign --force --deep --sign - \
    --identifier "${BUNDLE_ID}" \
    "$APP_PATH" || echo "Warning: codesign failed (continuing)."
else
  echo "[3/4] codesign not available — skipping."
fi

echo "[4/4] Building professional DMG…"
STAGING="$(mktemp -d "${TMPDIR:-/tmp}/qualityups-dmg.XXXXXX")"
cleanup() { rm -rf "$STAGING"; }
trap cleanup EXIT

cp -R "$APP_PATH" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

# Volume icon (optional)
if [[ -f "assets/icon/app.icns" ]]; then
  cp "assets/icon/app.icns" "$STAGING/.VolumeIcon.icns"
fi

# Hidden DS_Store layout via AppleScript when possible; fall back to plain DMG
mkdir -p dist
DMG_RW="${ROOT}/dist/${DMG_NAME}-rw.dmg"
DMG_FINAL="${ROOT}/dist/${DMG_NAME}.dmg"
rm -f "$DMG_RW" "$DMG_FINAL"

hdiutil create \
  -volname "$VOLUME_NAME" \
  -srcfolder "$STAGING" \
  -ov -format UDRW \
  -fs HFS+ \
  "$DMG_RW"

DEVICE="$(hdiutil attach -readwrite -noverify -noautoopen "$DMG_RW" | awk 'END{print $1}')"
MOUNT="/Volumes/${VOLUME_NAME}"

# Wait for mount
for _ in $(seq 1 30); do
  [[ -d "$MOUNT" ]] && break
  sleep 0.2
done

if [[ -d "$MOUNT" ]]; then
  # Set custom icon bit when VolumeIcon exists
  if [[ -f "$MOUNT/.VolumeIcon.icns" ]]; then
    SetFile -a C "$MOUNT" 2>/dev/null || true
  fi

  # Arrange icons in Finder (Applications + app side by side)
  osascript <<EOF || true
tell application "Finder"
  tell disk "$VOLUME_NAME"
    open
    set current view of container window to icon view
    set toolbar visible of container window to false
    set statusbar visible of container window to false
    set the bounds of container window to {120, 120, 780, 520}
    set viewOptions to the icon view options of container window
    set arrangement of viewOptions to not arranged
    set icon size of viewOptions to 128
    set position of item "${APP_NAME}.app" of container window to {160, 220}
    set position of item "Applications" of container window to {480, 220}
    update without registering applications
    delay 1
    close
  end tell
end tell
EOF

  sync
  hdiutil detach "$DEVICE" -force || hdiutil detach "$MOUNT" -force || true
else
  echo "Warning: could not mount RW image for layout; compressing as-is."
  hdiutil detach "$DEVICE" -force 2>/dev/null || true
fi

hdiutil convert "$DMG_RW" -format ULMO -imagekey zlib-level=9 -o "$DMG_FINAL"
rm -f "$DMG_RW"

# Internet-enable for older Finder download behavior
hdiutil internet-enable -yes "$DMG_FINAL" 2>/dev/null || true

echo
echo "Done."
echo "  App:  ${APP_PATH}"
echo "  DMG:  ${DMG_FINAL}"
echo
echo "Notarization (optional, Apple Developer ID):"
echo "  xcrun notarytool submit \"${DMG_FINAL}\" --keychain-profile <PROFILE> --wait"
echo "  xcrun stapler staple \"${DMG_FINAL}\""
