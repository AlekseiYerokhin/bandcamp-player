import signal
import sys

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from src.core.controller import Controller
from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    controller = Controller(window)
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
