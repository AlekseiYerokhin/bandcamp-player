import json

import pytest
from curl_cffi import requests as curl_requests

import bandcamp_player.core.bandcamp_api as bc


class _FakeResponse:
    def __init__(self, payload):
        self.status_code = 200
        self.headers = {"Content-Type": "application/json"}
        self.text = "" if payload is None else (json.dumps(payload) if not isinstance(payload, str) else payload)

    def json(self):
        return json.loads(self.text)


class _FakeSession:
    def __init__(self, outcomes, capture=None):
        self._outcomes = list(outcomes)
        self._capture = capture
        self._i = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def _next(self):
        outcome = self._outcomes[min(self._i, len(self._outcomes) - 1)]
        self._i += 1
        if callable(outcome):
            outcome = outcome()
        if isinstance(outcome, (dict, str)):
            return _FakeResponse(outcome)
        return outcome

    def get(self, url, **kwargs):
        if self._capture is not None:
            self._capture.append((url, kwargs))
        out = self._next()
        if isinstance(out, Exception):
            raise out
        return out

    def post(self, url, **kwargs):
        return self.get(url, **kwargs)


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(bc.BandcampAPI, "MIN_INTERVAL", 0)
    return bc.BandcampAPI()


def _patch_session(monkeypatch, *outcomes, capture=None):
    fake = _FakeSession(outcomes, capture=capture)
    monkeypatch.setattr(bc.BandcampAPI, "_session", lambda self: fake)
    return fake


def _patch_single(monkeypatch, payload=None, error=None, capture=None):
    def _make():
        if error is not None:
            return error
        return _FakeResponse(payload) if payload is not None else _FakeResponse(None)

    return _patch_session(monkeypatch, _make, capture=capture)


# --- search ---------------------------------------------------------------

def test_search_normalizes_artists_albums_and_filters_tracks(api, monkeypatch):
    payload = {
        "results": [
            {"type": "b", "id": 4199458029, "name": "Chamber",
             "location": "Nashville, Tennessee", "img": "https://f4.bcbits.com/img/0033016061_23.jpg"},
            {"type": "a", "id": 2242839143, "band_id": 4199458029, "band_name": "Chamber",
             "name": "Tears of Joy", "art_id": 4171759085},
            {"type": "t", "id": 891815764, "band_id": 4199458029, "band_name": "Chamber",
             "name": "Chamber", "art_id": 111},
        ]
    }
    _patch_single(monkeypatch, payload)

    results = api.search("Chamber")

    assert [r["type"] for r in results] == ["artist", "album"]  # track filtered out

    artist, album = results
    assert artist["band_id"] == 4199458029 and artist["id"] == 4199458029
    assert artist["artist"] == "Nashville, Tennessee"
    assert album["title"] == "Tears of Joy"
    assert album["band_id"] == 4199458029 and album["id"] == 2242839143
    assert album["image_url"] == "https://f4.bcbits.com/img/a4171759085_9.jpg"


def test_search_handles_missing_location(api, monkeypatch):
    _patch_single(monkeypatch, {"results": [
        {"type": "b", "id": 1, "name": "No Location", "location": None, "img": ""},
    ]})
    results = api.search("x")
    assert results[0]["artist"] == ""


def test_search_can_include_tracks(api, monkeypatch):
    _patch_single(monkeypatch, {"results": [
        {"type": "t", "id": 5, "band_id": 2, "band_name": "B", "name": "T", "art_id": 9},
    ]})
    results = api.search("x", include_tracks=True)
    assert results[0]["type"] == "track"


def test_search_request_url_and_params(api, monkeypatch):
    captured = []
    _patch_single(monkeypatch, {"results": []}, capture=captured)
    api.search("echo chamber")
    url, kwargs = captured[0]
    assert "/fuzzysearch/2/app_autocomplete" in url
    assert kwargs["params"]["q"] == "echo chamber"
    assert kwargs["params"]["param_with_locations"] == "true"


# --- band_details ---------------------------------------------------------

def test_band_details_normalizes_discography(api, monkeypatch):
    payload = {
        "name": "Chamber",
        "bio": "Psychotic Mosh Metal",
        "bio_image_id": 33016061,
        "discography": [
            {"item_id": 2242839143, "item_type": "album", "title": "Tears of Joy",
             "art_id": 4171759085, "release_date": "30 Oct 2024 00:00:00 GMT"},
            {"item_id": 999, "item_type": "track", "title": "Lone Track", "art_id": 7},
        ],
    }
    _patch_single(monkeypatch, payload)

    band = api.band_details(4199458029)

    assert band["name"] == "Chamber"
    assert band["image_url"] == "https://f4.bcbits.com/img/0033016061_10.jpg"
    assert len(band["albums"]) == 2
    first = band["albums"][0]
    assert first["item_id"] == 2242839143
    assert first["item_type"] == "album"
    assert first["image_url"] == "https://f4.bcbits.com/img/a4171759085_9.jpg"


