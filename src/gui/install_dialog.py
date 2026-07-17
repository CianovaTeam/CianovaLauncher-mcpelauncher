from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFrame, QRadioButton,
                             QTabWidget, QWidget, QComboBox, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal, QProcess, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent
import os
import ssl
import zipfile
import re
import urllib.request
import urllib.error
import json
import threading
from src.gui import custom_dialogs as messagebox
from src.utils.dialogs import ask_open_filename_native
from src.utils.logger import logger
from src import constants as c

class VersionFetcher(QThread):
    """Thread that fetches available version data from a remote manifest URL."""
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, arch):
        """Initialize the fetcher with the target CPU architecture."""
        super().__init__()
        self.arch = arch

    def run(self):
        """Fetch version manifest data and emit finished or error signal."""
        try:
            url = c.VERSION_MANIFEST_URL.format(arch=self.arch)
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=ctx) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    self.finished.emit(data)
                else:
                    self.error.emit(f"HTTP {response.status}")
        except Exception as e:
            self.error.emit(str(e))

class VersionWarningsFetcher(QThread):
    """Thread that fetches version compatibility warnings from a remote JSON."""
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(c.VERSION_WARNINGS_URL, timeout=8, context=ctx) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    self.finished.emit(data.get("warnings", []))
                else:
                    self.finished.emit([])
        except Exception as e:
            logger.warning(f"Failed to fetch version warnings: {e}")
            self.finished.emit([])

