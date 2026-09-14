# AGENTS.md

Project guide for AI coding agents working in this repository.

## What this is

A desktop **Bandcamp player**: PySide6 (Qt6) UI + libVLC playback + Bandcamp's
undocumented mobile JSON API. Shipped as a single-file AppImage.

The data layer talks to `bandcamp.com/api/mobile/*` directly over HTTPS.

## Commands

```bash
# Run from source (needs libvlc installed)
source venv/bin/activate
python main.py

# Tests (no network; HTTP is mocked)
pytest

# Lint
ruff check .

# Build the AppImage -> build/Bandcamp-Player-x86_64.AppImage
./packaging/build-appimage.sh
```

`venv/` is the local virtualenv; use `venv/bin/python` and `venv/bin/pip` if
not activated.

## Architecture

```
main.py -> Controller -> BandcampEngine -> BandcampAPI  (data, worker threads)
                      -> AudioPlayer     -> libVLC      (playback)
         MainWindow  <- Qt signals
```

- `src/core/bandcamp_api.py` — **pure, Qt-free** API client. All HTTP lives
  here. Functions: `search`, `band_details`, `tralbum_details`; normalizers
  return plain dicts. Raises `BandcampAPIError` on any failure.
- `src/core/engine.py` — `QObject`; runs each API call on a daemon thread and
  emits `search_results_ready` / `album_data_ready` / `artist_data_ready`
  (`bool, payload`). Never block the GUI thread here.
- `src/core/controller.py` — wires UI events to engine/player; owns navigation
  state (`_last_view`, `_current_band_id`, `_tracks`).
- `src/core/player.py` — thin libVLC wrapper.
- `src/ui/main_window.py` — the entire UI (cards, sections, tracklist, player bar).

## Conventions

- UI text/labels are English. Keep the dark theme in `_apply_styles`.
- Data is identified by **IDs** (`band_id`, `tralbum_id`), not URLs.
- Album art URL: `https://f4.bcbits.com/img/a{art_id}_{size}.jpg`.
  Band image URL: `https://f4.bcbits.com/img/{image_id:010d}_{size}.jpg`.
- Keep `bandcamp_api.py` free of Qt imports so it stays unit-testable.

## Gotchas

- **Use `urllib`, not `requests`.** Bandcamp's Fastly bot detection challenges
  urllib3 (`requests`) even on the JSON API; stdlib `urllib` works with the
  same headers. Do not "modernize" this to `requests`.
- **Album search images.** The autocomplete `img` field is malformed for
  albums (`{id}_3.jpg` → 404). Build album/track images from `art_id` instead.
  Artist `img` is fine as-is.
- **VLC plugin set is intentionally trimmed** in `packaging/build-appimage.sh`.
  If audio stops working, the missing plugin is usually a demuxer — MP3 needs
  `demux/libes_plugin.so` + `packetizer/libpacketizer_mpegaudio_plugin.so`.
- **`bandcamp.spec` `_STRIP_BINARIES`** removes bundled `libvlc`/FFmpeg/
  fontconfig copies so they don't shadow the AppImage's own libraries. Don't
  remove it without testing playback in the built AppImage.
- **Stream URLs play without a Referer** (mobile `streaming_url` is
  referer-tolerant). No referer logic is needed.
- **Search has no pagination** (autocomplete, ≤50 best-match results) — there is
  no "Load More".

## Testing

- `tests/` uses `pytest`. `bandcamp_api.py` is tested with monkeypatched
  `urllib` responses — **no live network calls in tests**.
- When changing API parsing, update the fixtures in the tests accordingly.

## Branching

Feature work happens on branches (e.g. `feat/my-feature`); `main` stays
releasable. Don't commit build artifacts (`build/`, `dist/`, `*.AppImage`).
