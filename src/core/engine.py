import json
from PySide6.QtCore import QObject, Signal, QUrl, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from .network import BandcampRequestInterceptor


class SilentWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, source_id):
        pass


class BandcampEngine(QObject):
    login_completed = Signal(bool, dict)
    album_data_ready = Signal(bool, dict)
    search_results_ready = Signal(bool, list)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._interceptor = BandcampRequestInterceptor()

        self._profile = QWebEngineProfile("bandcamp_profile", self)
        self._profile.setUrlRequestInterceptor(self._interceptor)

        self._page = SilentWebEnginePage(self._profile, self)
        self._page.loadFinished.connect(self._on_page_load_finished)
        self._pending_action = None
        self._pending_url = None
        self._login_view = None

        self._search_page = SilentWebEnginePage(self._profile, self)
        self._search_page.loadFinished.connect(self._on_search_page_load_finished)

    def cleanup(self):
        if hasattr(self, '_login_view') and self._login_view:
            self._login_view.close()
            self._login_view.deleteLater()
            self._login_view = None
        if hasattr(self, '_page') and self._page:
            self._page.deleteLater()
            self._page = None
        if hasattr(self, '_search_page') and self._search_page:
            self._search_page.deleteLater()
            self._search_page = None
        if hasattr(self, '_profile') and self._profile:
            self._profile.deleteLater()
            self._profile = None

    def __del__(self):
        self.cleanup()

    def login(self):
        self._login_view = QWebEngineView()
        self._login_view.setPage(self._page)
        self._login_view.setWindowTitle("Bandcamp Login")
        self._login_view.resize(800, 600)
        self._login_view.setUrl(QUrl("https://www.bandcamp.com/login"))
        self._login_view.loadFinished.connect(self._on_login_page_load_finished)
        self._login_view.show()

    def _on_login_page_load_finished(self, ok):
        if not ok:
            return

        current_url = self._login_view.url().toString()
        if "bandcamp.com/login" not in current_url and "bandcamp.com/home" in current_url:
            self._login_view.page().runJavaScript(
                "document.cookie",
                lambda result: self._extract_login_cookies(result)
            )

    def _extract_login_cookies(self, cookie_string):
        cookies = {}
        if cookie_string:
            for item in cookie_string.split(";"):
                if "=" in item:
                    key, value = item.strip().split("=", 1)
                    cookies[key] = value

        has_required = "client_id" in cookies and "user_id" in cookies or "fan_id" in cookies
        if has_required:
            self._login_view.close()
            self._login_view = None
            self.login_completed.emit(True, cookies)

    def get_album_data(self, url):
        self._pending_action = "album_data"
        self._pending_url = url
        self._interceptor.set_referer(url)
        self._page.setUrl(QUrl(url))

    def _on_page_load_finished(self, ok):
        if self._pending_action == "album_data":
            if ok:
                QTimer.singleShot(1000, self._extract_tralbum_data)
            else:
                self.album_data_ready.emit(False, {})
                self._pending_action = None

    def _extract_tralbum_data(self):
        js_code = """
        (function() {
            if (typeof TralbumData !== 'undefined') {
                return JSON.stringify(TralbumData);
            }
            var scripts = document.querySelectorAll('script');
            for (var i = 0; i < scripts.length; i++) {
                var text = scripts[i].textContent;
                var match = text.match(/var\\s+TralbumData\\s*=\\s*({[\\s\\S]*?});/);
                if (match) {
                    try {
                        return JSON.stringify(TralbumData);
                    } catch(e) {
                        return null;
                    }
                }
            }
            return null;
        })()
        """
        self._page.runJavaScript(js_code, self._on_tralbum_data_extracted)

    def _on_tralbum_data_extracted(self, result):
        if result:
            try:
                data = json.loads(result)
                self.album_data_ready.emit(True, data)
            except json.JSONDecodeError:
                self.album_data_ready.emit(False, {})
        else:
            self.album_data_ready.emit(False, {})
        self._pending_action = None

    def search(self, query: str):
        self._pending_action = "search"
        encoded_query = query.replace(' ', '+')
        url = f"https://bandcamp.com/search?q={encoded_query}&item_type=a"
        self._search_page.setUrl(QUrl(url))

    def _on_search_page_load_finished(self, ok):
        if self._pending_action == "search":
            if ok:
                QTimer.singleShot(2000, self._extract_search_results)
            else:
                self.search_results_ready.emit(False, [])
                self._pending_action = None

    def _extract_search_results(self):
        js_code = """
        (function() {
            var results = [];
            var items = document.querySelectorAll('.result-items li.searchresult');
            if (items.length === 0) {
                items = document.querySelectorAll('.search .result-items li');
            }
            if (items.length === 0) {
                items = document.querySelectorAll('[data-result]');
            }
            for (var i = 0; i < Math.min(items.length, 20); i++) {
                var item = items[i];
                var heading = item.querySelector('.heading a') || item.querySelector('a[itemprop="url"]') || item.querySelector('.itemurl a') || item.querySelector('h2 a, h3 a, .title a');
                var subhead = item.querySelector('.subhead') || item.querySelector('.iteminfo .subhead');
                var art = item.querySelector('.art img') || item.querySelector('.item img') || item.querySelector('img');

                if (heading) {
                    var imgUrl = '';
                    if (art) {
                        imgUrl = art.getAttribute('data-original') || art.getAttribute('src') || '';
                        if (imgUrl && imgUrl.startsWith('//')) {
                            imgUrl = 'https:' + imgUrl;
                        }
                    }
                    results.push({
                        title: heading.textContent.trim(),
                        artist: subhead ? subhead.textContent.trim().replace(/^by\\s+/i, '').replace(/^from\\s+/i, '') : '',
                        url: heading.href || '',
                        image_url: imgUrl
                    });
                }
            }
            return JSON.stringify(results);
        })()
        """
        self._search_page.runJavaScript(js_code, self._on_search_results_extracted)

    def _on_search_results_extracted(self, result):
        if result:
            try:
                data = json.loads(result)
                self.search_results_ready.emit(True, data)
            except json.JSONDecodeError:
                self.search_results_ready.emit(False, [])
        else:
            self.search_results_ready.emit(False, [])
        self._pending_action = None
