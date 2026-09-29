"""Playback queue: the tracks currently playing, independent of the view.

Opening an album in the UI shows its tracklist (a *view*), but playback
lives in its own queue. Browsing another album must not disturb what is
currently playing or where auto-advance will go next.
"""


class PlaybackQueue:
    """Ordered list of tracks to play, with a current index.

    Tracks are dicts with at least ``title``, ``url``, ``duration``. The
    queue is mutated by ``next``/``previous`` and can be reloaded wholesale
    by ``load`` when the user picks a track from a (possibly different) view.
    """

    def __init__(self):
        self._tracks: list[dict] = []
        self._index = -1

    @property
    def tracks(self) -> list[dict]:
        return self._tracks

    @property
    def index(self) -> int:
        return self._index

    def load(self, tracks: list[dict], index: int = 0):
        self._tracks = list(tracks)
        self._index = index if 0 <= index < len(self._tracks) else -1

    def current(self) -> dict | None:
        if 0 <= self._index < len(self._tracks):
            return self._tracks[self._index]
        return None

    def has_next(self) -> bool:
        return self._index < len(self._tracks) - 1

    def has_previous(self) -> bool:
        return self._index > 0

    def next(self) -> dict | None:
        if self.has_next():
            self._index += 1
            return self.current()
        return None

    def previous(self) -> dict | None:
        if self.has_previous():
            self._index -= 1
            return self.current()
        return None

    def reset(self):
        """Drop playback position but keep tracks so Play can restart."""
        self._index = -1