class GooglePlayTab(QWidget):
    """Tab widget for searching and installing versions from Google Play."""

    def __init__(self, parent_dialog):
        super().__init__()
        self.dialog = parent_dialog
        self.app = parent_dialog.parent_app
        self.all_versions_data = []
        self.fetcher = None
        self.setup_ui()
        self.load_versions("x86_64")

    def setup_ui(self):
        """Build the UI layout for the Google Play tab."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Login Section
        self.btn_login = QPushButton(c.t("UI_BUTTON_LOGIN_GOOGLE"))
        self.btn_login.setFixedHeight(40)
        self.btn_login.clicked.connect(self.do_login)
        layout.addWidget(self.btn_login)

        self.lbl_session_status = QLabel("")
        self.lbl_session_status.setAlignment(Qt.AlignCenter)
        self.lbl_session_status.setStyleSheet("font-weight: bold; font-size: 11px;")
        layout.addWidget(self.lbl_session_status)

        # Arch & Filter Selection
        selectors_layout = QHBoxLayout()

        # Arch
        selectors_layout.addWidget(QLabel(c.t("UI_LABEL_SELECT_ARCH")))
        self.combo_arch = QComboBox()
        self.combo_arch.addItems(["x86_64", "x86"])
        self.combo_arch.currentTextChanged.connect(self.load_versions)
        selectors_layout.addWidget(self.combo_arch, 1)

        # Filter
        selectors_layout.addWidget(QLabel(c.t("UI_LABEL_FILTER_VERSIONS")))
        self.combo_filter = QComboBox()
        self.combo_filter.addItems([c.t("UI_FILTER_STABLE"), c.t("UI_FILTER_ALL"), c.t("UI_FILTER_BETA")])
        self.combo_filter.setCurrentText(c.t("UI_FILTER_STABLE"))
        self.combo_filter.currentTextChanged.connect(self.apply_filter)
        selectors_layout.addWidget(self.combo_filter, 1)

        layout.addLayout(selectors_layout)

        # Version Selection
        layout.addWidget(QLabel(c.t("UI_LABEL_SELECT_VERSION")))
        self.combo_versions = QComboBox()
        layout.addWidget(self.combo_versions)

        layout.addStretch()

        # Progress Section
        self.status_label = QLabel(c.t("UI_STATUS_LOGIN_REQUIRED"))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.btn_download = QPushButton(c.t("UI_BUTTON_INSTALL_NOW"))
        self.btn_download.setObjectName("ActionButton")
        self.btn_download.setFixedHeight(50)
        self.btn_download.clicked.connect(self.start_download_flow)
        layout.addWidget(self.btn_download)

        # Call this LAST to ensure btn_download exists
        self.update_session_status()

    def do_login(self):
        """Launch the Google login flow and monitor for session token."""
        # Avoid double-launch
        if getattr(self, "_login_poll_timer", None) and self._login_poll_timer.isActive():
            return

        self.btn_login.setEnabled(False)
        self.lbl_session_status.setText(c.t("UI_STATUS_LOGIN_IN_PROGRESS"))
        self.lbl_session_status.setStyleSheet(
            f"color: {c.COLOR_PRIMARY_GREEN}; font-weight: bold; font-size: 11px;"
        )

        # Create poll timer BEFORE launching to avoid race:
        # if process exits before the timer exists, on_finished tries to
        # stop a nonexistent timer and leaves the UI stuck in "loading".
        self._login_poll_count = 0
        self._login_poll_max = 30  # 30 * 2s = 60s
        self._login_poll_timer = QTimer(self)
        self._login_poll_timer.timeout.connect(self._poll_login_status)

        def on_signin_finished(exit_code):
            # Re-enable login and refresh session immediately when signin window closes
            self.btn_login.setEnabled(True)
            if self._login_poll_timer.isActive():
                self._login_poll_timer.stop()
            self.update_session_status()

        proc = self.app.logic.launch_google_login(self.app, on_finished=on_signin_finished)
        if proc is None:
            self.btn_login.setEnabled(True)
            if self._login_poll_timer.isActive():
                self._login_poll_timer.stop()
            self.update_session_status()
            return

        # Only start the poll timer if the process is still running
        # (sometimes QProcess finishes before we get here)
        if proc.state() == QProcess.NotRunning:
            # Already finished; on_finished already ran and cleaned up
            logger.debug("do_login: signin process already finished, skipping poll timer")
        else:
            self._login_poll_timer.start(2000)

    def _poll_login_status(self):
        self._login_poll_count += 1
        if self.app.logic.check_google_session(self.app):
            self._login_poll_timer.stop()
            self.btn_login.setEnabled(True)
            self.update_session_status()
            return

        self.lbl_session_status.setText(
            c.t("UI_STATUS_LOGIN_WAITING", s=self._login_poll_count * 2)
        )

        if self._login_poll_count >= self._login_poll_max:
            self._login_poll_timer.stop()
            self.btn_login.setEnabled(True)
            self.update_session_status()

    def update_session_status(self):
        """Update the UI to reflect the current Google session state."""
        is_active = self.app.logic.check_google_session(self.app)
        if is_active:
            self.lbl_session_status.setText(c.t("UI_STATUS_SESSION_ACTIVE"))
            self.lbl_session_status.setStyleSheet(f"color: {c.COLOR_PRIMARY_GREEN}; font-weight: bold; font-size: 11px;")
            self.btn_download.setEnabled(True)
        else:
            self.lbl_session_status.setText(c.t("UI_STATUS_SESSION_INACTIVE"))
            self.lbl_session_status.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 11px;")
            self.btn_download.setEnabled(False)

        # Force button color update respecting disabled state
        accent = c.THEME_COLOR_MAP.get(self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue"), "#1f6aa5")
        self.btn_download.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent}; 
                color: white; 
                border-radius: 12px; 
                font-weight: bold;
            }}
            QPushButton:disabled {{
                background-color: #444444;
                color: #888888;
            }}
        """)

    def load_versions(self, arch):
        """Fetch available versions for the given architecture in a background thread."""
        # Stop any ongoing fetch
        if self.fetcher and self.fetcher.isRunning():
            self.fetcher.terminate()
            self.fetcher.wait()

        self.all_versions_data = []
        self.combo_versions.clear()
        self.combo_versions.addItem(c.t("UI_LABEL_SEARCHING"))
        self.combo_versions.setEnabled(False)

        self.fetcher = VersionFetcher(arch)
        self.fetcher.finished.connect(self.on_versions_loaded)
        self.fetcher.error.connect(self.on_versions_error)
        self.fetcher.start()

    def on_versions_loaded(self, data):
        """Handle successfully loaded version data and apply the current filter."""
        self.all_versions_data = data
        self.apply_filter()

    def on_versions_error(self, err):
        """Display an error message when version loading fails."""
        logger.error(f"Error loading versions: {err}")
        self.combo_versions.clear()
        self.combo_versions.addItem(f"❌ Error al cargar (Verificar Internet)")
        self.combo_versions.setEnabled(True)

    def apply_filter(self, _text=None):
        """Filter the version list by stable/beta/all and populate the combo box."""
        self.combo_versions.clear()
        self.combo_versions.setEnabled(True)
        
        if not self.all_versions_data:
            return

        filter_type = self.combo_filter.currentText()

        # "Latest (auto)" — vcode=0 → app_logic omits -v so Google picks
        # whichever version is currently being offered. Most reliable path:
        # specific old vcodes from the manifest are often rejected with
        # status=2 even on accounts that own the app.
        self.combo_versions.addItem(c.t("UI_VERSION_LATEST_LABEL"), (0, "latest"))

        # data is list of lists [[vcode, vname, isbeta], ...]
        # Reversed to show newest first
        for ver in reversed(self.all_versions_data):
            is_beta = len(ver) > 2 and bool(ver[2])

            if filter_type == c.t("UI_FILTER_STABLE") and is_beta:
                continue
            if filter_type == c.t("UI_FILTER_BETA") and not is_beta:
                continue

            display = f"{ver[1]} ({ver[0]})"
            if is_beta:
                display += " [BETA]"
            self.combo_versions.addItem(display, (ver[0], ver[1])) # Store both code and name


    def start_download_flow(self):
        """Begin downloading and installing the selected Google Play version."""
        version_data = self.combo_versions.currentData()
        if not version_data:
            logger.warning("start_download_flow: no version selected")
            return

        version_code, version_name = version_data
        arch = self.combo_arch.currentText()

        warning = self.dialog.get_warning_for_version(version_name)
        if warning:
            messagebox.showwarning(
                self,
                "Aviso de compatibilidad",
                f"Se ha reportado que la versión {version_name} "
                f"presenta problemas conocidos:\n\n{warning}\n\n"
                f"Puedes continuar con la instalación si lo deseas."
            )

        # Determine target mode/path
        mode_key = self.dialog.target_mode_val
        is_target_flatpak = (mode_key == c.MODE_INSTALL_FLATPAK)
        target_root = self.dialog.get_target_root()
        flatpak_id = self.dialog.entry_flatpak_id.text().strip() if is_target_flatpak else None

        logger.info(f"start_download_flow: vcode={version_code} vname={version_name} "
              f"arch={arch} mode={mode_key} target_root={target_root} flatpak_id={flatpak_id}")

        self.btn_download.setEnabled(False)
        self.btn_download.setText(c.t("UI_STATUS_DOWNLOADING"))
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(c.t("UI_STATUS_DOWNLOADING"))

        # This will call logic to start gplaydl and then extraction
        self.app.logic.download_and_install_google(
            self.app, version_code, version_name, arch,
            target_root, is_target_flatpak, flatpak_id,
            progress_callback=self.update_progress,
            status_callback=self.status_label.setText,
            finished_callback=self.on_finished
        )

    def update_progress(self, value):
        """Update the progress bar to the given percentage value."""
        self.progress_bar.setValue(value)

    def on_finished(self, success, message):
        """Handle completion of the download and install process."""
        self.btn_download.setEnabled(True)
        self.btn_download.setText(c.t("UI_BUTTON_INSTALL_NOW"))
        self.progress_bar.setVisible(False)
        if success:
            messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), message)
            self.dialog.accept()
        else:
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), message)

