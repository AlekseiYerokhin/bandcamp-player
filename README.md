# Bandcamp Player

A desktop music player for [Bandcamp](https://bandcamp.com), built with **PySide6 (Qt6)** and **libVLC**, shipped as a single-file **AppImage**.

Search Bandcamp, browse an artist's discography, open an album's tracklist, and stream it — with a clean, dark, native-feeling UI.

> [!NOTE]
> Bandcamp has no public content API, so this app talks to the same undocumented JSON endpoints the official mobile apps use. No scraping, no embedded browser.

---

## Features

- **Search** artists and albums via Bandcamp's autocomplete API
- **Artist pages** with bio, photo, and full discography
- **Album / track pages** with tracklist, durations, and cover art
- **Streaming playback** with play/pause, next/previous, seek, and volume
- **Auto-advance** through an album, with a guard so a failed track never skips the rest
- **Back navigation** that remembers whether you came from search or an artist page
- **Single-file AppImage** — no installation, no system Python required

## Tech stack

| Layer | Choice |
|---|---|
| UI | PySide6 / Qt6 Widgets |
| Playback | python-vlc (libVLC) |
| Data | Bandcamp mobile JSON API via stdlib `urllib` |
| Packaging | PyInstaller → AppImage |

## Architecture

```
┌──────────────┐   Qt signals   ┌──────────────┐   worker threads   ┌───────────────┐
│  UI (Qt)     │ ─────────────▶ │  Controller  │ ─────────────────▶ │ BandcampEngine│
│ main_window  │ ◀───────────── │              │ ◀───────────────── │  + BandcampAPI│
└──────────────┘                └──────┬───────┘                    └───────┬───────┘
                                       │ playback                            │ HTTPS (JSON)
                                       ▼                                     ▼
                                ┌──────────────┐                    ┌────────────────┐
                                │  AudioPlayer │                    │ bandcamp.com/  │
                                │  (libVLC)    │                    │ api/mobile/... │
                                └──────────────┘                    └────────────────┘
```

- `src/core/bandcamp_api.py` — pure, Qt-free API client (search, artist, album), with retry + throttling
- `src/core/engine.py` — `QObject` that runs API calls on daemon threads and emits Qt signals
- `src/core/controller.py` — wires UI events to the engine and player; owns navigation state
- `src/core/player.py` — libVLC wrapper
- `src/ui/main_window.py` — the entire UI

## Engineering highlights

- **Dropped QtWebEngine for the mobile API.** The first version rendered Bandcamp pages in a headless Chromium and scraped the DOM. It worked, but the AppImage weighed **183 MB** and started slowly. Rewriting the data layer against Bandcamp's mobile JSON API cut the bundle to **65 MB** and made fetches several times faster.
- **`urllib`, not `requests`.** Bandcamp fronts its HTML pages with a Fastly JS challenge. The JSON API endpoints are *not* challenged — but `requests` (urllib3) still trips the bot detection, while stdlib `urllib` sails through with identical headers. The client uses `urllib` accordingly.
- **VLC inside an AppImage.** Bundling `libvlc`, `libvlccore`, and a hand-picked set of plugins (demuxers, decoders, the `es` elementary-stream demux, the `mpegaudio` packetizer, the `gnutls` TLS plugin) so HTTPS streaming works out of the box — no system VLC required.
- **PyInstaller hygiene.** Excluded bundled `libvlc`/FFmpeg/fontconfig copies that shadowed the AppImage's own libraries, and passed `--no-plugins-cache` / `--ignore-config` to libVLC for deterministic, quiet startup.

## Getting started

### Prerequisites

- Python 3.10+
- VLC libraries (`libvlc`)

```bash
# Debian / Ubuntu
sudo apt install libvlc-dev vlc-plugin-base

# Arch
sudo pacman -S vlc

# Fedora
sudo dnf install vlc
```

### Run from source

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Build the AppImage

```bash
pip install pyinstaller
./packaging/build-appimage.sh
# -> build/Bandcamp-Player-x86_64.AppImage
```

The script runs PyInstaller, assembles an AppDir (bundling VLC libraries and plugins), and packages it with `appimagetool`. CI builds and attaches the AppImage to tagged releases.

## Project structure

```
├── main.py                      # entry point
├── src/
│   ├── core/
│   │   ├── bandcamp_api.py      # Qt-free Bandcamp API client
│   │   ├── engine.py            # threaded data engine (Qt signals)
│   │   ├── controller.py        # UI <-> engine/player wiring
│   │   └── player.py            # libVLC audio player
│   └── ui/
│       └── main_window.py       # the UI
├── packaging/
│   ├── AppDir/                  # AppRun + .desktop
│   └── build-appimage.sh        # AppImage build script
├── tests/                       # pytest suite
├── bandcamp.spec                # PyInstaller spec
└── .github/workflows/           # CI + release builds
```

## Testing

```bash
pip install pytest
pytest
```

The API client is pure and Qt-free, so it is unit-tested with mocked HTTP responses — no network required.

## License

[MIT](LICENSE) © Aleksei Yerokhin
