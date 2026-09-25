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
    ctrl._on_search_requested("chamber")
    ctrl._on_search_results(False, [], "HTTP 503 Service Unavailable")
    label = win.search_view.content_layout.itemAt(0).widget()
    assert "HTTP 503" in label.text()


def test_empty_search_shows_no_results_placeholder(harness):
    ctrl, _engine, _player, win = harness
    ctrl._on_search_requested("zzzz")
    assert win.search_view.content_layout.count() == 1
    ctrl._on_search_results(True, [], "")
    label = win.search_view.content_layout.itemAt(0).widget()
    assert 'No results for "zzzz"' in label.text()


def test_empty_album_shows_tracklist_placeholder(harness):
    ctrl, _engine, _player, win = harness
    ctrl._on_album_data(True, {"title": "A", "tracks": []}, "")
    assert win.tracklist_layout.count() == 1
    assert "No tracks" in win.tracklist_layout.itemAt(0).widget().text()


def test_empty_artist_shows_discography_placeholder(harness):
    ctrl, _engine, _player, win = harness
    ctrl._on_artist_data(True, {"name": "A", "albums": []}, "")
    assert win.discography_layout.count() == 1
    assert "No releases" in win.discography_layout.itemAt(0).widget().text()


def test_non_streamable_track_is_disabled(harness):
    ctrl, _engine, player, win = harness
    ctrl._on_album_data(True, {
        "title": "A",
        "tracks": [
            {"title": "Streamable", "duration": 1000, "url": "u1"},
            {"title": "No stream", "duration": 1000, "url": ""},
        ],
    }, "")
    row = win.tracklist_layout.itemAt(1).widget()
    assert row._streamable is False
    ctrl._play_track(1)
    assert player.url is None
    assert ctrl._current_track_index == -1
    assert "not available" in win.statusBar().currentMessage()


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


def test_track_search_result_fetches_tralbum(harness):
    ctrl, engine, _player, win = harness
    ctrl._on_search_results(True, [
        {"type": "track", "title": "Chamber", "artist": "Chamber",
         "band_id": 4199458029, "id": 891815764, "image_url": "", "url": ""},
    ], "")
    assert win.results_layout.count() == 1  # one 'Tracks' section
    card = win.search_view.sections["track"]["grid"].itemAt(0).widget()
    card.clicked.emit(4199458029, 891815764, "track")
    assert engine.album_calls == [(4199458029, 891815764, "t")]


class FakeMpris(QObject):
    command_requested = Signal(str, int)
    volume_requested = Signal(float)

    def __init__(self):
        super().__init__()
        self.track_args = None
        self.playback_status = None
        self.position_ms = None
        self.seeked_ms = None

    def set_track(self, title, artist="", album="", duration_ms=0, art_url=""):
        self.track_args = (title, artist, album, duration_ms, art_url)

    def set_playback(self, status, metadata=None):
        self.playback_status = status

    def set_position_ms(self, ms):
        self.position_ms = ms

    def emit_seeked(self, ms):
        self.seeked_ms = ms


@pytest.fixture
def mpris_harness(window, qtbot):
    from bandcamp_player.core.controller import Controller

    engine = FakeEngine()
    player = FakePlayer()
    mpris = FakeMpris()
    controller = Controller(window, engine=engine, player=player, mpris=mpris)
    return controller, engine, player, window, mpris


def _load_two_track_album(ctrl):
    ctrl._on_album_data(True, {
        "title": "A Love To Kill For",
        "artist": "Chamber",
        "art_id": 1,
        "tracks": [
            {"title": "Chamber", "duration": 70000, "url": "https://stream/1"},
            {"title": "Retribution", "duration": 137000, "url": "https://stream/2"},
        ],
    }, "")


def test_mpris_volume_uses_float_signal(mpris_harness):
    _ctrl, _engine, player, win, mpris = mpris_harness
    mpris.volume_requested.emit(0.35)
    assert player.volume == 35
    assert win.get_volume() == 35
    mpris.volume_requested.emit(1.0)
    assert player.volume == 100


def test_mpris_pause_after_last_track_restarts_album(mpris_harness):
    ctrl, _engine, player, _win, mpris = mpris_harness
    _load_two_track_album(ctrl)
    ctrl._play_track(1)
    ctrl._on_track_ended()
    assert ctrl._current_track_index == -1
    ctrl._on_mpris_command("play", 0)
    assert ctrl._current_track_index == 0
    assert player.url == "https://stream/1"
    assert mpris.playback_status == "Playing"


def test_mpris_quit_calls_window_quit(window, qtbot, monkeypatch):
    from bandcamp_player.core.controller import Controller

    engine = FakeEngine()
    player = FakePlayer()
    mpris = FakeMpris()
    controller = Controller(window, engine=engine, player=player, mpris=mpris)
    quitted = []
    monkeypatch.setattr(window, "quit", lambda: quitted.append(True))
    controller._on_mpris_command("quit", 0)
    assert quitted == [True]


def test_artist_name_sent_to_mpris(mpris_harness):
    ctrl, _engine, _player, _win, mpris = mpris_harness
    _load_two_track_album(ctrl)
    ctrl._play_track(0)
    assert mpris.track_args[1] == "Chamber"


def test_pause_command_does_not_resume(mpris_harness):
    ctrl, _engine, player, _win, mpris = mpris_harness
    _load_two_track_album(ctrl)
    ctrl._play_track(0)
    player._playing = False
    ctrl._on_mpris_command("pause", 0)
    assert player.is_playing() is False
    assert mpris.playback_status == "Paused"


def test_mpris_set_position_seeks_player(mpris_harness):
    ctrl, _engine, player, _win, mpris = mpris_harness
    _load_two_track_album(ctrl)
    ctrl._on_mpris_command("set_position", 5000000)
    assert player._time == 5000
    assert mpris.seeked_ms == 5000


def test_mpris_seek_emits_seeked(mpris_harness):
    ctrl, _engine, player, _win, mpris = mpris_harness
    _load_two_track_album(ctrl)
    player._time = 1000
    ctrl._on_mpris_command("seek", 2000000)
    assert player._time == 3000
    assert mpris.seeked_ms == 3000


def test_ui_seek_emits_seeked(mpris_harness):
    ctrl, _engine, _player, _win, mpris = mpris_harness
    _load_two_track_album(ctrl)
    ctrl._on_progress_moved(15000)
    assert mpris.seeked_ms == 15000


def test_position_tick_does_not_emit_seeked(mpris_harness):
    ctrl, _engine, _player, _win, mpris = mpris_harness
    _load_two_track_album(ctrl)
    ctrl._on_position_changed(12000)
    assert mpris.position_ms == 12000
    assert mpris.seeked_ms is None
