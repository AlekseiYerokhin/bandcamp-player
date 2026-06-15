from PySide6.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PySide6.QtCore import QObject


class BandcampRequestInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._referer_url = ""

    def set_referer(self, url):
        self._referer_url = url

    def interceptRequest(self, info):
        url = info.requestUrl().toString()

        if ".mp3" in url or ".ogg" in url:
            if self._referer_url:
                info.setHttpHeader(b"Referer", self._referer_url.encode())
