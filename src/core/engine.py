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

    def cleanup(self):
        pass

    def search(self, query):
        threading.Thread(target=self._search_worker, args=(query,), daemon=True).start()

    def get_artist_data(self, band_id):
        threading.Thread(target=self._artist_worker, args=(band_id,), daemon=True).start()

    def get_album_data(self, band_id, tralbum_id, tralbum_type="a"):
        threading.Thread(
            target=self._album_worker,
            args=(band_id, tralbum_id, tralbum_type),
            daemon=True,
        ).start()

    def _search_worker(self, query):
        try:
            results = self._api.search(query)
            self.search_results_ready.emit(True, results)
        except BandcampAPIError:
            self.search_results_ready.emit(False, [])

    def _artist_worker(self, band_id):
        try:
            data = self._api.band_details(band_id)
            self.artist_data_ready.emit(True, data)
        except BandcampAPIError:
            self.artist_data_ready.emit(False, {})

    def _album_worker(self, band_id, tralbum_id, tralbum_type):
        try:
            data = self._api.tralbum_details(band_id, tralbum_id, tralbum_type)
            self.album_data_ready.emit(True, data)
        except BandcampAPIError:
            self.album_data_ready.emit(False, {})