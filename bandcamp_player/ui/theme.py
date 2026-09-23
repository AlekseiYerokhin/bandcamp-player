"""Dark theme stylesheet for the Bandcamp player."""


STYLESHEET = """
QMainWindow {
    background-color: #121212;
}
QStatusBar {
    background-color: #181818;
    color: #b3b3b3;
    border-top: 1px solid #282828;
}
#searchFrame {
    background-color: #181818;
    border-bottom: 1px solid #282828;
}
#searchInput {
    background-color: #2a2a2a;
    color: #ffffff;
    border: 1px solid #3a3a3a;
    border-radius: 20px;
    padding: 8px 15px;
    font-size: 14px;
}
#searchInput:focus {
    border: 1px solid #0cacd7;
}
#searchButton {
    background-color: #0cacd7;
    color: #ffffff;
    border: none;
    border-radius: 20px;
    padding: 8px 25px;
    font-size: 14px;
    font-weight: bold;
}
#searchButton:hover {
    background-color: #2ec4e0;
}
#searchButton:pressed {
    background-color: #0a98be;
}
#centralStack {
    background-color: #121212;
    color: #ffffff;
}
#resultsScroll, #tracklistScroll, #discographyScroll {
    background-color: #121212;
    border: none;
    color: #ffffff;
}
#resultsContainer {
    background-color: #121212;
    color: #ffffff;
}
#tracklistContainer {
    background-color: #121212;
    color: #ffffff;
}
#albumTitle {
    color: #ffffff;
    font-size: 24px;
    font-weight: bold;
}
#artistName {
    color: #ffffff;
    font-size: 24px;
    font-weight: bold;
}
#backButton {
    background-color: transparent;
    color: #b3b3b3;
    border: none;
    font-size: 14px;
    padding: 5px 10px;
}
#backButton:hover {
    color: #ffffff;
}
#trackItem {
    background-color: transparent;
    color: #ffffff;
    padding: 10px;
    border-radius: 4px;
}
#trackItem:hover {
    background-color: #282828;
}
#trackItem[active="true"] {
    background-color: #233a42;
}
#sectionHeader {
    background-color: transparent;
    color: #ffffff;
    font-size: 20px;
    font-weight: bold;
    padding: 5px 10px;
    border: none;
    border-radius: 4px;
    text-align: left;
}
#sectionHeader:hover {
    background-color: #282828;
}
#playerBar {
    background-color: #181818;
    border-top: 1px solid #282828;
}
#controlButton {
    background-color: transparent;
    border: none;
    border-radius: 20px;
}
#controlButton:hover {
    background-color: #282828;
}
#playPauseButton {
    background-color: #0cacd7;
    border: none;
    border-radius: 25px;
}
#playPauseButton:hover {
    background-color: #2ec4e0;
}
#trackLabel {
    color: #ffffff;
    font-size: 13px;
}
#timeLabel {
    color: #b3b3b3;
    font-size: 12px;
}
#progressSlider::groove:horizontal {
    background: #4d4d4d;
    height: 4px;
    border-radius: 2px;
}
#progressSlider::handle:horizontal {
    background: #0cacd7;
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
#progressSlider::sub-page:horizontal {
    background: #0cacd7;
    border-radius: 2px;
}
#volumeSlider::groove:horizontal {
    background: #4d4d4d;
    height: 4px;
    border-radius: 2px;
}
#volumeSlider::handle:horizontal {
    background: #b3b3b3;
    width: 10px;
    height: 10px;
    margin: -3px 0;
    border-radius: 5px;
}
#volumeSlider::sub-page:horizontal {
    background: #b3b3b3;
    border-radius: 2px;
}
"""
