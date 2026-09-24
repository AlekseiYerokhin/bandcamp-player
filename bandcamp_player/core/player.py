from typing import Any

import vlc
from PySide6.QtCore import QObject, QTimer, Signal


class AudioPlayer(QObject):
    position_changed = Signal(int)
    playback_state_changed = Signal(int)
    track_ended = Signal()
    playback_error = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._instance: Any = vlc.Instance("--no-plugins-cache", "--ignore-config")
        self._player: Any = self._instance.media_player_new()

        self._position_timer = QTimer(self)
        self._position_timer.setInterval(500)
        self._position_timer.timeout.connect(self._update_position)

        event_manager = self._player.event_manager()
        event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)
        event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_error)

    def load_and_play(self, stream_url: str):
        media = self._instance.media_new(stream_url)
        media.add_option(':http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)')

        self._player.set_media(media)
        self._player.play()
        self._position_timer.start()
        self.playback_state_changed.emit(1)

    def play(self):
        self._player.play()
        self._position_timer.start()
        self.playback_state_changed.emit(1)

    def pause(self):
        self._player.set_pause(1)
        self._position_timer.stop()
        self.playback_state_changed.emit(0)

    def stop(self):
        self._player.stop()
        self._position_timer.stop()
        self.playback_state_changed.emit(0)

    def set_volume(self, volume: int):
        self._player.audio_set_volume(volume)

    def set_position(self, position_ms: int):
        duration = self._player.get_length()
        if duration > 0:
            self._player.set_position(position_ms / duration)

    def is_playing(self) -> bool:
        return self._player.is_playing()

    def get_length(self) -> int:
        return self._player.get_length()

    def get_time(self) -> int:
        return self._player.get_time()

    def cleanup(self):
        self.stop()
        self._position_timer.stop()

    def _update_position(self):
        self.position_changed.emit(self._player.get_time())

    def _on_end_reached(self, event):
        self.track_ended.emit()

    def _on_error(self, event):
        self.playback_error.emit()
