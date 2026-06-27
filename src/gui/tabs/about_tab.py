from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame
from PySide6.QtCore import Qt
from src import constants as c

class AboutTab(QWidget):
    """Tab displaying legal information, credits, and the launcher version."""
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 10, 20, 10)

        # Title
        self.title_label = QLabel(c.t("UI_TITLE_LEGAL"))
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.main_layout.addWidget(self.title_label)

        # Legal Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setObjectName("GroupFrame")

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)

        self.lbl_legal = QLabel(c.t("LEGAL_TEXT"))
        self.lbl_legal.setWordWrap(True)
        self.lbl_legal.setStyleSheet("font-size: 11px;")
        self.lbl_legal.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll_layout.addWidget(self.lbl_legal)

        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area, 1)

        # Credits
        self.credits_label = QLabel(c.t("CREDITOS"))
        self.credits_label.setAlignment(Qt.AlignCenter)
        self.credits_label.setStyleSheet("font-size: 12px;")
        self.main_layout.addWidget(self.credits_label)

        self.version_label = QLabel(f"{c.t("UI_VERSION_TEXT")}{c.VERSION_LAUNCHER}")
        self.version_label.setAlignment(Qt.AlignCenter)
        self.version_label.setStyleSheet("font-size: 11px; color: gray;")
        self.main_layout.addWidget(self.version_label)
