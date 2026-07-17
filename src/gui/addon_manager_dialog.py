from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFrame, QTabWidget,
                             QScrollArea, QWidget, QCheckBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QIcon, QDragEnterEvent, QDropEvent
from src.gui import custom_dialogs as messagebox
from src import constants as c
from src.core import addon_manager
from src.core.moddb_service import (
    ModDBFetchWorker, get_cached_moddb, is_mod_installed,
    get_mod_info, find_asset_for_arch
)
from src.utils.image_manager import ImageManager
from src.utils import dialogs
from src.utils.process_utils import open_path
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
            mods = addon_manager.scan_mods(self.app)
            data.extend(mods)
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
        self.setAcceptDrops(True)

        self.addons_data = []
        self.moddb_data = None
        self._moddb_fetch_started = False
        self._moddb_fetch_error = None
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.render_filtered_list)

        # Load cached moddb immediately (fast, local) — no network fetch on open
        self.moddb_data = get_cached_moddb(self.app.active_path)
        self._moddb_worker = None

        self.setup_ui()
        self.refresh_list()

    def _drop_file_types(self):
        """Return accepted file extensions for the current tab."""
        current_idx = self.tab_widget.currentIndex()
        tab_id = self.tabs.get(current_idx, (None, None, None))[2]
        if tab_id == "mods":
            return (".so", ".zip")
        return (".mcpack", ".mcaddon", ".mcworld", ".mcworldtemplate", ".mctemplate")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            exts = self._drop_file_types()
            for url in event.mimeData().urls():
                if any(url.toLocalFile().endswith(e) for e in exts):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent):
        exts = self._drop_file_types()
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if any(path.endswith(e) for e in exts):
                paths.append(path)
        if paths:
            current_idx = self.tab_widget.currentIndex()
            tab_id = self.tabs.get(current_idx, (None, None, None))[2]
            if tab_id == "mods":
                self._install_mod_task(paths)
            else:
                self._install_task(paths)

    def closeEvent(self, event):
        """Clean up background workers when the dialog closes."""
        if self._moddb_worker and self._moddb_worker.isRunning():
            self._moddb_worker.quit()
            self._moddb_worker.wait(2000)
            self._moddb_worker = None
        super().closeEvent(event)

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

        btn_import = QPushButton(f"📥 {c.t('UI_BUTTON_IMPORT_FILE')}")
        btn_import.setFixedHeight(35)
        btn_import.setStyleSheet(f"background-color: {c.COLOR_GREEN_BUTTON}; color: white; font-weight: bold;")
        btn_import.clicked.connect(self.import_file)
        row1.addWidget(btn_import)
        self.header_layout.addLayout(row1)

        # Row 2: Status Indicators
        row2 = QHBoxLayout()
        profile = self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.t("UI_PROFILE_DEFAULT"))
        install_mode = c.t("UI_INSTALL_MODES").get(self.app.config.get(c.CONFIG_KEY_INSTALL_MODE), "Unknown")

        lbl_profile = QLabel(f"👤 {c.t('UI_LABEL_PROFILE')} {profile}")
        lbl_profile.setStyleSheet(f"color: {c.COLOR_PRIMARY_GREEN}; font-size: 11px;")
        row2.addWidget(lbl_profile)

        lbl_mode = QLabel(f"📦 {c.t('UI_LABEL_INSTALLATION')} {install_mode}")
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
            (c.t("UI_TAB_BP"), "bp"),
            (c.t("UI_TAB_MCPE_MODS"), "mods")
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

    def _start_moddb_fetch(self):
        """Start background fetch of mod database."""
        if self._moddb_fetch_started:
            return
        self._moddb_fetch_started = True
        self._moddb_fetch_error = None
        self._moddb_worker = ModDBFetchWorker(self.app.active_path)
        self._moddb_worker.finished.connect(self.on_moddb_fetched)
        self._moddb_worker.error.connect(self._on_moddb_fetch_error)
        self._moddb_worker.start()

    def _on_moddb_fetch_error(self, err):
        """Handle moddb fetch error."""
        self._moddb_worker = None
        self._moddb_fetch_error = err
        self.moddb_data = self.moddb_data or []
        current_idx = self.tab_widget.currentIndex()
        tab_id = self.tabs.get(current_idx, (None, None, None))[2]
        if tab_id == "mods":
            self.render_filtered_list()

    def on_moddb_fetched(self, data):
        """Handle fresh moddb data from the background fetch."""
        self._moddb_worker = None
        self.moddb_data = data
        current_idx = self.tab_widget.currentIndex()
        tab_id = self.tabs.get(current_idx, (None, None, None))[2]
        if tab_id == "mods":
            self.render_filtered_list()

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
            "rp": "resource_packs",
            "mods": "mods"
        }
        folder_filter = folder_map.get(tab_id, "")

        filtered = [
            a for a in self.addons_data
            if (a.get("folder") == folder_filter or (folder_filter == "resource_packs" and a.get("folder") in ("resource_packs", "skin_packs", "custom_skins")))
            and (not search_query or search_query in a.get("name", "").lower() or search_query in a.get("description", "").lower())
        ]
        filtered.sort(key=lambda x: x.get("name", "").lower())

        # Open folder button per tab
        folder_paths = {
            "worlds": os.path.join(self.app.active_path, "games", "com.mojang", "minecraftWorlds"),
            "rp": os.path.join(self.app.active_path, "games", "com.mojang", "resource_packs"),
            "bp": os.path.join(self.app.active_path, "games", "com.mojang", "behavior_packs"),
            "mods": os.path.join(self.app.active_path, c.MODS_DIR),
        }
        tab_folder = folder_paths.get(tab_id)
        if tab_folder:
            header_row = QHBoxLayout()
            lbl_folder = QLabel(f"📂 {tab_folder}")
            lbl_folder.setStyleSheet("font-size: 11px; color: #666666;")
            header_row.addWidget(lbl_folder)
            header_row.addStretch()
            btn_open = QPushButton(c.t("UI_BUTTON_OPEN_FOLDER"))
            btn_open.setFixedHeight(28)
            btn_open.setStyleSheet("font-size: 11px; padding: 2px 10px;")
            btn_open.clicked.connect(lambda checked=False, p=tab_folder: open_path(p))
            header_row.addWidget(btn_open)
            layout.addLayout(header_row)

        # ── Mods tab: DRM header + installed mods + available mods ──
        if tab_id == "mods":
            installed_mods = [a for a in filtered if a.get("folder") == "mods"]
            available_from_moddb = []

            if self.moddb_data:
                installed_names = set()
                for m in installed_mods:
                    base = os.path.basename(m["name"])
                    if base.endswith(".so"):
                        base = base[:-3]
                    installed_names.add(base)
                for entry in self.moddb_data:
                    mname = entry.get("name", "")
                    if mname == "mcpelauncher-updates":
                        continue
                    # Extract mod dir name from entry (usually the name itself)
                    mod_dir_name = mname
                    if not is_mod_installed(self.app.active_path, mod_dir_name):
                        available_from_moddb.append(entry)

            # DRM header
            drm_status = self.app.logic.get_drm_mod_status(self.app)
            drm_header_frame = QFrame()
            drm_header_frame.setStyleSheet("background-color: #2a2a2a; border-radius: 8px; padding: 4px;")
            drm_header_layout = QVBoxLayout(drm_header_frame)
            drm_header_layout.setContentsMargins(10, 8, 10, 8)

            status_icons = {
                "installed": "✓",
                "disabled": "⚠",
                "missing": "✗"
            }
            status_colors = {
                "installed": c.COLOR_PRIMARY_GREEN,
                "disabled": c.COLOR_YELLOW_BUTTON,
                "missing": c.COLOR_RED_BUTTON
            }
            status_labels = {
                "installed": c.t("UI_DRM_MOD_STATUS_INSTALLED"),
                "disabled": c.t("UI_DRM_MOD_STATUS_DISABLED"),
                "missing": c.t("UI_DRM_MOD_STATUS_MISSING")
            }
            icon = status_icons.get(drm_status, "?")
            color = status_colors.get(drm_status, "gray")
            label_text = status_labels.get(drm_status, "?")

            status_line = QHBoxLayout()
            lbl_icon = QLabel(icon)
            lbl_icon.setStyleSheet(f"font-size: 16px; color: {color};")
            status_line.addWidget(lbl_icon)

            lbl_info = QLabel(f"<b>Mod DRM (mcpelauncher-updates)</b> — {label_text}")
            lbl_info.setStyleSheet(f"font-size: 12px; color: {color};")
            status_line.addWidget(lbl_info)
            status_line.addStretch()
            drm_header_layout.addLayout(status_line)

            lbl_desc = QLabel(c.t("UI_DRM_MOD_DESC"))
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet("font-size: 11px; color: #888888;")
            drm_header_layout.addWidget(lbl_desc)

            if drm_status == "missing":
                btn_install = QPushButton(f"📥 {c.t('UI_BUTTON_INSTALL_DRM_MOD')}")
                btn_install.setFixedHeight(35)
                btn_install.setStyleSheet(f"background-color: {c.COLOR_GREEN_BUTTON}; color: white; font-weight: bold; border-radius: 8px;")
                btn_install.clicked.connect(lambda: self._install_drm_and_refresh())
                drm_header_layout.addWidget(btn_install)
            elif drm_status == "disabled":
                btn_activate = QPushButton("▶ Activar Mod DRM")
                btn_activate.setFixedHeight(35)
                btn_activate.setStyleSheet(f"background-color: {c.COLOR_YELLOW_BUTTON}; color: white; font-weight: bold; border-radius: 8px;")
                btn_activate.clicked.connect(lambda: self._toggle_drm_mod())
                drm_header_layout.addWidget(btn_activate)

            layout.addWidget(drm_header_frame)

            # Installed mods
            for addon in installed_mods:
                self.create_item_ui(layout, addon)

            # Available mods from moddb — only fetched on user request
            if self.moddb_data is None:
                if self._moddb_fetch_error:
                    lbl_moddb = QLabel(f"⚠ Error de red — {c.t('UI_AVAILABLE_MODS_HEADER')}")
                    lbl_moddb.setStyleSheet("font-size: 12px; color: #ef4444; padding: 8px 0;")
                    layout.addWidget(lbl_moddb)
                    btn_retry = QPushButton("↻ Reintentar")
                    btn_retry.setFixedHeight(28)
                    btn_retry.setStyleSheet("font-size: 11px; padding: 2px 10px;")
                    btn_retry.clicked.connect(lambda: (setattr(self, '_moddb_fetch_started', False), self._start_moddb_fetch()))
                    layout.addWidget(btn_retry)
                elif self._moddb_fetch_started:
                    lbl_moddb = QLabel("⏳ Cargando lista de mods...")
                    lbl_moddb.setStyleSheet("font-size: 12px; color: #888; padding: 8px 0;")
                    layout.addWidget(lbl_moddb)
                else:
                    lbl_prompt = QLabel("Presiona '↻ Actualizar' para ver los mods disponibles en mcpelauncher-moddb")
                    lbl_prompt.setStyleSheet("font-size: 12px; color: #888; padding: 12px 0;")
                    lbl_prompt.setWordWrap(True)
                    layout.addWidget(lbl_prompt)
                    btn_refresh = QPushButton("↻ Actualizar lista de mods")
                    btn_refresh.setFixedHeight(32)
                    btn_refresh.setStyleSheet("font-size: 12px; padding: 4px 16px;")
                    btn_refresh.clicked.connect(self._start_moddb_fetch)
                    layout.addWidget(btn_refresh)
            elif available_from_moddb:
                sep_frame = QFrame()
                sep_frame.setFrameShape(QFrame.HLine)
                sep_frame.setStyleSheet("color: #555; margin: 10px 0;")
                layout.addWidget(sep_frame)

                avail_header = QLabel(f"📦 {c.t('UI_AVAILABLE_MODS_HEADER')}")
                avail_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #aaa; padding: 8px 0;")
                layout.addWidget(avail_header)

                for entry in available_from_moddb:
                    self._create_available_mod_ui(layout, entry)

                btn_refresh = QPushButton("↻ Actualizar lista")
                btn_refresh.setFixedHeight(28)
                btn_refresh.setStyleSheet("font-size: 11px; padding: 2px 10px; margin-top: 8px;")
                btn_refresh.clicked.connect(lambda: (setattr(self, '_moddb_fetch_started', False), self._start_moddb_fetch()))
                layout.addWidget(btn_refresh)

        else:
            # Non-mods tabs: render normally
            for addon in filtered:
                self.create_item_ui(layout, addon)

    def _install_drm_and_refresh(self):
        """Install DRM mod and refresh the mods list when done."""
        self.app.logic.install_drm_mod(self.app, on_done=self.refresh_list)

    def _create_available_mod_ui(self, layout, mod_entry):
        """Render a card for an available (not installed) mod from the moddb."""
        mod_name = mod_entry.get("name", "Unknown")
        mod_desc = mod_entry.get("description", "")
        mod_url = mod_entry.get("url", "")

        latest_ver = ""
        versions = mod_entry.get("versions", [])
        if versions:
            latest_ver = versions[-1].get("version", "")

        item_frame = QFrame()
        item_frame.setStyleSheet("background-color: #333333; border-radius: 12px;")
        item_layout = QHBoxLayout(item_frame)
        item_layout.setContentsMargins(15, 15, 15, 15)

        # Icon placeholder
        lbl_icon = QLabel()
        lbl_icon.setFixedSize(90, 90)
        pixmap = ImageManager.get_image("icon.png", size=(90, 90))
        lbl_icon.setPixmap(pixmap)
        item_layout.addWidget(lbl_icon)

        # Info
        info_layout = QVBoxLayout()
        name_text = mod_name
        if latest_ver:
            name_text += f" (v{latest_ver})"

        lbl_name = QLabel(name_text)
        lbl_name.setStyleSheet("font-size: 16px; font-weight: bold; color: #cccccc;")
        info_layout.addWidget(lbl_name)

        lbl_status = QLabel(f"[Mod MCPELauncher] — {c.t('UI_MOD_NOT_INSTALLED')}")
        lbl_status.setStyleSheet("font-size: 11px; color: gray;")
        info_layout.addWidget(lbl_status)

        if mod_desc:
            lbl_desc = QLabel(mod_desc)
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet("font-size: 12px; color: #888888;")
            info_layout.addWidget(lbl_desc)

        item_layout.addLayout(info_layout, 1)

        # Actions
        actions_layout = QHBoxLayout()

        btn_install = QPushButton(f"📥 {c.t('UI_BUTTON_INSTALL_MOD')}")
        btn_install.setFixedSize(130, 40)
        btn_install.setStyleSheet(f"background-color: {c.COLOR_GREEN_BUTTON}; color: white; font-weight: bold; border-radius: 8px;")
        btn_install.clicked.connect(lambda checked=False, n=mod_name: self._install_from_moddb(n))
        actions_layout.addWidget(btn_install)

        item_layout.addLayout(actions_layout)
        layout.addWidget(item_frame)

    def _install_from_moddb(self, mod_name):
        """Install a mod from the mod database."""
        self.app.logic.install_mod_from_moddb(self.app, mod_name, on_done=self.refresh_list)

    def _toggle_drm_mod(self):
        """Find and activate the disabled DRM mod."""
        drm_dir = os.path.join(self.app.active_path, c.MODS_DIR, "mcpelauncher-updates")
        for root, dirs, files in os.walk(drm_dir):
            for f in files:
                if f == "libmcpelauncher-updates.so.disabled":
                    src = os.path.join(root, f)
                    dst = os.path.join(root, "libmcpelauncher-updates.so")
                    try:
                        os.rename(src, dst)
                        self.refresh_list()
                    except OSError as e:
                        messagebox.showerror(self, c.t("UI_ERROR_TITLE"), str(e))
                    return

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
        icon_path = addon.get("icon_path")
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        if not pixmap or pixmap.isNull():
            pixmap = ImageManager.get_image("icon.png", size=(90, 90))

        lbl_icon.setPixmap(pixmap)
        item_layout.addWidget(lbl_icon)

        # Info
        info_layout = QVBoxLayout()
        addon_name = addon.get("name", "Unknown")
        addon_version = addon.get("version", "")
        addon_enabled = addon.get("enabled", False)
        addon_folder = addon.get("folder", "")
        addon_launch = addon.get("launch", True) if addon_folder == "mods" else None
        name_text = addon_name
        if addon_version:
            name_text += f" (v{addon_version})"

        lbl_name = QLabel(name_text)
        lbl_name.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {'white' if addon_enabled else '#888888'};")
        info_layout.addWidget(lbl_name)

        if addon_folder != "minecraftWorlds":
            status_text = c.t("UI_STATUS_ACTIVE") if addon_enabled else c.t("UI_STATUS_DISABLED")
            type_str = f"[{addon.get('type_label', '?')}] - {status_text}"
            lbl_type = QLabel(type_str)
            lbl_type.setStyleSheet(f"font-size: 11px; color: {c.COLOR_PRIMARY_GREEN if addon_enabled else 'gray'};")
            info_layout.addWidget(lbl_type)

        if addon_folder == "mods":
            size = addon.get("size", 0)
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size/(1024*1024):.1f} MB"
            lbl_size = QLabel(size_str)
            lbl_size.setStyleSheet("font-size: 11px; color: gray;")
            info_layout.addWidget(lbl_size)

            lbl_path = QLabel(f"📁 {addon.get('path', '')}")
            lbl_path.setWordWrap(True)
            lbl_path.setStyleSheet("font-size: 10px; color: #666666;")
            info_layout.addWidget(lbl_path)

        if addon.get("description"):
            lbl_desc = QLabel(addon.get("description", ""))
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet("font-size: 12px; color: gray;")
            info_layout.addWidget(lbl_desc)

        item_layout.addLayout(info_layout, 1)

        # Actions
        actions_layout = QHBoxLayout()
        if addon_folder == "mods" and addon_enabled:
            chk_launch = QCheckBox(c.t("UI_MOD_LAUNCH_CHECK"))
            chk_launch.setChecked(addon_launch)
            chk_launch.setStyleSheet("font-size: 11px; color: white;")
            chk_launch.clicked.connect(lambda checked, a=addon: self._on_launch_toggle(a, checked))
            actions_layout.addWidget(chk_launch)

        if addon_folder != "minecraftWorlds":
            btn_text = c.t("UI_BUTTON_DEACTIVATE") if addon_enabled else c.t("UI_BUTTON_ACTIVATE")
            btn_color = c.COLOR_RED_BUTTON if addon_enabled else c.COLOR_GREEN_BUTTON

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

    def _on_launch_toggle(self, addon, checked):
        """Toggle the launch flag for a mod and persist it."""
        addon["launch"] = checked
        if addon.get("path"):
            addon_manager.set_mod_launch_state(self.app, addon["path"], checked)

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
        """Enable or disable the given addon/mod in a background thread."""
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

        toggle_func = addon_manager.toggle_mod if addon["folder"] == "mods" else addon_manager.toggle_addon
        self.action_worker = AddonActionWorker(toggle_func, self.app, addon)
        self.action_worker.finished.connect(on_finished)
        self.action_worker.error.connect(on_error)
        self.action_worker.start()

    def delete(self, addon):
        """Delete the given addon after user confirmation."""
        if messagebox.askyesno(self, c.t("UI_CONFIRM_DELETE_TITLE"), f"{c.t('UI_BUTTON_DELETE')} {addon['name']}?"):
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
        """Open a file picker for addons/mods and install them depending on active tab."""
        current_idx = self.tab_widget.currentIndex()
        tab_id = self.tabs.get(current_idx, (None, None, None))[2]

        if tab_id == "mods":
            file_path = dialogs.ask_open_filename_native(
                self,
                title=c.t("UI_OPEN_FILE_TITLE"),
                filetypes=[("Mod MCPELauncher", "*.so *.zip"), (c.t("UI_ALL_FILES_TYPE"), "*.*")]
            )
            if not file_path: return
            self._install_mod_task([file_path])
        else:
            file_path = dialogs.ask_open_filename_native(
                self,
                title=c.t("UI_OPEN_FILE_TITLE"),
                filetypes=[(c.t("UI_MCPACK_FILES_TYPE"), "*.mcpack *.mcaddon *.mcworld *.mcworldtemplate *.mctemplate"), (c.t("UI_ALL_FILES_TYPE"), "*.*")]
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

    def _install_mod_task(self, file_paths):
        from src.gui.progress_dialog import ProgressDialog
        self.progress_action = ProgressDialog(self, c.t("UI_INFO_TITLE"), "Instalando mods...")
        self.progress_action.show()

        def run_install(paths):
            for f in paths:
                addon_manager.install_mod_file(self.app.active_path, f)
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
