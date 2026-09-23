"""Controller tests with faked engine/player — no network, no libVLC."""

import pytest
from PySide6.QtCore import QObject, Signal

from bandcamp_player.ui.main_window import MainWindow


class FakeEngine(QObject):
    search_results_ready = Signal(bool, list, str)
    album_data_ready = Signal(bool, dict, str)
    artist_data_ready = Signal(bool, dict, str)

    def __init__(self):
        super().__init__()
        self.searches = []
        self.artist_calls = []
        self.album_calls = []
        self.cleaned_up = False

    def search(self, query):
        self.searches.append(query)

    def get_artist_data(self, band_id):
        self.artist_calls.append(band_id)

    def get_album_data(self, band_id, tralbum_id, tralbum_type="a"):
        self.album_calls.append((band_id, tralbum_id, tralbum_type))

    def cleanup(self):
        self.cleaned_up = True


class FakePlayer(QObject):
    position_changed = Signal(int)
    playback_state_changed = Signal(int)
    track_ended = Signal()
    playback_error = Signal()

    def __init__(self):
        super().__init__()
        self.volume = None
        self.url = None
        self._playing = False
        self._time = 0
        self._length = 0
        self.cleaned_up = False

    def set_volume(self, volume):
        self.volume = volume

    def load_and_play(self, url):
        self.url = url
        self._playing = True

    def play(self):
        self._playing = True

    def pause(self):
        self._playing = False

    def stop(self):
        self._playing = False

    def set_position(self, ms):
        self._time = ms

    def is_playing(self):
        return self._playing

    def get_length(self):
        return self._length

    def get_time(self):
        return self._time

    def cleanup(self):
        self.cleaned_up = True


@pytest.fixture
def window(qtbot):
    return MainWindow()


@pytest.fixture
def harness(window, qtbot):
    from bandcamp_player.core.controller import Controller

    engine = FakeEngine()
    player = FakePlayer()
    controller = Controller(window, engine=engine, player=player)
    return controller, engine, player, window


def test_search_routes_to_engine(harness):
    ctrl, engine, _player, _win = harness
    ctrl._on_search_requested("Chamber")
    assert engine.searches == ["Chamber"]
    assert ctrl._last_view == "search"


def test_artist_click_fetches_discography(harness):
    ctrl, engine, _player, win = harness
    ctrl._on_artist_clicked(4199458029)
    assert engine.artist_calls == [4199458029]

    ctrl._on_artist_data(True, {
        "name": "Chamber",
        "image_url": "",
        "albums": [{"title": "Tears of Joy", "item_id": 1, "item_type": "album", "image_url": ""}],
    }, "")
    assert ctrl._last_view == "artist"
    assert win.discography_layout.count() == 1


def test_album_flow_and_track_play(harness):
    ctrl, engine, player, win = harness
    ctrl._on_artist_clicked(4199458029)
    ctrl._on_album_clicked(4199458029, 609345249, "a")
    assert engine.album_calls == [(4199458029, 609345249, "a")]

    ctrl._on_album_data(True, {
        "title": "A Love To Kill For",
        "art_id": 1,
        "tracks": [
            {"title": "Chamber", "duration": 70000, "url": "https://stream/1"},
            {"title": "Retribution", "duration": 137000, "url": "https://stream/2"},
        ],
    }, "")
    assert len(ctrl._tracks) == 2
    assert win.tracklist_layout.count() == 2

    ctrl._play_track(1)
    assert ctrl._current_track_index == 1
    assert player.url == "https://stream/2"


def test_back_navigation_resets_on_search(harness):
    ctrl, _engine, _player, _win = harness
    ctrl._on_artist_clicked(1)
    ctrl._on_artist_data(True, {"name": "A", "image_url": "", "albums": []}, "")
    assert ctrl._last_view == "artist"
    ctrl._on_search_requested("x")
    assert ctrl._last_view == "search"


def test_track_ended_advances(harness):
    ctrl, _engine, _player, _win = harness
    ctrl._on_album_data(True, {
        "title": "A",
        "art_id": 1,
        "tracks": [
            {"title": "1", "duration": 1000, "url": "u1"},
            {"title": "2", "duration": 1000, "url": "u2"},
        ],
    }, "")
    ctrl._play_track(0)
    ctrl._on_track_ended()
    assert ctrl._current_track_index == 1


def test_search_error_shown_in_status(harness):
    ctrl, _engine, _player, win = harness
    ctrl._on_search_results(False, [], "HTTP 503 Service Unavailable")
    assert "HTTP 503" in win.statusBar().currentMessage()


def test_playback_error_stops_and_shows_status(harness):
    ctrl, _engine, _player, win = harness
    ctrl._on_playback_error()
    assert "Playback error" in win.statusBar().currentMessage()


def test_search_signal_wiring(harness, qtbot):
    ctrl, engine, _player, win = harness
    ctrl._on_search_requested("Chamber")
    engine.search_results_ready.emit(True, [
        {"type": "album", "title": "Tears of Joy", "artist": "Chamber",
         "band_id": 1, "id": 2, "image_url": "", "url": ""},
    ], "")
    qtbot.wait(100)
    assert win.results_layout.count() == 1  # one section widget


def test_album_card_click_connects_signal(harness, qtbot):
    ctrl, engine, _player, win = harness
    ctrl._on_artist_clicked(4199458029)
    ctrl._on_artist_data(True, {
        "name": "Chamber",
        "image_url": "",
        "albums": [{"title": "Tears of Joy", "item_id": 609345249, "item_type": "album", "image_url": ""}],
    }, "")
    card = win.discography_layout.itemAt(0).widget()
    card.clicked.emit(4199458029, 609345249, "album")
    assert engine.album_calls == [(4199458029, 609345249, "album")]
