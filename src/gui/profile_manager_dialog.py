from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QScrollArea, QWidget, QInputDialog)
from PySide6.QtCore import Qt
from src import constants as c
from src.gui import custom_dialogs as messagebox

class ProfileManagerDialog(QDialog):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle(c.UI_PROFILES_MANAGER_TITLE)
        self.resize(500, 500)

        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # Header
        self.btn_add = QPushButton(f"➕ {c.UI_BUTTON_ADD_PROFILE}")
        self.btn_add.setObjectName("ToolButton")
        self.btn_add.setFixedHeight(35)
        self.btn_add.clicked.connect(self.add_profile)
        self.main_layout.addWidget(self.btn_add)

        # List
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

        self.setStyleSheet("background-color: #2b2b2b; color: white;")

    def refresh_list(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        profiles = self.app.logic.get_profiles(self.app)
        current = self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE)

        for p in sorted(profiles):
            self.create_item(p, p == current)

    def create_item(self, name, is_current):
        frame = QFrame()
        bg = c.COLOR_SELECTED_GREEN if is_current else "#333333"
        frame.setStyleSheet(f"background-color: {bg}; border-radius: 10px;")
        layout = QHBoxLayout(frame)

        status_dot = "●" if is_current else "○"
        lbl_name = QLabel(f"{status_dot} {name}")
        lbl_name.setStyleSheet("font-weight: bold; color: white;")
        layout.addWidget(lbl_name)

        layout.addStretch()

        if name != c.UI_PROFILE_DEFAULT:
            btn_rename = QPushButton("✏️")
            btn_rename.setFixedSize(35, 30)
            btn_rename.clicked.connect(lambda checked=False, n=name: self.rename_profile(n))
            layout.addWidget(btn_rename)

            if not is_current:
                btn_del = QPushButton("🗑️")
                btn_del.setFixedSize(35, 30)
                btn_del.setStyleSheet(f"background-color: {c.COLOR_RED_BUTTON}; color: white;")
                btn_del.clicked.connect(lambda checked=False, n=name: self.delete_profile(n))
                layout.addWidget(btn_del)
        else:
            lbl_def = QLabel("[System]")
            lbl_def.setStyleSheet("font-size: 11px; color: #aaaaaa; font-weight: bold;")
            layout.addWidget(lbl_def)

        self.scroll_layout.addWidget(frame)

    def _sync_ui(self):
        if hasattr(self.app.settings_tab, "refresh_profile_list"):
            self.app.settings_tab.refresh_profile_list()
        if hasattr(self.app.play_tab, "update_profile_indicator"):
            self.app.play_tab.update_profile_indicator()

    def add_profile(self):
        name, ok = QInputDialog.getText(self, c.UI_BUTTON_ADD_PROFILE, c.UI_PROFILE_NAME_REQUIRED)
        if ok and name:
            # Reusing logic from app_logic would be better, but app_logic uses CTkInputDialog
            # I should update app_logic to be toolkit-agnostic or update it to use PySide6
            # For now, let's keep it consistent.
            if self.app.logic.create_profile_pyside(self.app, name):
                self.refresh_list()
                self._sync_ui()

    def rename_profile(self, old_name):
        new_name, ok = QInputDialog.getText(self, c.UI_BUTTON_RENAME_PROFILE, c.UI_PROFILE_NAME_REQUIRED, text=old_name)
        if ok and new_name and self.app.logic.rename_profile(self.app, old_name, new_name):
            self.refresh_list()
            self._sync_ui()

    def delete_profile(self, name):
        if self.app.logic.delete_profile(self.app, name):
            self.refresh_list()
            self._sync_ui()
