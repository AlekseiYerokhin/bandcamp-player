"""SVG icons and the icon button widget used across the UI."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QPushButton

SVG_PREV = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect x="4" y="5" width="2.5" height="14" fill="{c}"/><polygon points="19,5 8,12 19,19" fill="{c}"/></svg>'
SVG_NEXT = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="5,5 16,12 5,19" fill="{c}"/><rect x="17.5" y="5" width="2.5" height="14" fill="{c}"/></svg>'
SVG_PLAY = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="7,4 20,12 7,20" fill="{c}"/></svg>'
SVG_PAUSE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect x="5" y="4" width="4.5" height="16" rx="1" fill="{c}"/><rect x="14.5" y="4" width="4.5" height="16" rx="1" fill="{c}"/></svg>'
SVG_VOL_HIGH = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="3,9 7,9 12,4 12,20 7,15 3,15" fill="{c}"/><path d="M15.5,8.5 Q18,12 15.5,15.5" stroke="{c}" stroke-width="1.8" fill="none" stroke-linecap="round"/><path d="M18,5.5 Q22,12 18,18.5" stroke="{c}" stroke-width="1.8" fill="none" stroke-linecap="round"/></svg>'
SVG_VOL_MED = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="3,9 7,9 12,4 12,20 7,15 3,15" fill="{c}"/><path d="M16,8 Q19,12 16,16" stroke="{c}" stroke-width="1.8" fill="none" stroke-linecap="round"/></svg>'
SVG_VOL_LOW = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="3,9 7,9 12,4 12,20 7,15 3,15" fill="{c}"/></svg>'
SVG_VOL_MUTE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="3,9 7,9 12,4 12,20 7,15 3,15" fill="{c}"/><line x1="16" y1="9" x2="22" y2="15" stroke="{c}" stroke-width="2" stroke-linecap="round"/><line x1="22" y1="9" x2="16" y2="15" stroke="{c}" stroke-width="2" stroke-linecap="round"/></svg>'


def icon_from_svg(svg_template, size=24, color="#ffffff"):
    svg_str = svg_template.replace("{c}", color)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer = QSvgRenderer(svg_str.encode())
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


class IconButton(QPushButton):
    def __init__(self, svg_template, icon_size=20, normal_color="#b3b3b3", hover_color="#ffffff", parent=None):
        super().__init__(parent)
        self._svg = svg_template
        self._icon_size = icon_size
        self._normal_color = normal_color
        self._hover_color = hover_color
        self._update_icon(self._normal_color)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _update_icon(self, color):
        self.setIcon(icon_from_svg(self._svg, self._icon_size, color))
        self.setIconSize(QSize(self._icon_size, self._icon_size))

    def set_icon_svg(self, svg_template, color=None):
        self._svg = svg_template
        self._update_icon(color or self._normal_color)

    def enterEvent(self, event):
        self._update_icon(self._hover_color)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_icon(self._normal_color)
        super().leaveEvent(event)