def test_band_details_uses_post(api, monkeypatch):
    captured = []
    _patch_single(monkeypatch, {"name": "x", "discography": []}, capture=captured)
    api.band_details(1)
    url, kwargs = captured[0]
    assert "band_details" in url
    assert kwargs.get("json") == {"band_id": 1}


# --- tralbum_details ------------------------------------------------------

def test_tralbum_details_normalizes_tracks(api, monkeypatch):
    payload = {
        "title": "A Love To Kill For",
        "tralbum_artist": "Chamber",
        "art_id": 4084618854,
        "bandcamp_url": "https://chambertn.bandcamp.com/album/a-love-to-kill-for",
        "tracks": [
            {"title": "Chamber", "track_num": 1, "duration": 70.5,
             "streaming_url": {"mp3-128": "https://bandcamp.com/stream_redirect?enc=mp3-128&track_id=1"}},
            {"title": "No Stream", "track_num": 2, "duration": 10.0, "streaming_url": {}},
        ],
    }
    _patch_single(monkeypatch, payload)

    album = api.tralbum_details(4199458029, 609345249, "a")

    assert album["title"] == "A Love To Kill For"
    assert album["artist"] == "Chamber"
    assert album["art_id"] == 4084618854
    assert len(album["tracks"]) == 2
    assert album["tracks"][0]["duration"] == 70500  # seconds -> ms
    assert album["tracks"][0]["url"].startswith("https://bandcamp.com/stream_redirect")
    assert album["tracks"][1]["url"] == ""


def test_tralbum_details_maps_album_track_type(api, monkeypatch):
    captured = []
    _patch_single(monkeypatch, {"title": "X", "art_id": 1, "bandcamp_url": "", "tracks": []}, capture=captured)

    api.tralbum_details(1, 2, "album")
    assert captured[0][1]["params"]["tralbum_type"] == "a"

    api.tralbum_details(1, 2, "track")
    assert captured[1][1]["params"]["tralbum_type"] == "t"


# --- error handling -------------------------------------------------------

def test_api_error_body_raises(api, monkeypatch):
    _patch_single(monkeypatch, {"error": True, "error_message": "band_id 1 not found"})
    with pytest.raises(bc.BandcampAPIError, match="band_id 1 not found"):
        api.band_details(1)


def _http_response(status, text):
    resp = _FakeResponse(None)
    resp.status_code = status
    resp.headers = {"Content-Type": "text/html"}
    resp.text = text
    return resp


def test_http_error_raises(api, monkeypatch):
    _patch_session(monkeypatch, lambda: _http_response(404, "<html>not found</html>"))
    with pytest.raises(bc.BandcampAPIError, match="HTTP 404"):
        api.search("x")


def test_retry_succeeds_after_transient_5xx(api, monkeypatch):
    monkeypatch.setattr(bc.time, "sleep", lambda s: None)
    _patch_session(monkeypatch, lambda: _http_response(503, "oops"), _FakeResponse({"name": "Chamber", "discography": []}))
    band = api.band_details(1)
    assert band["name"] == "Chamber"


def test_retry_second_failure_raises_bandcamp_api_error(api, monkeypatch):
    monkeypatch.setattr(bc.time, "sleep", lambda s: None)
    _patch_session(monkeypatch, lambda: _http_response(503, "oops"))
    with pytest.raises(bc.BandcampAPIError, match=r"Network error|Non-JSON|HTTP 503"):
        api.band_details(1)


def test_retry_validates_error_body(api, monkeypatch):
    monkeypatch.setattr(bc.time, "sleep", lambda s: None)
    _patch_session(monkeypatch, lambda: _http_response(503, "oops"), {"error": True, "error_message": "still broken"})
    with pytest.raises(bc.BandcampAPIError, match="still broken"):
        api.band_details(1)


def test_network_error_raises(api, monkeypatch):
    _patch_session(monkeypatch, lambda: curl_requests.RequestsError("dns failure"))
    with pytest.raises(bc.BandcampAPIError, match="Network error"):
        api.search("x")


def test_invalid_json_raises(api, monkeypatch):
    _patch_session(monkeypatch, lambda: _http_response(200, "<html>challenge</html>"))
    with pytest.raises(bc.BandcampAPIError, match="Non-JSON response"):
        api.search("x")


# --- image helpers --------------------------------------------------------

def test_image_url_helpers():
    assert bc.BandcampAPI.image_url(4171759085) == "https://f4.bcbits.com/img/a4171759085_10.jpg"
    assert bc.BandcampAPI.image_url(4171759085, "3") == "https://f4.bcbits.com/img/a4171759085_3.jpg"
    assert bc.BandcampAPI.image_url(None) == ""
    assert bc.BandcampAPI._band_image_url(33016061) == "https://f4.bcbits.com/img/0033016061_10.jpg"
    assert bc.BandcampAPI._band_image_url(None) == ""
