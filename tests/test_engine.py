import time

import pytest

pytest.importorskip("PySide6.QtCore")


def test_stale_search_response_is_dropped(monkeypatch):
    from PySide6.QtCore import QCoreApplication

    from core.engine import BandcampEngine

    app = QCoreApplication.instance() or QCoreApplication([])
    engine = BandcampEngine()
    emitted = []

    def fake_search(query):
        if query == "slow":
            time.sleep(0.3)
            return [{"type": "album", "title": "slow"}]
        return [{"type": "album", "title": "fast"}]

    monkeypatch.setattr(engine._api, "search", fake_search)
    engine.search_results_ready.connect(lambda ok, data: emitted.append((ok, data)))

    engine.search("slow")  # id 1, completes last
    engine.search("fast")  # id 2, completes first

    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)

    assert emitted == [(True, [{"type": "album", "title": "fast"}])]
