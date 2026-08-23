from PySide6.QtCore import QObject
from .engine import BandcampEngine
from .player import AudioPlayer


class Controller(QObject):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.engine = BandcampEngine()
        self.player = AudioPlayer()
        self._current_album_url: str | None = None
        self._tracks = []
        self._current_track_index = -1
        
        self._search_results = {'album': [], 'track': [], 'artist': []}
        self._search_displayed = {'album': 0, 'track': 0, 'artist': 0}
        self._page_size = 12

        self._connect_signals()
        self._setup_player()

    def _connect_signals(self):
        self.window.closing.connect(self._on_window_closing)
        self.window.search_requested.connect(self._on_search_requested)
        self.window.load_more_requested.connect(self._on_load_more_clicked)
        self.engine.search_results_ready.connect(self._on_search_results)
        self.engine.album_data_ready.connect(self._on_album_data)
        self.engine.artist_data_ready.connect(self._on_artist_data)

        self.player.position_changed.connect(self._on_position_changed)
        self.player.duration_changed.connect(self._on_duration_changed)
        self.player.playback_state_changed.connect(self._on_playback_state_changed)

        self.window.play_pause_button.clicked.connect(self._on_play_pause_clicked)
        self.window.prev_button.clicked.connect(self._on_prev_clicked)
        self.window.next_button.clicked.connect(self._on_next_clicked)
        self.window.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.window.progress_slider.sliderMoved.connect(self._on_progress_moved)

    def _setup_player(self):
        self.player.set_volume(self.window.volume_slider.value())

    def _on_window_closing(self):
        self.engine.cleanup()
        self.player.cleanup()

    def _on_search_requested(self, query: str):
        self.window.clear_results()
        self.engine.search(query)

    def _on_search_results(self, success: bool, results: list):
        self.window.search_finished()
        self.window.clear_results()

        if not success:
            self.window.show_search_results()
            return

        self._search_results = {'album': [], 'track': [], 'artist': []}
        self._search_displayed = {'album': 0, 'track': 0, 'artist': 0}

        for result in results:
            result_type = result.get('type', 'album')
            if result_type in self._search_results:
                self._search_results[result_type].append(result)

        print(f"Search results: {len(self._search_results['album'])} albums, {len(self._search_results['track'])} tracks, {len(self._search_results['artist'])} artists")

        for result_type in ['album', 'track', 'artist']:
            if self._search_results[result_type]:
                self._display_search_section(result_type)

        self.window.show_search_results()

    def _display_search_section(self, result_type: str):
        items = self._search_results[result_type]
        start = self._search_displayed[result_type]
        end = min(start + self._page_size, len(items))
        
        if start == 0:
            self.window.add_search_section(result_type)
        
        for i in range(start, end):
            result = items[i]
            card = self.window.add_album_to_results(
                result['title'],
                result['artist'],
                result.get('image_url') or None,
                result_type
            )
            if card:
                card.mousePressEvent = lambda e, url=result['url'], rtype=result_type: self._on_result_clicked(url, rtype)
        
        self._search_displayed[result_type] = end
        
        has_more = end < len(items)
        self.window.update_section_load_more(result_type, has_more)

    def _on_load_more_clicked(self, result_type: str):
        self._display_search_section(result_type)

    def _on_result_clicked(self, url: str, result_type: str):
        if result_type == 'album' or result_type == 'track':
            self._on_album_clicked(url)
        elif result_type == 'artist':
            self._on_artist_clicked(url)

    def _on_album_clicked(self, url: str):
        self._current_album_url = url
        self.engine.get_album_data(url)

    def _on_artist_clicked(self, url: str):
        self.engine.get_artist_data(url)

    def _on_album_data(self, success: bool, data: dict):
        if success:
            self._display_album(data)

    def _on_artist_data(self, success: bool, data: dict):
        if success:
            self._display_artist_discography(data)

    def _display_album(self, data: dict):
        album_title = data.get('current', {}).get('title', 'Unknown Album')
        self.window.album_title_label.setText(album_title)

        art_id = data.get('art_id')
        if art_id:
            cover_url = f"https://f4.bcbits.com/img/a{art_id}_10.jpg"
            self.window.set_album_cover(cover_url)

        while self.window.tracklist_layout.count():
            item = self.window.tracklist_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._tracks = []
        track_list = data.get('trackinfo', [])

        for i, track in enumerate(track_list, 1):
            title = track.get('title', 'Unknown')
            duration_ms = int(track.get('duration', 0) * 1000)
            duration_str = self._format_duration(duration_ms)

            self._tracks.append({
                'title': title,
                'url': (track.get('file') or {}).get('mp3-128', ''),
                'duration': duration_ms
            })

            track_widget = self.window.add_track_to_tracklist(i, title, duration_str)
            track_widget.mousePressEvent = lambda e, idx=i-1: self._play_track(idx)

        self.window.show_tracklist()

    def _display_artist_discography(self, data: dict):
        artist_name = data.get('name', 'Unknown Artist')
        self.window.set_artist_name(artist_name)

        image_url = data.get('image_url')
        if image_url:
            self.window.set_artist_image(image_url)

        self.window.clear_discography()

        albums = data.get('albums', [])
        for album in albums:
            title = album.get('title', 'Unknown')
            album_url = album.get('url', '')
            album_image = album.get('image_url')
            album_type = album.get('type', 'album')

            card = self.window.add_discography_album(title, album_image, album_type)
            if card and album_url:
                card.mousePressEvent = lambda e, url=album_url: self._on_album_clicked(url)

        self.window.show_artist_discography()

    def _play_track(self, index: int):
        if 0 <= index < len(self._tracks):
            self._current_track_index = index
            track = self._tracks[index]

            self.player.load_and_play(track['url'], self._current_album_url or "")
            self.window.set_current_track(track['title'])

    def _on_play_pause_clicked(self):
        if self.player.is_playing():
            self.player.pause()
        else:
            if self._current_track_index == -1 and self._tracks:
                self._play_track(0)
            else:
                self.player.play()

    def _on_prev_clicked(self):
        if self._current_track_index > 0:
            self._play_track(self._current_track_index - 1)

    def _on_next_clicked(self):
        if self._current_track_index < len(self._tracks) - 1:
            self._play_track(self._current_track_index + 1)

    def _on_volume_changed(self, value: int):
        self.player.set_volume(value)

    def _on_position_changed(self, position: int):
        if not self.window.progress_slider.isSliderDown():
            duration = self.player._player.get_length()
            self.window.set_progress(position, duration)

    def _on_duration_changed(self, duration: int):
        pass

    def _on_playback_state_changed(self, state):
        is_playing = state == 1
        self.window.set_play_state(is_playing)

        if not is_playing and self._current_track_index < len(self._tracks) - 1:
            if self.player._player.get_time() >= self.player._player.get_length() - 500:
                self._on_next_clicked()

    def _on_progress_moved(self, position: int):
        duration = self.player._player.get_length()
        new_position = int((position / 100.0) * duration)
        self.player.set_position(new_position)

    def _format_duration(self, ms: int) -> str:
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
