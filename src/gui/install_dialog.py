from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFrame, QRadioButton,
                             QTabWidget, QWidget, QComboBox, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal, QProcess, QTimer
import os
import zipfile
import re
import urllib.request
import json
import threading
from src.gui import custom_dialogs as messagebox
from src.utils.dialogs import ask_open_filename_native
from src import constants as c

class GooglePlayTab(QWidget):
    def __init__(self, parent_dialog):
        super().__init__()
        self.dialog = parent_dialog
        self.app = parent_dialog.parent_app
        self.all_versions_data = []
        self.setup_ui()
        self.load_versions("x86_64")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Login Section
        self.btn_login = QPushButton(c.UI_BUTTON_LOGIN_GOOGLE)
        self.btn_login.setFixedHeight(40)
        self.btn_login.clicked.connect(self.do_login)
        layout.addWidget(self.btn_login)

        self.lbl_session_status = QLabel("")
        self.lbl_session_status.setAlignment(Qt.AlignCenter)
        self.lbl_session_status.setStyleSheet("font-weight: bold; font-size: 11px;")
        layout.addWidget(self.lbl_session_status)
        self.update_session_status()

        # Arch & Filter Selection
        selectors_layout = QHBoxLayout()

        # Arch
        selectors_layout.addWidget(QLabel(c.UI_LABEL_SELECT_ARCH))
        self.combo_arch = QComboBox()
        self.combo_arch.addItems(["x86_64", "x86"])
        self.combo_arch.currentTextChanged.connect(self.load_versions)
        selectors_layout.addWidget(self.combo_arch, 1)

        # Filter
        selectors_layout.addWidget(QLabel(c.UI_LABEL_FILTER_VERSIONS))
        self.combo_filter = QComboBox()
        self.combo_filter.addItems([c.UI_FILTER_ALL, c.UI_FILTER_STABLE, c.UI_FILTER_BETA])
        self.combo_filter.currentTextChanged.connect(self.apply_filter)
        selectors_layout.addWidget(self.combo_filter, 1)

        layout.addLayout(selectors_layout)

        # Version Selection
        layout.addWidget(QLabel(c.UI_LABEL_SELECT_VERSION))
        self.combo_versions = QComboBox()
        layout.addWidget(self.combo_versions)

        layout.addStretch()

        # Progress Section
        self.status_label = QLabel(c.UI_STATUS_LOGIN_REQUIRED)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.btn_download = QPushButton(c.UI_BUTTON_INSTALL_NOW)
        self.btn_download.setObjectName("ActionButton")
        self.btn_download.setFixedHeight(50)
        self.btn_download.clicked.connect(self.start_download_flow)
        layout.addWidget(self.btn_download)

    def do_login(self):
        self.app.logic.launch_google_login(self.app)
        # Check status again after a while as the login window is external
        QTimer.singleShot(5000, self.update_session_status)

    def update_session_status(self):
        is_active = self.app.logic.check_google_session(self.app)
        if is_active:
            self.lbl_session_status.setText(c.UI_STATUS_SESSION_ACTIVE)
            self.lbl_session_status.setStyleSheet(f"color: {c.COLOR_PRIMARY_GREEN}; font-weight: bold; font-size: 11px;")
        else:
            self.lbl_session_status.setText(c.UI_STATUS_SESSION_INACTIVE)
            self.lbl_session_status.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 11px;")

    def load_versions(self, arch):
        # Fetch versions from manifest URL asynchronously
        self.combo_versions.clear()
        self.combo_versions.addItem(c.UI_LABEL_SEARCHING)
        self.combo_versions.setEnabled(False)

        def fetch():
            try:
                url = c.VERSION_MANIFEST_URL.format(arch=arch)
                with urllib.request.urlopen(url, timeout=5) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode())
                        self.all_versions_data = data
                        QTimer.singleShot(0, self.apply_filter)
            except Exception as e:
                print(f"Error loading versions: {e}")
                QTimer.singleShot(0, lambda: [self.combo_versions.clear(), self.combo_versions.setEnabled(True)])

        threading.Thread(target=fetch, daemon=True).start()

    def apply_filter(self):
        self.combo_versions.clear()
        self.combo_versions.setEnabled(True)
        filter_type = self.combo_filter.currentText()

        # data is list of lists [[vcode, vname, isbeta], ...]
        for ver in self.all_versions_data:
            is_beta = len(ver) > 2 and ver[2]

            if filter_type == c.UI_FILTER_STABLE and is_beta:
                continue
            if filter_type == c.UI_FILTER_BETA and not is_beta:
                continue

            display = f"{ver[1]} ({ver[0]})"
            if is_beta:
                display += " [BETA]"
            self.combo_versions.addItem(display, (ver[0], ver[1])) # Store both code and name

    def start_download_flow(self):
        version_data = self.combo_versions.currentData()
        if not version_data: return

        version_code, version_name = version_data
        arch = self.combo_arch.currentText()

        # Determine target mode/path
        mode_key = self.dialog.target_mode_val
        is_target_flatpak = (mode_key == c.MODE_INSTALL_FLATPAK)
        target_root = self.dialog.get_target_root()
        flatpak_id = self.dialog.entry_flatpak_id.text().strip() if is_target_flatpak else None

        self.btn_download.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(c.UI_STATUS_DOWNLOADING)

        # This will call logic to start gplaydl and then extraction
        self.app.logic.download_and_install_google(
            self.app, version_code, version_name, arch,
            target_root, is_target_flatpak, flatpak_id,
            progress_callback=self.update_progress,
            status_callback=self.status_label.setText,
            finished_callback=self.on_finished
        )

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_finished(self, success, message):
        self.btn_download.setEnabled(True)
        self.progress_bar.setVisible(False)
        if success:
            messagebox.showinfo(self, c.UI_SUCCESS_TITLE, message)
            self.dialog.accept()
        else:
            messagebox.showerror(self, c.UI_ERROR_TITLE, message)

