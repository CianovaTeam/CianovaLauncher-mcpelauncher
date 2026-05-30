from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFrame, QTabWidget, QScrollArea, QWidget)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QIcon
from src.gui import custom_dialogs as messagebox
from src import constants as c
from src.core import addon_manager
from src.utils.image_manager import ImageManager
from src.utils import dialogs
import os
import threading
from PySide6.QtCore import QThread, Signal

class AddonWorker(QThread):
    """Background worker that scans all addons (worlds, resource packs, behavior packs)."""
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, app):
        super().__init__()
        self.app = app

    def run(self):
        try:
            data = addon_manager.scan_all_addons(self.app)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

class AddonActionWorker(QThread):
    """Background worker for addon actions like toggle, delete, and install."""
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, action_func, *args):
        super().__init__()
        self.action_func = action_func
        self.args = args

    def run(self):
        try:
            res = self.action_func(*self.args)
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))

class AddonManagerDialog(QDialog):
    """Dialog for browsing, searching, toggling, and importing addons (worlds, resource/behavior packs)."""
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent
        self.setWindowTitle(c.t("UI_ADDON_MANAGER_TITLE"))
        self.resize(950, 750)

        self.addons_data = []
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.render_filtered_list)

        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        """Build the dialog layout with search bar, tabs (worlds/RP/BP), and filter controls."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # Header
        self.header_layout = QVBoxLayout()
        self.main_layout.addLayout(self.header_layout)

        # Row 1: Search and Main buttons
        row1 = QHBoxLayout()
        self.entry_search = QLineEdit()
        self.entry_search.setPlaceholderText(c.t("UI_SEARCH_PLACEHOLDER"))
        self.entry_search.setMinimumWidth(300)
        self.entry_search.textChanged.connect(self.on_search_delay)
        row1.addWidget(self.entry_search)

        btn_reload = QPushButton("↻")
        btn_reload.setMinimumSize(50, 45)
        btn_reload.setStyleSheet("font-size: 24px; font-weight: bold; padding: 5px;")
        btn_reload.clicked.connect(self.refresh_list)
        row1.addWidget(btn_reload)

        row1.addStretch()

        btn_import = QPushButton(f"📥 {c.t("UI_BUTTON_IMPORT_FILE")}")
        btn_import.setFixedHeight(35)
        btn_import.setStyleSheet(f"background-color: {c.COLOR_GREEN_BUTTON}; color: white; font-weight: bold;")
        btn_import.clicked.connect(self.import_file)
        row1.addWidget(btn_import)
        self.header_layout.addLayout(row1)

        # Row 2: Status Indicators
        row2 = QHBoxLayout()
        profile = self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.t("UI_PROFILE_DEFAULT"))
        install_mode = c.t("UI_INSTALL_MODES").get(self.app.config.get(c.CONFIG_KEY_INSTALL_MODE), "Unknown")

        lbl_profile = QLabel(f"👤 {c.t("UI_LABEL_PROFILE")} {profile}")
        lbl_profile.setStyleSheet(f"color: {c.COLOR_PRIMARY_GREEN}; font-size: 11px;")
        row2.addWidget(lbl_profile)

        lbl_mode = QLabel(f"📦 {c.t("UI_LABEL_INSTALLATION")} {install_mode}")
        lbl_mode.setStyleSheet("color: gray; font-size: 11px;")
        row2.addWidget(lbl_mode)
        row2.addStretch()
        self.header_layout.addLayout(row2)

        # Tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.render_filtered_list)
        self.main_layout.addWidget(self.tab_widget)

        self.tabs = {}
        tab_configs = [
            (c.t("UI_TAB_WORLDS"), "worlds"),
            (c.t("UI_TAB_RP"), "rp"),
            (c.t("UI_TAB_BP"), "bp")
        ]
        for tab_display_name, tab_id in tab_configs:
            tab = QWidget()
            layout = QVBoxLayout(tab)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setStyleSheet("background: transparent;")

            content = QWidget()
            content_layout = QVBoxLayout(content)
            content_layout.setAlignment(Qt.AlignTop)
            scroll.setWidget(content)
            layout.addWidget(scroll)

            idx = self.tab_widget.addTab(tab, tab_display_name)
            self.tabs[idx] = (content_layout, content, tab_id)

        self.setStyleSheet("background-color: #2b2b2b; color: white;")

    def on_search_delay(self):
        """Start a debounce timer to re-render the list after the user stops typing."""
        self._search_timer.start(300)

    def refresh_list(self):
        """Start a background scan of all addons and show a progress dialog."""
        from src.gui.progress_dialog import ProgressDialog
        self.progress = ProgressDialog(self, c.t("UI_ANALYZING_TITLE"), c.t("UI_SCANNING_RESOURCES"))
        self.progress.show()

        self.worker = AddonWorker(self.app)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.error.connect(self.on_scan_error)
        self.worker.start()

    def on_scan_finished(self, data):
        """Handle the completed addon scan and render the filtered list."""
        self.addons_data = data
        self.progress.accept()
        self.render_filtered_list()

    def on_scan_error(self, err):
        """Display an error message when addon scanning fails."""
        self.progress.accept()
        messagebox.showerror(self, c.t("UI_ERROR_TITLE"), err)

    def render_filtered_list(self):
        """Rebuild the visible addon list filtered by search query and active tab."""
        current_idx = self.tab_widget.currentIndex()
        if current_idx not in self.tabs: return
        layout, content_widget, tab_id = self.tabs[current_idx]

        # Clear layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        search_query = self.entry_search.text().lower()

        folder_map = {
            "worlds": "minecraftWorlds",
            "bp": "behavior_packs",
            "rp": "resource_packs"
        }
        folder_filter = folder_map.get(tab_id, "")

        filtered = [
            a for a in self.addons_data
            if (a["folder"] == folder_filter or (folder_filter == "resource_packs" and a["folder"] not in ["minecraftWorlds", "behavior_packs"]))
            and (not search_query or search_query in a["name"].lower() or search_query in a["description"].lower())
        ]
        filtered.sort(key=lambda x: x["name"].lower())

        for addon in filtered:
            self.create_item_ui(layout, addon)

    def create_item_ui(self, layout, addon):
        """Create a single addon item widget with icon, info, and action buttons."""
        item_frame = QFrame()
        item_frame.setStyleSheet(f"background-color: #333333; border-radius: 12px;")
        item_layout = QHBoxLayout(item_frame)
        item_layout.setContentsMargins(15, 15, 15, 15)

        # Icon
        lbl_icon = QLabel()
        lbl_icon.setFixedSize(90, 90)
        pixmap = None
        if addon["icon_path"] and os.path.exists(addon["icon_path"]):
            pixmap = QPixmap(addon["icon_path"]).scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        if not pixmap or pixmap.isNull():
            pixmap = ImageManager.get_image("icon.png", size=(90, 90))

        lbl_icon.setPixmap(pixmap)
        item_layout.addWidget(lbl_icon)

        # Info
        info_layout = QVBoxLayout()
        name_text = addon["name"]
        if addon["version"]: name_text += f" (v{addon['version']})"

        lbl_name = QLabel(name_text)
        lbl_name.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {'white' if addon['enabled'] else '#888888'};")
        info_layout.addWidget(lbl_name)

        if addon["folder"] != "minecraftWorlds":
            status_text = c.t("UI_STATUS_ACTIVE") if addon["enabled"] else c.t("UI_STATUS_DISABLED")
            type_str = f"[{addon['type_label']}] - {status_text}"
            lbl_type = QLabel(type_str)
            lbl_type.setStyleSheet(f"font-size: 11px; color: {c.COLOR_PRIMARY_GREEN if addon['enabled'] else 'gray'};")
            info_layout.addWidget(lbl_type)

        if addon["description"]:
            lbl_desc = QLabel(addon["description"])
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet("font-size: 12px; color: gray;")
            info_layout.addWidget(lbl_desc)

        item_layout.addLayout(info_layout, 1)

        # Actions
        actions_layout = QHBoxLayout()
        if addon["folder"] != "minecraftWorlds":
            btn_text = c.t("UI_BUTTON_DEACTIVATE") if addon["enabled"] else c.t("UI_BUTTON_ACTIVATE")
            btn_color = c.COLOR_RED_BUTTON if addon["enabled"] else c.COLOR_GREEN_BUTTON

            btn_toggle = QPushButton(btn_text)
            btn_toggle.setFixedSize(130, 40)
            btn_toggle.setStyleSheet(f"background-color: {btn_color}; color: white; font-weight: bold; border-radius: 8px;")
            btn_toggle.clicked.connect(lambda checked=False, a=addon: self.toggle(a))
            actions_layout.addWidget(btn_toggle)
        else:
            btn_exp = QPushButton(c.t("UI_BUTTON_EXPORT"))
            btn_exp.setFixedSize(130, 40)
            btn_exp.setStyleSheet(f"background-color: {c.COLOR_BLUE_BUTTON}; color: white; font-weight: bold; border-radius: 8px;")
            btn_exp.clicked.connect(lambda: self.export_world(addon))
            actions_layout.addWidget(btn_exp)

        btn_del = QPushButton("🗑️")
        btn_del.setFixedSize(45, 38)
        btn_del.setStyleSheet(f"background-color: {c.COLOR_RED_BUTTON}; color: white; border-radius: 8px;")
        btn_del.clicked.connect(lambda: self.delete(addon))
        actions_layout.addWidget(btn_del)

        item_layout.addLayout(actions_layout)
        layout.addWidget(item_frame)

    def export_world(self, addon):
        """Export the selected world as a .mcworld file to a chosen directory."""
        dest_dir = dialogs.ask_directory_native(self, title=c.t("UI_SELECT_DEST_FOLDER_TITLE"))
        if dest_dir:
            success, msg = addon_manager.export_world(addon["path"], dest_dir)
            if success:
                messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), c.t("UI_WORLD_EXPORTED_SUCCESS", path=msg))
            else:
                messagebox.showerror(self, c.t("UI_ERROR_TITLE"), msg)

    def toggle(self, addon):
        """Enable or disable the given addon (resource/behavior pack) in a background thread."""
        from src.gui.progress_dialog import ProgressDialog
        self.progress_action = ProgressDialog(self, c.t("UI_INFO_TITLE"), c.t("UI_TOGGLING_STATUS"))
        self.progress_action.show()

        def on_finished(new_path):
            addon["enabled"] = not addon["enabled"]
            addon["path"] = new_path
            self.progress_action.accept()
            self.render_filtered_list()

        def on_error(err):
            self.progress_action.accept()
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), str(err))

        self.action_worker = AddonActionWorker(addon_manager.toggle_addon, self.app, addon)
        self.action_worker.finished.connect(on_finished)
        self.action_worker.error.connect(on_error)
        self.action_worker.start()

    def delete(self, addon):
        """Delete the given addon after user confirmation."""
        if messagebox.askyesno(self, c.t("UI_CONFIRM_DELETE_TITLE"), f"{c.t("UI_BUTTON_DELETE")} {addon['name']}?"):
            from src.gui.progress_dialog import ProgressDialog
            self.progress_action = ProgressDialog(self, c.t("UI_INFO_TITLE"), c.t("UI_DELETING_RESOURCE"))
            self.progress_action.show()

            def on_finished(success):
                if success and addon in self.addons_data:
                    self.addons_data.remove(addon)
                self.progress_action.accept()
                self.render_filtered_list()

            def on_error(err):
                self.progress_action.accept()
                messagebox.showerror(self, c.t("UI_ERROR_TITLE"), str(err))

            self.action_worker = AddonActionWorker(addon_manager.delete_addon, addon["path"])
            self.action_worker.finished.connect(on_finished)
            self.action_worker.error.connect(on_error)
            self.action_worker.start()

    def import_file(self):
        """Open a file picker for .mcpack/.mcaddon/.mcworld files and install them."""
        file_path = dialogs.ask_open_filename_native(
            self,
            title=c.t("UI_OPEN_FILE_TITLE"),
            filetypes=[(c.t("UI_MCPACK_FILES_TYPE"), "*.mcpack *.mcaddon *.mcworld *.mcworldtemplate"), (c.t("UI_ALL_FILES_TYPE"), "*.*")]
        )
        if not file_path: return
        self._install_task([file_path])

    def _install_task(self, file_paths):
        from src.gui.progress_dialog import ProgressDialog
        self.progress_action = ProgressDialog(self, c.t("UI_INFO_TITLE"), c.t("UI_INSTALLING_PACK"))
        self.progress_action.show()

        def run_install(paths):
            for f in paths:
                addon_manager.install_addon_file(self.app.active_path, f)
            return True

        def on_finished(res):
            self.progress_action.accept()
            self.refresh_list()

        def on_error(err):
            self.progress_action.accept()
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), str(err))

        self.action_worker = AddonActionWorker(run_install, file_paths)
        self.action_worker.finished.connect(on_finished)
        self.action_worker.error.connect(on_error)
        self.action_worker.start()
