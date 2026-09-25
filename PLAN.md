# PLAN.md — Roadmap & Feature Vision

This document captures the planned direction of the project. It describes the
next headline feature, why it matters, and the technical work it requires.

## The idea: user-composed playlists

The app today is a *browser + player*: you search, open an artist, open an
album, and stream it. The natural next step — the feature that turns a player
into a *music app* — is letting the user **compose playlists from any track —
or entire album — they find**.

Users can collect individual tracks or whole albums into named playlists,
reorder them, and play them back with the existing next/prev/auto-advance
behavior. "Add album" is a one-click shortcut that resolves the album once and
stages all its tracks as individual playlist entries, reusing the same stable
track-reference mechanism. This is the single biggest step in usefulness and
the clearest extension of the current architecture.

## Why this is the right next feature

- It **reuses the entire existing pipeline** — streaming, playback state,
  auto-advance, now-playing highlight all already exist for albums.
- It **changes the product shape**: from "look things up" to "build something
  of your own" — which is what keeps users returning.
- It is **well-scoped**: the hard 20% (streaming, queue, persistence) is mostly
  understood; the remaining work is storage + UI + a playback-queue refactor.

## Technical feasibility — PROVEN

The one thing that determines whether playlists are viable is how stream URLs
behave. Verified against the live API:

- `tralbum_details` returns a signed `streaming_url.mp3-128`
  (`https://bandcamp.com/stream_redirect?enc=mp3-128&track_id=...&ts=...&token=...`).
- The `ts`/`token` is **time-limited, not per-request**. Two fetches seconds
  apart return the *same* URL; the token expires after a window (~hours).
- Therefore a playlist **cannot store permanent URLs** — but it **can store
  stable references** and re-resolve a fresh URL at play time:

```python
# saved to playlist (stable, permanent):
{"band_id": 4199458029, "tralbum_id": 609345249, "track_num": 1}

# at play time (fresh, time-limited):
api.tralbum_details(band_id, tralbum_id, "a")["tracks"][track_num - 1]["url"]
```

This re-resolution is the exact code path already used for normal playback, so
playlist playback is **proven viable** with no new streaming work.

## Design

### Storage
Local JSON file in the app data dir (XDG: `~/.local/share/bandcamp-player/`),
keyed by playlist name:

```json
{
  "My Playlist": [
    {"band_id": 4199458029, "tralbum_id": 609345249, "track_num": 1,
     "title": "Chamber", "artist": "Chamber", "album": "A Love To Kill For"}
  ]
}
```

Display metadata is stored alongside the IDs so playlists render without
network calls; stream URLs are never persisted.

### Playback queue
Generalize the current album-scoped queue (`_tracks`, `_current_track_index`
in the controller) into a queue that can be populated from an album **or** a
playlist. Auto-advance, next/prev, and now-playing highlight carry over as-is.

### Fresh stream resolution
Resolve the stream URL at play time (per the pattern above), with a small
in-memory per-album cache since tokens are valid for a window.

### UI
- A **Playlists** view: list of playlists + track detail.
- **Add to playlist** from the album tracklist (a `+` button or context menu;
  creates/selects a playlist) — per track, or **add the whole album** at once.
- **Add album** from an album's header/actions and from album cards in search
  results / artist discography: resolves the album once and stages all tracks.
- Create, rename, delete playlists; remove/reorder tracks within one.

## Scope / phases

- **Phase 1 — core (v1)**
  - Persistence: JSON file (load/save/atomic write).
  - Playlist data model + controller queue refactor.
  - Album tracklist → "Add to playlist" (per track or whole album).
  - Playlist view: play, next/prev, auto-advance, highlight.
- **Phase 2 — management**
  - Create/rename/delete playlists; remove tracks; reorder (drag & drop).
  - Search results → "add track" / "add album" (re-enables track-type
    results, previously deferred).
  - Artist discography album cards → "add album".
- **Phase 3 — stretch**
  - Shuffle; import/export (e.g., M3U with track references).
  - Duplicate/move between playlists; "currently playing" indicator.

## Risks & considerations

- **Bandcamp terms.** The feature streams the same public preview streams the
  official player serves; there is no DRM circumvention. Requests are already
  throttled. This is fine for a personal project; review Bandcamp's terms if
  the app is ever distributed widely.
- **Token expiry** is handled by the resolve-fresh-at-play design (no storage
  of signed URLs).
- **Scope control.** The playback-queue refactor is the main risk surface; it
  is isolated in `controller.py` and covered by the existing headless
  end-to-end verification pattern.

## Windows installer — future track

### Why
The app is already cross-platform by construction (Qt Widgets + python-vlc +
stdlib `urllib`), so Windows is a low-cost second platform. A native installer
(`Bandcamp-Player-Setup-x86_64.exe`) opens the app to a much larger audience,
and the AppImage already runs under WSL2 as a fallback.

### Takeaways from the Linux/AppImage work
- **The data layer ports as-is.** `BandcampAPI` is Qt-free and uses only stdlib
  `urllib`; the Fastly/urllib lesson applies unchanged on Windows.
- **Playback is the only real porting surface.** python-vlc loads `libvlc` via
  ctypes on every platform; the work is locating/bundling `libvlc.dll` +
  `libvlccore.dll` and a trimmed VLC plugin set — the same plugin-selection
  logic already proven in the AppImage.
- **Bundler hygiene transfers.** Keep PyInstaller from shadowing the bundled
  VLC libs, and keep VLC startup quiet (`--no-plugins-cache`,
  `--ignore-config`) — the `_STRIP_BINARIES` lesson, on Windows.
- **The UI is already cross-platform.** QtWidgets + `QNetworkAccessManager`
  (images) + tray icon need no platform-specific code.

### Steps
1. **Verify from source on Windows.** `pip install .`, then
   `python main.py` with system VLC installed (audio via WASAPI/DirectSound).
2. **Decide VLC bundling.** (a) require system VLC — smallest installer, but
   users must install VLC; or (b) bundle `libvlc.dll` + a trimmed plugin set —
   best UX, larger installer.
3. **Windows PyInstaller spec.** Produce `bandcamp-player.exe` (onedir
   recommended: faster startup, easier VLC bundling); handle
   `PYTHON_VLC_LIB_PATH`.
4. **Wrap in an installer.** Inno Setup (free, scriptable) or NSIS →
   `Bandcamp-Player-Setup-x86_64.exe` with desktop / start-menu shortcuts.
5. **CI.** Add a `windows-latest` GitHub Actions job building and attaching the
   installer to releases — parallel to the existing AppImage job.
6. **Test.** Clean install, audio on WASAPI, tray icon, fonts; update the
   README with Windows install instructions.

### Scope note
Independent of the playlist feature — a parallel track that doesn't change the
core architecture.

## Open questions

- JSON file vs SQLite for larger playlists?
- Should playlists be exportable (M3U) — Phase 3 or later?
- Add-to-playlist UX: context menu vs `+` button per row?
- Cloud sync is deliberately **out of scope** (needs accounts + server); local
  playlists only, at least initially.