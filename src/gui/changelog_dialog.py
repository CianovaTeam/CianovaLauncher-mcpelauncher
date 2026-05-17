from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel, QFrame
from PySide6.QtCore import Qt
import os
from src import constants as c
from src.utils.resource_path import resource_path
from src.utils.image_manager import ImageManager

class ChangelogDialog(QDialog):
    def __init__(self, parent, version=None):
        super().__init__(parent)
        ver_str = version if version else c.VERSION_LAUNCHER
        self.setWindowTitle(c.UI_WELCOME_NEW_VERSION_TITLE.format(ver=ver_str))
        self.resize(700, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.setup_ui(ver_str)

    def setup_ui(self, version):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header with Icon
        header = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(ImageManager.get_image("icon.png", size=(48, 48)))
        header.addWidget(icon_lbl)

        title = QLabel(c.UI_WELCOME_NEW_VERSION_TITLE.format(ver=version))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        header.addWidget(title, 1)
        layout.addLayout(header)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #444444;")
        line.setFixedHeight(1)
        layout.addWidget(line)

        # Changelog View
        from PySide6.QtWidgets import QTextBrowser
        self.txt_view = QTextBrowser()
        self.txt_view.setReadOnly(True)
        self.txt_view.setFrameShape(QFrame.NoFrame)
        self.txt_view.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-size: 13px; padding: 10px;")
        
        # Loading content
        content = self.load_changelog()
        self.txt_view.setMarkdown(content)
        layout.addWidget(self.txt_view)

        # Button
        btn_close = QPushButton("OK")
        btn_close.setFixedHeight(40)
        btn_close.setFixedWidth(120)
        btn_close.setStyleSheet(f"background-color: {c.COLOR_PRIMARY_GREEN}; color: white; font-weight: bold; border-radius: 8px;")
        btn_close.clicked.connect(self.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def load_changelog(self):
        try:
            path = resource_path("Docs/Changelog.md")
            if not os.path.exists(path):
                # Fallback to local dev path
                path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Docs/Changelog.md")
            
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"# Error\nNo se pudo cargar el historial de cambios: {e}"
