from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt

class ProgressDialog(QDialog):
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(400, 150)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        from src import constants as c
        self.label = QLabel(message)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 13px; color: white;")
        layout.addWidget(self.label)

        self.progressbar = QProgressBar()
        self.progressbar.setRange(0, 0) # Indeterminate mode
        self.progressbar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                background-color: #333333;
            }
            QProgressBar::chunk {
                background-color: #1f6aa5;
            }
        """)
        layout.addWidget(self.progressbar)

        self.setStyleSheet("background-color: #2b2b2b;")

    def close(self):
        self.accept()
