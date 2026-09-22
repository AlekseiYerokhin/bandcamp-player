---
name: build-appimage
description: Use when building, rebuilding, or troubleshooting the AppImage packaging — build-appimage.sh, bandcamp.spec, VLC plugin bundling, AppRun, or "why won't audio play in the AppImage". Covers the build flow, verification, and known gotchas.
---

# Build the AppImage

## What this is

The app ships as a single-file AppImage built with PyInstaller + `appimagetool`.
This skill covers the build flow and the packaging-specific gotchas that have
bitten this project before.

## Build

From the repository root, with the venv active:

```bash
./packaging/build-appimage.sh
# -> build/Bandcamp-Player-x86_64.AppImage
```

The script:
1. runs `pyinstaller bandcamp.spec` (bundles the app + Qt + Python)
2. assembles `build/bandcamp-player.AppDir` (AppRun, .desktop, icon,
   `usr/lib/libvlc.so*`, and a **hand-picked** subset of VLC plugins)
3. packages it with `appimagetool`

## Verify

After a build, at minimum:

- `./build/Bandcamp-Player-x86_64.AppImage` starts without errors.
- A track actually plays audio (search → artist → album → play).

## Gotchas

- **VLC plugin set is intentionally trimmed.** If audio stops working in the
  AppImage, the missing plugin is usually a demuxer. MP3 needs
  `demux/libes_plugin.so` + `packetizer/libpacketizer_mpegaudio_plugin.so`
  (this VLC build has no `libmp3_plugin.so`). Keep `codec/libavcodec_plugin.so`
  and `demux/libavformat_plugin.so` as ffmpeg fallbacks.
- **`bandcamp.spec` `_STRIP_BINARIES`** removes bundled `libvlc`/`libvlccore`/
  FFmpeg/fontconfig copies so they don't shadow the AppImage's own libraries in
  `LD_LIBRARY_PATH`. Don't remove it without testing playback in the built
  AppImage.
- **`AppRun`** sets `VLC_PLUGIN_PATH`, `PYTHON_VLC_LIB_PATH`, and fontconfig
  paths. `--no-plugins-cache` and `--ignore-config` are passed to the VLC
  instance in `bandcamp_player/core/player.py` to keep startup fast and quiet.
- **Build artifacts are gitignored** (`build/`, `dist/`, `*.AppImage`).