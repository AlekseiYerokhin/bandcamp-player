from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class AlbumCard(QFrame):
    """A clickable album/artist card that emits its identity on click."""

    # qint64: Bandcamp ids exceed signed 32-bit int (Signal(int) would overflow)
    clicked = Signal('qint64', 'qint64', str)  # band_id, item_id, item_type

    def __init__(self, title, artist="", image_url=None, parent=None):
        super().__init__(parent)
        self.band_id = None
        self.item_id = None
        self.item_type = "album"

        self.setObjectName("albumCard")
        self.setFixedSize(200, 250)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(title)
        self.setStyleSheet("""
            #albumCard {
                background-color: #181818;
                border-radius: 8px;
                padding: 12px;
            }
            #albumCard:hover {
                background-color: #282828;
            }
            #albumCard:focus {
                background-color: #282828;
                border: 2px solid #0cacd7;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(176, 176)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("background-color: #2a2a2a; border-radius: 4px;")

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold;")
        title_label.setWordWrap(True)

        artist_label = QLabel(artist)
        artist_label.setStyleSheet("color: #b3b3b3; font-size: 12px;")
        artist_label.setWordWrap(True)

        layout.addWidget(self.cover_label)
        layout.addWidget(title_label)
        layout.addWidget(artist_label)
        layout.addStretch()

    def set_click_data(self, band_id, item_id, item_type):
        self.band_id = band_id
        self.item_id = item_id
        self.item_type = item_type

    def mousePressEvent(self, event):
        self.clicked.emit(self.band_id, self.item_id, self.item_type)
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit(self.band_id, self.item_id, self.item_type)
            event.accept()
        else:
            super().keyPressEvent(event)


class TrackRow(QFrame):
    """A clickable tracklist row that emits its index on click."""

    clicked = Signal(int)

    def __init__(self, index, title, duration, streamable=True, parent=None):
        super().__init__(parent)
        self._index = index
        self._active = False
        self._streamable = streamable

        self.setObjectName("trackItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        number_label = QLabel(str(index + 1))
        number_label.setFixedWidth(30)
        number_label.setStyleSheet("color: #b3b3b3; font-size: 14px; background: transparent;")

        self._title_label = QLabel(title)
        self._title_label.setStyleSheet("color: #ffffff; font-size: 14px; background: transparent;")

        duration_label = QLabel(duration)
        duration_label.setStyleSheet("color: #b3b3b3; font-size: 13px; background: transparent;")

        layout.addWidget(number_label)
        layout.addWidget(self._title_label, 1)
        layout.addWidget(duration_label)

        if not streamable:
            self.set_streamable(False)

    def set_streamable(self, streamable: bool):
        self._streamable = streamable
        self.setCursor(Qt.CursorShape.PointingHandCursor if streamable else Qt.CursorShape.ForbiddenCursor)
        if not streamable:
            self._title_label.setStyleSheet("color: #666666; font-size: 14px; background: transparent;")
            self.setProperty("disabled", True)
            self.style().unpolish(self)
            self.style().polish(self)

    def set_active(self, active: bool):
        self._active = active
        self.setProperty("active", active)
        color = "#0cacd7" if active else "#ffffff"
        self._title_label.setStyleSheet(f"color: {color}; font-size: 14px; background: transparent;")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if self._streamable:
            self.clicked.emit(self._index)
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if self._streamable:
                self.clicked.emit(self._index)
            event.accept()
        else:
            super().keyPressEvent(event)
