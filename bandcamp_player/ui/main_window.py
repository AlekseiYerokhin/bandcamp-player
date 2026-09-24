import contextlib
import os

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QSlider,
    QStackedWidget,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from bandcamp_player.ui import theme
from bandcamp_player.ui.icons import (
    SVG_NEXT,
    SVG_PAUSE,
    SVG_PLAY,
    SVG_PREV,
    SVG_VOL_HIGH,
    SVG_VOL_LOW,
    SVG_VOL_MED,
    SVG_VOL_MUTE,
    IconButton,
)
from bandcamp_player.ui.image_loader import ImageLoader
from bandcamp_player.ui.views import ArtistDiscographyView, SearchResultsView, TracklistView

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets")


def _format_ms(ms: int) -> str:
    seconds = ms // 1000
    minutes = seconds // 60
    seconds %= 60
    return f"{minutes}:{seconds:02d}"


class MainWindow(QMainWindow):
    search_requested = Signal(str)

    seek_requested = Signal(int)

    play_pause_requested = Signal()
    previous_requested = Signal()
    next_requested = Signal()
    volume_changed = Signal(int)
    progress_moved = Signal(int)

    closing = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bandcamp Player")
        self.resize(1100, 700)

        icon_path = os.path.join(_ASSETS_DIR, "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._image_loader = ImageLoader(self)
        self._setup_ui()
        self._apply_styles()
        self._load_settings()
        self._setup_tray()

    def _load_settings(self):
        settings = QSettings()
        self.volume_slider.setValue(int(settings.value("volume", 70)))
        size = settings.value("window/size")
        pos = settings.value("window/pos")
        if size is not None:
            self.resize(size)
        if pos is not None:
            self.move(pos)

    def _save_settings(self):
        settings = QSettings()
        settings.setValue("volume", self.volume_slider.value())
        settings.setValue("window/size", self.size())
        settings.setValue("window/pos", self.pos())

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self._tray_icon = None
            return
        icon_path = os.path.join(_ASSETS_DIR, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

        self._tray_menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self._show_window)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_app)

        self._tray_menu.addAction(show_action)
        self._tray_menu.addSeparator()
        self._tray_menu.addAction(quit_action)

        self._tray_icon = QSystemTrayIcon(icon, self)
        self._tray_icon.setContextMenu(self._tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _quit_app(self):
        self._save_settings()
        self.closing.emit()
        if self._tray_icon is not None:
            self._tray_icon.hide()
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    def closeEvent(self, event: QCloseEvent):
        if self._tray_icon is not None and self._tray_icon.isVisible():
            self.hide()
            event.ignore()
            return
        self._save_settings()
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

        self._vol_up_shortcut = QShortcut("Ctrl+Up", self)
        self._vol_up_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._vol_up_shortcut.activated.connect(lambda: self.volume_slider.setValue(min(100, self.volume_slider.value() + 5)))

        self._vol_down_shortcut = QShortcut("Ctrl+Down", self)
        self._vol_down_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._vol_down_shortcut.activated.connect(lambda: self.volume_slider.setValue(max(0, self.volume_slider.value() - 5)))

        self._play_pause_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self._play_pause_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self._play_pause_shortcut.activated.connect(self.play_pause_requested.emit)

        self._seek_fwd_shortcut = QShortcut("Ctrl+Right", self)
        self._seek_fwd_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._seek_fwd_shortcut.activated.connect(lambda: self.seek_requested.emit(5000))

        self._seek_back_shortcut = QShortcut("Ctrl+Left", self)
        self._seek_back_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._seek_back_shortcut.activated.connect(lambda: self.seek_requested.emit(-5000))

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

        self.search_view = SearchResultsView(self._image_loader)
        self.artist_view = ArtistDiscographyView(self._image_loader)
        self.track_view = TracklistView(self._image_loader)

        self.search_results_widget = self.search_view
        self.artist_discography_widget = self.artist_view
        self.tracklist_widget = self.track_view

        self.stacked_widget.addWidget(self.search_results_widget)
        self.stacked_widget.addWidget(self.artist_discography_widget)
        self.stacked_widget.addWidget(self.tracklist_widget)

        parent_layout.addWidget(self.stacked_widget)

        # Back-compat aliases used by controller/tests.
        self.results_layout = self.search_view.content_layout
        self.discography_layout = self.artist_view.content_layout
        self.tracklist_layout = self.track_view.content_layout
        self.artist_back_button = self.artist_view.back_button
        self.back_button = self.track_view.back_button
        self.artist_image_label = self.artist_view.artist_image_label
        self.artist_name_label = self.artist_view.artist_name_label
        self.album_cover_label = self.track_view.album_cover_label
        self.album_title_label = self.track_view.album_title_label

        self.artist_view.back_button.clicked.connect(self.show_search_results)
        self.track_view.back_button.clicked.connect(self.show_search_results)

    def show_artist_discography(self):
        self.stacked_widget.setCurrentWidget(self.artist_discography_widget)

    def set_artist_name(self, name):
        self.artist_view.set_artist_name(name)

    def set_artist_image(self, image_url):
        if image_url:
            self._image_loader.load(image_url, self.artist_view.artist_image_label, 200)

    def add_discography_album(self, title, image_url=None, album_type='album'):
        return self.artist_view.add_album(title, image_url, album_type)

    def clear_discography(self):
        self._abort_pending_images()
        self.artist_view.clear()

    def show_discography_placeholder(self, text):
        self._abort_pending_images()
        self.artist_view.show_placeholder(text)

    def show_tracklist_placeholder(self, text):
        self._abort_pending_images()
        self.track_view.show_placeholder(text)

    def _setup_player_bar(self, parent_layout):
        player_bar = QFrame()
        player_bar.setObjectName("playerBar")
        player_bar.setFixedHeight(80)
        player_layout = QHBoxLayout(player_bar)
        player_layout.setContentsMargins(20, 10, 20, 10)
        player_layout.setSpacing(15)

        self.prev_button = IconButton(SVG_PREV, icon_size=18, normal_color="#b3b3b3", hover_color="#ffffff")
        self.prev_button.setObjectName("controlButton")
        self.prev_button.setFixedSize(40, 40)

        self.play_pause_button = IconButton(SVG_PLAY, icon_size=20, normal_color="#ffffff", hover_color="#ffffff")
        self.play_pause_button.setObjectName("playPauseButton")
        self.play_pause_button.setFixedSize(50, 50)

        self.next_button = IconButton(SVG_NEXT, icon_size=18, normal_color="#b3b3b3", hover_color="#ffffff")
        self.next_button.setObjectName("controlButton")
        self.next_button.setFixedSize(40, 40)

        self.track_info_layout = QVBoxLayout()
        self.track_info_layout.setSpacing(2)
        self.current_track_label = QLabel("No track playing")
        self.current_track_label.setObjectName("trackLabel")
        self.current_artist_label = QLabel("")
        self.current_artist_label.setObjectName("trackArtistLabel")
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setObjectName("progressSlider")
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(0)
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setObjectName("timeLabel")
        slider_row = QHBoxLayout()
        slider_row.setSpacing(8)
        slider_row.addWidget(self.progress_slider, 1)
        slider_row.addWidget(self.time_label)
        self.track_info_layout.addWidget(self.current_track_label)
        self.track_info_layout.addWidget(self.current_artist_label)
        self.track_info_layout.addLayout(slider_row)

        self.volume_layout = QHBoxLayout()
        self.volume_layout.setSpacing(8)
        self.volume_button = IconButton(SVG_VOL_HIGH, icon_size=22, normal_color="#b3b3b3", hover_color="#b3b3b3")
        self.volume_button.setObjectName("controlButton")
        self.volume_button.setFixedSize(28, 28)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("volumeSlider")
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self._update_volume_icon)
        self.volume_slider.valueChanged.connect(self.volume_changed.emit)
        self.volume_layout.addWidget(self.volume_button)
        self.volume_layout.addWidget(self.volume_slider)

        self.prev_button.clicked.connect(self.previous_requested.emit)
        self.next_button.clicked.connect(self.next_requested.emit)
        self.progress_slider.sliderMoved.connect(self.progress_moved.emit)

        player_layout.addWidget(self.prev_button)
        player_layout.addWidget(self.play_pause_button)
        player_layout.addWidget(self.next_button)
        player_layout.addLayout(self.track_info_layout, 1)
        player_layout.addLayout(self.volume_layout)

        parent_layout.addWidget(player_bar)

    def _apply_styles(self):
        self.setStyleSheet(theme.STYLESHEET)

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

    def show_search_loading(self):
        self.search_view.show_placeholder("Searching...")

    def show_search_placeholder(self, text):
        self._abort_pending_images()
        self.search_view.show_placeholder(text)

    def show_status(self, message: str, timeout_ms: int = 5000):
        self.statusBar().showMessage(message, timeout_ms)

    def show_search_results(self):
        self.search_frame.show()
        self.stacked_widget.setCurrentWidget(self.search_results_widget)

    def clear_results(self):
        self._abort_pending_images()
        self.search_view.clear()

    def show_tracklist(self, back_callback=None):
        self.stacked_widget.setCurrentWidget(self.tracklist_widget)
        if back_callback:
            with contextlib.suppress(RuntimeError):
                self.track_view.back_button.clicked.disconnect()
            self.track_view.back_button.clicked.connect(back_callback)

    def add_search_section(self, result_type: str):
        self.search_view.add_section(result_type)

    def add_album_to_results(self, title, artist, image_url=None, result_type='album'):
        return self.search_view.add_album(title, artist, image_url, result_type)

    def _load_image(self, url, label, size=176):
        self._image_loader.load(url, label, size)

    def _abort_pending_images(self):
        self._image_loader.abort_all()

    def set_album_cover(self, image_url):
        if image_url:
            self._image_loader.load(image_url, self.track_view.album_cover_label, 200)

    def add_track_to_tracklist(self, track_number, title, duration, streamable=True):
        return self.track_view.add_track(track_number, title, duration, streamable=streamable)

    def clear_tracklist(self):
        self._abort_pending_images()
        self.track_view.clear()

    def highlight_track(self, index: int):
        self.track_view.highlight(index)

    def set_current_track(self, title):
        self.current_track_label.setText(title)

    def set_current_artist(self, artist):
        self.current_artist_label.setText(artist)

    def set_volume(self, value):
        self.volume_slider.setValue(value)

    def get_volume(self) -> int:
        return self.volume_slider.value()

    def is_progress_slider_down(self) -> bool:
        return self.progress_slider.isSliderDown()

    def set_album_title(self, title):
        self.track_view.album_title_label.setText(title)

    def set_play_state(self, playing: bool):
        self.play_pause_button.set_icon_svg(SVG_PAUSE if playing else SVG_PLAY, "#ffffff")

    def set_progress(self, position: int, duration: int):
        if duration > 0:
            self.progress_slider.setRange(0, duration)
            self.progress_slider.setValue(position)

    def set_time(self, position: int, duration: int):
        self.time_label.setText(f"{_format_ms(position)} / {_format_ms(duration)}")

    def _update_volume_icon(self, value):
        if value == 0:
            svg = SVG_VOL_MUTE
        elif value < 33:
            svg = SVG_VOL_LOW
        elif value < 66:
            svg = SVG_VOL_MED
        else:
            svg = SVG_VOL_HIGH
        self.volume_button.set_icon_svg(svg, "#b3b3b3")
