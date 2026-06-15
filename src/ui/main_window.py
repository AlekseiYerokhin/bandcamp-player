from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QStackedWidget, QScrollArea, QFrame, QSlider, QLabel, QGridLayout,
    QSizePolicy
)
from PySide6.QtCore import Qt, QSize, Signal, QUrl
from PySide6.QtGui import QPixmap, QIcon, QCloseEvent
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


class MainWindow(QMainWindow):
    search_requested = Signal(str)

    closing = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bandcamp Player")
        self.setMinimumSize(1100, 700)
        self._image_loader = QNetworkAccessManager(self)
        self._image_loader.finished.connect(self._on_image_loaded)
        self._pending_images = {}
        self._setup_ui()
        self._apply_styles()

    def closeEvent(self, event: QCloseEvent):
        self.closing.emit()
        super().closeEvent(event)

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._setup_search_bar(main_layout)
        self._setup_central_area(main_layout)
        self._setup_player_bar(main_layout)

    def _setup_search_bar(self, parent_layout):
        self.search_frame = QFrame()
        self.search_frame.setObjectName("searchFrame")
        search_layout = QHBoxLayout(self.search_frame)
        search_layout.setContentsMargins(15, 10, 15, 10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for artists, albums, or tracks...")
        self.search_input.setObjectName("searchInput")
        self.search_input.returnPressed.connect(self._on_search_triggered)

        self.search_button = QPushButton("Search")
        self.search_button.setObjectName("searchButton")
        self.search_button.clicked.connect(self._on_search_triggered)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        parent_layout.addWidget(self.search_frame)

    def _setup_central_area(self, parent_layout):
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("centralStack")

        self.search_results_widget = self._create_search_results_widget()
        self.tracklist_widget = self._create_tracklist_widget()

        self.stacked_widget.addWidget(self.search_results_widget)
        self.stacked_widget.addWidget(self.tracklist_widget)

        parent_layout.addWidget(self.stacked_widget)

    def _create_search_results_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("resultsScroll")

        self.results_grid_widget = QWidget()
        self.results_grid = QGridLayout(self.results_grid_widget)
        self.results_grid.setSpacing(20)
        self.results_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll.setWidget(self.results_grid_widget)
        layout.addWidget(scroll)

        return widget

    def _create_tracklist_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        self.album_cover_label = QLabel()
        self.album_cover_label.setFixedSize(200, 200)
        self.album_cover_label.setAlignment(Qt.AlignCenter)
        self.album_cover_label.setStyleSheet("background-color: #2a2a2a; border-radius: 4px;")
        self.album_title_label = QLabel("Album Title")
        self.album_title_label.setObjectName("albumTitle")
        self.back_button = QPushButton("← Back")
        self.back_button.setObjectName("backButton")
        self.back_button.clicked.connect(self.show_search_results)

        header_layout.addWidget(self.back_button)
        header_layout.addWidget(self.album_cover_label)
        header_layout.addWidget(self.album_title_label)
        header_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("tracklistScroll")

        self.tracklist_container = QWidget()
        self.tracklist_container.setObjectName("tracklistContainer")
        self.tracklist_layout = QVBoxLayout(self.tracklist_container)
        self.tracklist_layout.setSpacing(8)
        self.tracklist_layout.setAlignment(Qt.AlignTop)

        scroll.setWidget(self.tracklist_container)

        layout.addLayout(header_layout)
        layout.addWidget(scroll)

        return widget

    def _setup_player_bar(self, parent_layout):
        player_bar = QFrame()
        player_bar.setObjectName("playerBar")
        player_bar.setFixedHeight(80)
        player_layout = QHBoxLayout(player_bar)
        player_layout.setContentsMargins(20, 10, 20, 10)
        player_layout.setSpacing(15)

        self.prev_button = QPushButton("⏮")
        self.prev_button.setObjectName("controlButton")
        self.prev_button.setFixedSize(40, 40)

        self.play_pause_button = QPushButton("▶")
        self.play_pause_button.setObjectName("playPauseButton")
        self.play_pause_button.setFixedSize(50, 50)

        self.next_button = QPushButton("⏭")
        self.next_button.setObjectName("controlButton")
        self.next_button.setFixedSize(40, 40)

        self.track_info_layout = QVBoxLayout()
        self.track_info_layout.setSpacing(2)
        self.current_track_label = QLabel("No track playing")
        self.current_track_label.setObjectName("trackLabel")
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setObjectName("progressSlider")
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(100)
        self.track_info_layout.addWidget(self.current_track_label)
        self.track_info_layout.addWidget(self.progress_slider)

        self.volume_layout = QVBoxLayout()
        self.volume_layout.setSpacing(2)
        self.volume_label = QLabel("🔊")
        self.volume_label.setAlignment(Qt.AlignCenter)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setObjectName("volumeSlider")
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(100)
        self.volume_layout.addWidget(self.volume_label)
        self.volume_layout.addWidget(self.volume_slider)

        player_layout.addWidget(self.prev_button)
        player_layout.addWidget(self.play_pause_button)
        player_layout.addWidget(self.next_button)
        player_layout.addLayout(self.track_info_layout, 1)
        player_layout.addLayout(self.volume_layout)

        parent_layout.addWidget(player_bar)

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            #searchFrame {
                background-color: #181818;
                border-bottom: 1px solid #282828;
            }
            #searchInput {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 20px;
                padding: 8px 15px;
                font-size: 14px;
            }
            #searchInput:focus {
                border: 1px solid #1db954;
            }
            #searchButton {
                background-color: #1db954;
                color: #ffffff;
                border: none;
                border-radius: 20px;
                padding: 8px 25px;
                font-size: 14px;
                font-weight: bold;
            }
            #searchButton:hover {
                background-color: #1ed760;
            }
            #searchButton:pressed {
                background-color: #1aa34a;
            }
            #centralStack {
                background-color: #121212;
                color: #ffffff;
            }
            #resultsScroll, #tracklistScroll {
                background-color: #121212;
                border: none;
                color: #ffffff;
            }
            #tracklistContainer {
                background-color: #121212;
                color: #ffffff;
            }
            #albumTitle {
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
            }
            #backButton {
                background-color: transparent;
                color: #b3b3b3;
                border: none;
                font-size: 14px;
                padding: 5px 10px;
            }
            #backButton:hover {
                color: #ffffff;
            }
            #trackItem {
                background-color: transparent;
                color: #ffffff;
                padding: 10px;
                border-radius: 4px;
            }
            #trackItem:hover {
                background-color: #282828;
            }
            #playerBar {
                background-color: #181818;
                border-top: 1px solid #282828;
            }
            #controlButton {
                background-color: transparent;
                color: #b3b3b3;
                border: none;
                border-radius: 20px;
                font-size: 18px;
            }
            #controlButton:hover {
                color: #ffffff;
                background-color: #282828;
            }
            #playPauseButton {
                background-color: #1db954;
                color: #ffffff;
                border: none;
                border-radius: 25px;
                font-size: 20px;
            }
            #playPauseButton:hover {
                background-color: #1ed760;
            }
            #trackLabel {
                color: #ffffff;
                font-size: 13px;
            }
            #progressSlider::groove:horizontal {
                background: #4d4d4d;
                height: 4px;
                border-radius: 2px;
            }
            #progressSlider::handle:horizontal {
                background: #1db954;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            #progressSlider::sub-page:horizontal {
                background: #1db954;
                border-radius: 2px;
            }
            #volumeSlider::groove:horizontal {
                background: #4d4d4d;
                height: 4px;
                border-radius: 2px;
            }
            #volumeSlider::handle:horizontal {
                background: #b3b3b3;
                width: 10px;
                height: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
            #volumeSlider::sub-page:horizontal {
                background: #b3b3b3;
                border-radius: 2px;
            }
        """)

    def _on_search_triggered(self):
        query = self.search_input.text().strip()
        if not query:
            return
        self.search_button.setEnabled(False)
        self.search_button.setText("Searching...")
        self.clear_results()
        self.search_requested.emit(query)

    def search_finished(self):
        self.search_button.setEnabled(True)
        self.search_button.setText("Search")

    def show_search_results(self):
        self.search_frame.show()
        self.stacked_widget.setCurrentWidget(self.search_results_widget)

    def clear_results(self):
        while self.results_grid.count():
            item = self.results_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def show_tracklist(self):
        self.search_frame.hide()
        self.stacked_widget.setCurrentWidget(self.tracklist_widget)

    def add_album_to_results(self, title, artist, image_url=None):
        row = self.results_grid.count() // 3
        col = self.results_grid.count() % 3

        album_widget = self._create_album_card(title, artist, image_url)
        self.results_grid.addWidget(album_widget, row, col)
        return album_widget

    def _load_image(self, url, label, size=176):
        if not url:
            return
        if url.startswith('//'):
            url = 'https:' + url
        qurl = QUrl(url)
        if not qurl.isValid():
            return
        request = QNetworkRequest(qurl)
        request.setRawHeader(b"User-Agent", b"Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        request.setRawHeader(b"Referer", b"https://bandcamp.com/")
        reply = self._image_loader.get(request)
        self._pending_images[reply] = (label, size)

    def _on_image_loaded(self, reply):
        entry = self._pending_images.pop(reply, None)
        if entry is None:
            reply.deleteLater()
            return
        label, size = entry
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            if data.size() > 0:
                pixmap = QPixmap()
                if pixmap.loadFromData(data):
                    label.setPixmap(pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    label.setMinimumSize(1, 1)
        reply.deleteLater()

    def set_album_cover(self, image_url):
        if image_url:
            self._load_image(image_url, self.album_cover_label, 200)

    def _create_album_card(self, title, artist, image_url=None):
        card = QFrame()
        card.setObjectName("albumCard")
        card.setFixedSize(200, 250)
        card.setStyleSheet("""
            #albumCard {
                background-color: #181818;
                border-radius: 8px;
                padding: 12px;
            }
            #albumCard:hover {
                background-color: #282828;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        cover_label = QLabel()
        cover_label.setFixedSize(176, 176)
        cover_label.setAlignment(Qt.AlignCenter)
        cover_label.setStyleSheet("background-color: #2a2a2a; border-radius: 4px;")

        if image_url:
            self._load_image(image_url, cover_label, 176)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold;")
        title_label.setWordWrap(True)

        artist_label = QLabel(artist)
        artist_label.setStyleSheet("color: #b3b3b3; font-size: 12px;")
        artist_label.setWordWrap(True)

        layout.addWidget(cover_label)
        layout.addWidget(title_label)
        layout.addWidget(artist_label)
        layout.addStretch()

        return card

    def add_track_to_tracklist(self, track_number, title, duration):
        track_widget = self._create_track_item(track_number, title, duration)
        self.tracklist_layout.addWidget(track_widget)
        return track_widget

    def _create_track_item(self, track_number, title, duration):
        item = QFrame()
        item.setObjectName("trackItem")

        layout = QHBoxLayout(item)
        layout.setContentsMargins(10, 5, 10, 5)

        number_label = QLabel(str(track_number))
        number_label.setFixedWidth(30)
        number_label.setStyleSheet("color: #b3b3b3; font-size: 14px; background: transparent;")

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #ffffff; font-size: 14px; background: transparent;")

        duration_label = QLabel(duration)
        duration_label.setStyleSheet("color: #b3b3b3; font-size: 13px; background: transparent;")

        layout.addWidget(number_label)
        layout.addWidget(title_label, 1)
        layout.addWidget(duration_label)

        return item

    def set_current_track(self, title):
        self.current_track_label.setText(title)

    def set_play_state(self, playing: bool):
        self.play_pause_button.setText("⏸" if playing else "▶")

    def set_progress(self, position: int, duration: int):
        if duration > 0:
            self.progress_slider.setValue(int((position / duration) * 100))
