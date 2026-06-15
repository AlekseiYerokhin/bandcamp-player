import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bandcamp Player (Qt)")
        self.resize(400, 200)
        
        layout = QVBoxLayout()
        label = QLabel("Hello from Qt on Linux Mint!", self)
        label.setStyleSheet("color: white; font-size: 18px;")
        layout.addWidget(label)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        
        # Simple dark theme
        self.setStyleSheet("QMainWindow { background-color: #1e1e1e; }")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
