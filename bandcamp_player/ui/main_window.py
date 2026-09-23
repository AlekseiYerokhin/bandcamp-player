import contextlib
import os

import shiboken6
from PySide6.QtCore import QSettings, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from bandcamp_player.ui import theme
from bandcamp_player.ui.cards import AlbumCard, TrackRow

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets")


def _format_ms(ms: int) -> str:
    seconds = ms // 1000
    minutes = seconds // 60
    seconds %= 60
    return f"{minutes}:{seconds:02d}"


_SVG_PREV = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect x="4" y="5" width="2.5" height="14" fill="{c}"/><polygon points="19,5 8,12 19,19" fill="{c}"/></svg>'
_SVG_NEXT = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="5,5 16,12 5,19" fill="{c}"/><rect x="17.5" y="5" width="2.5" height="14" fill="{c}"/></svg>'
_SVG_PLAY = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="7,4 20,12 7,20" fill="{c}"/></svg>'
_SVG_PAUSE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect x="5" y="4" width="4.5" height="16" rx="1" fill="{c}"/><rect x="14.5" y="4" width="4.5" height="16" rx="1" fill="{c}"/></svg>'
_SVG_VOL_HIGH = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="3,9 7,9 12,4 12,20 7,15 3,15" fill="{c}"/><path d="M15.5,8.5 Q18,12 15.5,15.5" stroke="{c}" stroke-width="1.8" fill="none" stroke-linecap="round"/><path d="M18,5.5 Q22,12 18,18.5" stroke="{c}" stroke-width="1.8" fill="none" stroke-linecap="round"/></svg>'
_SVG_VOL_MED = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="3,9 7,9 12,4 12,20 7,15 3,15" fill="{c}"/><path d="M16,8 Q19,12 16,16" stroke="{c}" stroke-width="1.8" fill="none" stroke-linecap="round"/></svg>'
_SVG_VOL_LOW = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="3,9 7,9 12,4 12,20 7,15 3,15" fill="{c}"/></svg>'
_SVG_VOL_MUTE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="3,9 7,9 12,4 12,20 7,15 3,15" fill="{c}"/><line x1="16" y1="9" x2="22" y2="15" stroke="{c}" stroke-width="2" stroke-linecap="round"/><line x1="22" y1="9" x2="16" y2="15" stroke="{c}" stroke-width="2" stroke-linecap="round"/></svg>'


def _icon_from_svg(svg_template, size=24, color="#ffffff"):
    svg_str = svg_template.replace("{c}", color)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer = QSvgRenderer(svg_str.encode())
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


class IconButton(QPushButton):
    def __init__(self, svg_template, icon_size=20, normal_color="#b3b3b3", hover_color="#ffffff", parent=None):
        super().__init__(parent)
        self._svg = svg_template
        self._icon_size = icon_size
        self._normal_color = normal_color
        self._hover_color = hover_color
        self._update_icon(self._normal_color)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _update_icon(self, color):
        self.setIcon(_icon_from_svg(self._svg, self._icon_size, color))
        self.setIconSize(QSize(self._icon_size, self._icon_size))

    def set_icon_svg(self, svg_template, color=None):
        self._svg = svg_template
        self._update_icon(color or self._normal_color)

    def enterEvent(self, event):
        self._update_icon(self._hover_color)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_icon(self._normal_color)
        super().leaveEvent(event)


