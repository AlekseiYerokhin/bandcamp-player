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


def test_play_pause_button_emits_request(qtbot):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from bandcamp_player.ui.main_window import MainWindow

    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    got = []
    win.play_pause_requested.connect(lambda: got.append(True))
    QTest.mouseClick(win.play_pause_button, Qt.MouseButton.LeftButton)
    assert got == [True]


def _fake_card():
    from bandcamp_player.ui.cards import AlbumCard

    return AlbumCard("X")
