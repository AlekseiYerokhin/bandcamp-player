import logging
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QObject, Signal

from .bandcamp_api import BandcampAPI, BandcampAPIError

logger = logging.getLogger(__name__)


class BandcampEngine(QObject):
    album_data_ready = Signal(bool, dict, str)
    search_results_ready = Signal(bool, list, str)
    artist_data_ready = Signal(bool, dict, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._api = BandcampAPI()
        self._search_id = 0
        self._artist_id = 0
        self._album_id = 0
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="engine")

    def cleanup(self):
        self._executor.shutdown(wait=False, cancel_futures=True)

    def search(self, query):
        self._search_id += 1
        search_id = self._search_id
        self._executor.submit(self._search_worker, query, search_id)

    def get_artist_data(self, band_id):
        self._artist_id += 1
        artist_id = self._artist_id
        self._executor.submit(self._artist_worker, band_id, artist_id)

    def get_album_data(self, band_id, tralbum_id, tralbum_type="a"):
        self._album_id += 1
        album_id = self._album_id
        self._executor.submit(
            self._album_worker,
            band_id,
            tralbum_id,
            tralbum_type,
            album_id,
        )

    def _search_worker(self, query, search_id):
        ok, results, error = True, None, ""
        try:
            results = self._api.search(query)
        except BandcampAPIError as e:
            ok, error = False, str(e)
            logger.error("Search failed: %s", e)
        except Exception as e:
            ok, error = False, str(e)
            logger.exception("Unexpected error during search")
        if search_id == self._search_id:
            self.search_results_ready.emit(ok, results if ok else [], error)

    def _artist_worker(self, band_id, artist_id):
        ok, data, error = True, None, ""
        try:
            data = self._api.band_details(band_id)
        except BandcampAPIError as e:
            ok, error = False, str(e)
            logger.error("Artist fetch failed: %s", e)
        except Exception as e:
            ok, error = False, str(e)
            logger.exception("Unexpected error during artist fetch")
        if artist_id == self._artist_id:
            self.artist_data_ready.emit(ok, data if ok else {}, error)

    def _album_worker(self, band_id, tralbum_id, tralbum_type, album_id):
        ok, data, error = True, None, ""
        try:
            data = self._api.tralbum_details(band_id, tralbum_id, tralbum_type)
        except BandcampAPIError as e:
            ok, error = False, str(e)
            logger.error("Album fetch failed: %s", e)
        except Exception as e:
            ok, error = False, str(e)
            logger.exception("Unexpected error during album fetch")
        if album_id == self._album_id:
            self.album_data_ready.emit(ok, data if ok else {}, error)
