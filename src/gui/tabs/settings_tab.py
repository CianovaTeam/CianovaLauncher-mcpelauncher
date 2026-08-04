from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QScrollArea, QFrame, QLineEdit, QPushButton,
                             QCheckBox, QSlider, QGridLayout, QFormLayout, QGroupBox,
                             QStackedWidget, QStyledItemDelegate, QButtonGroup)
from PySide6.QtCore import Qt, QSize
from src.utils.voxel_icons import category_icon, profile_icon, block_icon
from PySide6.QtGui import QDragEnterEvent, QDropEvent
import os
from src import constants as c
from src.core import language_manager
from src.utils.dialogs import ask_open_filename_native
from src.utils.resource_path import resource_path
from src.utils.logger import logger


class SettingsTab(QWidget):
    """Settings tab with categorized sections, stacked pages, and a sticky footer bar."""

    CATEGORIES = [
        ("general", "UI_CATEGORY_GENERAL"),
        ("launch", "UI_CATEGORY_LAUNCH"),
        ("compat", "UI_CATEGORY_PERFORMANCE"),
        ("appearance", "UI_CATEGORY_APPEARANCE"),
    ]

    CATEGORY_METHODS = {
        "general": ["setup_profiles_section", "setup_discord_section"],
        "launch": ["setup_binaries_section", "setup_launch_action_section"],
        "compat": ["setup_compatibility_section"],
        "appearance": [
            "setup_appearance_section", "setup_section_opacity_section",
            "setup_background_section", "setup_sticker_section",
        ],
    }

    _DROP_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")

    ICONS = {}
    SIDEBAR_EXPANDED = 180
    SIDEBAR_COLLAPSED = 50

    def __init__(self, parent, app):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.app = app
        self._pages = {}
        self._cat_buttons = {}
        self._active_cat = None
        self._groups = {}
        self.checks = {}
        self._retranslate_labels = []
        self._appearance_labels = []
        self.lbl_binary_version = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)

        self._body_layout = QHBoxLayout()
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(0)
        self.main_layout.addLayout(self._body_layout, 1)

        self.setup_sidebar()

        self.stack = QStackedWidget()
        self._body_layout.addWidget(self.stack, 1)

        for key, _ in self.CATEGORIES:
            self._init_page(key)

        for cat_key, methods in self.CATEGORY_METHODS.items():
            self._set_active_page(cat_key)
            for method_name in methods:
                getattr(self, method_name)()

        self._setup_footer_bar()

        self._set_active_page("launch")
        self.on_settings_mode_change(self.combo_settings_mode.currentText())
        self.toggle_custom_env()
        self._switch_category("general")

    # ── Drag & drop ──────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if any(url.toLocalFile().lower().endswith(e) for e in self._DROP_IMAGE_EXTS):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if any(path.lower().endswith(e) for e in self._DROP_IMAGE_EXTS):
                self.entry_bg_path.setText(path)
                return

    # ── Category infrastructure ──────────────────────────────────

    def _init_page(self, key):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName(f"SettingsCategoryPage_{key}")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content.setObjectName("SettingsPageContent")
        scroll_layout = QVBoxLayout(content)
        scroll_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.stack.addWidget(page)
        self._pages[key] = (page, scroll_layout)

    def _set_active_page(self, key):
        _, self.scroll_layout = self._pages[key]

    def _switch_category(self, key):
        page, _ = self._pages[key]
        self.stack.setCurrentWidget(page)
        self._active_cat = key
        for k, btn in self._cat_buttons.items():
            active = k == key
            btn.setProperty("active", active)
            btn.setChecked(active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def setup_sidebar(self):
        self._sidebar_expanded = True
        self._sidebar = QFrame()
        self._sidebar.setObjectName("SettingsSidebar")
        self._sidebar.setFixedWidth(self.SIDEBAR_EXPANDED)

        layout = QVBoxLayout(self._sidebar)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self._toggle_btn = QPushButton("☰")
        self._toggle_btn.setObjectName("SidebarToggle")
        self._toggle_btn.setFixedHeight(36)
        self._toggle_btn.clicked.connect(self._toggle_sidebar)
        layout.addWidget(self._toggle_btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,0.1);")
        layout.addWidget(sep)

        self._cat_buttons = {}
        for key, label_key in self.CATEGORIES:
            label = c.t(label_key)
            btn = QPushButton(label)
            btn.setObjectName("SidebarButton")
            btn.setIcon(category_icon(key))
            btn.setIconSize(QSize(20, 20))
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.clicked.connect(lambda checked=False, k=key: self._switch_category(k))
            layout.addWidget(btn)
            self._cat_buttons[key] = btn

        layout.addStretch()
        self._body_layout.insertWidget(0, self._sidebar)

    def _toggle_sidebar(self):
        self._sidebar_expanded = not self._sidebar_expanded
        if self._sidebar_expanded:
            self._sidebar.setFixedWidth(self.SIDEBAR_EXPANDED)
            for key, label_key in self.CATEGORIES:
                self._cat_buttons[key].setText(c.t(label_key))
                self._cat_buttons[key].setIcon(category_icon(key))
        else:
            self._sidebar.setFixedWidth(self.SIDEBAR_COLLAPSED)
            for key in self._cat_buttons:
                self._cat_buttons[key].setText("")

    def _add_tooltip_button(self, layout, title, tooltip):
        btn_info = QPushButton("?")
        btn_info.setObjectName("ToolButton")
        btn_info.setFixedSize(22, 22)
        btn_info.clicked.connect(lambda checked=False, t=title, m=tooltip: self.app.show_info(t, m))
        layout.addWidget(btn_info)

    def _setup_footer_bar(self):
        """Sticky bar at the bottom with Save and Restore Defaults buttons."""
        bar = QFrame()
        bar.setObjectName("SettingsFooterBar")
        bar.setFixedHeight(52)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(15, 5, 15, 5)

        self.btn_save = QPushButton(c.t("UI_BUTTON_SAVE_SETTINGS"))
        self.btn_save.setObjectName("SaveButton")
        self.btn_save.setFixedHeight(c.BTN_HEIGHT)
        self.btn_save.clicked.connect(self.save_settings)
        layout.addWidget(self.btn_save)

        self.btn_restore = QPushButton(c.t("UI_BUTTON_RESTORE_DEFAULTS"))
        self.btn_restore.setObjectName("SaveButton")
        self.btn_restore.setFixedHeight(c.BTN_HEIGHT)
        self.btn_restore.clicked.connect(self.app.restore_default_settings)
        layout.addWidget(self.btn_restore)

        layout.addStretch()

        self.lbl_binary_version = QLabel("")
        _mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        muted = "#aaaaaa" if _mode == "Dark" else "#555555"
        self.lbl_binary_version.setStyleSheet(f"color: {muted}; font-size: 11px;")
        layout.addWidget(self.lbl_binary_version)

        self.main_layout.addWidget(bar)

    # ── General ──────────────────────────────────────────────────

    def setup_profiles_section(self):
        group = QGroupBox(c.t("UI_PROFILES_MANAGER_TITLE"))
        self._groups["UI_PROFILES_MANAGER_TITLE"] = group
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        row = QHBoxLayout()
        row.addWidget(QLabel(c.t("UI_LABEL_PROFILE")))
        self.combo_profile = QComboBox()
        self.combo_profile.setMinimumWidth(200)
        self._populate_profile_combo()
        self.combo_profile.currentTextChanged.connect(self.on_profile_change)

        mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        accent = c.THEME_COLOR_MAP.get(self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue"), "#1f6aa5")
        input_bg = "#333333" if mode == "Dark" else "#ffffff"
        input_text = "white" if mode == "Dark" else "#242424"
        input_border = "#444444" if mode == "Dark" else "#cccccc"
        self.combo_profile.setStyleSheet(f"""
            QComboBox {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 4px;
                padding: 6px 10px;
                font-weight: bold;
                font-size: 13px;
            }}
            QComboBox:focus {{
                border: 1px solid {accent};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 28px;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                width: 10px;
                height: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {accent};
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 6px 10px;
                border-radius: 4px;
                min-height: 28px;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {accent};
                color: white;
            }}
        """)
        row.addWidget(self.combo_profile, 1)
        self.btn_manage_prof = QPushButton("⚙️")
        self.btn_manage_prof.setObjectName("ToolButton")
        self.btn_manage_prof.setFixedSize(28, 28)
        self.btn_manage_prof.clicked.connect(self.open_profile_manager)
        row.addWidget(self.btn_manage_prof)
        layout.addLayout(row)

        if not getattr(self.app, "profiles_supported", True):
            self.combo_profile.setEnabled(False)
            self.btn_manage_prof.setEnabled(False)
            self.combo_profile.setToolTip(c.t("UI_SYMLINK_NOT_SUPPORTED_MSG"))
            warn = QLabel(c.t("UI_SYMLINK_NOT_SUPPORTED_TITLE"))
            warn.setStyleSheet("color: #ff9800; font-size: 10px; font-weight: bold;")
            warn.setAlignment(Qt.AlignCenter)
            layout.addWidget(warn)

        self.scroll_layout.addWidget(group)

        self._add_spacer()

    # ── Launch ────────────────────────────────────────────────────

    def setup_binaries_section(self):
        group = QGroupBox(c.t("UI_SECTION_BINARIES"))
        self._groups["UI_SECTION_BINARIES"] = group
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        if not self.app.running_in_flatpak:
            mode_keys = [c.MODE_BIN_SYSTEM, c.MODE_BIN_LOCAL, c.MODE_BIN_CUSTOM, c.MODE_BIN_FLATPAK]
        else:
            mode_keys = [c.MODE_BIN_SYSTEM, c.MODE_BIN_CUSTOM, c.MODE_BIN_FLATPAK]

        form = QFormLayout()
        self.combo_settings_mode = QComboBox()
        for k in mode_keys:
            self.combo_settings_mode.addItem(c.t("UI_BIN_MODES")[k], k)
        current_mode = self.app.config.get(c.CONFIG_KEY_MODE, c.MODE_BIN_SYSTEM)
        idx = self.combo_settings_mode.findData(current_mode)
        if idx >= 0:
            self.combo_settings_mode.setCurrentIndex(idx)
        self.combo_settings_mode.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        form.addRow(c.t("UI_LABEL_BIN_MODE"), self.combo_settings_mode)

        self.frame_flatpak_id = QFrame()
        fid_layout = QHBoxLayout(self.frame_flatpak_id)
        fid_layout.setContentsMargins(0, 0, 0, 0)
        self.entry_flatpak_id = QLineEdit()
        self.entry_flatpak_id.setText(
            self.app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.MCPELAUNCHER_FLATPAK_ID)
        )
        fid_layout.addWidget(self.entry_flatpak_id, 1)
        form.addRow(c.t("UI_LABEL_FLATPAK_ID"), self.frame_flatpak_id)

        layout.addLayout(form)

        self.inputs = {}
        paths_group = QGroupBox(c.t("UI_LABEL_BINARY_PATHS"))
        self._groups["UI_LABEL_BINARY_PATHS"] = paths_group
        paths_group.setCheckable(False)
        paths_layout = QFormLayout(paths_group)
        for label, key in [
            (c.t("UI_LABEL_CLIENT_GAME"), c.CONFIG_KEY_CLIENT),
            (c.t("UI_LABEL_EXTRACTOR_APK"), c.CONFIG_KEY_EXTRACT),
            (c.t("UI_LABEL_SIGNIN_UI"), c.CONFIG_KEY_SIGNIN_UI),
            (c.t("UI_LABEL_GPLAYDL"), c.CONFIG_KEY_GPLAYDL),
            (c.t("UI_LABEL_GPLAYVER"), c.CONFIG_KEY_GPLAYVER),
            (c.t("UI_LABEL_WEBVIEW_OPTIONAL"), c.CONFIG_KEY_WEBVIEW),
            (c.t("UI_LABEL_ERROR_HANDLER_OPTIONAL"), c.CONFIG_KEY_ERROR),
            (c.t("UI_LABEL_MSA_DAEMON"), c.CONFIG_KEY_MSA_DAEMON),
        ]:
            row = QHBoxLayout()
            e = QLineEdit()
            e.setText(self.app.config[c.CONFIG_KEY_BINARY_PATHS].get(key, ""))
            row.addWidget(e, 1)
            b = QPushButton("...")
            b.setObjectName("ToolButton")
            b.setFixedSize(28, 28)
            b.clicked.connect(lambda checked=False, k=key, ent=e: self.browse_path(k, ent))
            row.addWidget(b)
            paths_layout.addRow(label, row)
            self.inputs[key] = (e, b, paths_group)

        layout.addWidget(paths_group)

        self.combo_settings_mode.currentTextChanged.connect(self.on_settings_mode_change)
        self.on_settings_mode_change(self.combo_settings_mode.currentText())

        self.scroll_layout.addWidget(group)
        self._add_spacer()

    def setup_launch_action_section(self):
        group = QGroupBox(c.t("UI_LAUNCH_ACTION_LABEL"))
        self._groups["UI_LAUNCH_ACTION_LABEL"] = group
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        row = QHBoxLayout()
        row.addWidget(QLabel(c.t("UI_LAUNCH_ACTION_LABEL")))
        self.combo_launch_action = QComboBox()
        self.combo_launch_action.addItem(c.t("UI_LAUNCH_ACTION_CLOSE"), c.LAUNCH_ACTION_CLOSE)
        self.combo_launch_action.addItem(c.t("UI_LAUNCH_ACTION_HIDE"), c.LAUNCH_ACTION_HIDE)
        self.combo_launch_action.addItem(c.t("UI_LAUNCH_ACTION_NONE"), c.LAUNCH_ACTION_NONE)
        current_action = self.app.config.get(c.CONFIG_KEY_LAUNCH_ACTION, c.LAUNCH_ACTION_CLOSE)
        idx = self.combo_launch_action.findData(current_action)
        if idx >= 0:
            self.combo_launch_action.setCurrentIndex(idx)
        self.combo_launch_action.currentIndexChanged.connect(
            lambda: (self.app.sync_launch_action_ui(self.combo_launch_action.currentData()),
                     self.app.config_manager.set(c.CONFIG_KEY_LAUNCH_ACTION, self.combo_launch_action.currentData()))
        )
        row.addWidget(self.combo_launch_action, 1)
        layout.addLayout(row)

        self.cb_custom_env = QCheckBox(c.t("UI_CUSTOM_ARGS_CHECKBOX"))
        self.cb_custom_env.setChecked(self.app.config.get(c.CONFIG_KEY_CUSTOM_ENV_ENABLED, False))
        self.cb_custom_env.stateChanged.connect(
            lambda state: (self.toggle_custom_env(),
                           self.app.config_manager.set(c.CONFIG_KEY_CUSTOM_ENV_ENABLED, state == Qt.Checked.value))
        )
        layout.addWidget(self.cb_custom_env)

        self.f_custom_vars = QFrame()
        cv_layout = QHBoxLayout(self.f_custom_vars)
        cv_layout.setContentsMargins(0, 0, 0, 0)
        cv_layout.addWidget(QLabel(c.t("UI_CUSTOM_ARGS_LABEL")))
        self.entry_custom_vars = QLineEdit()
        self.entry_custom_vars.setText(self.app.config.get(c.CONFIG_KEY_CUSTOM_ENV_VARS, ""))
        self.entry_custom_vars.editingFinished.connect(
            lambda: self.app.config_manager.set(c.CONFIG_KEY_CUSTOM_ENV_VARS, self.entry_custom_vars.text())
        )
        cv_layout.addWidget(self.entry_custom_vars, 1)
        layout.addWidget(self.f_custom_vars)

        self.scroll_layout.addWidget(group)
        self._add_spacer()

    # ── Performance / Compatibility ──────────────────────────────

    def setup_compatibility_section(self):
        group = QGroupBox(c.t("UI_SECTION_COMPATIBILITY"))
        self._groups["UI_SECTION_COMPATIBILITY"] = group
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        for label, key, tooltip in [
            (c.t("UI_GAMEMODE_CHECKBOX"), c.CONFIG_KEY_GAMEMODE_ENABLED, c.t("UI_GAMEMODE_TOOLTIP")),
            (c.t("UI_NVIDIA_PRIME_CHECKBOX"), c.CONFIG_KEY_NVIDIA_PRIME, c.t("UI_NVIDIA_PRIME_TOOLTIP")),
            (c.t("UI_ZINK_CHECKBOX"), c.CONFIG_KEY_ZINK_MODE, c.t("UI_ZINK_TOOLTIP")),
            (c.t("UI_FORCE_OPENGL_CHECKBOX"), c.CONFIG_KEY_FORCE_OPENGL, c.t("UI_FORCE_OPENGL_TOOLTIP")),
            (c.t("UI_FORCE_GLES32_CHECKBOX"), c.CONFIG_KEY_FORCE_GLES32, c.t("UI_FORCE_GLES32_TOOLTIP")),
            (c.t("UI_DISABLE_VSYNC_CHECKBOX"), c.CONFIG_KEY_DISABLE_VSYNC, c.t("UI_DISABLE_VSYNC_TOOLTIP")),
            (c.t("UI_FORCE_DISCRETE_GPU_CHECKBOX"), c.CONFIG_KEY_FORCE_DISCRETE_GPU, c.t("UI_FORCE_DISCRETE_GPU_TOOLTIP")),
        ]:
            row = QHBoxLayout()
            cb = QCheckBox(label)
            cb.setChecked(self.app.config.get(key, False))
            cb.stateChanged.connect(lambda state, k=key: self.app.config_manager.set(k, state == Qt.Checked.value))
            row.addWidget(cb)
            btn_info = QPushButton("?")
            btn_info.setObjectName("ToolButton")
            btn_info.setFixedSize(22, 22)
            btn_info.clicked.connect(lambda checked=False, t=label, m=tooltip: self.app.show_info(t, m))
            row.addWidget(btn_info)
            row.addStretch()
            layout.addLayout(row)
            self.checks[key] = cb

        self.checks[c.CONFIG_KEY_GAMEMODE_ENABLED].stateChanged.connect(
            lambda state: self.app.sync_gamemode_ui(state == Qt.Checked.value)
        )

        self.scroll_layout.addWidget(group)
        self._add_spacer()

    # ── Appearance ────────────────────────────────────────────────

    def setup_appearance_section(self):
        group = QGroupBox(c.t("UI_SECTION_APPEARANCE"))
        self._groups["UI_SECTION_APPEARANCE"] = group
        layout = QVBoxLayout(group)
        layout.setSpacing(16)

        mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        theme_color = self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
        accent = c.THEME_COLOR_MAP.get(theme_color, "#1f6aa5")
        text_color = "#DCE4EE" if mode == "Dark" else "#242424"
        frame_bg = "#3a3a3a" if mode == "Dark" else "#e8e8e8"

        # ── Appearance Mode (Dark/Light toggle) ──
        mode_label = QLabel(c.t("UI_LABEL_APPEARANCE_MODE"))
        mode_label.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color};")
        self._appearance_labels.append(mode_label)
        layout.addWidget(mode_label)

        mode_row = QHBoxLayout()
        self.mode_group = QButtonGroup()
        self.modes = {}
        for k, v in c.t("UI_APPEARANCE_MODES").items():
            btn = QPushButton(v)
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {frame_bg};
                    color: {text_color};
                    border: 2px solid transparent;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 6px 20px;
                }}
                QPushButton:checked {{
                    background-color: {accent};
                    color: white;
                    border: 2px solid {accent};
                }}
                QPushButton:hover:!checked {{
                    border: 2px solid {accent};
                }}
            """)
            self.mode_group.addButton(btn)
            self.modes[k] = btn
            if k == mode:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked=False, k=k: self._on_mode_btn_clicked(k))
            mode_row.addWidget(btn)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # ── Color Theme (color circles) ──
        theme_label = QLabel(c.t("UI_LABEL_COLOR_THEME"))
        theme_label.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color}; margin-top: 4px;")
        self._appearance_labels.append(theme_label)
        layout.addWidget(theme_label)

        self._theme_btns = []
        theme_grid = QGridLayout()
        theme_grid.setSpacing(14)
        themes = list(c.t("UI_THEME_NAMES").keys())
        for i, t in enumerate(themes):
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setFixedSize(46, 46)
            color = c.THEME_COLOR_MAP.get(t, "#1f6aa5")
            border = "3px solid white" if t == theme_color else "2px solid transparent"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    border-radius: 23px;
                    border: {border};
                    min-width: 46px;
                    min-height: 46px;
                }}
                QPushButton:hover {{
                    border: 3px solid white;
                }}
            """)
            btn.setToolTip(c.t("UI_THEME_NAMES").get(t, t.capitalize()))
            btn.clicked.connect(lambda checked=False, key=t: self._on_theme_btn_clicked(key))
            theme_grid.addWidget(btn, i // 6, i % 6)
            self._theme_btns.append(btn)
        layout.addLayout(theme_grid)
        layout.addSpacing(24)

        # ── Language ──
        self.langs_dict = language_manager.get_available_languages()
        self.combo_lang = QComboBox()
        for k, v in self.langs_dict.items():
            self.combo_lang.addItem(v, k)
        current_lang = self.app.config.get(c.CONFIG_KEY_LANGUAGE, "en")
        idx = self.combo_lang.findData(current_lang)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        self.combo_lang.currentTextChanged.connect(self.on_language_change)
        self.combo_lang.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        lang_row = QHBoxLayout()
        lang_label = QLabel(c.t("UI_LABEL_LANGUAGE"))
        lang_label.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color};")
        self._appearance_labels.append(lang_label)
        lang_row.addWidget(lang_label)
        lang_row.addWidget(self.combo_lang, 1)
        layout.addLayout(lang_row)

        # ── UI Scale ──
        self.combo_scale = QComboBox()
        self.combo_scale.addItems(["1.0", "1.25", "1.5", "1.75", "2.0"])
        curr_scale = str(self.app.config.get(c.CONFIG_KEY_UI_SCALE, "1.0"))
        self.combo_scale.setCurrentText(curr_scale)
        self.combo_scale.currentTextChanged.connect(self.on_scale_change)
        scale_row = QHBoxLayout()
        scale_label = QLabel(c.t("UI_LABEL_UI_SCALE"))
        scale_label.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color};")
        self._appearance_labels.append(scale_label)
        scale_row.addWidget(scale_label)
        scale_row.addWidget(self.combo_scale)
        scale_note = QLabel(c.t("UI_RESTART_SCALE_MSG"))
        scale_note.setStyleSheet("color: #ff9800; font-size: 10px;")
        scale_row.addWidget(scale_note)
        scale_row.addStretch()
        layout.addLayout(scale_row)

        # ── Version card style ──
        style_box = QGroupBox(c.t("UI_LABEL_VERSION_LIST_STYLE"))
        self._groups["UI_LABEL_VERSION_LIST_STYLE"] = style_box
        style_form = QFormLayout(style_box)

        self.combo_list_style = QComboBox()
        for k, v in c.t("UI_LIST_STYLES").items():
            self.combo_list_style.addItem(v, k)
        current_style = self.app.config.get(c.CONFIG_KEY_VERSION_LIST_STYLE, c.STYLE_LIST)
        idx = self.combo_list_style.findData(current_style)
        if idx >= 0:
            self.combo_list_style.setCurrentIndex(idx)
        self.combo_list_style.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.combo_list_style.currentTextChanged.connect(self.on_style_combo_changed)
        style_form.addRow(c.t("UI_LABEL_STYLE"), self.combo_list_style)

        self.slider_icon = QSlider(Qt.Horizontal)
        self.slider_icon.setRange(16, 128)
        self.slider_icon.setValue(self.app.config.get(c.CONFIG_KEY_VERSION_ICON_SIZE, 32))
        self.slider_icon.valueChanged.connect(self.on_appearance_setting_change)
        self.slider_icon.sliderReleased.connect(self.on_appearance_released)
        icon_row = QHBoxLayout()
        icon_row.addWidget(self.slider_icon, 1)
        self.lbl_icon_val = QLabel(str(self.slider_icon.value()))
        icon_row.addWidget(self.lbl_icon_val)
        style_form.addRow(c.t("UI_LABEL_ICON_SIZE"), icon_row)

        self.slider_title = QSlider(Qt.Horizontal)
        self.slider_title.setRange(8, 32)
        self.slider_title.setValue(self.app.config.get(c.CONFIG_KEY_VERSION_TITLE_SIZE, 13))
        self.slider_title.valueChanged.connect(self.on_appearance_setting_change)
        self.slider_title.sliderReleased.connect(self.on_appearance_released)
        title_row = QHBoxLayout()
        title_row.addWidget(self.slider_title, 1)
        self.lbl_title_val = QLabel(str(self.slider_title.value()))
        title_row.addWidget(self.lbl_title_val)
        style_form.addRow(c.t("UI_LABEL_TITLE_SIZE"), title_row)

        self.slider_card_width = QSlider(Qt.Horizontal)
        self.slider_card_width.setRange(80, 400)
        self.slider_card_width.setValue(self.app.config.get(c.CONFIG_KEY_VERSION_CARD_WIDTH, 180))
        self.slider_card_width.valueChanged.connect(self.on_appearance_setting_change)
        self.slider_card_width.sliderReleased.connect(self.on_appearance_released)
        cw_row = QHBoxLayout()
        cw_row.addWidget(self.slider_card_width, 1)
        self.lbl_card_width_val = QLabel(str(self.slider_card_width.value()))
        cw_row.addWidget(self.lbl_card_width_val)
        style_form.addRow(c.t("UI_LABEL_CARD_WIDTH"), cw_row)

        self.slider_card_height = QSlider(Qt.Horizontal)
        self.slider_card_height.setRange(60, 300)
        self.slider_card_height.setValue(self.app.config.get(c.CONFIG_KEY_VERSION_CARD_HEIGHT, 145))
        self.slider_card_height.valueChanged.connect(self.on_appearance_setting_change)
        self.slider_card_height.sliderReleased.connect(self.on_appearance_released)
        ch_row = QHBoxLayout()
        ch_row.addWidget(self.slider_card_height, 1)
        self.lbl_card_height_val = QLabel(str(self.slider_card_height.value()))
        ch_row.addWidget(self.lbl_card_height_val)
        style_form.addRow(c.t("UI_LABEL_CARD_HEIGHT"), ch_row)

        layout.addWidget(style_box)

        self.scroll_layout.addWidget(group)
        self._add_spacer()

    def setup_section_opacity_section(self):
        group = QGroupBox(c.t("UI_LABEL_SECTION_OPACITY").rstrip(":"))
        self._groups["UI_LABEL_SECTION_OPACITY"] = group
        layout = QVBoxLayout(group)

        row = QHBoxLayout()
        self.slider_section_opacity = QSlider(Qt.Horizontal)
        self.slider_section_opacity.setRange(0, 100)
        self.slider_section_opacity.setValue(self.app.config.get(c.CONFIG_KEY_SECTION_OPACITY, 100))
        self.slider_section_opacity.valueChanged.connect(self.on_section_opacity_change)
        self.slider_section_opacity.sliderReleased.connect(self.on_section_opacity_released)
        row.addWidget(self.slider_section_opacity, 1)
        self.lbl_section_opacity = QLabel(str(self.slider_section_opacity.value()))
        self.lbl_section_opacity.setStyleSheet("font-weight: bold; min-width: 35px;")
        row.addWidget(self.lbl_section_opacity)
        layout.addLayout(row)

        self.scroll_layout.addWidget(group)
        self._add_spacer()

    def setup_background_section(self):
        group = QGroupBox(c.t("UI_SECTION_BACKGROUND"))
        self._groups["UI_SECTION_BACKGROUND"] = group
        layout = QVBoxLayout(group)

        form = QFormLayout()

        path_row = QHBoxLayout()
        self.entry_bg_path = QLineEdit()
        self.entry_bg_path.setText(self.app.config.get(c.CONFIG_KEY_BG_PATH, ""))
        self.entry_bg_path.textChanged.connect(self.on_bg_change)
        path_row.addWidget(self.entry_bg_path, 1)
        btn_browse = QPushButton("...")
        btn_browse.setFixedSize(44, c.BTN_HEIGHT)
        btn_browse.clicked.connect(self.browse_bg)
        path_row.addWidget(btn_browse)
        form.addRow(c.t("UI_LABEL_BG_PATH"), path_row)

        x_row = QHBoxLayout()
        self.slider_bg_x = QSlider(Qt.Horizontal)
        self.slider_bg_x.setRange(-1000, 1000)
        self.slider_bg_x.setValue(self.app.config.get(c.CONFIG_KEY_BG_X, 0))
        self.slider_bg_x.valueChanged.connect(self.on_bg_change)
        self.slider_bg_x.sliderReleased.connect(self.on_bg_released)
        x_row.addWidget(self.slider_bg_x, 1)
        self.lbl_bg_x = QLabel(str(self.slider_bg_x.value()))
        x_row.addWidget(self.lbl_bg_x)
        form.addRow(c.t("UI_LABEL_BG_X"), x_row)

        y_row = QHBoxLayout()
        self.slider_bg_y = QSlider(Qt.Horizontal)
        self.slider_bg_y.setRange(-1000, 1000)
        self.slider_bg_y.setValue(self.app.config.get(c.CONFIG_KEY_BG_Y, 0))
        self.slider_bg_y.valueChanged.connect(self.on_bg_change)
        self.slider_bg_y.sliderReleased.connect(self.on_bg_released)
        y_row.addWidget(self.slider_bg_y, 1)
        self.lbl_bg_y = QLabel(str(self.slider_bg_y.value()))
        y_row.addWidget(self.lbl_bg_y)
        form.addRow(c.t("UI_LABEL_BG_Y"), y_row)

        opacity_row = QHBoxLayout()
        self.slider_bg_opacity = QSlider(Qt.Horizontal)
        self.slider_bg_opacity.setRange(0, 100)
        self.slider_bg_opacity.setValue(self.app.config.get(c.CONFIG_KEY_BG_OPACITY, 100))
        self.slider_bg_opacity.valueChanged.connect(self.on_bg_change)
        self.slider_bg_opacity.sliderReleased.connect(self.on_bg_released)
        opacity_row.addWidget(self.slider_bg_opacity, 1)
        self.lbl_bg_opacity = QLabel(str(self.slider_bg_opacity.value()))
        opacity_row.addWidget(self.lbl_bg_opacity)
        form.addRow(c.t("UI_LABEL_BG_OPACITY"), opacity_row)

        zoom_row = QHBoxLayout()
        self.slider_bg_zoom = QSlider(Qt.Horizontal)
        self.slider_bg_zoom.setRange(10, 500)
        self.slider_bg_zoom.setValue(self.app.config.get(c.CONFIG_KEY_BG_ZOOM, 100))
        self.slider_bg_zoom.valueChanged.connect(self.on_bg_change)
        self.slider_bg_zoom.sliderReleased.connect(self.on_bg_released)
        zoom_row.addWidget(self.slider_bg_zoom, 1)
        self.lbl_bg_zoom = QLabel(str(self.slider_bg_zoom.value()))
        zoom_row.addWidget(self.lbl_bg_zoom)
        form.addRow(c.t("UI_LABEL_BG_ZOOM"), zoom_row)

        layout.addLayout(form)
        self.scroll_layout.addWidget(group)
        self._add_spacer()

    def setup_sticker_section(self):
        group = QGroupBox(c.t("UI_SECTION_STICKER"))
        self._groups["UI_SECTION_STICKER"] = group
        layout = QVBoxLayout(group)

        form = QFormLayout()

        self.combo_sticker_mode = QComboBox()
        mode_map = c.t("UI_STICKER_MODES")
        for k, v in mode_map.items():
            self.combo_sticker_mode.addItem(v, k)
        curr_mode = self.app.config.get(c.CONFIG_KEY_STICKER_MODE, "none")
        idx = self.combo_sticker_mode.findData(curr_mode)
        if idx >= 0:
            self.combo_sticker_mode.setCurrentIndex(idx)
        self.combo_sticker_mode.currentTextChanged.connect(self.on_sticker_change)
        self.combo_sticker_mode.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        form.addRow(c.t("UI_LABEL_STICKER_MODE"), self.combo_sticker_mode)

        content_row = QHBoxLayout()
        self.entry_sticker_content = QLineEdit()
        self.entry_sticker_content.setText(self.app.config.get(c.CONFIG_KEY_STICKER_CONTENT, ""))
        self.entry_sticker_content.textChanged.connect(self.on_sticker_change)
        content_row.addWidget(self.entry_sticker_content, 1)
        btn_browse_s = QPushButton("...")
        btn_browse_s.setFixedSize(44, c.BTN_HEIGHT)
        btn_browse_s.clicked.connect(self.browse_sticker)
        content_row.addWidget(btn_browse_s)
        form.addRow(c.t("UI_LABEL_STICKER_CONTENT"), content_row)

        self.combo_sticker_corner = QComboBox()
        corner_map = c.t("UI_STICKER_CORNERS")
        for k, v in corner_map.items():
            self.combo_sticker_corner.addItem(v, k)
        curr_corner = self.app.config.get(c.CONFIG_KEY_STICKER_CORNER, "bottom-right")
        idx = self.combo_sticker_corner.findData(curr_corner)
        if idx >= 0:
            self.combo_sticker_corner.setCurrentIndex(idx)
        self.combo_sticker_corner.currentTextChanged.connect(self.on_sticker_change)
        self.combo_sticker_corner.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        form.addRow(c.t("UI_LABEL_STICKER_CORNER"), self.combo_sticker_corner)

        sx_row = QHBoxLayout()
        self.slider_sticker_x = QSlider(Qt.Horizontal)
        self.slider_sticker_x.setRange(0, 500)
        self.slider_sticker_x.setValue(self.app.config.get(c.CONFIG_KEY_STICKER_X, 10))
        self.slider_sticker_x.valueChanged.connect(self.on_sticker_change)
        self.slider_sticker_x.sliderReleased.connect(self.on_sticker_released)
        sx_row.addWidget(self.slider_sticker_x, 1)
        self.lbl_sticker_x = QLabel(str(self.slider_sticker_x.value()))
        sx_row.addWidget(self.lbl_sticker_x)
        form.addRow(c.t("UI_LABEL_STICKER_X"), sx_row)

        sy_row = QHBoxLayout()
        self.slider_sticker_y = QSlider(Qt.Horizontal)
        self.slider_sticker_y.setRange(0, 500)
        self.slider_sticker_y.setValue(self.app.config.get(c.CONFIG_KEY_STICKER_Y, 10))
        self.slider_sticker_y.valueChanged.connect(self.on_sticker_change)
        self.slider_sticker_y.sliderReleased.connect(self.on_sticker_released)
        sy_row.addWidget(self.slider_sticker_y, 1)
        self.lbl_sticker_y = QLabel(str(self.slider_sticker_y.value()))
        sy_row.addWidget(self.lbl_sticker_y)
        form.addRow(c.t("UI_LABEL_STICKER_Y"), sy_row)

        sz_row = QHBoxLayout()
        self.slider_sticker_zoom = QSlider(Qt.Horizontal)
        self.slider_sticker_zoom.setRange(10, 500)
        self.slider_sticker_zoom.setValue(self.app.config.get(c.CONFIG_KEY_STICKER_ZOOM, 100))
        self.slider_sticker_zoom.valueChanged.connect(self.on_sticker_change)
        self.slider_sticker_zoom.sliderReleased.connect(self.on_sticker_released)
        sz_row.addWidget(self.slider_sticker_zoom, 1)
        self.lbl_sticker_zoom = QLabel(str(self.slider_sticker_zoom.value()))
        sz_row.addWidget(self.lbl_sticker_zoom)
        form.addRow(c.t("UI_LABEL_STICKER_ZOOM"), sz_row)

        so_row = QHBoxLayout()
        self.slider_sticker_opacity = QSlider(Qt.Horizontal)
        self.slider_sticker_opacity.setRange(0, 100)
        self.slider_sticker_opacity.setValue(self.app.config.get(c.CONFIG_KEY_STICKER_OPACITY, 100))
        self.slider_sticker_opacity.valueChanged.connect(self.on_sticker_change)
        self.slider_sticker_opacity.sliderReleased.connect(self.on_sticker_released)
        so_row.addWidget(self.slider_sticker_opacity, 1)
        self.lbl_sticker_opacity = QLabel(str(self.slider_sticker_opacity.value()))
        so_row.addWidget(self.lbl_sticker_opacity)
        form.addRow(c.t("UI_LABEL_STICKER_OPACITY"), so_row)

        layout.addLayout(form)
        self.scroll_layout.addWidget(group)
        self._add_spacer()

    # ── Integrations ─────────────────────────────────────────────

    def setup_discord_section(self):
        group = QGroupBox(c.t("UI_DISCORD_RPC_SECTION_TITLE"))
        self._groups["UI_DISCORD_RPC_SECTION_TITLE"] = group
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        row = QHBoxLayout()
        self.check_discord_rpc = QCheckBox(c.t("UI_DISCORD_RPC_CHECKBOX"))
        self.check_discord_rpc.setChecked(self.app.config.get(c.CONFIG_KEY_DISCORD_RPC_ENABLED, False))
        row.addWidget(self.check_discord_rpc)
        btn_info = QPushButton("?")
        btn_info.setObjectName("ToolButton")
        btn_info.setFixedSize(25, 25)
        btn_info.clicked.connect(
            lambda checked=False: self.app.show_info(
                c.t("UI_DISCORD_RPC_CHECKBOX"), c.t("UI_DISCORD_RPC_TOOLTIP")
            )
        )
        row.addWidget(btn_info)
        row.addStretch()
        layout.addLayout(row)
        self.checks[c.CONFIG_KEY_DISCORD_RPC_ENABLED] = self.check_discord_rpc
        self.check_discord_rpc.stateChanged.connect(
            lambda state: self.app.sync_discord_rpc_ui(state == Qt.Checked.value)
        )

        ci_row = QHBoxLayout()
        ci_row.addWidget(QLabel(c.t("UI_DISCORD_RPC_CLIENT_ID_LABEL")))
        self.entry_discord_client_id = QLineEdit()
        self.entry_discord_client_id.setText(self.app.config.get(c.CONFIG_KEY_DISCORD_RPC_CLIENT_ID, ""))
        self.entry_discord_client_id.setPlaceholderText(c.DISCORD_DEFAULT_CLIENT_ID)
        ci_row.addWidget(self.entry_discord_client_id, 1)
        layout.addLayout(ci_row)

        self.scroll_layout.addWidget(group)
        self._add_spacer()

    def retranslate_ui(self):
        for key, label_key in self.CATEGORIES:
            self._cat_buttons[key].setText(c.t(label_key))
            self._cat_buttons[key].setIcon(category_icon(key))
        for key, group in self._groups.items():
            text = c.t(key)
            if key == "UI_LABEL_SECTION_OPACITY":
                text = text.rstrip(":")
            group.setTitle(text)
        if hasattr(self, "btn_save"):
            self.btn_save.setText(c.t("UI_BUTTON_SAVE_SETTINGS"))
        if hasattr(self, "btn_restore"):
            self.btn_restore.setText(c.t("UI_BUTTON_RESTORE_DEFAULTS"))
        for widget, label_key in self._retranslate_labels:
            widget.setText(c.t(label_key))
        if hasattr(self, "modes"):
            for k, btn in self.modes.items():
                btn.setText(c.t("UI_APPEARANCE_MODES").get(k, k))

    # ── Helpers ──────────────────────────────────────────────────

    def _add_spacer(self):
        self.scroll_layout.addSpacing(8)

    def browse_path(self, key, entry):
        path = ask_open_filename_native(self.app, title=f"{c.t('UI_OPEN_FILE_TITLE')}")
        if path:
            entry.setText(path)

    def update_binary_version_info(self):
        if self.lbl_binary_version is None:
            return
        mode = self.app.config.get(c.CONFIG_KEY_MODE, c.t("UI_DEFAULT_MODE"))
        if mode == c.MODE_BIN_FLATPAK or self.app.running_in_flatpak:
            self.lbl_binary_version.setText(c.BINARY_VERSION_INFO)
        else:
            info_path = os.path.join(self.app.compiled_path, "info.txt")
            if os.path.exists(info_path):
                try:
                    with open(info_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        if len(lines) >= 2:
                            self.lbl_binary_version.setText(lines[1].strip())
                        else:
                            self.lbl_binary_version.setText(c.BINARY_VERSION_FALLBACK)
                except (OSError, UnicodeDecodeError) as e:
                    logger.debug(f"Could not read binary info.txt: {e}")
                    self.lbl_binary_version.setText(c.BINARY_VERSION_FALLBACK)
            else:
                self.lbl_binary_version.setText(c.BINARY_VERSION_FALLBACK)

    def on_settings_mode_change(self, display_name):
        mode_key = self.combo_settings_mode.currentData() or c.MODE_BIN_SYSTEM
        is_flatpak = mode_key == c.MODE_BIN_FLATPAK
        is_custom = mode_key == c.MODE_BIN_CUSTOM
        self.frame_flatpak_id.setVisible(is_flatpak)
        for key, (e, b, parent) in self.inputs.items():
            e.setEnabled(is_custom)
            b.setEnabled(is_custom)
            parent.setVisible(is_custom)
        self.update_binary_version_info()

    def toggle_custom_env(self):
        enabled = self.cb_custom_env.isChecked()
        if c.CONFIG_KEY_NVIDIA_PRIME in self.checks:
            self.checks[c.CONFIG_KEY_NVIDIA_PRIME].setEnabled(not enabled)
        if c.CONFIG_KEY_ZINK_MODE in self.checks:
            self.checks[c.CONFIG_KEY_ZINK_MODE].setEnabled(not enabled)
        self.entry_custom_vars.setEnabled(enabled)
        mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        if enabled:
            text_color = "white" if mode == "Dark" else "#242424"
            self.f_custom_vars.setStyleSheet("")
            self.entry_custom_vars.setStyleSheet(
                f"color: {text_color}; padding: 4px; border: 1px solid {'#444' if mode == 'Dark' else '#ccc'}; border-radius: 6px; background-color: {'#333' if mode == 'Dark' else '#fff'};"
            )
        else:
            disabled_text = "#666" if mode == "Dark" else "#999"
            disabled_bg = "#2a2a2a" if mode == "Dark" else "#f0f0f0"
            self.f_custom_vars.setStyleSheet("")
            self.entry_custom_vars.setStyleSheet(
                f"color: {disabled_text}; background-color: {disabled_bg}; border: 1px dashed {'#555' if mode == 'Dark' else '#bbb'}; border-radius: 6px;"
            )

    # ── Slots ────────────────────────────────────────────────────

    def _on_theme_btn_clicked(self, theme_key):
        if hasattr(self, 'combo_theme'):
            self.combo_theme.deleteLater()
            del self.combo_theme
        self._update_theme_btns(theme_key)
        self.app.change_appearance("color", theme_key)

    def _update_theme_btns(self, selected_key):
        for btn, key in zip(self._theme_btns, list(c.t("UI_THEME_NAMES").keys())):
            color = c.THEME_COLOR_MAP.get(key, "#1f6aa5")
            border = "3px solid white" if key == selected_key else "2px solid transparent"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    border-radius: 23px;
                    border: {border};
                    min-width: 46px;
                    min-height: 46px;
                }}
                QPushButton:hover {{
                    border: 3px solid white;
                }}
            """)

    def _refresh_per_widget_styles(self):
        mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        theme_color = self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
        accent = c.THEME_COLOR_MAP.get(theme_color, "#1f6aa5")
        text_color = "#DCE4EE" if mode == "Dark" else "#1a1a1a"
        frame_bg = "#3a3a3a" if mode == "Dark" else "#e8e8e8"
        input_bg = "#2a2a2a" if mode == "Dark" else "#ffffff"
        input_text = "#ffffff" if mode == "Dark" else "#1a1a1a"
        input_border = "#555555" if mode == "Dark" else "#c1c9d4"
        slider_groove = "#4a4a4a" if mode == "Dark" else "#c9c9c9"

        combo_qss = f"""
            QComboBox {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 13px;
            }}
            QComboBox:hover {{ border: 1px solid {accent}; }}
            QComboBox:focus {{ border: 1px solid {accent}; }}
            QComboBox::drop-down {{ border: none; width: 24px; background: transparent; }}
            QComboBox::down-arrow {{
                width: 10px;
                height: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 4px;
                selection-background-color: {accent};
                selection-color: white;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 5px 8px;
                min-height: 26px;
            }}
        """

        line_qss = f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 4px;
                padding: 5px 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {accent}; }}
        """

        slider_qss = f"""
            QSlider {{
                min-height: 24px;
            }}
            QSlider::groove:horizontal {{
                background: {slider_groove};
                height: 6px;
                border-radius: 3px;
                border: 1px solid {input_border};
                margin: 2px 0;
            }}
            QSlider::handle:horizontal {{
                background: {accent};
                border: 1px solid {input_border};
                width: 16px;
                height: 16px;
                margin: -3px 0;
                border-radius: 8px;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 3px;
            }}
        """

        for label in self._appearance_labels:
            label.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color};")

        muted_color = "#aaaaaa" if mode == "Dark" else "#555555"
        if hasattr(self, "lbl_binary_version"):
            self.lbl_binary_version.setStyleSheet(f"color: {muted_color}; font-size: 11px;")

        for name in ["combo_profile", "combo_settings_mode", "combo_launch_action",
                     "combo_lang", "combo_scale", "combo_list_style",
                     "combo_sticker_mode", "combo_sticker_corner"]:
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setStyleSheet(combo_qss)

        for name in ["entry_flatpak_id", "entry_discord_client_id",
                     "entry_bg_path", "entry_sticker_content"]:
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setStyleSheet(line_qss)

        if hasattr(self, "inputs"):
            for key, (e, b, parent) in self.inputs.items():
                e.setStyleSheet(line_qss)

        for name in ["slider_icon", "slider_title", "slider_card_width", "slider_card_height",
                     "slider_section_opacity", "slider_bg_x", "slider_bg_y",
                     "slider_bg_opacity", "slider_bg_zoom", "slider_sticker_x",
                     "slider_sticker_y", "slider_sticker_zoom", "slider_sticker_opacity"]:
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setStyleSheet(slider_qss)

        if hasattr(self, 'modes'):
            for k, btn in self.modes.items():
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {frame_bg};
                        color: {text_color};
                        border: 2px solid {input_border};
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 13px;
                        padding: 6px 20px;
                    }}
                    QPushButton:checked {{
                        background-color: {accent};
                        color: white;
                        border: 2px solid {accent};
                    }}
                    QPushButton:hover:!checked {{
                        border: 2px solid {accent};
                    }}
                """)

        self.toggle_custom_env()

    def _on_mode_btn_clicked(self, mode_key):
        for k, btn in self.modes.items():
            btn.setChecked(k == mode_key)
        self.app.config_manager.set(c.CONFIG_KEY_APPEARANCE, mode_key)
        self.app.apply_theme_settings()
        self._refresh_per_widget_styles()

    def on_theme_change(self, display_name):
        theme_key = self.combo_theme.currentData() or "blue"
        self.app.change_appearance("color", theme_key)

    def on_appearance_mode_change(self, display_name):
        mode_key = self.combo_app_mode.currentData() or "Dark"
        self.app.config_manager.set(c.CONFIG_KEY_APPEARANCE, mode_key)
        self.app.apply_theme_settings()
        self._refresh_per_widget_styles()

    def on_language_change(self, display_name):
        lang_code = self.combo_lang.currentData() or "en"
        self.app.config_manager.set(c.CONFIG_KEY_LANGUAGE, lang_code)
        language_manager.load_language(lang_code)
        self.app.retranslate_all()

    def on_scale_change(self, value):
        self.app.config[c.CONFIG_KEY_UI_SCALE] = value
        self.app.config_manager.save_config()

    def on_section_opacity_change(self):
        val = self.slider_section_opacity.value()
        self.lbl_section_opacity.setText(str(val))
        self.app.config_manager.set(c.CONFIG_KEY_SECTION_OPACITY, val)
        if not hasattr(self, '_opacity_debounce'):
            from PySide6.QtCore import QTimer
            self._opacity_debounce = QTimer()
            self._opacity_debounce.setSingleShot(True)
            self._opacity_debounce.timeout.connect(self.app.apply_theme_settings)
        self._opacity_debounce.start(50)

    def on_section_opacity_released(self):
        self.app.config_manager.set(c.CONFIG_KEY_SECTION_OPACITY, self.slider_section_opacity.value())

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
        self.app.personalization_timer.start()

    def on_bg_released(self):
        self.app.config_manager.set(c.CONFIG_KEY_BG_PATH, self.entry_bg_path.text())
        self.app.config_manager.set(c.CONFIG_KEY_BG_X, self.slider_bg_x.value())
        self.app.config_manager.set(c.CONFIG_KEY_BG_Y, self.slider_bg_y.value())
        self.app.config_manager.set(c.CONFIG_KEY_BG_OPACITY, self.slider_bg_opacity.value())
        self.app.config_manager.set(c.CONFIG_KEY_BG_ZOOM, self.slider_bg_zoom.value())

    def browse_bg(self):
        p = ask_open_filename_native(self.app, title=c.t("UI_LABEL_BG_PATH"))
        if p:
            self.entry_bg_path.setText(p)

    def on_sticker_change(self):
        self.lbl_sticker_x.setText(str(self.slider_sticker_x.value()))
        self.lbl_sticker_y.setText(str(self.slider_sticker_y.value()))
        self.lbl_sticker_zoom.setText(str(self.slider_sticker_zoom.value()))
        self.lbl_sticker_opacity.setText(str(self.slider_sticker_opacity.value()))
        mode_key = self.combo_sticker_mode.currentData() or "none"
        corner_key = self.combo_sticker_corner.currentData() or "bottom-right"
        self.app.config[c.CONFIG_KEY_STICKER_MODE] = mode_key
        self.app.config[c.CONFIG_KEY_STICKER_CONTENT] = self.entry_sticker_content.text()
        self.app.config[c.CONFIG_KEY_STICKER_CORNER] = corner_key
        self.app.config[c.CONFIG_KEY_STICKER_X] = self.slider_sticker_x.value()
        self.app.config[c.CONFIG_KEY_STICKER_Y] = self.slider_sticker_y.value()
        self.app.config[c.CONFIG_KEY_STICKER_ZOOM] = self.slider_sticker_zoom.value()
        self.app.config[c.CONFIG_KEY_STICKER_OPACITY] = self.slider_sticker_opacity.value()
        self.app.personalization_timer.start()

    def on_sticker_released(self):
        self.app.config_manager.set(c.CONFIG_KEY_STICKER_MODE, self.app.config.get(c.CONFIG_KEY_STICKER_MODE, "none"))
        self.app.config_manager.set(c.CONFIG_KEY_STICKER_CONTENT, self.entry_sticker_content.text())
        self.app.config_manager.set(c.CONFIG_KEY_STICKER_CORNER, self.app.config.get(c.CONFIG_KEY_STICKER_CORNER, "bottom-right"))
        self.app.config_manager.set(c.CONFIG_KEY_STICKER_X, self.slider_sticker_x.value())
        self.app.config_manager.set(c.CONFIG_KEY_STICKER_Y, self.slider_sticker_y.value())
        self.app.config_manager.set(c.CONFIG_KEY_STICKER_ZOOM, self.slider_sticker_zoom.value())
        self.app.config_manager.set(c.CONFIG_KEY_STICKER_OPACITY, self.slider_sticker_opacity.value())

    def browse_sticker(self):
        p = ask_open_filename_native(self.app, title=c.t("UI_LABEL_STICKER_CONTENT"))
        if p:
            self.entry_sticker_content.setText(p)

    def on_appearance_setting_change(self):
        self.lbl_icon_val.setText(str(self.slider_icon.value()))
        self.lbl_title_val.setText(str(self.slider_title.value()))
        if hasattr(self, 'lbl_card_width_val'):
            self.lbl_card_width_val.setText(str(self.slider_card_width.value()))
        if hasattr(self, 'lbl_card_height_val'):
            self.lbl_card_height_val.setText(str(self.slider_card_height.value()))

    def on_style_combo_changed(self):
        style_key = self.combo_list_style.currentData() or c.STYLE_LIST
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_LIST_STYLE, style_key)
        self.app.logic.refresh_version_list(self.app)

    def on_appearance_released(self):
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_ICON_SIZE, self.slider_icon.value())
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_TITLE_SIZE, self.slider_title.value())
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_CARD_WIDTH, self.slider_card_width.value())
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_CARD_HEIGHT, self.slider_card_height.value())
        self.app.logic.refresh_version_list(self.app)
        if hasattr(self.app, "tools_tab"):
            self.app.tools_tab.refresh_tools_ui()

    def on_profile_change(self, display_text):
        profile_name = self.combo_profile.currentData()
        if profile_name:
            self.app.logic.switch_profile(self.app, profile_name)
            self.refresh_profile_list()

    def open_profile_manager(self):
        from src.gui.profile_manager_dialog import ProfileManagerDialog
        dialog = ProfileManagerDialog(self.app, self.app)
        dialog.exec()
        self.refresh_profile_list()

    def refresh_profile_list(self):
        self.combo_profile.blockSignals(True)
        self._populate_profile_combo()
        self.combo_profile.blockSignals(False)

    def _populate_profile_combo(self):
        self.combo_profile.clear()
        current = self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, "")
        profiles = sorted(self.app.logic.get_profiles(self.app))
        for idx, p in enumerate(profiles):
            icon = profile_icon(idx)
            prefix = "★ " if p == current else ""
            self.combo_profile.addItem(icon, prefix + p, p)
        idx = self.combo_profile.findData(current)
        if idx >= 0:
            self.combo_profile.setCurrentIndex(idx)

    def save_settings(self):
        mode_key = self.combo_settings_mode.currentData() or c.MODE_BIN_SYSTEM
        self.app.config_manager.set(c.CONFIG_KEY_MODE, mode_key)
        self.app.config_manager.set(c.CONFIG_KEY_FLATPAK_ID, self.entry_flatpak_id.text())
        for key, cb in self.checks.items():
            self.app.config_manager.set(key, cb.isChecked())
        self.app.config_manager.set(c.CONFIG_KEY_CUSTOM_ENV_VARS, self.entry_custom_vars.text())
        self.app.config_manager.set(c.CONFIG_KEY_DISCORD_RPC_CLIENT_ID, self.entry_discord_client_id.text().strip())
        if mode_key == c.MODE_BIN_CUSTOM:
            for key, (e, b, parent) in self.inputs.items():
                paths = dict(self.app.config.get(c.CONFIG_KEY_BINARY_PATHS, {}))
                paths[key] = e.text()
                self.app.config_manager.set(c.CONFIG_KEY_BINARY_PATHS, paths)
        from src.gui import custom_dialogs as messagebox
        messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), c.t("UI_SAVE_SUCCESS_MSG"))
