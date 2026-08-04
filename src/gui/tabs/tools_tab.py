from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QFrame, QGridLayout)
from PySide6.QtCore import Qt
from src import constants as c

class ToolsTab(QWidget):
    """Tools tab displaying grouped utility buttons for management, customization, files, and system tasks."""
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(c.SECTION_PADDING, 5, c.SECTION_PADDING, c.SECTION_PADDING)

        # Header
        self.header_layout = QHBoxLayout()
        self.main_layout.addLayout(self.header_layout)

        self.lbl_tools_status = QLabel("")
        self.lbl_tools_status.setObjectName("FloatingLabel")
        self.lbl_tools_status.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.header_layout.addWidget(self.lbl_tools_status)

        self.header_layout.addStretch()

        self.lbl_current_profile = QLabel("")
        self.lbl_current_profile.setObjectName("FloatingLabel")
        self.lbl_current_profile.setStyleSheet(f"color: {c.COLOR_PRIMARY_GREEN}; font-size: 11px;")
        self.header_layout.addWidget(self.lbl_current_profile)

        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.scroll_content.setMinimumWidth(480)
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setSpacing(12)

        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

        self.lbl_shader_status = None
        self.refresh_tools_ui()

    def retranslate_ui(self):
        self.lbl_tools_status.setText("")
        current = self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.t("UI_PROFILE_DEFAULT"))
        self.lbl_current_profile.setText(f"👤 {c.t('UI_LABEL_PROFILE')} {current}")
        self.refresh_tools_ui()

    def get_tools_data(self):
        """Return the grouped tool definitions with icons, labels, and callbacks."""
        groups = [
            {
                "title": c.t("UI_SECTION_MANAGEMENT"),
                "icon": "⚙️",
                "tools": [
                    {"text": c.t("UI_BUTTON_INSTALL_APK"), "icon": "📥", "cmd": self.app.install_apk_dialog, "color": None},
                    {"text": c.t("UI_BUTTON_MANAGE_SHORTCUT"), "icon": "🗑️", "cmd": self.app.open_version_manager, "color": None},
                    {"text": c.t("UI_BUTTON_MIGRATE_DATA"), "icon": "🚀", "cmd": self.app.open_migration_tool, "color": None},
                ]
            },
            {
                "title": c.t("UI_SECTION_CUSTOMIZATION"),
                "icon": "🎨",
                "tools": [
                    {"text": c.t("UI_BUTTON_SKIN_PACK_CREATOR"), "icon": "👕", "cmd": self.app.open_skin_tool, "color": None},
                    {"text": c.t("UI_BUTTON_GAME_CONFIG"), "icon": "🛠️", "cmd": self.app.open_game_config_tool, "color": None},
                    {"text": c.t("UI_BUTTON_DISABLE_SHADERS"), "icon": "✨", "cmd": lambda: self.app.logic.disable_shaders(self.app), "color": c.COLOR_YELLOW_BUTTON, "show_status": True},
                ]
            },
            {
                "title": c.t("UI_SECTION_FILES"),
                "icon": "📂",
                "tools": [
                    {"text": c.t("UI_BUTTON_ADDON_MANAGER"), "icon": "📦", "cmd": self.app.open_addon_manager, "color": None},
                    {"text": c.t("UI_BUTTON_OPEN_DATA_FOLDER"), "icon": "📁", "cmd": lambda: self.app.logic.open_data_folder(self.app), "color": None},
                    {"text": c.t("UI_BUTTON_OPEN_SCREENSHOTS"), "icon": "📸", "cmd": lambda: self.app.logic.export_screenshots_dialog(self.app), "color": None},
                ]
            },
            {
                "title": c.t("UI_SECTION_SYSTEM"),
                "icon": "💻",
                "tools": [
                    {
                        "text": c.t("UI_BUTTON_VERIFY_DEPS_FLATPAK") if self.app.running_in_flatpak else c.t("UI_BUTTON_VERIFY_DEPS_LOCAL"),
                        "icon": "📦", "cmd": lambda: self.app.logic.verify_dependencies(self.app), "color": None
                    },
                    {"text": c.t("UI_BUTTON_VERIFY_HW"), "icon": "🔍", "cmd": lambda: self.app.logic.check_requirements_dialog(self.app), "color": None},
                    {"text": c.t("UI_LABEL_COMPATIBLE_RANGE"), "icon": "✅", "cmd": None, "show_compat": True}
                ]
            }
        ]
        return groups

    def _muted(self):
        return "#aaaaaa" if self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark") == "Dark" else "#555555"

    def refresh_tools_ui(self):
        """Rebuild the tools area, honoring the current layout style (list, columns, or grid)."""
        # Clear layout safely
        from src.core.ui_utils import clear_layout
        clear_layout(self.scroll_layout)

        layout_style = self.app.config.get(c.CONFIG_KEY_TOOLS_LAYOUT, c.STYLE_COLUMNS)
        groups = self.get_tools_data()

        if layout_style == c.STYLE_LIST:
            self._render_list(groups)
        elif layout_style == c.STYLE_COLUMNS:
            self._render_columns(groups)
        else: # GRID
            self._render_grid(groups)

        # Footer Credits
        footer = QLabel(c.t("CREDITOS"))
        footer.setStyleSheet(f"color: {self._muted()}; font-size: 11px;")
        footer.setAlignment(Qt.AlignCenter)
        self.scroll_layout.addWidget(footer)

    def _create_tool_button(self, parent_layout, tool):
        if tool.get("show_compat"):
            container = QWidget()
            l = QVBoxLayout(container)
            l.setContentsMargins(0, 5, 0, 5)
            l.setSpacing(2)

            t1 = QLabel(tool["text"])
            t1.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {self._muted()};")
            t1.setAlignment(Qt.AlignCenter)
            l.addWidget(t1)

            range_val_text = self.app.logic.get_compatibility_range(self.app)
            t2 = QLabel(range_val_text)
            t2.setStyleSheet(f"color: {c.COLOR_PRIMARY_GREEN}; font-weight: bold; font-size: 14px;")
            t2.setAlignment(Qt.AlignCenter)
            l.addWidget(t2)

            parent_layout.addWidget(container)
            return

        if tool.get("show_drm_status"):
            container = QWidget()
            l = QVBoxLayout(container)
            l.setContentsMargins(0, 5, 0, 5)
            l.setSpacing(2)

            t1 = QLabel(tool["text"])
            t1.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {self._muted()};")
            t1.setAlignment(Qt.AlignCenter)
            l.addWidget(t1)

            drm_status = self.app.logic.get_drm_mod_status(self.app)
            if drm_status == "installed":
                status_text = c.t("UI_DRM_MOD_STATUS_INSTALLED")
                status_color = c.COLOR_PRIMARY_GREEN
            elif drm_status == "disabled":
                status_text = c.t("UI_DRM_MOD_STATUS_DISABLED")
                status_color = c.COLOR_YELLOW_BUTTON
            else:
                status_text = c.t("UI_DRM_MOD_STATUS_MISSING")
                status_color = c.COLOR_RED_BUTTON
            t2 = QLabel(status_text)
            t2.setStyleSheet(f"color: {status_color}; font-weight: bold; font-size: 14px;")
            t2.setAlignment(Qt.AlignCenter)
            l.addWidget(t2)

            desc = QLabel(c.t("UI_DRM_MOD_DESC"))
            desc.setWordWrap(True)
            desc.setStyleSheet(f"font-size: 11px; color: {self._muted()};")
            desc.setAlignment(Qt.AlignCenter)
            l.addWidget(desc)

            credit = QLabel(c.t("UI_DRM_MOD_CREDIT"))
            credit.setWordWrap(True)
            credit.setStyleSheet(f"font-size: 10px; color: {self._muted()}; font-style: italic;")
            credit.setAlignment(Qt.AlignCenter)
            l.addWidget(credit)

            parent_layout.addWidget(container)
            return

        btn = QPushButton(f"{tool['icon']} {tool['text']}")
        btn.setFixedHeight(c.BTN_HEIGHT + 6)

        if tool.get("color"):
            bg = tool['color']
            r = int(bg[1:3], 16); g = int(bg[3:5], 16); b = int(bg[5:7], 16)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            text_color = "#242424" if luminance > 0.5 else "white"
            btn.setStyleSheet(f"background-color: {bg}; color: {text_color}; border-radius: 8px; font-size: 13px; font-weight: bold;")
        else:
            btn.setObjectName("ToolButton")

        if tool["cmd"]:
            btn.clicked.connect(tool["cmd"])
        else:
            btn.setEnabled(False)
        parent_layout.addWidget(btn)

        if tool.get("show_status"):
            self.lbl_shader_status = QLabel(c.t("UI_LABEL_SHADERS_STATUS"))
            muted = "#aaaaaa" if self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark") == "Dark" else "#555555"
            self.lbl_shader_status.setStyleSheet(f"font-size: 11px; color: {muted};")
            self.lbl_shader_status.setAlignment(Qt.AlignCenter)
            parent_layout.addWidget(self.lbl_shader_status)
            self.app.logic.update_shader_status_label(self.app)

    def _render_list(self, groups):
        for group in groups:
            frame = QFrame()
            frame.setObjectName("GroupFrame")
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(15, 13, 15, 13)
            layout.setSpacing(7)

            title = QLabel(f"{group['icon']} {group['title']}")
            title.setObjectName("HeaderLabel")
            title.setAlignment(Qt.AlignCenter)
            title.setFixedHeight(32)
            layout.addWidget(title)

            for tool in group["tools"]:
                self._create_tool_button(layout, tool)

            self.scroll_layout.addWidget(frame)

    def _render_columns(self, groups):
        grid = QGridLayout()
        self.scroll_layout.addLayout(grid)

        for i, group in enumerate(groups):
            frame = QFrame()
            frame.setObjectName("GroupFrame")
            frame.setMinimumHeight(200)
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(15, 13, 15, 13)
            layout.setSpacing(7)

            title = QLabel(f"{group['icon']} {group['title']}")
            title.setObjectName("HeaderLabel")
            title.setAlignment(Qt.AlignCenter)
            title.setFixedHeight(32)
            layout.addWidget(title)

            for tool in group["tools"]:
                self._create_tool_button(layout, tool)

            layout.addStretch(1)

            grid.addWidget(frame, i // 2, i % 2)

    def _render_grid(self, groups):
        grid = QGridLayout()
        self.scroll_layout.addLayout(grid)

        all_tools = []
        for group in groups:
            for tool in group["tools"]:
                all_tools.append(tool)

        for i, tool in enumerate(all_tools):
            card = QFrame()
            card.setObjectName("ToolCard")
            card.setFixedSize(180, 145)
            layout = QVBoxLayout(card)
            layout.setAlignment(Qt.AlignCenter)

            icon = QLabel(tool["icon"])
            icon.setStyleSheet("font-size: 42px;")
            icon.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon)

            text = QLabel(tool["text"])
            text.setWordWrap(True)
            text.setAlignment(Qt.AlignCenter)
            text.setStyleSheet("font-weight: bold; font-size: 12px;")
            layout.addWidget(text)

            # Make the card clickable (simplified for now, ideally use a custom class)
            btn = QPushButton()
            btn.setParent(card)
            btn.setGeometry(0, 0, 180, 145)
            btn.setStyleSheet("background: transparent; border: none;")
            btn.clicked.connect(tool["cmd"])

            grid.addWidget(card, i // 3, i % 3)

            if tool.get("show_status"):
                self.lbl_shader_status = QLabel("...")
                self.lbl_shader_status.setStyleSheet("font-size: 9px; color: gray;")
                layout.addWidget(self.lbl_shader_status)
                self.app.logic.update_shader_status_label(self.app)
