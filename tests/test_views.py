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


def _fake_card():
    from bandcamp_player.ui.cards import AlbumCard

    return AlbumCard("X")
