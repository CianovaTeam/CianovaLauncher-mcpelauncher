from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QScrollArea, QWidget, QInputDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from src import constants as c
from src.gui import custom_dialogs as messagebox
from src.utils.colors import hex_to_rgba, adjust_color


class ProfileManagerDialog(QDialog):
    """Dialog for creating, renaming, and deleting user profiles."""
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle(c.t("UI_PROFILES_MANAGER_TITLE"))
        self.resize(520, 520)
        self.setMinimumSize(420, 350)

        mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        theme_color = self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
        self.accent = c.THEME_COLOR_MAP.get(theme_color, "#1f6aa5")
        self.bg = "#242424" if mode == "Dark" else "#ebebeb"
        self.text = "#DCE4EE" if mode == "Dark" else "#242424"
        self.card_bg = "#333333" if mode == "Dark" else "#d0d0d0"
        self.input_bg = "#333333" if mode == "Dark" else "#ffffff"
        self.input_border = "#444444" if mode == "Dark" else "#cccccc"
        self.muted = "#888888"

        self.setup_ui()
        self.refresh_list()

    def _style(self):
        return f"""
            QDialog {{
                background-color: {self.bg};
                color: {self.text};
            }}
            QLabel {{
                color: {self.text};
                background: transparent;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget {{
                background: transparent;
            }}
            QScrollArea > QWidget > QWidget#ProfileList {{
                background-color: {self.bg};
            }}
            QPushButton#AddButton {{
                background-color: {self.accent};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 18px;
            }}
            QPushButton#AddButton:hover {{
                background-color: {adjust_color(self.accent, 20)};
            }}
            QPushButton#CardButton {{
                background: transparent;
                border: none;
                color: {self.text};
                font-size: 13px;
            }}
            QPushButton#CardButton:hover {{
                color: {self.accent};
            }}
            QPushButton#CloseButton {{
                background-color: transparent;
                color: {self.muted};
                border: 1px solid {hex_to_rgba(self.input_border, 0.5)};
                border-radius: 8px;
                font-size: 13px;
                padding: 8px 24px;
            }}
            QPushButton#CloseButton:hover {{
                background-color: {hex_to_rgba(self.accent, 0.15)};
                color: {self.text};
                border: 1px solid {self.accent};
            }}
            QScrollBar:vertical {{
                background: {self.bg};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.accent};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)

        self.setStyleSheet(self._style())

        header = QVBoxLayout()
        header.setSpacing(4)

        title = QLabel(c.t("UI_PROFILES_MANAGER_TITLE"))
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {self.accent};")
        header.addWidget(title)

        subtitle = QLabel("Manage your game profiles: each profile has its own config, versions, and data.")
        subtitle.setStyleSheet(f"font-size: 11px; color: {self.muted};")
        header.addWidget(subtitle)
        self.main_layout.addLayout(header)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton(f"＋ {c.t("UI_BUTTON_ADD_PROFILE")}")
        self.btn_add.setObjectName("AddButton")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.clicked.connect(self.add_profile)
        btn_row.addWidget(self.btn_add)
        btn_row.addStretch()
        self.main_layout.addLayout(btn_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ProfileList")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area, 1)

        footer = QHBoxLayout()
        btn_close = QPushButton(c.t("UI_BUTTON_CLOSE"))
        btn_close.setObjectName("CloseButton")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        footer.addStretch()
        footer.addWidget(btn_close)
        self.main_layout.addLayout(footer)

    def refresh_list(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        profiles = self.app.logic.get_profiles(self.app)
        current = self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE)

        for p in sorted(profiles):
            self._create_card(p, p == current)

    def _create_card(self, name, is_current):
        card = QFrame()
        card.setObjectName("ProfileCard")
        if is_current:
            border = f"1px solid {self.accent}"
            bg = hex_to_rgba(self.accent, 0.08)
        else:
            border = f"1px solid {hex_to_rgba(self.input_border, 0.3)}"
            bg = "transparent"
        card.setStyleSheet(f"""
            QFrame#ProfileCard {{
                background-color: {bg};
                border: {border};
                border-radius: 10px;
                padding: 4px;
            }}
            QFrame#ProfileCard:hover {{
                border: 1px solid {self.accent};
                background-color: {hex_to_rgba(self.accent, 0.04)};
            }}
        """)
        card.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 10, 10, 10)
        layout.setSpacing(10)

        icon = QLabel("★" if is_current else "○")
        icon.setStyleSheet(f"font-size: 16px; color: {self.accent if is_current else self.muted};")
        icon.setFixedWidth(20)
        layout.addWidget(icon)

        name_label = QLabel(name)
        name_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {self.text};")
        layout.addWidget(name_label, 1)

        if is_current:
            badge = QLabel("Active")
            badge.setStyleSheet(f"""
                font-size: 10px; font-weight: bold; color: {self.accent};
                background-color: {hex_to_rgba(self.accent, 0.12)};
                border-radius: 4px; padding: 2px 8px;
            """)
            layout.addWidget(badge)

        if name != c.t("UI_PROFILE_DEFAULT"):
            btn_rename = QPushButton("✏️")
            btn_rename.setObjectName("CardButton")
            btn_rename.setFixedSize(32, 28)
            btn_rename.setCursor(Qt.PointingHandCursor)
            btn_rename.clicked.connect(lambda checked=False, n=name: self.rename_profile(n))
            layout.addWidget(btn_rename)

            if not is_current:
                btn_del = QPushButton("🗑️")
                btn_del.setObjectName("CardButton")
                btn_del.setFixedSize(32, 28)
                btn_del.setCursor(Qt.PointingHandCursor)
                btn_del.clicked.connect(lambda checked=False, n=name: self.delete_profile(n))
                layout.addWidget(btn_del)
                self._make_switchable(card, name)
        else:
            tag = QLabel("[System]")
            tag.setStyleSheet(f"font-size: 11px; color: {self.muted}; font-weight: bold;")

            layout.addWidget(tag)

        self.scroll_layout.addWidget(card)

    def _make_switchable(self, card, name):
        def switch():
            self.app.logic.switch_profile(self.app, name)
            self.refresh_list()
            self._sync_ui()
        card.mousePressEvent = lambda event, s=switch: (s() if event.button() == Qt.LeftButton else None)

    def _sync_ui(self):
        if hasattr(self.app.settings_tab, "refresh_profile_list"):
            self.app.settings_tab.refresh_profile_list()
        if hasattr(self.app.play_tab, "update_profile_indicator"):
            self.app.play_tab.update_profile_indicator()
        if hasattr(self.app.tools_tab, "retranslate_ui"):
            self.app.tools_tab.retranslate_ui()

    def add_profile(self):
        name, ok = QInputDialog.getText(self, c.t("UI_BUTTON_ADD_PROFILE"), c.t("UI_PROFILE_NAME_REQUIRED"))
        if ok and name:
            if self.app.logic.create_profile_pyside(self.app, name):
                self.refresh_list()
                self._sync_ui()

    def rename_profile(self, old_name):
        new_name, ok = QInputDialog.getText(self, c.t("UI_BUTTON_RENAME_PROFILE"), c.t("UI_PROFILE_NAME_REQUIRED"), text=old_name)
        if ok and new_name and self.app.logic.rename_profile(self.app, old_name, new_name):
            self.refresh_list()
            self._sync_ui()

    def delete_profile(self, name):
        if self.app.logic.delete_profile(self.app, name):
            self.refresh_list()
            self._sync_ui()
