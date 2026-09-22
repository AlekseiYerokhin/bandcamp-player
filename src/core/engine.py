import threading

from PySide6.QtCore import QObject, Signal

from .bandcamp_api import BandcampAPI, BandcampAPIError


class BandcampEngine(QObject):
    album_data_ready = Signal(bool, dict)
    search_results_ready = Signal(bool, list)
    artist_data_ready = Signal(bool, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._api = BandcampAPI()
        self._search_id = 0
        self._artist_id = 0
        self._album_id = 0

    def cleanup(self):
        pass

    def search(self, query):
        self._search_id += 1
        search_id = self._search_id
        threading.Thread(target=self._search_worker, args=(query, search_id), daemon=True).start()

    def get_artist_data(self, band_id):
        self._artist_id += 1
        artist_id = self._artist_id
        threading.Thread(target=self._artist_worker, args=(band_id, artist_id), daemon=True).start()

    def get_album_data(self, band_id, tralbum_id, tralbum_type="a"):
        self._album_id += 1
        album_id = self._album_id
        threading.Thread(
            target=self._album_worker,
            args=(band_id, tralbum_id, tralbum_type, album_id),
            daemon=True,
        ).start()

    def _search_worker(self, query, search_id):
        try:
            results = self._api.search(query)
        except BandcampAPIError:
            results = None
        if search_id == self._search_id:
            if results is None:
                self.search_results_ready.emit(False, [])
            else:
                self.search_results_ready.emit(True, results)

    def _artist_worker(self, band_id, artist_id):
        try:
            data = self._api.band_details(band_id)
        except BandcampAPIError:
            data = None
        if artist_id == self._artist_id:
            if data is None:
                self.artist_data_ready.emit(False, {})
            else:
                self.artist_data_ready.emit(True, data)

    def _album_worker(self, band_id, tralbum_id, tralbum_type, album_id):
        try:
            data = self._api.tralbum_details(band_id, tralbum_id, tralbum_type)
        except BandcampAPIError:
            data = None
        if album_id == self._album_id:
            if data is None:
                self.album_data_ready.emit(False, {})
            else:
                self.album_data_ready.emit(True, data)
