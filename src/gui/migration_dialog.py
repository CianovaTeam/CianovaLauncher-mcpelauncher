from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFrame, QRadioButton, QComboBox, QCheckBox, QScrollArea, QWidget)
from PySide6.QtCore import Qt
import os
import shutil
import threading
from src.gui import custom_dialogs as messagebox
from src.utils.dialogs import ask_directory_native
from src.gui.progress_dialog import ProgressDialog
from src import constants as c

class MigrationDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_app = parent
        self.setWindowTitle(c.UI_MIGRATION_MANAGER_TITLE)
        self.resize(600, 700)

        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

        title = QLabel(c.UI_MIGRATION_TITLE)
        title.setObjectName("HeaderLabel")
        title.setStyleSheet("font-size: 22px;")
        title.setAlignment(Qt.AlignCenter)
        self.scroll_layout.addWidget(title)

        # --- Frame Origen ---
        self.frame_src = QFrame()
        self.frame_src.setStyleSheet(f"background-color: #333333; border-radius: {c.CORNER_RADIUS}px;")
        src_layout = QVBoxLayout(self.frame_src)

        src_layout.addWidget(QLabel(c.UI_SOURCE_LABEL))

        self.combo_src = QComboBox()
        self.combo_src.addItems(c.UI_SOURCE_MODES_DISPLAY)
        self.combo_src.currentTextChanged.connect(self.update_src_path_ui)
        src_layout.addWidget(self.combo_src)

        self.frame_flatpak_id = QFrame()
        fid_layout = QHBoxLayout(self.frame_flatpak_id)
        fid_layout.addWidget(QLabel(c.UI_LABEL_APP_ID))
        self.entry_flatpak_src_id = QLineEdit()
        self.entry_flatpak_src_id.setText(c.DEFAULT_FLATPAK_ID)
        fid_layout.addWidget(self.entry_flatpak_src_id)
        src_layout.addWidget(self.frame_flatpak_id)

        self.entry_src = QLineEdit()
        self.entry_src.setPlaceholderText(c.UI_PLACEHOLDER_SOURCE_PATH)
        src_layout.addWidget(self.entry_src)

        btn_browse_src = QPushButton(c.UI_BUTTON_BROWSE_FOLDER)
        btn_browse_src.clicked.connect(self.browse_src)
        src_layout.addWidget(btn_browse_src, 0, Qt.AlignRight)

        self.lbl_src_validation = QLabel("")
        self.lbl_src_validation.setStyleSheet("font-size: 10px; color: gray;")
        src_layout.addWidget(self.lbl_src_validation)

        self.scroll_layout.addWidget(self.frame_src)

        # --- Frame Destino ---
        self.frame_dst = QFrame()
        self.frame_dst.setStyleSheet(f"background-color: #333333; border-radius: {c.CORNER_RADIUS}px;")
        dst_layout = QVBoxLayout(self.frame_dst)

        dst_layout.addWidget(QLabel(c.UI_DESTINATION_LABEL))

        dst_sel_layout = QHBoxLayout()
        dst_sel_layout.addWidget(QLabel(f"👤 {c.UI_LABEL_PROFILE}"))
        self.combo_dst_profile = QComboBox()
        self.combo_dst_profile.addItems(self.parent_app.logic.get_profiles(self.parent_app))
        self.combo_dst_profile.setCurrentText(self.parent_app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.UI_PROFILE_DEFAULT))
        self.combo_dst_profile.currentTextChanged.connect(self.update_dst_path_info)
        dst_sel_layout.addWidget(self.combo_dst_profile)
        dst_layout.addLayout(dst_sel_layout)

        self.lbl_dst = QLabel("")
        self.lbl_dst.setStyleSheet("color: #3498db; font-size: 11px;")
        self.lbl_dst.setWordWrap(True)
        dst_layout.addWidget(self.lbl_dst)

        self.scroll_layout.addWidget(self.frame_dst)

        # --- Opciones de Migración ---
        self.frame_opts = QFrame()
        self.frame_opts.setStyleSheet(f"background-color: #333333; border-radius: {c.CORNER_RADIUS}px;")
        opts_layout = QVBoxLayout(self.frame_opts)

        opts_layout.addWidget(QLabel(c.UI_WHAT_TO_MIGRATE))

        self.cb_versions = QCheckBox(c.UI_MIGRATE_VERSIONS)
        self.cb_versions.setChecked(True)
        self.cb_versions.stateChanged.connect(self.on_migration_option_change)
        opts_layout.addWidget(self.cb_versions)

        self.cb_worlds = QCheckBox(c.UI_MIGRATE_WORLDS)
        self.cb_worlds.stateChanged.connect(self.on_migration_option_change)
        opts_layout.addWidget(self.cb_worlds)

        self.cb_resources = QCheckBox(c.UI_MIGRATE_RESOURCES)
        self.cb_resources.stateChanged.connect(self.on_migration_option_change)
        opts_layout.addWidget(self.cb_resources)

        self.cb_all = QCheckBox(c.UI_MIGRATE_ALL)
        self.cb_all.setStyleSheet("font-weight: bold;")
        self.cb_all.stateChanged.connect(self.on_all_migration_toggle)
        opts_layout.addWidget(self.cb_all)

        self.scroll_layout.addWidget(self.frame_opts)

        # --- Método de Migración ---
        self.frame_method = QFrame()
        self.frame_method.setStyleSheet(f"background-color: #333333; border-radius: {c.CORNER_RADIUS}px;")
        method_layout = QVBoxLayout(self.frame_method)

        method_layout.addWidget(QLabel(c.UI_MIGRATION_METHOD))

        self.rb_copy = QRadioButton(c.UI_METHOD_COPY)
        self.rb_copy.setChecked(True)
        method_layout.addWidget(self.rb_copy)

        self.rb_move = QRadioButton(c.UI_METHOD_MOVE)
        method_layout.addWidget(self.rb_move)

        self.rb_link = QRadioButton(c.UI_METHOD_LINK)
        method_layout.addWidget(self.rb_link)

        self.scroll_layout.addWidget(self.frame_method)

        # --- Acción ---
        self.btn_migrate = QPushButton(c.UI_BUTTON_START_MIGRATION)
        self.btn_migrate.setObjectName("ActionButton")
        self.btn_migrate.setFixedHeight(40)
        self.btn_migrate.clicked.connect(self.start_migration)
        self.main_layout.addWidget(self.btn_migrate)

        self.setStyleSheet("background-color: #2b2b2b; color: white;")
        self.update_src_path_ui(c.UI_SOURCE_MODES_DISPLAY[0])
        self.update_dst_path_info()

    def on_all_migration_toggle(self, state):
        checked = state == Qt.Checked
        self.cb_versions.setEnabled(not checked)
        self.cb_worlds.setEnabled(not checked)
        self.cb_resources.setEnabled(not checked)
        if checked:
            self.cb_versions.setChecked(False)
            self.cb_worlds.setChecked(False)
            self.cb_resources.setChecked(False)

    def on_migration_option_change(self):
        if self.cb_versions.isChecked() or self.cb_worlds.isChecked() or self.cb_resources.isChecked():
            self.cb_all.setChecked(False)

    def update_src_path_ui(self, choice):
        if choice == c.UI_SOURCE_MODES_DISPLAY[0]: # Local (.local)
            path = os.path.join(os.path.expanduser("~"), c.LOCAL_SHARE_DIR)
            self.entry_src.setText(path)
            self.entry_src.setEnabled(False)
            self.frame_flatpak_id.hide()
            self.validate_source_path(path)
        elif choice == c.UI_SOURCE_MODES_DISPLAY[1]: # Flatpak (por ID)
            self.entry_src.setEnabled(False)
            self.frame_flatpak_id.show()
            app_id = self.entry_flatpak_src_id.text().strip() or c.DEFAULT_FLATPAK_ID
            path = os.path.join(os.path.expanduser("~"), f"{c.FLATPAK_DATA_DIR}/{app_id}/{c.MCPELAUNCHER_DATA_SUBDIR}")
            self.entry_src.setText(path)
            self.validate_source_path(path)
        else: # Personalizado
            self.entry_src.setEnabled(True)
            self.frame_flatpak_id.hide()
            self.lbl_src_validation.setText("")

    def validate_source_path(self, path):
        if not path:
            self.lbl_src_validation.setText("")
            return False
        if os.path.exists(path):
            if "mcpelauncher" in path or os.path.exists(os.path.join(path, c.VERSIONS_DIR)):
                self.lbl_src_validation.setText(c.UI_VALID_FOLDER_DETECTED)
                self.lbl_src_validation.setStyleSheet("color: green; font-size: 10px;")
                return True
            else:
                self.lbl_src_validation.setText(c.UI_INVALID_FOLDER_WARNING)
                self.lbl_src_validation.setStyleSheet("color: orange; font-size: 10px;")
                return False
        else:
            self.lbl_src_validation.setText(c.UI_FOLDER_NOT_EXISTS)
            self.lbl_src_validation.setStyleSheet("color: red; font-size: 10px;")
            return False

    def browse_src(self):
        d = ask_directory_native(self, title=c.UI_SELECT_SOURCE_FOLDER)
        if d:
            self.entry_src.setEnabled(True)
            self.entry_src.setText(d)
            self.combo_src.setCurrentText(c.UI_SOURCE_MODES_DISPLAY[2])
            self.validate_source_path(d)

    def update_dst_path_info(self):
        profile = self.combo_dst_profile.currentText()
        path = os.path.join(self.parent_app.active_path, c.PROFILES_DIR, profile)
        self.lbl_dst.setText(f"Ruta: {path}")

    def start_migration(self):
        src = self.entry_src.text().strip()
        profile = self.combo_dst_profile.currentText()
        dst = os.path.join(self.parent_app.active_path, c.PROFILES_DIR, profile)

        method = "copy"
        if self.rb_move.isChecked(): method = "move"
        elif self.rb_link.isChecked(): method = "link"

        migrate_all = self.cb_all.isChecked()
        migrate_versions = self.cb_versions.isChecked()
        migrate_worlds = self.cb_worlds.isChecked()
        migrate_resources = self.cb_resources.isChecked()

        if not os.path.exists(src):
            messagebox.showerror(self, c.UI_ERROR_TITLE, c.UI_FOLDER_NOT_EXISTS)
            return
        if src == dst:
            messagebox.showerror(self, c.UI_ERROR_TITLE, c.UI_ERROR_SAME_FOLDER)
            return
        if not any([migrate_all, migrate_versions, migrate_worlds, migrate_resources]):
            messagebox.showwarning(self, c.UI_INFO_TITLE, c.UI_ERROR_NOTHING_SELECTED)
            return

        items = []
        if migrate_all: items.append("TODO")
        else:
            if migrate_versions: items.append(c.UI_MIGRATE_VERSIONS_SIMPLE)
            if migrate_worlds: items.append(c.UI_MIGRATE_WORLDS_SIMPLE)
            if migrate_resources: items.append(c.UI_MIGRATE_RESOURCES_SIMPLE)

        msg = c.UI_MIGRATION_CONFIRM_MSG.format(src=src, dst=dst, method=method.upper(), items=', '.join(items))
        if not messagebox.askyesno(self, c.UI_CONFIRM_TITLE, msg):
            return

        self.progress_dialog = ProgressDialog(self, c.UI_MIGRATING_TITLE, c.UI_MIGRATING_MSG)
        self.progress_dialog.show()

        thread = threading.Thread(target=self._run_migration, args=(src, dst, method, migrate_all, migrate_versions, migrate_worlds, migrate_resources))
        thread.start()

    def _run_migration(self, src, dst_profile_path, method, migrate_all, migrate_versions, migrate_worlds, migrate_resources):
        try:
            migrated_count = 0
            base_dst = self.parent_app.active_path

            def process_item(s_item, d_item):
                if os.path.exists(d_item): return False
                if method == "copy":
                    if os.path.isdir(s_item): shutil.copytree(s_item, d_item)
                    else: shutil.copy2(s_item, d_item)
                elif method == "move": shutil.move(s_item, d_item)
                elif method == "link": os.symlink(s_item, d_item)
                return True

            if migrate_all:
                if process_item(src, base_dst): migrated_count = 1
            else:
                if migrate_versions:
                    src_dir, dst_dir = os.path.join(src, c.VERSIONS_DIR), os.path.join(base_dst, c.VERSIONS_DIR)
                    if os.path.exists(src_dir):
                        os.makedirs(dst_dir, exist_ok=True)
                        for item in os.listdir(src_dir):
                            if process_item(os.path.join(src_dir, item), os.path.join(dst_dir, item)): migrated_count += 1
                if migrate_worlds:
                    src_dir, dst_dir = os.path.join(src, c.WORLDS_DIR), os.path.join(dst_profile_path, c.WORLDS_DIR)
                    if os.path.exists(src_dir):
                        os.makedirs(dst_dir, exist_ok=True)
                        for item in os.listdir(src_dir):
                            if process_item(os.path.join(src_dir, item), os.path.join(dst_dir, item)): migrated_count += 1
                if migrate_resources:
                    src_dir = os.path.join(src, "games/com.mojang/resource_packs")
                    dst_dir = os.path.join(dst_profile_path, "games/com.mojang/resource_packs")
                    if os.path.exists(src_dir):
                        os.makedirs(dst_dir, exist_ok=True)
                        for item in os.listdir(src_dir):
                            if process_item(os.path.join(src_dir, item), os.path.join(dst_dir, item)): migrated_count += 1

            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.on_migration_finished(migrated_count))
        except Exception as e:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.on_migration_error(str(e)))

    def on_migration_finished(self, count):
        self.progress_dialog.accept()
        messagebox.showinfo(self, c.UI_SUCCESS_TITLE, c.UI_MIGRATION_SUCCESS_MSG.format(count=count))
        self.parent_app.logic.refresh_version_list(self.parent_app)
        self.accept()

    def on_migration_error(self, err):
        self.progress_dialog.accept()
        messagebox.showerror(self, c.UI_ERROR_TITLE, f"Error: {err}")
