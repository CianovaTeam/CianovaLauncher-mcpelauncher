from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QScrollArea, QCheckBox, QPushButton, QFrame)
from PySide6.QtCore import Qt
from src import constants as c
from src.core.ui_utils import FlowLayout

class PlayTab(QWidget):
    """Main play tab with version list, launch options, and the play button."""
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # Layout principal
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(c.SECTION_PADDING, 5, c.SECTION_PADDING, c.SECTION_PADDING)
        self.main_layout.setSpacing(5)

        # 1. Cabecera (Status y Selectores) — FlowLayout wraps on narrow windows
        self.header_layout = FlowLayout()
        self.main_layout.addLayout(self.header_layout)

        self.lbl_status = QLabel(c.t("UI_LABEL_SEARCHING"))
        self.lbl_status.setObjectName("IndicatorPill")
        self.lbl_status.setStyleSheet("font-size: 12px;")
        self.header_layout.addWidget(self.lbl_status)

        self.lbl_game_status = QLabel(c.t("UI_GAME_STATUS_IDLE"))
        self.lbl_game_status.setObjectName("IndicatorPill")
        self.lbl_game_status.setStyleSheet("font-size: 11px;")
        self.header_layout.addWidget(self.lbl_game_status)

        # Push profile/install/mode selectors to the right side of the header
        self.header_layout.addSpacing(0)

        self.lbl_profile_indicator = QLabel("")
        self.lbl_profile_indicator.setObjectName("IndicatorPill")
        self.lbl_profile_indicator.setStyleSheet(f"color: {c.COLOR_PRIMARY_GREEN}; font-size: 11px;")
        self.header_layout.addWidget(self.lbl_profile_indicator)

        self.update_profile_indicator()

        # Disable profiles if not supported
        if not getattr(self.app, "profiles_supported", True):
            self.lbl_profile_indicator.setStyleSheet("color: #ff9800; font-size: 11px;")
            self.lbl_profile_indicator.setToolTip(c.t("UI_SYMLINK_NOT_SUPPORTED_MSG"))

        self.lbl_install = QLabel(c.t("UI_LABEL_INSTALLATION"))
        self.lbl_install.setObjectName("IndicatorPill")
        self.lbl_install.setStyleSheet("color: gray; font-size: 11px;")
        self.header_layout.addWidget(self.lbl_install)

        # Selector de modo
        if self.app.running_in_flatpak:
            mode_keys = [c.MODE_INSTALL_OWN, c.MODE_INSTALL_SHARED, c.MODE_INSTALL_FLATPAK]
        else:
            mode_keys = [c.MODE_INSTALL_LOCAL, c.MODE_INSTALL_FLATPAK]

        mode_values = [c.t("UI_INSTALL_MODES")[k] for k in mode_keys]

        self.combo_mode = QComboBox()
        self.combo_mode.addItems(mode_values)
        self.combo_mode.setFixedHeight(28)
        self.combo_mode.currentTextChanged.connect(lambda mode: self.app.logic.change_mode_ui(self.app, mode))
        self.header_layout.addWidget(self.combo_mode)

        # 2. Lista de Versiones
        version_title_container = QHBoxLayout()
        version_title_container.addStretch()
        self.lbl_version_title = QLabel(c.t("UI_LABEL_INSTALLED_VERSIONS"))
        self.lbl_version_title.setObjectName("IndicatorPill")
        self.lbl_version_title.setStyleSheet("font-size: 13px;")
        version_title_container.addWidget(self.lbl_version_title)
        version_title_container.addStretch()
        self.main_layout.addLayout(version_title_container)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

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

        self.combo_launch_action = QComboBox()
        self.combo_launch_action.addItem(c.t("UI_LAUNCH_ACTION_CLOSE"), c.LAUNCH_ACTION_CLOSE)
        self.combo_launch_action.addItem(c.t("UI_LAUNCH_ACTION_HIDE"), c.LAUNCH_ACTION_HIDE)
        self.combo_launch_action.addItem(c.t("UI_LAUNCH_ACTION_NONE"), c.LAUNCH_ACTION_NONE)
        current_action = self.app.config.get(c.CONFIG_KEY_LAUNCH_ACTION, c.LAUNCH_ACTION_CLOSE)
        idx = self.combo_launch_action.findData(current_action)
        if idx >= 0:
            self.combo_launch_action.setCurrentIndex(idx)
        self.combo_launch_action.currentIndexChanged.connect(
            lambda: self.app.sync_launch_action_ui(self.combo_launch_action.currentData())
        )
        self.opts_layout.addWidget(self.combo_launch_action)

        self.check_gamemode = QCheckBox(c.t("UI_CHECKBOX_GAMEMODE"))
        self.check_gamemode.setChecked(self.app.config.get(c.CONFIG_KEY_GAMEMODE_ENABLED, False))
        self.check_gamemode.stateChanged.connect(lambda state: self.app.sync_gamemode_ui(state == Qt.Checked.value))
        self.opts_layout.addWidget(self.check_gamemode)

        self.check_discord = QCheckBox(c.t("UI_CHECKBOX_DISCORD_RPC"))
        self.check_discord.setChecked(self.app.config.get(c.CONFIG_KEY_DISCORD_RPC_ENABLED, False))
        self.check_discord.stateChanged.connect(lambda state: (self.app.sync_discord_rpc_ui(state == Qt.Checked.value), self.save_quick_opts()))
        self.opts_layout.addWidget(self.check_discord)

        # 4. Botón Jugar (full-width)
        self.btn_launch = QPushButton(c.t("UI_BUTTON_PLAY_NOW"))
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
        """Return the currently selected version string."""
        return self._selected_version

    def set(self, value):
        """Set the currently selected version string."""
        self._selected_version = value

    def update_profile_indicator(self):
        """Refresh the profile name shown in the floating label."""
        current = self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.t("UI_PROFILE_DEFAULT"))
        self.lbl_profile_indicator.setText(f"👤 {c.t('UI_LABEL_PROFILE')} {current}")

    def set_game_status(self, running):
        if running:
            color = "#4CAF50"
            dot = "●"
            self.lbl_game_status.setText(f"<span style='color:white;'>{dot}</span> {c.t('UI_GAME_STATUS_RUNNING')}")
            self.lbl_game_status.setStyleSheet(
                f"font-size: 11px; font-weight: bold; color: white; "
                f"background-color: {color}; border-radius: 13px; padding: 4px 13px;"
            )
            self.lbl_game_status.setToolTip(c.t("UI_GAME_STATUS_RUNNING"))
        else:
            muted = "#aaaaaa" if self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark") == "Dark" else "#555555"
            dot = "●"
            self.lbl_game_status.setText(f"<span style='color:{muted};'>{dot}</span> {c.t('UI_GAME_STATUS_IDLE')}")
            self.lbl_game_status.setStyleSheet(f"font-size: 11px; color: {muted};")
            self.lbl_game_status.setToolTip(c.t("UI_GAME_STATUS_IDLE"))

    def retranslate_ui(self):
        self.lbl_status.setText(c.t("UI_LABEL_SEARCHING"))
        running = self.app._game_process is not None
        self.set_game_status(running)
        self.lbl_install.setText(c.t("UI_LABEL_INSTALLATION"))
        self.lbl_version_title.setText(c.t("UI_LABEL_INSTALLED_VERSIONS"))
        self.update_profile_indicator()
        self.combo_launch_action.clear()
        self.combo_launch_action.addItem(c.t("UI_LAUNCH_ACTION_CLOSE"), c.LAUNCH_ACTION_CLOSE)
        self.combo_launch_action.addItem(c.t("UI_LAUNCH_ACTION_HIDE"), c.LAUNCH_ACTION_HIDE)
        self.combo_launch_action.addItem(c.t("UI_LAUNCH_ACTION_NONE"), c.LAUNCH_ACTION_NONE)
        current_action = self.app.config.get(c.CONFIG_KEY_LAUNCH_ACTION, c.LAUNCH_ACTION_CLOSE)
        idx = self.combo_launch_action.findData(current_action)
        if idx >= 0:
            self.combo_launch_action.setCurrentIndex(idx)
        self.check_gamemode.setText(c.t("UI_CHECKBOX_GAMEMODE"))
        self.check_discord.setText(c.t("UI_CHECKBOX_DISCORD_RPC"))
        self.btn_launch.setText(c.t("UI_BUTTON_PLAY_NOW"))

    def save_quick_opts(self):
        """Persist the launch option checkboxes to config."""
        self.app.config_manager.set(c.CONFIG_KEY_DISCORD_RPC_ENABLED, self.check_discord.isChecked())

    # Helpers to clean children (replacement for winfo_children)
    @property
    def version_listbox(self):
        return self.version_list_widget
