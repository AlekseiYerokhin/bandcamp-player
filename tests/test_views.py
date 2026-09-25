"""UI view tests — adaptive grid reflow and view construction (offscreen)."""

import pytest

pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture
def grid():
    from bandcamp_player.ui.views import GridContainer

    return GridContainer()


def test_card_grid_columns_follow_width(grid):
    for _i in range(6):
        grid.grid.add_card(_fake_card())
    assert grid.grid.columns_for_width(700) == 3
    assert grid.grid.columns_for_width(1200) == 5
    assert grid.grid.columns_for_width(1900) == 6


def test_card_grid_reflow_keeps_cards(grid):
    from bandcamp_player.ui.cards import AlbumCard

    for i in range(6):
        grid.grid.add_card(AlbumCard(f"Album {i}"))
    grid.grid.reflow(1200)
    assert grid.grid._last_columns == 5
    assert grid.grid.count_cards() == 6
    grid.grid.reflow(700)
    assert grid.grid._last_columns == 3
    assert grid.grid.count_cards() == 6


def test_views_build_and_clear(qtbot):
    from PySide6.QtWidgets import QWidget

    from bandcamp_player.ui.image_loader import ImageLoader
    from bandcamp_player.ui.views import ArtistDiscographyView, SearchResultsView, TracklistView

    parent = QWidget()
    qtbot.addWidget(parent)
    loader = ImageLoader(parent)

    search = SearchResultsView(loader, parent)
    search.add_section("album")
    search.add_album("Tears of Joy", "Chamber", None, "album")
    assert search.content_layout.count() == 1
    search.clear()
    assert search.sections == {}

    artist = ArtistDiscographyView(loader, parent)
    artist.add_album("Tears of Joy", None, "album")
    assert artist.content_layout.count_cards() == 1
    artist.clear()
    assert artist.content_layout.count_cards() == 0

    track = TracklistView(loader, parent)
    track.add_track(1, "Chamber", "1:10")
    assert len(track._track_items) == 1
    track.clear()
    assert track._track_items == []


def test_placeholder_appears_in_views(qtbot):
    from bandcamp_player.ui.image_loader import ImageLoader
    from bandcamp_player.ui.views import SearchResultsView

    view = SearchResultsView(ImageLoader(), parent=None)
    qtbot.addWidget(view)
    view.show_placeholder("No results for x")
    assert view.content_layout.count() == 1
    assert "No results" in view.content_layout.itemAt(0).widget().text()


def test_track_row_disabled_when_not_streamable(qtbot):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from bandcamp_player.ui.cards import TrackRow

    row = TrackRow(0, "No stream", "1:00", streamable=False)
    qtbot.addWidget(row)
    row.show()
    assert row._streamable is False
    got = []
    row.clicked.connect(got.append)
    QTest.mouseClick(row, Qt.MouseButton.LeftButton)
    assert got == []

    row2 = TrackRow(1, "Ok", "1:00")
    qtbot.addWidget(row2)
    row2.show()
    got2 = []
    row2.clicked.connect(got2.append)
    QTest.mouseClick(row2, Qt.MouseButton.LeftButton)
    assert got2 == [1]


def test_track_row_keyboard_activation(qtbot):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from bandcamp_player.ui.cards import TrackRow

    row = TrackRow(2, "Ok", "1:00")
    qtbot.addWidget(row)
    row.show()
    row.setFocus()
    got = []
    row.clicked.connect(got.append)
    QTest.keyClick(row, Qt.Key.Key_Return)
    assert got == [2]

    row_disabled = TrackRow(3, "No", "1:00", streamable=False)
    qtbot.addWidget(row_disabled)
    row_disabled.show()
    got2 = []
    row_disabled.clicked.connect(got2.append)
    QTest.keyClick(row_disabled, Qt.Key.Key_Return)
    assert got2 == []


def test_album_card_activates_via_keyboard(qtbot):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from bandcamp_player.ui.cards import AlbumCard

    card = AlbumCard("Tears of Joy")
    card.set_click_data(3, 4, "album")
    qtbot.addWidget(card)
    card.show()
    got = []
    card.clicked.connect(lambda b, i, t: got.append((b, i, t)))
    card.setFocus()
    QTest.keyClick(card, Qt.Key.Key_Return)
    assert got == [(3, 4, "album")]


def test_volume_button_mutes_and_restores(qtbot):
    from bandcamp_player.ui.main_window import MainWindow

    win = MainWindow()
    qtbot.addWidget(win)
    win.volume_slider.setValue(70)
    win._toggle_mute()
    assert win.volume_slider.value() == 0
    assert win._muted is True
    win._toggle_mute()
    assert win.volume_slider.value() == 70
    assert win._muted is False


def test_volume_button_unmutes_from_zero(qtbot):
    from bandcamp_player.ui.main_window import MainWindow

    win = MainWindow()
    qtbot.addWidget(win)
    win.volume_slider.setValue(0)
    win._toggle_mute()
    assert win._muted is True
    win._toggle_mute()
    assert win.volume_slider.value() == 70


def test_track_row_keeps_grey_after_highlight(qtbot):
    from bandcamp_player.ui.cards import TrackRow

    row = TrackRow(0, "No stream", "1:00", streamable=False)
    qtbot.addWidget(row)
    row.set_streamable(False)
    assert row.property("disabled") is True
    row.set_active(False)
    assert row.property("disabled") is True
    assert row._streamable is False


def test_play_pause_click_drives_player(qtbot):
    """Integration: a real click on the play/pause button must reach the player.

    Regression guard for the P2 signal refactor that left the button unwired
    (Space worked via shortcut, clicks did nothing).
    """
    from PySide6.QtCore import QObject, Qt, Signal
    from PySide6.QtTest import QTest

    from bandcamp_player.core.controller import Controller
    from bandcamp_player.ui.main_window import MainWindow

    class FakeEngine(QObject):
        search_results_ready = Signal(bool, list, str)
        album_data_ready = Signal(bool, dict, str)
        artist_data_ready = Signal(bool, dict, str)

        def search(self, q):
            pass

        def get_artist_data(self, b):
            pass

        def get_album_data(self, *a):
            pass

        def cleanup(self):
            pass

    class FakePlayer(QObject):
        position_changed = Signal(int)
        playback_state_changed = Signal(int)
        track_ended = Signal()
        playback_error = Signal()

        def __init__(self):
            super().__init__()
            self._playing = False
            self._time = 0

        def load_and_play(self, url):
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
            return 0

        def get_time(self):
            return self._time

        def set_volume(self, v):
            pass

        def cleanup(self):
            pass

    win = MainWindow()
    qtbot.addWidget(win)
    player = FakePlayer()
    ctrl = Controller(win, engine=FakeEngine(), player=player)
    win.show()

    ctrl._on_album_data(True, {
        "title": "A",
        "tracks": [{"title": "t1", "duration": 1000, "url": "u1"}],
    }, "")

    QTest.mouseClick(win.play_pause_button, Qt.MouseButton.LeftButton)
    assert player.is_playing() is True
    QTest.mouseClick(win.play_pause_button, Qt.MouseButton.LeftButton)
    assert player.is_playing() is False


def _fake_card():
    from bandcamp_player.ui.cards import AlbumCard

    return AlbumCard("X")
