# Migration: QtWebEngine Scraping → Bandcamp Mobile API

## Goal
Replace the QtWebEngine-based HTML/JS scraping with direct calls to Bandcamp's
unofficial mobile API. Drop QtWebEngine entirely → much smaller AppImage
(~183MB → ~45MB), faster loads, less RAM, simpler packaging.

## Status
- [x] Step 1: `BandcampAPI.tralbum_details` (album tracks + stream URLs) — DONE
- [x] Step 2: `band_details` (artist + discography) — DONE
- [x] Step 3: `search` (autocomplete) — DONE
- [x] Step 4: polish (errors/retry, throttle, image_url) — DONE
- [x] Step 5: rewrite `engine.py` (threads + signals, drop WebEngine) — DONE
- [x] Step 6: delete `network.py`, fix imports — DONE
- [x] Step 7: controller ID-based navigation + drop Load More — DONE
- [x] Step 8: `main_window.py` remove Load More button/signal — DONE
- [x] Step 9: packaging (spec + AppRun), rebuild AppImage — DONE (183MB → 65MB)
- [ ] Step 10 (pass 2): track search (`type t`)

## Verified API surface (proven with stdlib `urllib`, no browser)
| Operation | Endpoint | Method |
|---|---|---|
| Search | `/api/fuzzysearch/2/app_autocomplete?q=<q>&param_with_locations=true` | GET |
| Artist page | `/api/mobile/24/band_details` | POST `{"band_id":N}` |
| Album/track | `/api/mobile/25/tralbum_details?band_id=N&tralbum_id=M&tralbum_type=a` | GET |
| Stream | `streaming_url["mp3-128"]` → `bandcamp.com/stream_redirect` | VLC plays it |
| Images | `https://f4.bcbits.com/img/{art_id}_<size>.jpg` | GET |

Facts:
- API endpoints are NOT Fastly-challenged (only HTML pages are).
- **Transport: must use stdlib `urllib`, NOT `requests`/urllib3** — `requests`
  gets a Fastly challenge page (`_fs_ch_st_` cookie); `urllib` returns JSON.
- Discography arrives as structured JSON — no DOM scraping.
- Stream URLs are time-limited but fresh per request.
- **Streams play WITHOUT a Referer** (mobile `streaming_url` is referer-tolerant) →
  drop referer logic in player/controller.

## Incremental implementation steps

### Step 1 — `tralbum_details` (DONE)
- [x] Create `src/core/bandcamp_api.py` with `BandcampAPI` class + urllib transport
- [x] `tralbum_details(band_id, tralbum_id, tralbum_type='a') -> dict`
- [x] Normalized shape: `{title, art_id, bandcamp_url, tracks:[{title, track_num, duration(ms), url}]}`
- [x] Verified: "A Love To Kill For" → 14 tracks, all with stream URLs
- [x] Verified: stream URL plays in VLC with NO referer

### Step 2 — `band_details` (DONE)
- [x] Add `_post` helper to urllib transport
- [x] `band_details(band_id) -> dict` → `{name, bio, image_url, albums:[{title, item_id, item_type, image_url, release_date}]}`
- [x] `image_url(art_id)` + `_band_image_url(image_id)` helpers (fixed double-underscore bug)
- [x] Verified: band 4199458029 → 7 albums with item_id/item_type/art_id; image URLs return 200

### Step 3 — `search` (DONE)
- [x] `search(query, include_tracks=False)` via autocomplete; normalize types `b`/`a`/`t`
- [x] Filter out `type t` by default (pass 2 re-adds); guard None `location`/`band_name`
- [x] Verified: "Chamber" → 36 artists + 14 albums, all with band_id/id/image_url

### Step 4 — polish (DONE)
- [x] `image_url(art_id, suffix='10')` — suffix is the size number (no underscore); band image zero-padded
- [x] `BandcampAPIError` on HTTP errors, network errors, bad JSON, and API `{"error": true}` bodies
- [x] Retry once on 429/5xx with 1s backoff
- [x] Thread-safe ~300ms throttle (class-level lock)

### Step 5 — rewrite `src/core/engine.py`
- [ ] Keep class `BandcampEngine` + signals:
      `search_results_ready(bool, list)`, `album_data_ready(bool, dict)`,
      `artist_data_ready(bool, dict)`, `cleanup()`
