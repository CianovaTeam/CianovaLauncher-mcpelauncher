from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QScrollArea, QCheckBox, QPushButton, QFrame)
from PySide6.QtCore import Qt, Signal
from src import constants as c

class PlayTab(QWidget):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # Layout principal
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(c.SECTION_PADDING, 5, c.SECTION_PADDING, c.SECTION_PADDING)
        self.main_layout.setSpacing(5)

        # 1. Cabecera (Status y Selectores)
        self.header_layout = QHBoxLayout()
        self.main_layout.addLayout(self.header_layout)

        self.lbl_status = QLabel(c.UI_LABEL_SEARCHING)
        self.lbl_status.setObjectName("FloatingLabel")
        self.lbl_status.setStyleSheet(f"font-size: 12px; font-weight: bold;")
        self.header_layout.addWidget(self.lbl_status)

        self.header_layout.addStretch()

        # Frame para selectores
        self.selectors_layout = QHBoxLayout()
        self.header_layout.addLayout(self.selectors_layout)

        self.lbl_profile_indicator = QLabel("")
        self.lbl_profile_indicator.setObjectName("FloatingLabel")
        self.lbl_profile_indicator.setStyleSheet(f"color: {c.COLOR_PRIMARY_GREEN}; font-size: 11px;")
        self.selectors_layout.addWidget(self.lbl_profile_indicator)

        self.update_profile_indicator()

        # Disable profiles if not supported
        if not getattr(self.app, "profiles_supported", True):
            self.lbl_profile_indicator.setStyleSheet("color: #ff9800; font-size: 11px;")
            self.lbl_profile_indicator.setToolTip(c.UI_SYMLINK_NOT_SUPPORTED_MSG)

        self.lbl_install = QLabel(c.UI_LABEL_INSTALLATION)
        self.lbl_install.setObjectName("FloatingLabel")
        self.lbl_install.setStyleSheet("color: gray; font-size: 11px;")
        self.selectors_layout.addWidget(self.lbl_install)

        # Selector de modo
        if self.app.running_in_flatpak:
            mode_keys = [c.MODE_INSTALL_OWN, c.MODE_INSTALL_SHARED, c.MODE_INSTALL_FLATPAK]
        else:
            mode_keys = [c.MODE_INSTALL_LOCAL, c.MODE_INSTALL_FLATPAK]

        mode_values = [c.UI_INSTALL_MODES[k] for k in mode_keys]

        self.combo_mode = QComboBox()
        self.combo_mode.addItems(mode_values)
        self.combo_mode.setFixedWidth(170)
        self.combo_mode.setFixedHeight(28)
        self.combo_mode.currentTextChanged.connect(lambda mode: self.app.logic.change_mode_ui(self.app, mode))
        self.selectors_layout.addWidget(self.combo_mode)

        # 2. Lista de Versiones
        version_title_container = QHBoxLayout()
        version_title_container.addStretch()
        self.lbl_version_title = QLabel(c.UI_LABEL_INSTALLED_VERSIONS)
        self.lbl_version_title.setObjectName("FloatingLabel")
        self.lbl_version_title.setStyleSheet("font-weight: bold; color: #DCE4EE;")
        version_title_container.addWidget(self.lbl_version_title)
        version_title_container.addStretch()
        self.main_layout.addLayout(version_title_container)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("border: none; background-color: transparent;")

        self.version_list_widget = QWidget()
        self.version_list_widget.setObjectName("VersionList")
        self.version_list_layout = QVBoxLayout(self.version_list_widget)
        self.version_list_layout.setContentsMargins(5, 5, 5, 5)
        self.version_list_layout.setSpacing(10)
        self.version_list_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.version_list_widget)
        self.main_layout.addWidget(self.scroll_area, 1) # Expandir

        # 3. Opciones de Lanzamiento
        self.opts_layout = QHBoxLayout()
        self.opts_layout.setAlignment(Qt.AlignCenter)
        self.main_layout.addLayout(self.opts_layout)

        self.check_close_on_launch = QCheckBox(c.UI_CHECKBOX_CLOSE_ON_LAUNCH)
        self.check_close_on_launch.setChecked(self.app.config.get(c.CONFIG_KEY_CLOSE_ON_LAUNCH, False))
        self.check_close_on_launch.stateChanged.connect(lambda: self.save_quick_opts())
        self.opts_layout.addWidget(self.check_close_on_launch)

        self.check_gamemode = QCheckBox(c.UI_CHECKBOX_GAMEMODE)
        self.check_gamemode.setChecked(self.app.config.get(c.CONFIG_KEY_GAMEMODE_ENABLED, False))
        self.check_gamemode.stateChanged.connect(lambda state: self.app.sync_gamemode_ui(state == Qt.Checked))
        self.opts_layout.addWidget(self.check_gamemode)

        if not self.app.running_in_flatpak:
            self.check_debug_log = QCheckBox(c.UI_CHECKBOX_DEBUG_LOG)
            self.check_debug_log.setChecked(self.app.config.get(c.CONFIG_KEY_DEBUG_LOG, False))
            self.check_debug_log.stateChanged.connect(lambda: self.save_quick_opts())
            self.opts_layout.addWidget(self.check_debug_log)
        else:
            self.check_debug_log = None

        self.check_discord = QCheckBox(c.UI_CHECKBOX_DISCORD_RPC)
        self.check_discord.setChecked(self.app.config.get(c.CONFIG_KEY_DISCORD_RPC_ENABLED, False))
        self.check_discord.stateChanged.connect(lambda state: (self.app.sync_discord_rpc_ui(state == Qt.Checked), self.save_quick_opts()))
        self.opts_layout.addWidget(self.check_discord)

        # 4. Botón Jugar
        self.btn_launch = QPushButton(c.UI_BUTTON_PLAY_NOW)
        self.btn_launch.setObjectName("PlayButton")
        self.btn_launch.setFixedHeight(50)
        self.btn_launch.clicked.connect(lambda: self.app.logic.launch_game(self.app))
        self.main_layout.addWidget(self.btn_launch)

        # Mock version_var for compatibility
        self._selected_version = ""

    @property
    def version_var(self):
        return self

    def get(self):
        return self._selected_version

    def set(self, value):
        self._selected_version = value

    def update_profile_indicator(self):
        current = self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.UI_PROFILE_DEFAULT)
        self.lbl_profile_indicator.setText(f"👤 {c.UI_LABEL_PROFILE} {current}")

    def save_quick_opts(self):
        # Sync values to app config
        self.app.config[c.CONFIG_KEY_CLOSE_ON_LAUNCH] = self.check_close_on_launch.isChecked()
        self.app.config[c.CONFIG_KEY_DISCORD_RPC_ENABLED] = self.check_discord.isChecked()
        if self.check_debug_log:
            self.app.config[c.CONFIG_KEY_DEBUG_LOG] = self.check_debug_log.isChecked()

        # Sync with main app logic for consistency across tabs
        self.app.sync_close_on_launch_ui(self.check_close_on_launch.isChecked())

        self.app.config_manager.save_config()

    # Helpers to clean children (replacement for winfo_children)
    @property
    def version_listbox(self):
        return self.version_list_widget
