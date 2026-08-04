from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt
from src.gui.custom_dialogs import _find_theme


class ProgressDialog(QDialog):
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(450, 160)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        from src import constants as c
        mode, self.accent = _find_theme(parent)
        light = mode != "Dark"
        self.dialog_bg = "#f4f5f7" if light else "#242424"
        self.text_color = "#1a1a1a" if light else "#ffffff"
        self.muted_color = "#666666" if light else "#a0a0a0"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.label = QLabel(message)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setStyleSheet(f"font-size: 13px; color: {self.text_color};")
        layout.addWidget(self.label)

        self.progressbar = QProgressBar()
        self.progressbar.setRange(0, 0)
        self.progressbar.setMinimumWidth(380)
        self.progressbar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {"#4a4a4a" if not light else "#b9c0cb"};
                border-radius: 5px;
                text-align: center;
                background-color: {"#333333" if not light else "#e6e8ec"};
            }}
            QProgressBar::chunk {{
                background-color: {self.accent};
            }}
        """)
        layout.addWidget(self.progressbar)

        self.setStyleSheet(f"background-color: {self.dialog_bg};")

    def set_message(self, text):
        self.label.setText(text)

    def close(self):
        self.accept()
