from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QScrollArea, QFrame, QLineEdit, QPushButton, QCheckBox, QSlider, QGridLayout, QTextEdit)
from PySide6.QtCore import Qt
import os
from src import constants as c
from src.core import language_manager
from src.utils.dialogs import ask_open_filename_native
from src.utils.resource_path import resource_path

class SettingsTab(QWidget):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("border: none;")

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

        # --- Perfiles ---
        self.setup_profiles_section()

        # --- Binarios ---
        self.setup_binaries_section()

        # --- Botones Acción ---
        self.setup_actions_section()

        # --- Compatibilidad ---
        self.setup_compatibility_section()

        # --- Apariencia ---
        self.setup_appearance_section()

        # --- Opacidad Secciones ---
        self.setup_section_opacity_section()

        # --- Fondo Personalizado ---
        self.setup_background_section()

        # --- Sticker ---
        self.setup_sticker_section()

        # Init visual state
        self.on_settings_mode_change(self.combo_settings_mode.currentText())
        self.toggle_custom_env()

    def setup_profiles_section(self):
        frame = QFrame()
        frame.setObjectName("GroupFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = QLabel(c.UI_PROFILES_MANAGER_TITLE)
        title.setObjectName("HeaderLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        selector_layout = QHBoxLayout()
        selector_layout.setContentsMargins(15, 0, 15, 0)
        selector_layout.setSpacing(10)
        layout.addLayout(selector_layout)

        selector_layout.addWidget(QLabel(c.UI_LABEL_PROFILE))

        self.combo_profile = QComboBox()
        self.combo_profile.addItems(self.app.logic.get_profiles(self.app))
        self.combo_profile.setCurrentText(self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.UI_PROFILE_DEFAULT))
        self.combo_profile.currentTextChanged.connect(self.on_profile_change)
        self.combo_profile.setMinimumWidth(200)
        selector_layout.addWidget(self.combo_profile, 1)

        self.btn_manage_prof = QPushButton("⚙️")
        self.btn_manage_prof.setObjectName("ToolButton")
        self.btn_manage_prof.setFixedSize(35, 35)
        self.btn_manage_prof.clicked.connect(self.open_profile_manager)
        selector_layout.addWidget(self.btn_manage_prof)

        # Disable if not supported
        if not getattr(self.app, "profiles_supported", True):
            self.combo_profile.setEnabled(False)
            self.btn_manage_prof.setEnabled(False)
            self.combo_profile.setToolTip(c.UI_SYMLINK_NOT_SUPPORTED_MSG)
            lbl_warn = QLabel(c.UI_SYMLINK_NOT_SUPPORTED_TITLE)
            lbl_warn.setStyleSheet("color: #ff9800; font-size: 10px; font-weight: bold;")
            lbl_warn.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl_warn)

        self.scroll_layout.addWidget(frame)

    def setup_binaries_section(self):
        frame = QFrame()
        frame.setObjectName("GroupFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = QLabel(c.UI_SECTION_BINARIES)
        title.setObjectName("HeaderLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        if not self.app.running_in_flatpak:
            mode_keys = [c.MODE_BIN_SYSTEM, c.MODE_BIN_LOCAL, c.MODE_BIN_CUSTOM, c.MODE_BIN_FLATPAK]
        else:
            mode_keys = [c.MODE_BIN_SYSTEM, c.MODE_BIN_CUSTOM, c.MODE_BIN_FLATPAK]

        modes_display = [c.UI_BIN_MODES[k] for k in mode_keys]

        self.combo_settings_mode = QComboBox()
        self.combo_settings_mode.addItems(modes_display)
        current_mode = self.app.config.get(c.CONFIG_KEY_MODE, c.UI_DEFAULT_MODE)
        self.combo_settings_mode.setCurrentText(c.UI_BIN_MODES.get(current_mode, c.UI_BIN_MODES[c.MODE_BIN_SYSTEM]))
        self.combo_settings_mode.currentTextChanged.connect(self.on_settings_mode_change)
        self.combo_settings_mode.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        layout.addWidget(self.combo_settings_mode)

        # Flatpak ID
        self.frame_flatpak_id = QFrame()
        fid_layout = QHBoxLayout(self.frame_flatpak_id)
        fid_layout.addWidget(QLabel(c.UI_LABEL_FLATPAK_ID))
        self.entry_flatpak_id = QLineEdit()
        self.entry_flatpak_id.setText(self.app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.MCPELAUNCHER_FLATPAK_ID))
        fid_layout.addWidget(self.entry_flatpak_id)
        layout.addWidget(self.frame_flatpak_id)

        # Binary Version Label
        self.lbl_binary_version = QLabel("")
        self.lbl_binary_version.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.lbl_binary_version)
        self.update_binary_version_info()

        # Paths
        self.inputs = {}
        for label, key in [
            (c.UI_LABEL_CLIENT_GAME, c.CONFIG_KEY_CLIENT),
            (c.UI_LABEL_EXTRACTOR_APK, c.CONFIG_KEY_EXTRACT),
            (c.UI_LABEL_SIGNIN_UI, c.CONFIG_KEY_SIGNIN_UI),
            (c.UI_LABEL_GPLAYDL, c.CONFIG_KEY_GPLAYDL),
            (c.UI_LABEL_GPLAYVER, c.CONFIG_KEY_GPLAYVER),
            (c.UI_LABEL_WEBVIEW_OPTIONAL, c.CONFIG_KEY_WEBVIEW),
            (c.UI_LABEL_ERROR_HANDLER_OPTIONAL, c.CONFIG_KEY_ERROR)
        ]:
            f = QFrame()
            fl = QHBoxLayout(f)
            fl.addWidget(QLabel(label), 0)
            e = QLineEdit()
            e.setText(self.app.config[c.CONFIG_KEY_BINARY_PATHS].get(key, ""))
            fl.addWidget(e, 1)
            b = QPushButton("...")
            b.setObjectName("ToolButton")
            b.setFixedSize(35, 35)
            b.clicked.connect(lambda checked=False, k=key, ent=e: self.browse_path(k, ent))
            fl.addWidget(b, 0)
            layout.addWidget(f)
            self.inputs[key] = (e, b, f)

        self.scroll_layout.addWidget(frame)

    def setup_actions_section(self):
        f = QFrame()
        f.setObjectName("GroupFrame")
        l = QHBoxLayout(f)
        l.setContentsMargins(15, 15, 15, 15)
        l.setSpacing(10)

        btn_save = QPushButton(c.UI_BUTTON_SAVE_SETTINGS)
        btn_save.setObjectName("SaveButton")
        btn_save.setFixedHeight(c.BTN_HEIGHT)
        btn_save.clicked.connect(self.save_settings)
        l.addWidget(btn_save)

        btn_restore = QPushButton(c.UI_BUTTON_RESTORE_DEFAULTS)
        btn_restore.setFixedHeight(c.BTN_HEIGHT)
        btn_restore.clicked.connect(self.app.restore_default_settings)
        l.addWidget(btn_restore)

        self.scroll_layout.addWidget(f)

    def setup_compatibility_section(self):
        frame = QFrame()
        frame.setObjectName("GroupFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = QLabel(c.UI_SECTION_COMPATIBILITY)
        title.setObjectName("HeaderLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.checks = {}
        # Order: Gamemode, NVIDIA, Zink, Close on launch, Custom Args
        configs = [
            (c.UI_GAMEMODE_CHECKBOX, c.CONFIG_KEY_GAMEMODE_ENABLED, c.UI_GAMEMODE_TOOLTIP),
            (c.UI_NVIDIA_PRIME_CHECKBOX, c.CONFIG_KEY_NVIDIA_PRIME, c.UI_NVIDIA_PRIME_TOOLTIP),
            (c.UI_ZINK_CHECKBOX, c.CONFIG_KEY_ZINK_MODE, c.UI_ZINK_TOOLTIP)
        ]

        for label, key, tooltip in configs:
            f = QFrame()
            fl = QHBoxLayout(f)
            cb = QCheckBox(label)
            cb.setChecked(self.app.config.get(key, False))
            fl.addWidget(cb)
            btn_info = QPushButton("?")
            btn_info.setObjectName("ToolButton")
            btn_info.setFixedSize(25, 25)
            btn_info.clicked.connect(lambda checked=False, t=label, m=tooltip: self.app.show_info(t, m))
            fl.addWidget(btn_info)
            layout.addWidget(f)
            self.checks[key] = cb

        # Close on Launch
        f_close = QFrame()
        fl_close = QHBoxLayout(f_close)
        self.check_close_on_launch = QCheckBox(c.UI_CHECKBOX_CLOSE_ON_LAUNCH)
        self.check_close_on_launch.setChecked(self.app.config.get(c.CONFIG_KEY_CLOSE_ON_LAUNCH, False))
        self.check_close_on_launch.stateChanged.connect(lambda state: self.app.sync_close_on_launch_ui(state == Qt.Checked))
        fl_close.addWidget(self.check_close_on_launch)
        layout.addWidget(f_close)

        # Custom Args Checkbox directly above entry
        f_custom_env = QFrame()
        fl_custom_env = QHBoxLayout(f_custom_env)
        self.cb_custom_env = QCheckBox(c.UI_CUSTOM_ARGS_CHECKBOX)
        self.cb_custom_env.setChecked(self.app.config.get(c.CONFIG_KEY_CUSTOM_ENV_ENABLED, False))
        fl_custom_env.addWidget(self.cb_custom_env)
        btn_info_custom = QPushButton("?")
        btn_info_custom.setObjectName("ToolButton")
        btn_info_custom.setFixedSize(25, 25)
        btn_info_custom.clicked.connect(lambda checked=False: self.app.show_info(c.UI_CUSTOM_ARGS_CHECKBOX, c.UI_CUSTOM_ARGS_TOOLTIP))
        fl_custom_env.addWidget(btn_info_custom)
        layout.addWidget(f_custom_env)
        self.checks[c.CONFIG_KEY_CUSTOM_ENV_ENABLED] = self.cb_custom_env

        # Custom Env Entry
        self.f_custom_vars = QFrame()
        cv_layout = QHBoxLayout(self.f_custom_vars)
        cv_layout.setContentsMargins(0, 5, 0, 5)
        cv_layout.addWidget(QLabel(c.UI_CUSTOM_ARGS_LABEL))
        self.entry_custom_vars = QLineEdit()
        self.entry_custom_vars.setText(self.app.config.get(c.CONFIG_KEY_CUSTOM_ENV_VARS, ""))
        cv_layout.addWidget(self.entry_custom_vars, 1)
        layout.addWidget(self.f_custom_vars)

        self.checks[c.CONFIG_KEY_CUSTOM_ENV_ENABLED].stateChanged.connect(self.toggle_custom_env)
        self.checks[c.CONFIG_KEY_GAMEMODE_ENABLED].stateChanged.connect(lambda state: self.app.sync_gamemode_ui(state == Qt.Checked))

        # Discord Rich Presence
        f_discord = QFrame()
        fl_discord = QHBoxLayout(f_discord)
        self.check_discord_rpc = QCheckBox(c.UI_DISCORD_RPC_CHECKBOX)
        self.check_discord_rpc.setChecked(self.app.config.get(c.CONFIG_KEY_DISCORD_RPC_ENABLED, False))
        fl_discord.addWidget(self.check_discord_rpc)
        btn_info_discord = QPushButton("?")
        btn_info_discord.setObjectName("ToolButton")
        btn_info_discord.setFixedSize(25, 25)
        btn_info_discord.clicked.connect(lambda checked=False: self.app.show_info(c.UI_DISCORD_RPC_CHECKBOX, c.UI_DISCORD_RPC_TOOLTIP))
        fl_discord.addWidget(btn_info_discord)
        layout.addWidget(f_discord)
        self.checks[c.CONFIG_KEY_DISCORD_RPC_ENABLED] = self.check_discord_rpc
        self.check_discord_rpc.stateChanged.connect(lambda state: self.app.sync_discord_rpc_ui(state == Qt.Checked))

        self.scroll_layout.addWidget(frame)

    def update_binary_version_info(self):
        mode = self.app.config.get(c.CONFIG_KEY_MODE, c.UI_DEFAULT_MODE)
        if mode == c.MODE_BIN_FLATPAK or self.app.running_in_flatpak:
            self.lbl_binary_version.setText(c.BINARY_VERSION_INFO)
        else:
            # Check for info.txt in the same directory as the launcher (compiled_path)
            info_path = os.path.join(self.app.compiled_path, "info.txt")
            if os.path.exists(info_path):
                try:
                    with open(info_path, "r") as f:
                        lines = f.readlines()
                        if len(lines) >= 2:
                            self.lbl_binary_version.setText(lines[1].strip())
                        else:
                            self.lbl_binary_version.setText(c.BINARY_VERSION_FALLBACK)
                except:
                    self.lbl_binary_version.setText(c.BINARY_VERSION_FALLBACK)
            else:
                self.lbl_binary_version.setText(c.BINARY_VERSION_FALLBACK)

    def setup_section_opacity_section(self):
        frame = QFrame()
        frame.setObjectName("GroupFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = QLabel(c.UI_LABEL_SECTION_OPACITY.rstrip(':'))
        title.setObjectName("HeaderLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setContentsMargins(10, 5, 10, 5)
        layout.addLayout(grid)

        lbl_slider = QLabel(c.UI_LABEL_SECTION_OPACITY)
        lbl_slider.setStyleSheet("font-size: 13px;")
        grid.addWidget(lbl_slider, 0, 0)
        self.slider_section_opacity = QSlider(Qt.Horizontal)
        self.slider_section_opacity.setRange(0, 100)
        self.slider_section_opacity.setValue(self.app.config.get(c.CONFIG_KEY_SECTION_OPACITY, 100))
        self.slider_section_opacity.valueChanged.connect(self.on_section_opacity_change)
        grid.addWidget(self.slider_section_opacity, 0, 1)
        self.lbl_section_opacity = QLabel(str(self.slider_section_opacity.value()))
        self.lbl_section_opacity.setStyleSheet("font-weight: bold; min-width: 35px;")
        grid.addWidget(self.lbl_section_opacity, 0, 2)

        self.scroll_layout.addWidget(frame)

    def setup_appearance_section(self):
        frame = QFrame()
        frame.setObjectName("GroupFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = QLabel(c.UI_SECTION_APPEARANCE)
        title.setObjectName("HeaderLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        grid = QGridLayout()
        layout.addLayout(grid)

        # Theme
        grid.addWidget(QLabel(c.UI_LABEL_COLOR_THEME), 0, 0)
        self.combo_theme = QComboBox()
        theme_keys = list(c.UI_THEME_NAMES.keys())
        self.theme_map = {c.UI_THEME_NAMES.get(k, k.capitalize()): k for k in theme_keys}
        self.combo_theme.addItems(list(self.theme_map.keys()))
        current_theme = self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
        current_display = next((display for display, key in self.theme_map.items() if key == current_theme), "Blue")
        self.combo_theme.setCurrentText(current_display)
        self.combo_theme.currentTextChanged.connect(self.on_theme_change)
        self.combo_theme.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        grid.addWidget(self.combo_theme, 0, 1)

        # App Mode
        grid.addWidget(QLabel(c.UI_LABEL_APPEARANCE_MODE), 1, 0)
        self.combo_app_mode = QComboBox()
        self.combo_app_mode.addItems(list(c.UI_APPEARANCE_MODES.values()))
        current_app_mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        self.combo_app_mode.setCurrentText(c.UI_APPEARANCE_MODES.get(current_app_mode, "Dark"))
        self.combo_app_mode.currentTextChanged.connect(self.on_appearance_mode_change)
        self.combo_app_mode.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        grid.addWidget(self.combo_app_mode, 1, 1)

        # Language
        grid.addWidget(QLabel(c.UI_LABEL_LANGUAGE), 3, 0)
        self.langs_dict = language_manager.get_available_languages()
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(list(self.langs_dict.values()))
        current_lang = self.app.config.get(c.CONFIG_KEY_LANGUAGE, "en")
        self.combo_lang.setCurrentText(self.langs_dict.get(current_lang, "English"))
        self.combo_lang.currentTextChanged.connect(self.on_language_change)
        self.combo_lang.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        grid.addWidget(self.combo_lang, 3, 1)

        # UI Scale
        grid.addWidget(QLabel(c.UI_LABEL_UI_SCALE), 4, 0)
        self.combo_scale = QComboBox()
        self.combo_scale.addItems(["1.0", "1.25", "1.5", "1.75", "2.0"])
        curr_scale = str(self.app.config.get(c.CONFIG_KEY_UI_SCALE, "1.0"))
        self.combo_scale.setCurrentText(curr_scale)
        self.combo_scale.currentTextChanged.connect(self.on_scale_change)
        grid.addWidget(self.combo_scale, 4, 1)
        lbl_scale_note = QLabel(c.UI_RESTART_SCALE_MSG)
        lbl_scale_note.setStyleSheet("color: #ff9800; font-size: 10px;")
        grid.addWidget(lbl_scale_note, 4, 2)

        # List Style
        grid.addWidget(QLabel(c.UI_LABEL_VERSION_LIST_STYLE), 5, 0)
        self.combo_list_style = QComboBox()
        self.combo_list_style.addItems(list(c.UI_LIST_STYLES.values()))
        current_style = self.app.config.get(c.CONFIG_KEY_VERSION_LIST_STYLE, c.STYLE_LIST)
        self.combo_list_style.setCurrentText(c.UI_LIST_STYLES.get(current_style, c.STYLE_LIST))
        self.combo_list_style.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.combo_list_style.currentTextChanged.connect(self.on_appearance_setting_change)
        grid.addWidget(self.combo_list_style, 5, 1)

        # Sliders
        grid.addWidget(QLabel(c.UI_LABEL_ICON_SIZE), 6, 0)
        self.slider_icon = QSlider(Qt.Horizontal)
        self.slider_icon.setRange(16, 128)
        self.slider_icon.setValue(self.app.config.get(c.CONFIG_KEY_VERSION_ICON_SIZE, 32))
        self.slider_icon.valueChanged.connect(self.on_appearance_setting_change)
        grid.addWidget(self.slider_icon, 6, 1)
        self.lbl_icon_val = QLabel(str(self.slider_icon.value()))
        grid.addWidget(self.lbl_icon_val, 6, 2)

        grid.addWidget(QLabel(c.UI_LABEL_TITLE_SIZE), 7, 0)
        self.slider_title = QSlider(Qt.Horizontal)
        self.slider_title.setRange(8, 32)
        self.slider_title.setValue(self.app.config.get(c.CONFIG_KEY_VERSION_TITLE_SIZE, 13))
        self.slider_title.valueChanged.connect(self.on_appearance_setting_change)
        grid.addWidget(self.slider_title, 7, 1)
        self.lbl_title_val = QLabel(str(self.slider_title.value()))
        grid.addWidget(self.lbl_title_val, 7, 2)

        # Card Width
        grid.addWidget(QLabel(c.UI_LABEL_CARD_WIDTH), 8, 0)
        self.slider_card_width = QSlider(Qt.Horizontal)
        self.slider_card_width.setRange(80, 400)
        self.slider_card_width.setValue(self.app.config.get(c.CONFIG_KEY_VERSION_CARD_WIDTH, 180))
        self.slider_card_width.valueChanged.connect(self.on_appearance_setting_change)
        grid.addWidget(self.slider_card_width, 8, 1)
        self.lbl_card_width_val = QLabel(str(self.slider_card_width.value()))
        grid.addWidget(self.lbl_card_width_val, 8, 2)

        # Card Height
        grid.addWidget(QLabel(c.UI_LABEL_CARD_HEIGHT), 9, 0)
        self.slider_card_height = QSlider(Qt.Horizontal)
        self.slider_card_height.setRange(60, 300)
        self.slider_card_height.setValue(self.app.config.get(c.CONFIG_KEY_VERSION_CARD_HEIGHT, 145))
        self.slider_card_height.valueChanged.connect(self.on_appearance_setting_change)
        grid.addWidget(self.slider_card_height, 9, 1)
        self.lbl_card_height_val = QLabel(str(self.slider_card_height.value()))
        grid.addWidget(self.lbl_card_height_val, 9, 2)

        self.scroll_layout.addWidget(frame)

    def setup_background_section(self):
        frame = QFrame()
        frame.setObjectName("GroupFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = QLabel(c.UI_SECTION_BACKGROUND)
        title.setObjectName("HeaderLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        grid = QGridLayout()
        layout.addLayout(grid)

        # Path
        grid.addWidget(QLabel(c.UI_LABEL_BG_PATH), 0, 0)
        self.entry_bg_path = QLineEdit()
        self.entry_bg_path.setText(self.app.config.get(c.CONFIG_KEY_BG_PATH, ""))
        self.entry_bg_path.textChanged.connect(self.on_bg_change)
        grid.addWidget(self.entry_bg_path, 0, 1)
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(40)
        btn_browse.clicked.connect(self.browse_bg)
        grid.addWidget(btn_browse, 0, 2)

        # X Pos
        grid.addWidget(QLabel(c.UI_LABEL_BG_X), 1, 0)
        self.slider_bg_x = QSlider(Qt.Horizontal)
        self.slider_bg_x.setRange(-1000, 1000)
        self.slider_bg_x.setValue(self.app.config.get(c.CONFIG_KEY_BG_X, 0))
        self.slider_bg_x.valueChanged.connect(self.on_bg_change)
        grid.addWidget(self.slider_bg_x, 1, 1)
        self.lbl_bg_x = QLabel(str(self.slider_bg_x.value()))
        grid.addWidget(self.lbl_bg_x, 1, 2)

        # Y Pos
        grid.addWidget(QLabel(c.UI_LABEL_BG_Y), 2, 0)
        self.slider_bg_y = QSlider(Qt.Horizontal)
        self.slider_bg_y.setRange(-1000, 1000)
        self.slider_bg_y.setValue(self.app.config.get(c.CONFIG_KEY_BG_Y, 0))
        self.slider_bg_y.valueChanged.connect(self.on_bg_change)
        grid.addWidget(self.slider_bg_y, 2, 1)
        self.lbl_bg_y = QLabel(str(self.slider_bg_y.value()))
        grid.addWidget(self.lbl_bg_y, 2, 2)

        # Opacity
        grid.addWidget(QLabel(c.UI_LABEL_BG_OPACITY), 3, 0)
        self.slider_bg_opacity = QSlider(Qt.Horizontal)
        self.slider_bg_opacity.setRange(0, 100)
        self.slider_bg_opacity.setValue(self.app.config.get(c.CONFIG_KEY_BG_OPACITY, 100))
        self.slider_bg_opacity.valueChanged.connect(self.on_bg_change)
        grid.addWidget(self.slider_bg_opacity, 3, 1)
        self.lbl_bg_opacity = QLabel(str(self.slider_bg_opacity.value()))
        grid.addWidget(self.lbl_bg_opacity, 3, 2)

        # Zoom
        grid.addWidget(QLabel(c.UI_LABEL_BG_ZOOM), 4, 0)
        self.slider_bg_zoom = QSlider(Qt.Horizontal)
        self.slider_bg_zoom.setRange(10, 500)
        self.slider_bg_zoom.setValue(self.app.config.get(c.CONFIG_KEY_BG_ZOOM, 100))
        self.slider_bg_zoom.valueChanged.connect(self.on_bg_change)
        grid.addWidget(self.slider_bg_zoom, 4, 1)
        self.lbl_bg_zoom = QLabel(str(self.slider_bg_zoom.value()))
        grid.addWidget(self.lbl_bg_zoom, 4, 2)

        self.scroll_layout.addWidget(frame)

    def setup_sticker_section(self):
        frame = QFrame()
        frame.setObjectName("GroupFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = QLabel(c.UI_SECTION_STICKER)
        title.setObjectName("HeaderLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        grid = QGridLayout()
        layout.addLayout(grid)

        # Mode
        grid.addWidget(QLabel(c.UI_LABEL_STICKER_MODE), 0, 0)
        self.combo_sticker_mode = QComboBox()
        self.sticker_mode_map = c.UI_STICKER_MODES
        self.combo_sticker_mode.addItems(list(self.sticker_mode_map.values()))
        curr_mode = self.app.config.get(c.CONFIG_KEY_STICKER_MODE, "none")
        self.combo_sticker_mode.setCurrentText(self.sticker_mode_map.get(curr_mode, "Desactivado"))
        self.combo_sticker_mode.currentTextChanged.connect(self.on_sticker_change)
        self.combo_sticker_mode.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        grid.addWidget(self.combo_sticker_mode, 0, 1)

        # Content
        grid.addWidget(QLabel(c.UI_LABEL_STICKER_CONTENT), 1, 0)
        self.entry_sticker_content = QLineEdit()
        self.entry_sticker_content.setText(self.app.config.get(c.CONFIG_KEY_STICKER_CONTENT, ""))
        self.entry_sticker_content.textChanged.connect(self.on_sticker_change)
        grid.addWidget(self.entry_sticker_content, 1, 1)
        btn_browse_s = QPushButton("...")
        btn_browse_s.setFixedWidth(40)
        btn_browse_s.clicked.connect(self.browse_sticker)
        grid.addWidget(btn_browse_s, 1, 2)

        # Corner
        grid.addWidget(QLabel(c.UI_LABEL_STICKER_CORNER), 2, 0)
        self.combo_sticker_corner = QComboBox()
        self.sticker_corner_map = c.UI_STICKER_CORNERS
        self.combo_sticker_corner.addItems(list(self.sticker_corner_map.values()))
        curr_corner = self.app.config.get(c.CONFIG_KEY_STICKER_CORNER, "bottom-right")
        self.combo_sticker_corner.setCurrentText(self.sticker_corner_map.get(curr_corner, "Inferior Derecha"))
        self.combo_sticker_corner.currentTextChanged.connect(self.on_sticker_change)
        self.combo_sticker_corner.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        grid.addWidget(self.combo_sticker_corner, 2, 1)

        # X Dist
        grid.addWidget(QLabel(c.UI_LABEL_STICKER_X), 3, 0)
        self.slider_sticker_x = QSlider(Qt.Horizontal)
        self.slider_sticker_x.setRange(0, 500)
        self.slider_sticker_x.setValue(self.app.config.get(c.CONFIG_KEY_STICKER_X, 10))
        self.slider_sticker_x.valueChanged.connect(self.on_sticker_change)
        grid.addWidget(self.slider_sticker_x, 3, 1)
        self.lbl_sticker_x = QLabel(str(self.slider_sticker_x.value()))
        grid.addWidget(self.lbl_sticker_x, 3, 2)

        # Y Dist
        grid.addWidget(QLabel(c.UI_LABEL_STICKER_Y), 4, 0)
        self.slider_sticker_y = QSlider(Qt.Horizontal)
        self.slider_sticker_y.setRange(0, 500)
        self.slider_sticker_y.setValue(self.app.config.get(c.CONFIG_KEY_STICKER_Y, 10))
        self.slider_sticker_y.valueChanged.connect(self.on_sticker_change)
        grid.addWidget(self.slider_sticker_y, 4, 1)
        self.lbl_sticker_y = QLabel(str(self.slider_sticker_y.value()))
        grid.addWidget(self.lbl_sticker_y, 4, 2)

        # Zoom
        grid.addWidget(QLabel(c.UI_LABEL_STICKER_ZOOM), 5, 0)
        self.slider_sticker_zoom = QSlider(Qt.Horizontal)
        self.slider_sticker_zoom.setRange(10, 500)
        self.slider_sticker_zoom.setValue(self.app.config.get(c.CONFIG_KEY_STICKER_ZOOM, 100))
        self.slider_sticker_zoom.valueChanged.connect(self.on_sticker_change)
        grid.addWidget(self.slider_sticker_zoom, 5, 1)
        self.lbl_sticker_zoom = QLabel(str(self.slider_sticker_zoom.value()))
        grid.addWidget(self.lbl_sticker_zoom, 5, 2)

        # Opacity
        grid.addWidget(QLabel(c.UI_LABEL_STICKER_OPACITY), 6, 0)
        self.slider_sticker_opacity = QSlider(Qt.Horizontal)
        self.slider_sticker_opacity.setRange(0, 100)
        self.slider_sticker_opacity.setValue(self.app.config.get(c.CONFIG_KEY_STICKER_OPACITY, 100))
        self.slider_sticker_opacity.valueChanged.connect(self.on_sticker_change)
        grid.addWidget(self.slider_sticker_opacity, 6, 1)
        self.lbl_sticker_opacity = QLabel(str(self.slider_sticker_opacity.value()))
        grid.addWidget(self.lbl_sticker_opacity, 6, 2)

        self.scroll_layout.addWidget(frame)

    def browse_path(self, key, entry):
        path = ask_open_filename_native(self.app, title=f"{c.UI_OPEN_FILE_TITLE}")
        if path:
            entry.setText(path)

    def on_settings_mode_change(self, display_name):
        mode_key = next((k for k, v in c.UI_BIN_MODES.items() if v == display_name), c.MODE_BIN_SYSTEM)
        is_flatpak = mode_key == c.MODE_BIN_FLATPAK
        is_custom = mode_key == c.MODE_BIN_CUSTOM

        self.frame_flatpak_id.setVisible(is_flatpak)
        for key, (e, b, f) in self.inputs.items():
            e.setEnabled(is_custom)
            b.setEnabled(is_custom)

        self.update_binary_version_info()

    def toggle_custom_env(self):
        enabled = self.checks[c.CONFIG_KEY_CUSTOM_ENV_ENABLED].isChecked()
        self.checks[c.CONFIG_KEY_NVIDIA_PRIME].setEnabled(not enabled)
        self.checks[c.CONFIG_KEY_ZINK_MODE].setEnabled(not enabled)
        self.entry_custom_vars.setEnabled(enabled)
        # Visual feedback for disabled state
        mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        if enabled:
            text_color = "white" if mode == "Dark" else "#242424"
            self.f_custom_vars.setStyleSheet("")
            self.entry_custom_vars.setStyleSheet(f"color: {text_color}; padding: 4px; border: 1px solid {'#444444' if mode == 'Dark' else '#cccccc'}; border-radius: 6px; background-color: {'#333333' if mode == 'Dark' else '#ffffff'};")
        else:
            # Grayed out appearance when disabled - subtle background to indicate inactive state
            disabled_text = "#666666" if mode == "Dark" else "#999999"
            disabled_bg = "#2a2a2a" if mode == "Dark" else "#f0f0f0"
            self.f_custom_vars.setStyleSheet("")
            self.entry_custom_vars.setStyleSheet(f"color: {disabled_text}; background-color: {disabled_bg}; border: 1px dashed {'#555555' if mode == 'Dark' else '#bbbbbb'}; border-radius: 6px;")

    def on_theme_change(self, display_name):
        theme_key = self.theme_map.get(display_name, "blue")
        self.app.change_appearance("color", theme_key)

    def on_appearance_mode_change(self, display_name):
        mode_key = next((k for k, v in c.UI_APPEARANCE_MODES.items() if v == display_name), "Dark")
        self.app.config[c.CONFIG_KEY_APPEARANCE] = mode_key
        self.app.config_manager.save_config()
        self.app.apply_theme_settings()

    def on_language_change(self, display_name):
        lang_code = next((k for k, v in self.langs_dict.items() if v == display_name), "en")
        self.app.config[c.CONFIG_KEY_LANGUAGE] = lang_code
        self.app.config_manager.save_config()

    def on_scale_change(self, value):
        self.app.config[c.CONFIG_KEY_UI_SCALE] = value
        self.app.config_manager.save_config()

    def on_section_opacity_change(self):
        val = self.slider_section_opacity.value()
        self.lbl_section_opacity.setText(str(val))
        self.app.config[c.CONFIG_KEY_SECTION_OPACITY] = val
        self.app.config_manager.save_config()
        # Apply theme globally - no need to refresh tools UI as QSS handles it
        self.app.apply_theme_settings()

    def on_bg_change(self):
        self.lbl_bg_x.setText(str(self.slider_bg_x.value()))
        self.lbl_bg_y.setText(str(self.slider_bg_y.value()))
        self.lbl_bg_opacity.setText(str(self.slider_bg_opacity.value()))
        self.lbl_bg_zoom.setText(str(self.slider_bg_zoom.value()))

        self.app.config[c.CONFIG_KEY_BG_PATH] = self.entry_bg_path.text()
        self.app.config[c.CONFIG_KEY_BG_X] = self.slider_bg_x.value()
        self.app.config[c.CONFIG_KEY_BG_Y] = self.slider_bg_y.value()
        self.app.config[c.CONFIG_KEY_BG_OPACITY] = self.slider_bg_opacity.value()
        self.app.config[c.CONFIG_KEY_BG_ZOOM] = self.slider_bg_zoom.value()

        self.app.config_manager.save_config()
        self.app.personalization_timer.start()

    def browse_bg(self):
        p = ask_open_filename_native(self.app, title=c.UI_LABEL_BG_PATH)
        if p: self.entry_bg_path.setText(p)

    def on_sticker_change(self):
        self.lbl_sticker_x.setText(str(self.slider_sticker_x.value()))
        self.lbl_sticker_y.setText(str(self.slider_sticker_y.value()))
        self.lbl_sticker_zoom.setText(str(self.slider_sticker_zoom.value()))
        self.lbl_sticker_opacity.setText(str(self.slider_sticker_opacity.value()))

        mode_disp = self.combo_sticker_mode.currentText()
        mode_key = next((k for k, v in self.sticker_mode_map.items() if v == mode_disp), "none")
        corner_disp = self.combo_sticker_corner.currentText()
        corner_key = next((k for k, v in self.sticker_corner_map.items() if v == corner_disp), "bottom-right")

        self.app.config[c.CONFIG_KEY_STICKER_MODE] = mode_key
        self.app.config[c.CONFIG_KEY_STICKER_CONTENT] = self.entry_sticker_content.text()
        self.app.config[c.CONFIG_KEY_STICKER_CORNER] = corner_key
        self.app.config[c.CONFIG_KEY_STICKER_X] = self.slider_sticker_x.value()
        self.app.config[c.CONFIG_KEY_STICKER_Y] = self.slider_sticker_y.value()
        self.app.config[c.CONFIG_KEY_STICKER_ZOOM] = self.slider_sticker_zoom.value()
        self.app.config[c.CONFIG_KEY_STICKER_OPACITY] = self.slider_sticker_opacity.value()

        self.app.config_manager.save_config()
        self.app.personalization_timer.start()

    def browse_sticker(self):
        p = ask_open_filename_native(self.app, title=c.UI_LABEL_STICKER_CONTENT)
        if p: self.entry_sticker_content.setText(p)

    def on_appearance_setting_change(self):
        self.lbl_icon_val.setText(str(self.slider_icon.value()))
        self.lbl_title_val.setText(str(self.slider_title.value()))
        if hasattr(self, 'lbl_card_width_val'):
            self.lbl_card_width_val.setText(str(self.slider_card_width.value()))
        if hasattr(self, 'lbl_card_height_val'):
            self.lbl_card_height_val.setText(str(self.slider_card_height.value()))

        # Save values
        style_disp = self.combo_list_style.currentText()
        style_key = next((k for k, v in c.UI_LIST_STYLES.items() if v == style_disp), c.STYLE_LIST)

        self.app.config[c.CONFIG_KEY_VERSION_LIST_STYLE] = style_key
        self.app.config[c.CONFIG_KEY_VERSION_ICON_SIZE] = self.slider_icon.value()
        self.app.config[c.CONFIG_KEY_VERSION_TITLE_SIZE] = self.slider_title.value()
        self.app.config[c.CONFIG_KEY_VERSION_CARD_WIDTH] = self.slider_card_width.value()
        self.app.config[c.CONFIG_KEY_VERSION_CARD_HEIGHT] = self.slider_card_height.value()

        self.app.config_manager.save_config()
        self.app.logic.refresh_version_list(self.app)
        if hasattr(self.app, "tools_tab"):
            self.app.tools_tab.refresh_tools_ui()

    def on_profile_change(self, profile_name):
        self.app.logic.switch_profile(self.app, profile_name)

    def open_profile_manager(self):
        from src.gui.profile_manager_dialog import ProfileManagerDialog
        dialog = ProfileManagerDialog(self.app, self.app)
        dialog.exec()
        self.refresh_profile_list()

    def refresh_profile_list(self):
        self.combo_profile.clear()
        self.combo_profile.addItems(self.app.logic.get_profiles(self.app))
        self.combo_profile.setCurrentText(self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE))

    def save_settings(self):
        disp = self.combo_settings_mode.currentText()
        mode_key = next((k for k, v in c.UI_BIN_MODES.items() if v == disp), c.MODE_BIN_SYSTEM)

        self.app.config[c.CONFIG_KEY_MODE] = mode_key
        self.app.config[c.CONFIG_KEY_FLATPAK_ID] = self.entry_flatpak_id.text()

        for key, cb in self.checks.items():
            self.app.config[key] = cb.isChecked()

        self.app.config[c.CONFIG_KEY_CUSTOM_ENV_VARS] = self.entry_custom_vars.text()

        if mode_key == c.MODE_BIN_CUSTOM:
            for key, (e, b, f) in self.inputs.items():
                self.app.config[c.CONFIG_KEY_BINARY_PATHS][key] = e.text()

        self.app.config_manager.save_config()
        from src.gui import custom_dialogs as messagebox
        messagebox.showinfo(self, c.UI_SUCCESS_TITLE, c.UI_SAVE_SUCCESS_MSG)
