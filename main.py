import logging
import signal
import sys

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from bandcamp_player.core.controller import Controller
from bandcamp_player.mpris import MprisService
from bandcamp_player.ui.main_window import MainWindow


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = QApplication(sys.argv)
    QCoreApplication.setOrganizationName("bandcamp-player")
    QCoreApplication.setApplicationName("bandcamp-player")
    mpris = MprisService()
    mpris.start()
    window = MainWindow()
    controller = Controller(window, mpris=mpris)
    window.show()
    window.raise_()
    window.activateWindow()

    def handle_sigint(*args):
        controller.engine.cleanup()
        controller.player.cleanup()
        for _ in range(3):
            app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents)
        app.quit()

    signal.signal(signal.SIGINT, handle_sigint)

    timer = QTimer()
    timer.start(200)
    timer.timeout.connect(lambda: None)

    result = app.exec()

    controller.engine.cleanup()
    controller.player.cleanup()
    sys.exit(result)


if __name__ == "__main__":
    main()