class MainWindow(QMainWindow):
    search_requested = Signal(str)

    closing = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bandcamp Player")
        self.setMinimumSize(1100, 700)

        icon_path = os.path.join(_ASSETS_DIR, "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._image_loader = QNetworkAccessManager(self)
        self._image_loader.finished.connect(self._on_image_loaded)
        self._pending_images = {}
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
        self._play_pause_shortcut.activated.connect(self.play_pause_button.animateClick)

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
        self.artist_discography_widget = self._create_artist_discography_widget()
        self.tracklist_widget = self._create_tracklist_widget()

        self.stacked_widget.addWidget(self.search_results_widget)
        self.stacked_widget.addWidget(self.artist_discography_widget)
        self.stacked_widget.addWidget(self.tracklist_widget)

        parent_layout.addWidget(self.stacked_widget)

    def _create_search_results_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("resultsScroll")

        self.results_container = QWidget()
        self.results_container.setObjectName("resultsContainer")
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(30)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._search_sections = {}

        scroll.setWidget(self.results_container)
        layout.addWidget(scroll)

        return widget

    def _create_artist_discography_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        self.artist_image_label = QLabel()
        self.artist_image_label.setFixedSize(200, 200)
        self.artist_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.artist_image_label.setStyleSheet("background-color: #2a2a2a; border-radius: 4px;")
        self.artist_name_label = QLabel("Artist Name")
        self.artist_name_label.setObjectName("artistName")
        self.artist_back_button = QPushButton("← Back")
        self.artist_back_button.setObjectName("backButton")
        self.artist_back_button.clicked.connect(self.show_search_results)

        header_layout.addWidget(self.artist_back_button)
        header_layout.addWidget(self.artist_image_label)
        self.artist_name_label.setWordWrap(True)
        header_layout.addWidget(self.artist_name_label, 1)
        header_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("discographyScroll")

        self.discography_container = QWidget()
        self.discography_container.setObjectName("discographyContainer")
        self.discography_layout = QGridLayout(self.discography_container)
        self.discography_layout.setSpacing(20)
        self.discography_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll.setWidget(self.discography_container)

        layout.addLayout(header_layout)
        layout.addWidget(scroll)

        return widget

    def show_artist_discography(self):
        self.stacked_widget.setCurrentWidget(self.artist_discography_widget)

    def set_artist_name(self, name):
        self.artist_name_label.setText(name)

    def set_artist_image(self, image_url):
        if image_url:
            self._load_image(image_url, self.artist_image_label, 200)

    def add_discography_album(self, title, image_url=None, album_type='album'):
        row = self.discography_layout.count() // 3
        col = self.discography_layout.count() % 3
        card = AlbumCard(title, image_url=image_url)
        if image_url:
            self._load_image(image_url, card.cover_label, 176)
        self.discography_layout.addWidget(card, row, col)
        return card

    def clear_discography(self):
        self._abort_pending_images()
        while self.discography_layout.count():
            item = self.discography_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _create_tracklist_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        self.album_cover_label = QLabel()
        self.album_cover_label.setFixedSize(200, 200)
        self.album_cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        self.tracklist_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._track_items = []

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

        self.prev_button = IconButton(_SVG_PREV, icon_size=18, normal_color="#b3b3b3", hover_color="#ffffff")
        self.prev_button.setObjectName("controlButton")
        self.prev_button.setFixedSize(40, 40)

        self.play_pause_button = IconButton(_SVG_PLAY, icon_size=20, normal_color="#ffffff", hover_color="#ffffff")
        self.play_pause_button.setObjectName("playPauseButton")
        self.play_pause_button.setFixedSize(50, 50)

        self.next_button = IconButton(_SVG_NEXT, icon_size=18, normal_color="#b3b3b3", hover_color="#ffffff")
        self.next_button.setObjectName("controlButton")
        self.next_button.setFixedSize(40, 40)

        self.track_info_layout = QVBoxLayout()
        self.track_info_layout.setSpacing(2)
        self.current_track_label = QLabel("No track playing")
        self.current_track_label.setObjectName("trackLabel")
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
        self.track_info_layout.addLayout(slider_row)

        self.volume_layout = QHBoxLayout()
        self.volume_layout.setSpacing(8)
        self.volume_button = IconButton(_SVG_VOL_HIGH, icon_size=22, normal_color="#b3b3b3", hover_color="#b3b3b3")
        self.volume_button.setObjectName("controlButton")
        self.volume_button.setFixedSize(28, 28)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("volumeSlider")
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self._update_volume_icon)
        self.volume_layout.addWidget(self.volume_button)
        self.volume_layout.addWidget(self.volume_slider)

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

    def show_status(self, message: str, timeout_ms: int = 5000):
        self.statusBar().showMessage(message, timeout_ms)

    def show_search_results(self):
        self.search_frame.show()
        self.stacked_widget.setCurrentWidget(self.search_results_widget)

    def clear_results(self):
        self._abort_pending_images()
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._search_sections = {}

    def show_tracklist(self, back_callback=None):
        self.stacked_widget.setCurrentWidget(self.tracklist_widget)
        if back_callback:
            with contextlib.suppress(RuntimeError):
                self.back_button.clicked.disconnect()
            self.back_button.clicked.connect(back_callback)

    def add_search_section(self, result_type: str):
        section_widget = QFrame()
        section_widget.setObjectName("searchSection")
        section_layout = QVBoxLayout(section_widget)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(15)

        header_btn = QPushButton(f"▼ {result_type.capitalize()}s")
        header_btn.setObjectName("sectionHeader")
        header_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(20)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        def toggle_section():
            is_visible = grid_widget.isVisible()
            grid_widget.setVisible(not is_visible)
            header_btn.setText(f"{'▶' if is_visible else '▼'} {result_type.capitalize()}s")

        header_btn.clicked.connect(toggle_section)

        section_layout.addWidget(header_btn)
        section_layout.addWidget(grid_widget)

        self._search_sections[result_type] = {
            'widget': section_widget,
            'grid': grid,
            'grid_widget': grid_widget
        }

        self.results_layout.addWidget(section_widget)

    def add_album_to_results(self, title, artist, image_url=None, result_type='album'):
        if result_type not in self._search_sections:
            self.add_search_section(result_type)

        section = self._search_sections[result_type]
        grid = section['grid']
        row = grid.count() // 3
        col = grid.count() % 3

        card = AlbumCard(title, artist)
        if image_url:
            self._load_image(image_url, card.cover_label, 176)
        grid.addWidget(card, row, col)
        return card

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

    def _abort_pending_images(self):
        for reply in list(self._pending_images):
            reply.abort()
        self._pending_images = {}

    def _on_image_loaded(self, reply):
        entry = self._pending_images.pop(reply, None)
        if entry is None:
            reply.deleteLater()
            return
        label, size = entry
        if reply.error() == QNetworkReply.NetworkError.NoError and shiboken6.isValid(label):
            data = reply.readAll()
            if data.size() > 0:
                pixmap = QPixmap()
                if pixmap.loadFromData(data):
                    label.setPixmap(pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    label.setMinimumSize(1, 1)
        reply.deleteLater()

    def set_album_cover(self, image_url):
        if image_url:
            self._load_image(image_url, self.album_cover_label, 200)

    def add_track_to_tracklist(self, track_number, title, duration):
        track_widget = TrackRow(track_number - 1, title, duration)
        self.tracklist_layout.addWidget(track_widget)
        self._track_items.append(track_widget)
        return track_widget

    def clear_tracklist(self):
        self._abort_pending_images()
        while self.tracklist_layout.count():
            item = self.tracklist_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._track_items = []

    def highlight_track(self, index: int):
        for i, item in enumerate(self._track_items):
            item.set_active(i == index)

    def set_current_track(self, title):
        self.current_track_label.setText(title)

    def set_play_state(self, playing: bool):
        self.play_pause_button.set_icon_svg(_SVG_PAUSE if playing else _SVG_PLAY, "#ffffff")

    def set_progress(self, position: int, duration: int):
        if duration > 0:
            self.progress_slider.setRange(0, duration)
            self.progress_slider.setValue(position)

    def set_time(self, position: int, duration: int):
        self.time_label.setText(f"{_format_ms(position)} / {_format_ms(duration)}")

    def _update_volume_icon(self, value):
        if value == 0:
            svg = _SVG_VOL_MUTE
        elif value < 33:
            svg = _SVG_VOL_LOW
        elif value < 66:
            svg = _SVG_VOL_MED
        else:
            svg = _SVG_VOL_HIGH
        self.volume_button.set_icon_svg(svg, "#b3b3b3")
