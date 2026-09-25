import time

import pytest

pytest.importorskip("PySide6.QtCore")


def test_stale_search_response_is_dropped(monkeypatch):
    from PySide6.QtCore import QCoreApplication

    from bandcamp_player.core.engine import BandcampEngine

    app = QCoreApplication.instance() or QCoreApplication([])
    engine = BandcampEngine()
    emitted = []

    def fake_search(query, include_tracks=False):
        if query == "slow":
            time.sleep(0.3)
            return [{"type": "album", "title": "slow"}]
        return [{"type": "album", "title": "fast"}]

    monkeypatch.setattr(engine._api, "search", fake_search)
    engine.search_results_ready.connect(lambda ok, data, err: emitted.append((ok, data)))

    engine.search("slow")  # id 1, completes last
    engine.search("fast")  # id 2, completes first

    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)

    assert emitted == [(True, [{"type": "album", "title": "fast"}])]


def test_stale_album_response_is_dropped(monkeypatch):
    from PySide6.QtCore import QCoreApplication

    from bandcamp_player.core.engine import BandcampEngine

    app = QCoreApplication.instance() or QCoreApplication([])
    engine = BandcampEngine()
    emitted = []

    def fake_tralbum(band_id, tralbum_id, tralbum_type="a"):
        if tralbum_id == 1:
            time.sleep(0.3)
            return {"title": "slow"}
        return {"title": "fast"}

    monkeypatch.setattr(engine._api, "tralbum_details", fake_tralbum)
    engine.album_data_ready.connect(lambda ok, data, err: emitted.append((ok, data.get("title"))))

    engine.get_album_data(1, 1, "a")  # id 1, completes last
    engine.get_album_data(1, 2, "a")  # id 2, completes first

    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)

    assert emitted == [(True, "fast")]


def test_search_failure_carries_error_message(monkeypatch):
    from PySide6.QtCore import QCoreApplication

    from bandcamp_player.core.bandcamp_api import BandcampAPIError
    from bandcamp_player.core.engine import BandcampEngine

    app = QCoreApplication.instance() or QCoreApplication([])
    engine = BandcampEngine()
    emitted = []

    def fail_search(query, include_tracks=False):
        raise BandcampAPIError("HTTP 503")

    monkeypatch.setattr(engine._api, "search", fail_search)
    engine.search_results_ready.connect(lambda ok, data, err: emitted.append((ok, data, err)))

    engine.search("x")

    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)

    assert emitted == [(False, [], "HTTP 503")]
