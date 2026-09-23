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

- `bandcamp_player/core/bandcamp_api.py` — **pure, Qt-free** API client. All HTTP lives
  here. Functions: `search`, `band_details`, `tralbum_details`; normalizers
  return plain dicts. Raises `BandcampAPIError` on any failure.
- `bandcamp_player/core/engine.py` — `QObject`; runs each API call on a daemon thread and
  emits `search_results_ready` / `album_data_ready` / `artist_data_ready`
  (`bool, payload`). Never block the GUI thread here.
- `bandcamp_player/core/controller.py` — wires UI events to engine/player; owns navigation
  state (`_last_view`, `_current_band_id`, `_tracks`).
- `bandcamp_player/core/player.py` — thin libVLC wrapper.
- `bandcamp_player/ui/main_window.py` — the entire UI (cards, sections, tracklist, player bar).

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
- **`build/` is shared by setuptools and the AppImage script.** `pip wheel`
  stages into `build/lib`; if a stale `build/lib` survives a package rename,
  it leaks the old package into the wheel. Clean `build/lib` (or run the
  AppImage script, which wipes `build/`) before building a wheel.
- **Stream URLs play without a Referer** (mobile `streaming_url` is
  referer-tolerant). No referer logic is needed.
- **Search has no pagination** (autocomplete, ≤50 best-match results) — there is
  no "Load More".

## Testing

- `tests/` uses `pytest`. `bandcamp_api.py` is tested with monkeypatched
  `urllib` responses — **no live network calls in tests**.
- When changing API parsing, update the fixtures in the tests accordingly.

## Git workflow

- **Every task gets its own branch.** Start each task on a fresh branch (e.g.
  `feat/my-feature`); `main` stays releasable and is never worked on directly.
- **Keep a branch to ~3 commits.** Each branch holds a small, focused set of
  separate commits — no more than ~3. If a task would need more, split it into
  separate tasks (each on its own branch). Don't bundle unrelated changes into
  one commit.
- **Agree the scope first.** Before starting, confirm with the user what the
  task is and roughly how it breaks down, so the branch stays focused.
- **Ask before every commit.** Never commit without the user's explicit
  approval — even when the change is small or the task was previously agreed.
- Don't commit build artifacts (`build/`, `dist/`, `*.AppImage`).