class LocalApkTab(QWidget):
    def __init__(self, parent_dialog):
        super().__init__()
        self.dialog = parent_dialog
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # 1. Selección de APK
        self.frame_apk = QFrame()
        self.frame_apk.setStyleSheet(f"background-color: #333333; border-radius: {c.CORNER_RADIUS}px;")
        apk_layout = QVBoxLayout(self.frame_apk)

        lbl_apk_title = QLabel(c.UI_APK_FILE_LABEL)
        lbl_apk_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        apk_layout.addWidget(lbl_apk_title)

        apk_input_layout = QHBoxLayout()
        self.entry_apk = QLineEdit()
        self.entry_apk.setPlaceholderText(c.UI_SELECT_APK_PLACEHOLDER)
        self.entry_apk.setReadOnly(True)
        apk_input_layout.addWidget(self.entry_apk)

        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(40)
        btn_browse.clicked.connect(self.browse_apk)
        apk_input_layout.addWidget(btn_browse)
        apk_layout.addLayout(apk_input_layout)

        self.layout.addWidget(self.frame_apk)

        # Label de Estado de Arquitectura
        self.lbl_arch = QLabel("")
        self.lbl_arch.setWordWrap(True)
        self.lbl_arch.setAlignment(Qt.AlignCenter)
        self.lbl_arch.setStyleSheet("font-weight: bold;")
        self.layout.addWidget(self.lbl_arch)

        # 2. Nombre de la Versión
        self.frame_name = QFrame()
        self.frame_name.setStyleSheet(f"background-color: #333333; border-radius: {c.CORNER_RADIUS}px;")
        name_layout = QVBoxLayout(self.frame_name)

        lbl_name_title = QLabel(c.UI_VERSION_NAME_LABEL)
        lbl_name_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        name_layout.addWidget(lbl_name_title)

        self.entry_name = QLineEdit()
        self.entry_name.setPlaceholderText(c.UI_VERSION_NAME_PLACEHOLDER)
        name_layout.addWidget(self.entry_name)

        self.layout.addWidget(self.frame_name)
        self.layout.addStretch()

        # Botón de Acción
        self.btn_install = QPushButton(c.UI_BUTTON_INSTALL_NOW)
        self.btn_install.setObjectName("ActionButton")
        self.btn_install.setFixedHeight(50)
        self.btn_install.setEnabled(False)
        self.btn_install.clicked.connect(self.start_install)
        self.layout.addWidget(self.btn_install)

    def browse_apk(self):
        path = ask_open_filename_native(self, title=c.UI_SELECT_APK_TITLE, filetypes=[(c.UI_APK_FILES_TYPE, "*.apk")])
        if path:
            self.entry_apk.setText(path)
            # Guess version
            base = os.path.basename(path)
            match = re.search(r"(\d+\.\d+(\.\d+)?)", base)
            if match:
                self.entry_name.setText(match.group(1))
            self.check_architecture(path)

    def check_architecture(self, apk_path):
        found_x86 = False
        found_x64 = False
        found_arm = False
        has_assets = False
        has_lib = False

        try:
            with zipfile.ZipFile(apk_path, "r") as z:
                for n in z.namelist():
                    if n.startswith("assets/"):
                        has_assets = True
                    if n.startswith("lib/"):
                        has_lib = True
                    if "lib/x86/" in n:
                        found_x86 = True
                    if "lib/x86_64/" in n:
                        found_x64 = True
                    if "lib/armeabi" in n or "lib/arm64" in n:
                        found_arm = True
        except Exception as e:
            self.lbl_arch.setText(c.UI_ERROR_READING_APK.format(e=e))
            self.lbl_arch.setStyleSheet("color: red; font-weight: bold;")
            self.btn_install.setEnabled(False)
            return

        is_compatible = False
        msg = ""
        color = "gray"

        if not has_assets or not has_lib:
            msg = c.UI_APK_INVALID
            color = "red"
        elif found_x86 or found_x64:
            msg = c.UI_APK_COMPATIBLE_X86
            color = "green"
            is_compatible = True
        elif found_arm:
            msg = c.UI_APK_INCOMPATIBLE_ARM
            color = "red"
        else:
            msg = c.UI_APK_INVALID
            color = "orange"

        self.lbl_arch.setText(msg)
        self.lbl_arch.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.btn_install.setEnabled(is_compatible)

    def start_install(self):
        apk = self.entry_apk.text().strip()
        name = self.entry_name.text().strip()
        if not apk or not os.path.exists(apk):
            messagebox.showerror(self, c.UI_ERROR_TITLE, c.UI_ERROR_SELECT_VALID_APK)
            return
        if not name:
            messagebox.showerror(self, c.UI_ERROR_TITLE, c.UI_ERROR_WRITE_VERSION_NAME)
            return

        target_root = self.dialog.get_target_root()
        is_target_flatpak = (self.dialog.target_mode_val == c.MODE_INSTALL_FLATPAK)
        f_id = self.dialog.entry_flatpak_id.text().strip() if is_target_flatpak else None

        self.dialog.accept()
        self.dialog.parent_app.logic.process_apk(
            self.dialog.parent_app, apk, name, target_root=target_root,
            is_target_flatpak=is_target_flatpak, flatpak_id=f_id
        )

class InstallDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_app = parent
        self.setWindowTitle(c.UI_INSTALL_NEW_VERSION_TITLE)
        self.resize(600, 700)

        self.target_mode_val = c.MODE_INSTALL_FLATPAK if parent.running_in_flatpak else c.MODE_INSTALL_LOCAL
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)

        # Tab Widget
        self.tabs = QTabWidget()
        self.google_tab = GooglePlayTab(self)
        self.local_tab = LocalApkTab(self)

        self.tabs.addTab(self.google_tab, c.UI_INSTALL_TAB_GOOGLE)
        self.tabs.addTab(self.local_tab, c.UI_INSTALL_TAB_LOCAL)
        self.main_layout.addWidget(self.tabs)

        # 3. Modo de Instalación (Global para ambas pestañas)
        self.frame_mode = QFrame()
        self.frame_mode.setStyleSheet(f"background-color: #333333; border-radius: {c.CORNER_RADIUS}px;")
        mode_layout = QVBoxLayout(self.frame_mode)

        lbl_mode_title = QLabel(c.UI_INSTALL_MODE_DEST_LABEL)
        lbl_mode_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        mode_layout.addWidget(lbl_mode_title)

        if self.parent_app.running_in_flatpak:
            modes_available = [
                (c.MODE_INSTALL_OWN, c.UI_INSTALL_MODE_OWN),
                (c.MODE_INSTALL_SHARED, c.UI_INSTALL_MODE_SHARED),
                (c.MODE_INSTALL_FLATPAK, c.UI_INSTALL_MODE_FLATPAK_DESC),
            ]
            default_mode = c.MODE_INSTALL_OWN
        else:
            modes_available = [
                (c.MODE_INSTALL_LOCAL, c.UI_INSTALL_MODE_LOCAL),
                (c.MODE_INSTALL_FLATPAK, c.UI_INSTALL_MODE_FLATPAK_DESC),
            ]
            default_mode = c.MODE_INSTALL_LOCAL

        self.target_mode_val = default_mode
        self.radio_buttons = []

        for mode_key, mode_display in modes_available:
            rb = QRadioButton(mode_display if mode_key != c.MODE_INSTALL_FLATPAK else c.UI_FLATPAK_CUSTOM_ID_LABEL)
            rb.setChecked(mode_key == default_mode)
            rb.toggled.connect(lambda checked, k=mode_key: self.set_target_mode(k) if checked else None)
            mode_layout.addWidget(rb)
            self.radio_buttons.append((rb, mode_key))

            if mode_key == c.MODE_INSTALL_FLATPAK:
                self.entry_flatpak_id = QLineEdit()
                self.entry_flatpak_id.setText(self.parent_app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.DEFAULT_FLATPAK_ID))
                self.entry_flatpak_id.setContentsMargins(25, 0, 0, 0)
                self.entry_flatpak_id.setEnabled(mode_key == default_mode)
                mode_layout.addWidget(self.entry_flatpak_id)

        self.main_layout.addWidget(self.frame_mode)
        self.setStyleSheet("background-color: #2b2b2b; color: white;")

    def set_target_mode(self, mode_key):
        self.target_mode_val = mode_key
        if hasattr(self, 'entry_flatpak_id'):
            self.entry_flatpak_id.setEnabled(mode_key == c.MODE_INSTALL_FLATPAK)

    def get_target_root(self):
        mode_key = self.target_mode_val
        if mode_key == c.MODE_INSTALL_FLATPAK:
            custom_id = self.entry_flatpak_id.text().strip() or c.DEFAULT_FLATPAK_ID
            return os.path.join(self.parent_app.home, f".var/app/{custom_id}/data/mcpelauncher")
        elif mode_key == c.MODE_INSTALL_OWN:
            return self.parent_app.our_data_path if self.parent_app.running_in_flatpak else self.parent_app.compiled_path
        elif mode_key == c.MODE_INSTALL_SHARED:
            return os.path.join(self.parent_app.home, c.LOCAL_SHARE_DIR)
        else: # MODE_INSTALL_LOCAL
            return self.parent_app.compiled_path
