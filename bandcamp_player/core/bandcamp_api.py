import json
import threading
import time
from typing import ClassVar

from curl_cffi import requests as curl_requests

_RETRYABLE_STATUS = (429, 500, 502, 503, 504)


class BandcampAPIError(Exception):
    pass


class BandcampAPI:
    BASE_URL = "https://bandcamp.com/api"
    HEADERS: ClassVar[dict[str, str]] = {
        "Accept": "application/json",
    }
    MIN_INTERVAL = 0.3
    _last_call_time = 0.0
    _throttle_lock = threading.Lock()

    def _session(self):
        # Chrome TLS impersonation is required: Bandcamp's Fastly CDN bounces
        # plain TLS clients (JA3/JA4 fingerprint gate) with a JS challenge.
        return curl_requests.Session(impersonate="chrome")

    def _get(self, path, params=None):
        url = self.BASE_URL + path
        with self._session() as session:
            return self._open(session.get, url, params=params)

    def _post(self, path, payload):
        url = self.BASE_URL + path
        with self._session() as session:
            return self._open(session.post, url, json=payload)

    def _throttle(self):
        with self._throttle_lock:
            elapsed = time.monotonic() - type(self)._last_call_time
            if elapsed < self.MIN_INTERVAL:
                time.sleep(self.MIN_INTERVAL - elapsed)
            type(self)._last_call_time = time.monotonic()

    def _open(self, send, url, **kwargs):
        self._throttle()
        data = self._request_once(send, url, kwargs, attempts=1)
        if isinstance(data, dict) and data.get("error"):
            raise BandcampAPIError(data.get("error_message") or "API error")
        return data

    def _request_once(self, send, url, kwargs, attempts):
        try:
            resp = send(url, headers=self.HEADERS, timeout=15, **kwargs)
        except curl_requests.RequestsError as e:
            raise BandcampAPIError(f"Network error: {e}") from e
        if resp.status_code in _RETRYABLE_STATUS and attempts > 0:
            time.sleep(1.0)
            return self._request_once(send, url, kwargs, attempts - 1)
        try:
            return json.loads(resp.text)
        except ValueError as e:
            snippet = (resp.text or "")[:200] or "<empty body>"
            raise BandcampAPIError(
                f"Non-JSON response from {url}: "
                f"HTTP {resp.status_code}, {resp.headers.get('Content-Type')}, "
                f"body: {snippet!r}"
            ) from e

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