class LocalApkTab(QWidget):
    """Tab widget for installing Minecraft from a local APK file."""

    def __init__(self, parent_dialog):
        super().__init__()
        self.dialog = parent_dialog
        self.setAcceptDrops(True)
        self.setup_ui()

    _NORMAL_STYLE = ""

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith(".apk"):
                    event.acceptProposedAction()
                    self.frame_apk.setStyleSheet(f"background-color: #3a3a3a; border-radius: {c.CORNER_RADIUS}px;")
                    return

    def dragLeaveEvent(self, event):
        self.frame_apk.setStyleSheet(self._NORMAL_STYLE)

    def dropEvent(self, event: QDropEvent):
        self.frame_apk.setStyleSheet(self._NORMAL_STYLE)
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.endswith(".apk"):
                self._set_apk_path(path)
                return

    def _set_apk_path(self, path):
        self.entry_apk.setText(path)
        base = os.path.basename(path)
        match = re.search(r"(\d+\.\d+(\.\d+)?)", base)
        if match:
            self.entry_name.setText(match.group(1))
        self.check_architecture(path)

    def setup_ui(self):
        """Build the UI layout for the local APK installation tab."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # 1. Selección de APK
        self.frame_apk = QFrame()
        self._NORMAL_STYLE = f"background-color: #333333; border-radius: {c.CORNER_RADIUS}px;"
        self.frame_apk.setStyleSheet(self._NORMAL_STYLE)
        apk_layout = QVBoxLayout(self.frame_apk)

        lbl_apk_title = QLabel(c.t("UI_APK_FILE_LABEL"))
        lbl_apk_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        apk_layout.addWidget(lbl_apk_title)

        apk_input_layout = QHBoxLayout()
        self.entry_apk = QLineEdit()
        self.entry_apk.setPlaceholderText(c.t("UI_SELECT_APK_PLACEHOLDER"))
        self.entry_apk.setReadOnly(True)
        apk_input_layout.addWidget(self.entry_apk)

        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(40)
        btn_browse.clicked.connect(self.browse_apk)
        apk_input_layout.addWidget(btn_browse)
        apk_layout.addLayout(apk_input_layout)

        lbl_drop_hint = QLabel(c.t("UI_APK_DROP_HINT"))
        lbl_drop_hint.setAlignment(Qt.AlignCenter)
        lbl_drop_hint.setStyleSheet("color: #888888; font-size: 12px; padding: 5px;")
        apk_layout.addWidget(lbl_drop_hint)

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

        lbl_name_title = QLabel(c.t("UI_VERSION_NAME_LABEL"))
        lbl_name_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        name_layout.addWidget(lbl_name_title)

        self.entry_name = QLineEdit()
        self.entry_name.setPlaceholderText(c.t("UI_VERSION_NAME_PLACEHOLDER"))
        name_layout.addWidget(self.entry_name)

        self.layout.addWidget(self.frame_name)
        self.layout.addStretch()

        # Botón de Acción
        self.btn_install = QPushButton(c.t("UI_BUTTON_INSTALL_NOW"))
        self.btn_install.setObjectName("ActionButton")
        self.btn_install.setFixedHeight(50)
        self.btn_install.setEnabled(False)
        self.btn_install.clicked.connect(self.start_install)
        self.layout.addWidget(self.btn_install)

    def browse_apk(self):
        """Open a file picker to select an APK and analyze its architecture."""
        path = ask_open_filename_native(self, title=c.t("UI_SELECT_APK_TITLE"), filetypes=[(c.t("UI_APK_FILES_TYPE"), "*.apk")])
        if path:
            self._set_apk_path(path)

    def check_architecture(self, apk_path):
        """Inspect the APK to determine x86, ARM support and compatibility."""
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
            self.lbl_arch.setText(c.t("UI_ERROR_READING_APK", e=e))
            self.lbl_arch.setStyleSheet("color: red; font-weight: bold;")
            self.btn_install.setEnabled(False)
            return

        is_compatible = False
        msg = ""
        color = "gray"

        if not has_assets or not has_lib:
            msg = c.t("UI_APK_INVALID")
            color = "red"
        elif found_x86 or found_x64:
            msg = c.t("UI_APK_COMPATIBLE_X86")
            color = "green"
            is_compatible = True
        elif found_arm:
            msg = c.t("UI_APK_INCOMPATIBLE_ARM")
            color = "red"
        else:
            msg = c.t("UI_APK_INVALID")
            color = "orange"

        self.lbl_arch.setText(msg)
        self.lbl_arch.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.btn_install.setEnabled(is_compatible)

    def start_install(self):
        """Validate inputs and trigger APK installation via the app logic."""
        apk = self.entry_apk.text().strip()
        name = self.entry_name.text().strip()
        if not apk or not os.path.exists(apk):
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), c.t("UI_ERROR_SELECT_VALID_APK"))
            return
        if not name:
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), c.t("UI_ERROR_WRITE_VERSION_NAME"))
            return

        warning = self.dialog.get_warning_for_version(name)
        if warning:
            messagebox.showwarning(
                self,
                "Aviso de compatibilidad",
                f"Se ha reportado que la versión {name} "
                f"presenta problemas conocidos:\n\n{warning}\n\n"
                f"Puedes continuar con la instalación si lo deseas."
            )

        target_root = self.dialog.get_target_root()
        is_target_flatpak = (self.dialog.target_mode_val == c.MODE_INSTALL_FLATPAK)
        f_id = self.dialog.entry_flatpak_id.text().strip() if is_target_flatpak else None

        self.dialog.parent_app.logic.process_apk(
            self.dialog.parent_app, apk, name, target_root=target_root,
            is_target_flatpak=is_target_flatpak, flatpak_id=f_id
        )
        self.dialog.accept()

class InstallDialog(QDialog):
    """Dialog for installing new Minecraft versions from APK files or Google Play."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_app = parent
        self.setWindowTitle(c.t("UI_INSTALL_NEW_VERSION_TITLE"))
        self.resize(600, 700)

        self.target_mode_val = c.MODE_INSTALL_FLATPAK if parent.running_in_flatpak else c.MODE_INSTALL_LOCAL
        self.warnings_data = []
        self._warnings_fetcher = None
        self._fetch_warnings()
        self.setup_ui()

    def setup_ui(self):
        """Build the full dialog UI with tabs, mode selection, and styling."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)

        # Tab Widget
        self.tabs = QTabWidget()
        self.google_tab = GooglePlayTab(self)
        self.local_tab = LocalApkTab(self)

        self.tabs.addTab(self.local_tab, c.t("UI_INSTALL_TAB_LOCAL"))
        self.tabs.addTab(self.google_tab, c.t("UI_INSTALL_TAB_GOOGLE"))
        self.main_layout.addWidget(self.tabs)

        # 3. Modo de Instalación (Global para ambas pestañas)
        self.frame_mode = QFrame()
        self.frame_mode.setStyleSheet(f"background-color: #333333; border-radius: {c.CORNER_RADIUS}px;")
        mode_layout = QVBoxLayout(self.frame_mode)

        lbl_mode_title = QLabel(c.t("UI_INSTALL_MODE_DEST_LABEL"))
        lbl_mode_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        mode_layout.addWidget(lbl_mode_title)

        if self.parent_app.running_in_flatpak:
            modes_available = [
                (c.MODE_INSTALL_OWN, c.t("UI_INSTALL_MODE_OWN")),
                (c.MODE_INSTALL_SHARED, c.t("UI_INSTALL_MODE_SHARED")),
                (c.MODE_INSTALL_FLATPAK, c.t("UI_INSTALL_MODE_FLATPAK_DESC")),
            ]
            default_mode = c.MODE_INSTALL_OWN
        else:
            modes_available = [
                (c.MODE_INSTALL_LOCAL, c.t("UI_INSTALL_MODE_LOCAL")),
                (c.MODE_INSTALL_FLATPAK, c.t("UI_INSTALL_MODE_FLATPAK_DESC")),
            ]
            default_mode = c.MODE_INSTALL_LOCAL

        self.target_mode_val = default_mode
        self.radio_buttons = []

        for mode_key, mode_display in modes_available:
            rb = QRadioButton(mode_display if mode_key != c.MODE_INSTALL_FLATPAK else c.t("UI_FLATPAK_CUSTOM_ID_LABEL"))
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
        """Update the selected installation mode and toggle the Flatpak ID field."""
        self.target_mode_val = mode_key
        if hasattr(self, 'entry_flatpak_id'):
            self.entry_flatpak_id.setEnabled(mode_key == c.MODE_INSTALL_FLATPAK)

    def _fetch_warnings(self):
        self._warnings_fetcher = VersionWarningsFetcher()
        self._warnings_fetcher.finished.connect(self._on_warnings_fetched)
        self._warnings_fetcher.start()

    def _on_warnings_fetched(self, warnings):
        self.warnings_data = warnings

    def get_warning_for_version(self, version_name):
        if not version_name or not self.warnings_data:
            return None
        for entry in self.warnings_data:
            if entry.get("version") == version_name:
                return entry.get("reason")
        return None

    def closeEvent(self, event):
        if self._warnings_fetcher and self._warnings_fetcher.isRunning():
            self._warnings_fetcher.requestInterruption()
            self._warnings_fetcher.wait(3000)
        if hasattr(self, 'google_tab') and self.google_tab.fetcher and self.google_tab.fetcher.isRunning():
            self.google_tab.fetcher.requestInterruption()
            self.google_tab.fetcher.wait(3000)
        super().closeEvent(event)

    def get_target_root(self):
        """Resolve the installation root path based on the selected mode."""
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
