"""Contract tests: run recorded real API responses through the normalizers.

The fixtures in tests/fixtures/ are verbatim responses captured from the live
Bandcamp API (search, tralbum_details, band_details). If Bandcamp changes the
response schema, these tests fail — catching drift before users do.
"""

import json
from pathlib import Path

import bandcamp_player.core.bandcamp_api as bc

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name):
    with open(FIXTURES / name) as f:
        return json.load(f)


# --- tralbum_details ------------------------------------------------------

def test_contract_tralbum_details_normalizes_real_response():
    raw = _load("tralbum_details_chamber.json")
    normalized = bc.BandcampAPI._normalize_tralbum(raw)

    assert normalized["title"] == "A Love To Kill For"
    assert normalized["artist"] == "Chamber"
    assert normalized["art_id"] is not None
    assert len(normalized["tracks"]) == len(raw["tracks"])

    for track, raw_track in zip(normalized["tracks"], raw["tracks"], strict=True):
        assert track["title"] == raw_track["title"]
        assert track["track_num"] == raw_track["track_num"]
        # seconds -> milliseconds
        assert track["duration"] == int(raw_track["duration"] * 1000)
        assert track["url"].startswith("https://bandcamp.com/stream_redirect")


def test_contract_tralbum_details_all_tracks_have_streams():
    raw = _load("tralbum_details_chamber.json")
    normalized = bc.BandcampAPI._normalize_tralbum(raw)
    assert all(t["url"] for t in normalized["tracks"])


# --- band_details ---------------------------------------------------------

def test_contract_band_details_normalizes_real_response():
    raw = _load("band_details_chamber.json")
    normalized = bc.BandcampAPI._normalize_band(raw)

    assert normalized["name"] == "Chamber"
    assert normalized["bio"]
    assert normalized["image_url"].startswith("https://f4.bcbits.com/img/")
    assert len(normalized["albums"]) == len(raw["discography"])

    for album in normalized["albums"]:
        assert album["item_id"] is not None
        assert album["item_type"] in ("album", "track")
        assert album["image_url"].startswith("https://f4.bcbits.com/img/")
        assert album["title"]


# --- search ---------------------------------------------------------------

def test_contract_search_normalizes_real_response():
    raw = _load("search_chamber.json")
    normalized = bc.BandcampAPI._normalize_search(raw, include_tracks=True)

    assert len(normalized) == len(raw["results"])
    for item in normalized:
        assert item["type"] in ("album", "artist", "track")
        assert item["title"]
        assert item["band_id"] is not None
        assert item["id"] is not None
        if item["type"] == "album":
            assert item["artist"]
            assert item["image_url"].startswith("https://f4.bcbits.com/img/")


def test_contract_search_result_shape_matches_controller_usage():
    """Search results are consumed by controller._display_search_section."""
    raw = _load("search_chamber.json")
    normalized = bc.BandcampAPI._normalize_search(raw, include_tracks=True)
    for item in normalized:
        assert {"title", "artist", "image_url", "band_id", "id", "type"} <= set(item)
