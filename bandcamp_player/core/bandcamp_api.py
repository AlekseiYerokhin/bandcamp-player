import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import ClassVar

_RETRYABLE_STATUS = (429, 500, 502, 503, 504)


class BandcampAPIError(Exception):
    pass


class BandcampAPI:
    BASE_URL = "https://bandcamp.com/api"
    HEADERS: ClassVar[dict[str, str]] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
    }
    MIN_INTERVAL = 0.3
    _last_call_time = 0.0
    _throttle_lock = threading.Lock()

    def _get(self, path, params=None):
        url = self.BASE_URL + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        return self._open(urllib.request.Request(url, headers=self.HEADERS))

    def _post(self, path, payload):
        url = self.BASE_URL + path
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={**self.HEADERS, "Content-Type": "application/json"},
            method="POST",
        )
        return self._open(req)

    def _throttle(self):
        with self._throttle_lock:
            elapsed = time.monotonic() - type(self)._last_call_time
            if elapsed < self.MIN_INTERVAL:
                time.sleep(self.MIN_INTERVAL - elapsed)
            type(self)._last_call_time = time.monotonic()

    def _open(self, req, timeout=15):
        self._throttle()
        data = self._request_once(req, timeout, attempts=1)
        if isinstance(data, dict) and data.get("error"):
            raise BandcampAPIError(data.get("error_message") or "API error")
        return data

    def _request_once(self, req, timeout, attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in _RETRYABLE_STATUS and attempts > 0:
                time.sleep(1.0)
                return self._request_once(req, timeout, attempts - 1)
            raise BandcampAPIError(f"HTTP {e.code}") from e
        except urllib.error.URLError as e:
            raise BandcampAPIError(f"Network error: {e.reason}") from e
        except (OSError, ValueError) as e:
            raise BandcampAPIError(str(e)) from e

    def tralbum_details(self, band_id, tralbum_id, tralbum_type="a"):
        code = "t" if tralbum_type in ("t", "track") else "a"
        data = self._get("/mobile/25/tralbum_details", {
            "band_id": band_id,
            "tralbum_id": tralbum_id,
            "tralbum_type": code,
        })
        return self._normalize_tralbum(data)

    def band_details(self, band_id):
        data = self._post("/mobile/24/band_details", {"band_id": band_id})
        return self._normalize_band(data)

    def search(self, query, include_tracks=False):
        data = self._get("/fuzzysearch/2/app_autocomplete", {
            "q": query,
            "param_with_locations": "true",
        })
        return self._normalize_search(data, include_tracks)

    @staticmethod
    def image_url(art_id, suffix="10"):
        if not art_id:
            return ""
        return f"https://f4.bcbits.com/img/a{art_id}_{suffix}.jpg"

    @staticmethod
    def _band_image_url(image_id, suffix="10"):
        if not image_id:
            return ""
        return f"https://f4.bcbits.com/img/{int(image_id):010d}_{suffix}.jpg"

    @staticmethod
    def _normalize_tralbum(data):
        tracks = []
        for track in data.get("tracks", []):
            stream = (track.get("streaming_url") or {}).get("mp3-128", "")
            tracks.append({
                "title": track.get("title", "Unknown"),
                "track_num": track.get("track_num", 0),
                "duration": int((track.get("duration") or 0) * 1000),
                "url": stream,
            })
        return {
            "title": data.get("title", "Unknown Album"),
            "artist": data.get("tralbum_artist") or data.get("band_name", "Unknown Artist"),
            "art_id": data.get("art_id"),
            "bandcamp_url": data.get("bandcamp_url", ""),
            "tracks": tracks,
        }

    @staticmethod
    def _normalize_band(data):
        albums = []
        for item in data.get("discography", []):
            albums.append({
                "title": item.get("title", "Unknown"),
                "item_id": item.get("item_id"),
                "item_type": item.get("item_type", "album"),
                "image_url": BandcampAPI.image_url(item.get("art_id"), "9"),
                "release_date": item.get("release_date", ""),
            })
        return {
            "name": data.get("name", "Unknown Artist"),
            "bio": data.get("bio", ""),
            "image_url": BandcampAPI._band_image_url(data.get("bio_image_id")),
            "albums": albums,
        }

    @staticmethod
    def _normalize_search(data, include_tracks):
        results = []
        for item in data.get("results", []):
            item_type = item.get("type")
            if item_type == "b":
                results.append({
                    "type": "artist",
                    "title": item.get("name", ""),
                    "artist": item.get("location") or "",
                    "band_id": item.get("id"),
                    "id": item.get("id"),
                    "image_url": item.get("img", ""),
                    "url": item.get("url", ""),
                })
            elif item_type == "a":
                results.append({
                    "type": "album",
                    "title": item.get("name", ""),
                    "artist": item.get("band_name") or "",
                    "band_id": item.get("band_id"),
                    "id": item.get("id"),
                    "image_url": BandcampAPI.image_url(item.get("art_id"), "9"),
                    "url": item.get("url", ""),
                })
            elif item_type == "t" and include_tracks:
                results.append({
                    "type": "track",
                    "title": item.get("name", ""),
                    "artist": item.get("band_name") or "",
                    "band_id": item.get("band_id"),
                    "id": item.get("id"),
                    "image_url": BandcampAPI.image_url(item.get("art_id"), "9"),
                    "url": item.get("url", ""),
                })
        return results
