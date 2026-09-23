# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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