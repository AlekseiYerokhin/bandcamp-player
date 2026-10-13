# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-12

### Changed

- **Fixed Bandcamp access** — Bandcamp's Fastly CDN now gates the mobile JSON API
  by TLS fingerprint (JA3/JA4). Switched the API transport from stdlib `urllib`
  to `curl_cffi` with Chrome TLS impersonation, restoring search, artist, and
  album playback without an embedded browser.
- **Playback survives browsing** — the playing queue is a separate
  `PlaybackQueue`; opening another album no longer hijacks what's playing.
  Stale stream-token failures re-fetch the album and retry once.
- **Real navigation stack** — Back now returns correctly from album/artist
  pages instead of relying on a single `_last_view` flag.
- **MPRIS completeness** — 64-bit positions (SetPosition past ~35 min no longer
  overflows), dynamic CanGoNext/CanGoPrevious, `Rate`/`Seeked` support, and the
  command dispatch refactored to a handler map.
- Better in-app feedback — loading/no-result placeholders, non-streamable
  tracks disabled, click-to-seek on the progress bar, volume-icon mute,
  keyboard-accessible cards.
- Engineering cleanup — thread-pooled engine, split UI modules, `QPixmapCache`
  for covers, timeout retries, single dependency source in `pyproject.toml`.

### Added

- Contract tests on recorded real Bandcamp API responses
- CI hardening — coverage gate, pip cache, reusable AppImage build workflow,
  pinned appimagetool with sha256 verification, live-API smoke test in the
  bundled AppImage
- Branch protection on `main` (required status checks, no direct pushes)

## [0.1.0] - 2026-09-23

First release.

### Added

- Bandcamp search (artists, albums, tracks) via the mobile JSON API — no
  embedded browser, no scraping
- Artist pages with bio, photo, and full discography
- Album / track pages with tracklist, durations, and cover art
- Streaming playback with play/pause, next/previous, millisecond-accurate
  seek, volume, and elapsed/total time
- Auto-advance through an album, driven by libVLC end-of-track events
- MPRIS integration — system media keys and desktop playback controls (Linux)
- Back navigation that remembers whether you came from search or an artist page
- Keyboard shortcuts, system tray support, and persisted settings
- Dark, native-feeling Qt theme
- Visible errors — failures show in a status bar and are written to a log
- Single-file AppImage — no installation, no system Python required

### Changed

- Rewrote the data layer from QtWebEngine DOM scraping to Bandcamp's
  undocumented mobile JSON API (AppImage: 183 MB → 65 MB, several times
  faster fetches)
- Moved from a polling timer to libVLC events for track-end detection and
  error reporting

### Security

- MIT license, © Aleksei Yerokhin

[0.1.0]: https://github.com/AlekseiYerokhin/bandcamp-player/releases/tag/v0.1.0