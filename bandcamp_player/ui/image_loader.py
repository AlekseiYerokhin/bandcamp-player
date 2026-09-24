"""Async image loading with an in-memory cache.

Loads cover art in the background, scales it, and applies it to QLabel
widgets. Caches by URL so revisiting an album/artist page does not re-download
images. Guards against deleted widgets (shiboken6.isValid) and supports
aborting all in-flight loads when a view is cleared.
"""

import shiboken6
from PySide6.QtCore import QObject, QUrl, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
_REFERER = "https://bandcamp.com/"


class ImageLoader(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = QNetworkAccessManager(self)
        self._manager.finished.connect(self._on_finished)
        self._pending = {}
        self._cache = {}

    def load(self, url, label, size=176):
        if not url:
            return
        if url.startswith("//"):
            url = "https:" + url
        qurl = QUrl(url)
        if not qurl.isValid():
            return
        cached = self._cache.get(url)
        if cached is not None:
            self._apply(label, cached, size)
            return
        request = QNetworkRequest(qurl)
        request.setRawHeader(b"User-Agent", _USER_AGENT.encode())
        request.setRawHeader(b"Referer", _REFERER.encode())
        reply = self._manager.get(request)
        self._pending[reply] = (url, label, size)

    def abort_all(self):
        for reply in list(self._pending):
            reply.abort()
        self._pending = {}

    def _on_finished(self, reply):
        entry = self._pending.pop(reply, None)
        if entry is None:
            reply.deleteLater()
            return
        url, label, size = entry
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            if data.size() > 0:
                pixmap = QPixmap()
                if pixmap.loadFromData(data):
                    self._cache[url] = pixmap
                    self._apply(label, pixmap, size)
        reply.deleteLater()

    def _apply(self, label, pixmap, size):
        if not shiboken6.isValid(label):
            return
        label.setPixmap(
            pixmap.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        label.setMinimumSize(1, 1)