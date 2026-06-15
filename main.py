import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.core.controller import Controller


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    controller = Controller(window)
    window.show()

    result = app.exec()

    sys.exit(result)


if __name__ == "__main__":
    main()
