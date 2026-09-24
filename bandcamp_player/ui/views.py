"""The three central views: search results, artist discography, tracklist."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from bandcamp_player.ui.cards import AlbumCard, TrackRow

_CARD_WIDTH = 220
_MIN_GAP = 20


class CardGrid(QGridLayout):
    """A grid that re-flows its cards to fit the available width."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSpacing(_MIN_GAP)
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._last_columns = 0

    def columns_for_width(self, width: int) -> int:
        if width <= 0:
            return 3
        columns = max(1, (width + _MIN_GAP) // (_CARD_WIDTH + _MIN_GAP))
        return min(columns, max(1, self.count()))

    def reflow(self, width: int):
        columns = self.columns_for_width(width)
        if columns == self._last_columns or self.count() == 0:
            return
        self._last_columns = columns
        widgets = []
        for i in range(self.count()):
            item = self.itemAt(i)
            if item and item.widget():
                widgets.append(item.widget())
            self.removeItem(item)
        for index, widget in enumerate(widgets):
            self.addWidget(widget, index // columns, index % columns)

    def add_card(self, widget):
        columns = self._last_columns or self.columns_for_width(self.parentWidget().width())
        row = self.count() // columns
        col = self.count() % columns
        self.addWidget(widget, row, col)

    def count_cards(self) -> int:
        return sum(1 for i in range(self.count()) if self.itemAt(i) and self.itemAt(i).widget())

_SCROLL_OBJECT_NAMES = {
    "search": "resultsScroll",
    "discography": "discographyScroll",
    "tracklist": "tracklistScroll",
}


class _ScrollingView(QWidget):
    """A view with a header-less scroll container that owns its content layout."""

    container_object_name = ""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName(_SCROLL_OBJECT_NAMES[self.kind])
        self.container = QWidget()
        self.container.setObjectName(self.container_object_name)
        self.content_layout = self._build_content_layout(self.container)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def _build_content_layout(self, container):
        raise NotImplementedError


class SearchResultsView(_ScrollingView):
    kind = "search"
    container_object_name = "resultsContainer"

    def __init__(self, image_loader, parent=None):
        self._image_loader = image_loader
        self.sections = {}
        super().__init__(parent)

    def _build_content_layout(self, container):
        layout = QVBoxLayout(container)
        layout.setSpacing(30)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        return layout

    def clear(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.sections = {}

    def add_section(self, result_type):
        section_widget = QFrame()
        section_widget.setObjectName("searchSection")
        section_layout = QVBoxLayout(section_widget)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(15)

        header_btn = QPushButton(f"▼ {result_type.capitalize()}s")
        header_btn.setObjectName("sectionHeader")
        header_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        grid_widget = QWidget()
        grid = CardGrid(grid_widget)
        grid_widget.grid = grid
        grid_widget.resizeEvent = lambda event: grid.reflow(event.size().width())

        def toggle_section():
            is_visible = grid_widget.isVisible()
            grid_widget.setVisible(not is_visible)
            header_btn.setText(f"{'▶' if is_visible else '▼'} {result_type.capitalize()}s")

        header_btn.clicked.connect(toggle_section)

        section_layout.addWidget(header_btn)
        section_layout.addWidget(grid_widget)

        self.sections[result_type] = {
            "widget": section_widget,
            "grid": grid,
            "grid_widget": grid_widget,
        }
        self.content_layout.addWidget(section_widget)

    def add_album(self, title, artist, image_url, result_type):
        if result_type not in self.sections:
            self.add_section(result_type)
        grid = self.sections[result_type]["grid"]
        card = AlbumCard(title, artist)
        if image_url:
            self._image_loader.load(image_url, card.cover_label, 176)
        grid.add_card(card)
        return card


class ArtistDiscographyView(_ScrollingView):
    kind = "discography"
    container_object_name = "discographyContainer"

    def __init__(self, image_loader, parent=None):
        self._image_loader = image_loader
        super().__init__(parent)
        header_layout = self._build_header()
        self.layout().insertLayout(0, header_layout)

    def _build_content_layout(self, container):
        layout = CardGrid(container)
        container.resizeEvent = lambda event: layout.reflow(event.size().width())
        return layout

    def _build_header(self):
        header_layout = QHBoxLayout()
        self.back_button = QPushButton("← Back")
        self.back_button.setObjectName("backButton")
        self.artist_image_label = QLabel()
        self.artist_image_label.setFixedSize(200, 200)
        self.artist_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.artist_image_label.setStyleSheet("background-color: #2a2a2a; border-radius: 4px;")
        self.artist_name_label = QLabel("Artist Name")
        self.artist_name_label.setObjectName("artistName")
        self.artist_name_label.setWordWrap(True)

        header_layout.addWidget(self.back_button)
        header_layout.addWidget(self.artist_image_label)
        header_layout.addWidget(self.artist_name_label, 1)
        header_layout.addStretch()
        return header_layout

    def set_artist_name(self, name):
        self.artist_name_label.setText(name)

    def add_album(self, title, image_url, album_type):
        card = AlbumCard(title, image_url=image_url)
        if image_url:
            self._image_loader.load(image_url, card.cover_label, 176)
        self.content_layout.add_card(card)
        return card

    def clear(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class TracklistView(_ScrollingView):
    kind = "tracklist"
    container_object_name = "tracklistContainer"

    def __init__(self, image_loader, parent=None):
        self._image_loader = image_loader
        self._track_items = []
        super().__init__(parent)
        header_layout = self._build_header()
        self.layout().insertLayout(0, header_layout)

    def _build_content_layout(self, container):
        layout = QVBoxLayout(container)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        return layout

    def _build_header(self):
        header_layout = QHBoxLayout()
        self.back_button = QPushButton("← Back")
        self.back_button.setObjectName("backButton")
        self.album_cover_label = QLabel()
        self.album_cover_label.setFixedSize(200, 200)
        self.album_cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.album_cover_label.setStyleSheet("background-color: #2a2a2a; border-radius: 4px;")
        self.album_title_label = QLabel("Album Title")
        self.album_title_label.setObjectName("albumTitle")

        header_layout.addWidget(self.back_button)
        header_layout.addWidget(self.album_cover_label)
        header_layout.addWidget(self.album_title_label)
        header_layout.addStretch()
        return header_layout

    def add_track(self, track_number, title, duration):
        track_widget = TrackRow(track_number - 1, title, duration)
        self.content_layout.addWidget(track_widget)
        self._track_items.append(track_widget)
        return track_widget

    def clear(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._track_items = []

    def highlight(self, index):
        for i, item in enumerate(self._track_items):
            item.set_active(i == index)
