from PySide6.QtCore import QObject

from .bandcamp_api import BandcampAPI
from .engine import BandcampEngine
from .player import AudioPlayer
from .queue import PlaybackQueue


class Controller(QObject):
    def __init__(self, window, parent=None, engine=None, player=None, mpris=None):
        super().__init__(parent)
        self.window = window
        self.engine = engine or BandcampEngine()
        self.player = player or AudioPlayer()
        self.mpris = mpris
        self._current_band_id: int | None = None
        self._current_tralbum_id: int | None = None
        self._current_tralbum_type = 'a'
        self._current_album_title = ""
        self._current_artist = ""
        self._current_art_url = ""

        self._view_tracks: list[dict] = []
        self._view_album_key: tuple | None = None
        self._queue = PlaybackQueue()
        self._queue_album_key: tuple | None = None
        self._playing = False
        self._refreshing_queue = False
        self._nav_stack: list[str] = ['search']

        self._search_results = {'album': [], 'track': [], 'artist': []}
        self._last_query = ""

        self._mpris_commands = self._setup_mpris_commands()

        self._connect_signals()
        self._setup_player()

    def _connect_signals(self):
        self.window.closing.connect(self._on_window_closing)
        self.window.search_requested.connect(self._on_search_requested)
        self.window.back_requested.connect(self._on_back)
        self.engine.search_results_ready.connect(self._on_search_results)
        self.engine.album_data_ready.connect(self._on_album_data)
        self.engine.artist_data_ready.connect(self._on_artist_data)

        self.player.position_changed.connect(self._on_position_changed)
        self.player.playback_state_changed.connect(self._on_playback_state_changed)
        self.player.track_ended.connect(self._on_track_ended)
        self.player.playback_error.connect(self._on_playback_error)

        self.window.play_pause_requested.connect(self._on_play_pause_clicked)
        self.window.previous_requested.connect(self._on_prev_clicked)
        self.window.next_requested.connect(self._on_next_clicked)
        self.window.volume_changed.connect(self._on_volume_changed)
        self.window.progress_moved.connect(self._on_progress_moved)
        self.window.seek_requested.connect(self._on_seek_requested)
        if self.mpris is not None:
            self.mpris.command_requested.connect(self._on_mpris_command)
            self.mpris.volume_requested.connect(self._on_mpris_volume)

    def _setup_player(self):
        self.player.set_volume(self.window.get_volume())

    def _on_window_closing(self):
        self.engine.cleanup()
        self.player.cleanup()

    def _on_search_requested(self, query: str):
        self._nav_stack = ['search']
        self._last_query = query
        self.window.clear_results()
        self.window.show_search_loading()
        self.engine.search(query)

    def _on_search_results(self, success: bool, results: list, error: str = ""):
        self.window.search_finished()

        if not success:
            self.window.show_search_results()
            self.window.show_search_placeholder(error or "Search failed")
            return

        self._search_results = {'album': [], 'track': [], 'artist': []}

        for result in results:
            result_type = result.get('type', 'album')
            if result_type in self._search_results:
                self._search_results[result_type].append(result)

        self.window.clear_results()

        if not any(self._search_results.values()):
            self.window.show_search_results()
            self.window.show_search_placeholder(f'No results for "{self._last_query}"')
            return

        for result_type in ['album', 'track', 'artist']:
            if self._search_results[result_type]:
                self._display_search_section(result_type)

        self.window.show_search_results()

    def _display_search_section(self, result_type: str):
        items = self._search_results[result_type]
        self.window.add_search_section(result_type)

        for result in items:
            card = self.window.add_album_to_results(
                result['title'],
                result['artist'],
                result.get('image_url') or None,
                result_type
            )
            if card:
                card.set_click_data(result['band_id'], result['id'], result_type)
                card.clicked.connect(self._on_result_clicked)

    def _on_result_clicked(self, band_id, item_id, result_type):
        if result_type == 'album':
            self._on_album_clicked(band_id, item_id, 'a')
        elif result_type == 'track':
            self._on_album_clicked(band_id, item_id, 't')
        elif result_type == 'artist':
            self._on_artist_clicked(band_id)

    def _on_album_clicked(self, band_id, tralbum_id, tralbum_type='a'):
        self._current_band_id = band_id
        self._current_tralbum_id = tralbum_id
        self._current_tralbum_type = tralbum_type
        self.window.show_tracklist_placeholder("Loading tracklist...")
        self.engine.get_album_data(band_id, tralbum_id, tralbum_type)

    def _on_artist_clicked(self, band_id):
        self._current_band_id = band_id
        self.window.show_discography_placeholder("Loading discography...")
        self.engine.get_artist_data(band_id)

    def _on_album_data(self, success: bool, data: dict, error: str = ""):
        if success:
            if self._refreshing_queue:
                self._refreshing_queue = False
                self._refresh_queue_urls(data)
                track = self._queue.current()
                if track and track.get('url'):
                    self._play_current()
                else:
                    self.window.show_status("Playback error")
                return
            self._display_album(data)
        else:
            self.window.show_status(error or "Failed to load album")

    def _on_artist_data(self, success: bool, data: dict, error: str = ""):
        if success:
            self._display_artist_discography(data)
        else:
            self.window.show_status(error or "Failed to load artist")

    def _display_album(self, data: dict):
        album_title = data.get('title', 'Unknown Album')
        self.window.set_album_title(album_title)
        self._current_album_title = album_title
        self._current_artist = data.get('artist', '')

        self.window.clear_tracklist()

        art_id = data.get('art_id')
        self._current_art_url = BandcampAPI.image_url(art_id, "16") if art_id else ""
        if art_id:
            self.window.set_album_cover(self._current_art_url)

        track_list = data.get('tracks', [])
        self._view_tracks = []
        for i, track in enumerate(track_list, 1):
            title = track.get('title', 'Unknown')
            duration_ms = int(track.get('duration', 0))
            duration_str = self._format_duration(duration_ms)
            url = track.get('url', '')

            self._view_tracks.append({
                'title': title,
                'url': url,
                'duration': duration_ms,
                'track_num': i,
            })

            track_widget = self.window.add_track_to_tracklist(i, title, duration_str, streamable=bool(url))
            track_widget.clicked.connect(self._play_track)

        if not track_list:
            self.window.show_tracklist_placeholder("No tracks to play")

        self._view_album_key = (self._current_band_id, self._current_tralbum_id, self._current_tralbum_type)
        self.window.highlight_track(-1)
        self._nav_stack.append('album')
        self.window.show_tracklist()

    def _display_artist_discography(self, data: dict):
        artist_name = data.get('name', 'Unknown Artist')
        self.window.set_artist_name(artist_name)
        self.window.set_artist_bio(data.get('bio', ''))

        self.window.clear_discography()

        image_url = data.get('image_url')
        if image_url:
            self.window.set_artist_image(image_url)

        band_id = self._current_band_id
        albums = data.get('albums', [])
        for album in albums:
            title = album.get('title', 'Unknown')
            album_image = album.get('image_url')
            album_type = album.get('item_type', 'album')

            card = self.window.add_discography_album(title, album_image, album_type)
            if card and album.get('item_id'):
                card.set_click_data(band_id, album['item_id'], album_type)
                card.clicked.connect(self._on_album_clicked)

        if not albums:
            self.window.show_discography_placeholder("No releases found")

        if self._nav_stack[-1:] != ['artist']:
            self._nav_stack.append('artist')
        self.window.show_artist_discography()

    def _on_back(self):
        if len(self._nav_stack) > 1:
            self._nav_stack.pop()
        target = self._nav_stack[-1] if self._nav_stack else 'search'
        if target == 'artist':
            self.window.show_artist_discography()
        else:
            self._nav_stack = ['search']
            self.window.show_search_results()

    def _play_track(self, index: int):
        if not 0 <= index < len(self._view_tracks):
            return
        track = self._view_tracks[index]
        if not track.get('url'):
            self.window.show_status("This track is not available for streaming")
            return
        self._queue.load(self._view_tracks, index)
        self._queue_album_key = self._view_album_key
        self._play_current()

    def _play_current(self):
        track = self._queue.current()
        if track is None:
            return
        if not track.get('url'):
            self.window.show_status("This track is not available for streaming")
            return
        self.player.load_and_play(track['url'])
        self._playing = True
        self.window.set_current_track(track['title'])
        self.window.set_current_artist(self._current_artist)
        if self._queue_album_key == self._view_album_key:
            self.window.highlight_track(self._queue.index)
        else:
            self.window.highlight_track(-1)
        self._mpris_track_changed(track)
        self._update_mpris_navigation()

    def _start_or_resume(self):
        if self._queue.current() is not None:
            self.player.play()
            self._playing = True
            self._set_mpris_playing(True)
            return
        if self._queue.tracks:
            self._queue.load(self._queue.tracks, 0)
            self._play_current()
        elif self._view_tracks:
            self._play_track(0)

    def _mpris_track_changed(self, track: dict):
        if self.mpris is None:
            return
        self.mpris.set_track(
            track['title'],
            artist=self._current_artist or "",
            album=self._current_album_title or "",
            duration_ms=track.get('duration', 0),
            art_url=self._current_art_url or "",
        )
        self.mpris.set_playback("Playing")

    def _update_mpris_navigation(self):
        if self.mpris is not None:
            self.mpris.set_navigation(self._queue.has_next(), self._queue.has_previous())

    def _on_mpris_command(self, command: str, arg: int):
        handler = self._mpris_commands.get(command)
        if handler is not None:
            handler(arg)

    def _setup_mpris_commands(self) -> dict:
        return {
            "play": self._mpris_play,
            "pause": self._mpris_pause,
            "play_pause": lambda arg: self._on_play_pause_clicked(),
            "next": lambda arg: self._on_next_clicked(),
            "previous": lambda arg: self._on_prev_clicked(),
            "stop": self._mpris_stop,
            "seek": self._mpris_seek,
            "set_position": self._mpris_set_position,
            "raise": self._mpris_raise,
            "quit": lambda arg: self.window.quit(),
        }

    def _mpris_play(self, arg):
        self._start_or_resume()

    def _mpris_pause(self, arg):
        self.player.pause()
        self._playing = False
        self._set_mpris_playing(False)

    def _mpris_stop(self, arg):
        self.player.stop()
        self._playing = False
        self._set_mpris_playing(False)

    def _mpris_seek(self, arg):
        current = self.player.get_time()
        self.player.set_position(max(0, current + arg // 1000))
        self._mpris_seeked()

    def _mpris_set_position(self, arg):
        self.player.set_position(arg // 1000)
        self._mpris_seeked()

    def _mpris_raise(self, arg):
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _on_mpris_volume(self, volume: float):
        value = int(volume * 100)
        self.player.set_volume(value)
        self.window.set_volume(value)

    def _mpris_seeked(self):
        if self.mpris is not None:
            self.mpris.emit_seeked(self.player.get_time())

    def _set_mpris_playing(self, playing: bool):
        if self.mpris is not None:
            self.mpris.set_playback("Playing" if playing else "Paused")

    def _on_play_pause_clicked(self):
        if self._playing:
            self.player.pause()
            self._playing = False
            self._set_mpris_playing(False)
        else:
            self._start_or_resume()

    def _on_prev_clicked(self):
        if self.player.get_time() > 3000:
            self.player.set_position(0)
            self._mpris_seeked()
        elif self._queue.has_previous():
            self._queue.previous()
            self._play_current()
        else:
            self.player.set_position(0)

    def _on_next_clicked(self):
        nxt = self._queue.next()
        if nxt is not None:
            self._play_current()

    def _on_volume_changed(self, value: int):
        self.player.set_volume(value)

    def _on_position_changed(self, position: int):
        duration = self.player.get_length()
        if not self.window.is_progress_slider_down():
            self.window.set_progress(position, duration)
        self.window.set_time(position, duration)
        if self.mpris is not None:
            self.mpris.set_position_ms(position)

    def _on_playback_state_changed(self, state):
        self._playing = state == 1
        self.window.set_play_state(self._playing)

    def _on_track_ended(self):
        nxt = self._queue.next()
        if nxt is not None:
            self._play_current()
        else:
            self._queue.reset()
            self._playing = False
            self.window.set_play_state(False)
            self._update_mpris_navigation()
            if self.mpris is not None:
                self.mpris.set_playback("Stopped")

    def _on_playback_error(self):
        self._playing = False
        self.window.set_play_state(False)
        self._set_mpris_playing(False)
        if self._queue_album_key and self._queue.index >= 0:
            self._refreshing_queue = True
            band_id, tralbum_id, tralbum_type = self._queue_album_key
            self.engine.get_album_data(band_id, tralbum_id, tralbum_type)
            return
        self.window.show_status("Playback error")

    def _refresh_queue_urls(self, data: dict):
        """Re-resolve stream URLs from a fresh album fetch (stale tokens)."""
        fresh_urls = [t.get('url', '') for t in data.get('tracks', [])]
        for i, track in enumerate(self._queue.tracks):
            if i < len(fresh_urls) and fresh_urls[i]:
                track['url'] = fresh_urls[i]
        if self._queue_album_key == self._view_album_key:
            self._view_tracks = self._queue.tracks

    def _on_progress_moved(self, position: int):
        self.player.set_position(position)
        self._mpris_seeked()

    def _on_seek_requested(self, offset_ms: int):
        current = self.player.get_time()
        self.player.set_position(max(0, current + offset_ms))
        self._mpris_seeked()

    def _format_duration(self, ms: int) -> str:
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
