#!/usr/bin/env bash
set -e
APP=ada
VERSION=${1:-0.1.0}
WORKDIR=$(pwd)
DIST="$WORKDIR/dist"
APPDIR="$WORKDIR/AppDir"

echo "▶ Cleaning previous build" && rm -rf "$DIST" "$APPDIR"
mkdir -p "$DIST" "$APPDIR"

# 1. Build standalone binary with PyInstaller
pyinstaller --onefile -n $APP -c modules/__main__.py \
  --add-data "assistant_config.yml:." \
  --hidden-import sounddevice --hidden-import pvporcupine

# 2. Prepare AppDir structure
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp "dist/$APP" "$APPDIR/usr/bin/"
cp appimage/AppRun "$APPDIR/" && chmod +x "$APPDIR/AppRun"
cp appimage/ada.desktop "$APPDIR/"
cp appimage/icons/ada.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/"

# 3. Build AppImage (needs appimagetool in PATH)
if ! command -v appimagetool &> /dev/null; then
  echo "appimagetool not found – please install from https://github.com/AppImage/AppImageKit/releases" >&2
  exit 1
fi
appimagetool "$APPDIR" "$DIST/AdaAssistant-$VERSION-$(uname -m).AppImage"

echo "✅ Built $DIST/AdaAssistant-$VERSION-$(uname -m).AppImage"