- [ ] Drop: QWebEngine page/profile/view, all JS extraction, QTimer delays,
      interceptor import, `login()`/cookie code (dead code — confirmed)
- [ ] Add: daemon `threading.Thread` per request; emit signals from worker
- [ ] New signatures (navigate by IDs):
      `search(query)`, `get_artist_data(band_id)`,
      `get_album_data(band_id, tralbum_id, tralbum_type='a')`

### Step 6 — delete `src/core/network.py`
- [ ] `BandcampRequestInterceptor` is WebEngine-only → remove + fix imports

### Step 7 — update `src/core/controller.py` (DONE)
- [x] Search results carry `band_id` + `id`; card clicks pass IDs
- [x] `_on_result_clicked(band_id, item_id, result_type)`
      - album → `_on_album_clicked(band_id, item_id, 'a')`
      - artist → `_on_artist_clicked(band_id)`
- [x] `_display_album`: `data['title']`, track `url` = `streaming_url['mp3-128']`,
      no referer needed
- [x] `_display_artist_discography`: cards click by `(band_id, item_id, item_type)`
- [x] Remove pagination (`_page_size`, `_search_displayed`, `_on_load_more_clicked`)
- [x] Keep: back-nav history, auto-advance guard
- [x] `player.load_and_play(stream_url)` — dropped the referer param

### Step 8 — update `src/ui/main_window.py` (DONE)
- [x] Remove the "Load More" button + `load_more_requested` signal + `update_section_load_more`
- [x] Remove dead `#loadMoreButton` CSS
- [x] Rest of UI unchanged; app starts cleanly offscreen

### Step 9 — packaging (DONE)
- [x] `bandcamp.spec`: removed WebEngine hiddenimports + all QML/Quick excludes; kept `_STRIP_BINARIES`
- [x] `AppRun`: removed `QT_QPA_PLATFORM_PLUGIN_PATH`
- [x] Rebuilt AppImage: **183MB → 65MB**; zero WebEngine/nss/QtQuick remnants in bundle
- [x] App starts cleanly; full flow verified headless (search → artist → album → `State.Playing`)

### Post-step fix — album search images
- [x] The autocomplete `img` field for albums is malformed (`{id}_3.jpg` → 404);
      build album/track image URLs from `art_id` via `BandcampAPI.image_url()` instead.
      (Artist `img` field is fine as-is.) Verified both return 200.

### Step 10 — pass 2: track search
- [ ] Track results (`type t`) + clicking a track → its page
- [ ] Fuller search endpoint investigation (if autocomplete feels too limited)

## Data mapping (old → new)
| Field | Old | New |
|---|---|---|
| Search title/artist | DOM `.heading`/`.subhead` | `name` / `band_name` or `location` |
| Search image | DOM img | `img` |
| Search click | `url` | `band_id` + `id` |
| Artist name/bio/img | JS `data-band`/`.bio-pic` | `name`/`bio`/`{bio_image_id}` |
| Artist albums | `#music-grid` DOM | `discography[]` (item_id, item_type, art_id) |
| Album title/cover | `TralbumData.current.title`/`art_id` | `title`/`art_id` |
| Track url | `file['mp3-128']` | `streaming_url['mp3-128']` |
| Track duration | `track['duration']` | `track['duration']` (identical) |

## Verification checklist
- [ ] App: Search → Artists + Albums sections populate
- [ ] Click artist → discography grid → click album → tracklist → audio plays
- [ ] Back: search→artist→album→back→artist (unchanged)
- [ ] Auto-advance at track end; single failed track doesn't skip album
- [ ] AppImage rebuild: size drop, clean startup, no WebEngine errors
- [ ] Covers + bio images load via QNetworkAccessManager

## Risks & mitigations
- Unofficial endpoints could change → try/except → graceful empty UI; `main` intact
- Fastly may challenge urllib3 → we use stdlib `urllib` (proven)
- Rate limiting → throttle + retry on 429
- Search is autocomplete (≤50, best-match) → acceptable; UI shows all at once
- Blocking requests → daemon worker threads + Qt queued signals

## Rollback
- `main` untouched. If API unreliable → delete `feat/api-engine`.