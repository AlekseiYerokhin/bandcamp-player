from PySide6.QtCore import QObject, Qt
from .engine import BandcampEngine
from .player import AudioPlayer


class Controller(QObject):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.engine = BandcampEngine()
        self.player = AudioPlayer()
        self._current_album_url = None
        self._tracks = []
        self._current_track_index = -1

        self._connect_signals()
        self._setup_player()

    def _connect_signals(self):
        self.window.closing.connect(self._on_window_closing)
        self.window.search_requested.connect(self._on_search_requested)
        self.engine.search_results_ready.connect(self._on_search_results)
        self.engine.album_data_ready.connect(self._on_album_data)

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
        self.player.stop()

    def _on_search_requested(self, query: str):
        self.window.clear_results()
        self.engine.search(query)

    def _on_search_results(self, success: bool, results: list):
        self.window.search_finished()

        if success:
            for result in results:
                card = self.window.add_album_to_results(
                    result['title'],
                    result['artist'],
                    result.get('image_url') or None
                )
                if card:
                    card.mousePressEvent = lambda e, url=result['url']: self._on_album_clicked(url)

    def _on_album_clicked(self, url: str):
        self._current_album_url = url
        self.engine.get_album_data(url)

    def _on_album_data(self, success: bool, data: dict):
        if success:
            self._display_album(data)

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

    def _play_track(self, index: int):
        if 0 <= index < len(self._tracks):
            self._current_track_index = index
            track = self._tracks[index]

            self.player.load_and_play(track['url'], self._current_album_url)
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
