from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QScrollArea, QFrame, QGridLayout)
from PySide6.QtCore import Qt, Signal
from src import constants as c
from src.utils.voxel_icons import tool_icon
from src.core.ui_utils import FlowLayout


class ClickableCard(QFrame):
    """QFrame that emits clicked when the user presses it with the left button."""
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ToolsTab(QWidget):
    """Tools tab displaying grouped utility buttons for management, customization, files, and system tasks."""
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(c.SECTION_PADDING, 5, c.SECTION_PADDING, c.SECTION_PADDING)

        # Header — FlowLayout so pills wrap on narrow windows
        self.header_layout = FlowLayout()
        self.main_layout.addLayout(self.header_layout)

        self.lbl_tools_status = QLabel("")
        self.lbl_tools_status.setObjectName("IndicatorPill")
        self.lbl_tools_status.setStyleSheet("font-size: 12px;")
        self.header_layout.addWidget(self.lbl_tools_status)

        self.lbl_current_profile = QLabel("")
        self.lbl_current_profile.setObjectName("IndicatorPill")
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
        self.scroll_layout.setSpacing(16)

        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

        self.lbl_shader_status = None
        self.refresh_tools_ui()

    def retranslate_ui(self):
        self.lbl_tools_status.setText("")
        current = self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.t("UI_PROFILE_DEFAULT"))
        self.lbl_current_profile.setText(f"👤 {c.t('UI_LABEL_PROFILE')} {current}")
        self.refresh_tools_ui()

    def _accent(self):
        theme = self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
        return c.THEME_COLOR_MAP.get(theme, "#1f6aa5")

    def get_tools_data(self):
        """Return the grouped tool definitions with icons, labels, and callbacks."""
        groups = [
            {
                "title": c.t("UI_SECTION_INSTALL"),
                "icon_kind": "download",
                "tools": [
                    {"text": c.t("UI_BUTTON_INSTALL_APK"), "kind": "download",
                     "desc": c.t("UI_TOOL_DESC_INSTALL_APK"),
                     "cmd": self.app.install_apk_dialog},
                    {"text": c.t("UI_BUTTON_MIGRATE_DATA"), "kind": "swap",
                     "desc": c.t("UI_TOOL_DESC_MIGRATE_DATA"),
                     "cmd": self.app.open_migration_tool},
                    {"text": c.t("UI_BUTTON_VERSION_MANAGER"), "kind": "list",
                     "desc": c.t("UI_TOOL_DESC_VERSION_MANAGER"),
                     "cmd": self.app.open_version_manager},
                ]
            },
            {
                "title": c.t("UI_SECTION_CONTENT"),
                "icon_kind": "cube",
                "tools": [
                    {"text": c.t("UI_BUTTON_ADDON_MANAGER"), "kind": "cube",
                     "desc": c.t("UI_TOOL_DESC_ADDON_MANAGER"),
                     "cmd": self.app.open_addon_manager},
                    {"text": c.t("UI_BUTTON_SKIN_PACK_CREATOR"), "kind": "shirt",
                     "desc": c.t("UI_TOOL_DESC_SKIN_PACK_CREATOR"),
                     "cmd": self.app.open_skin_tool},
                    {"text": c.t("UI_BUTTON_OPEN_SCREENSHOTS"), "kind": "camera",
                     "desc": c.t("UI_TOOL_DESC_OPEN_SCREENSHOTS"),
                     "cmd": lambda: self.app.logic.export_screenshots_dialog(self.app)},
                ]
            },
            {
                "title": c.t("UI_SECTION_CONFIGURATION"),
                "icon_kind": "sliders",
                "tools": [
                    {"text": c.t("UI_BUTTON_GAME_CONFIG"), "kind": "sliders",
                     "desc": c.t("UI_TOOL_DESC_GAME_CONFIG"),
                     "cmd": self.app.open_game_config_tool},
                    {"text": c.t("UI_BUTTON_DISABLE_SHADERS"), "kind": "sparkle",
                     "desc": c.t("UI_TOOL_DESC_DISABLE_SHADERS"),
                     "cmd": lambda: self.app.logic.disable_shaders(self.app),
                     "show_status": True},
                    {"text": c.t("UI_BUTTON_OPEN_DATA_FOLDER"), "kind": "folder",
                     "desc": c.t("UI_TOOL_DESC_OPEN_DATA_FOLDER"),
                     "cmd": lambda: self.app.logic.open_data_folder(self.app)},
                ]
            },
            {
                "title": c.t("UI_SECTION_SYSTEM"),
                "icon_kind": "shield",
                "tools": [
                    {
                        "text": c.t("UI_BUTTON_VERIFY_DEPS_FLATPAK") if self.app.running_in_flatpak else c.t("UI_BUTTON_VERIFY_DEPS_LOCAL"),
                        "kind": "plug",
                        "desc": c.t("UI_TOOL_DESC_VERIFY_DEPS"),
                        "cmd": lambda: self.app.logic.verify_dependencies(self.app)
                    },
                    {"text": c.t("UI_BUTTON_VERIFY_HW"), "kind": "search",
                     "desc": c.t("UI_TOOL_DESC_VERIFY_HW"),
                     "cmd": lambda: self.app.logic.check_requirements_dialog(self.app)},
                    {"text": c.t("UI_LABEL_COMPATIBLE_RANGE"), "kind": "shield",
                     "desc": c.t("UI_TOOL_DESC_COMPATIBLE_RANGE"),
                     "cmd": None, "show_compat": True}
                ]
            }
        ]
        return groups

    def _muted(self):
        return "#aaaaaa" if self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark") == "Dark" else "#404040"

    def refresh_tools_ui(self):
        """Rebuild the tools area, honoring the current layout style (columns or grid)."""
        from src.core.ui_utils import clear_layout
        clear_layout(self.scroll_layout)

        self.lbl_shader_status = None
        layout_style = self.app.config.get(c.CONFIG_KEY_TOOLS_LAYOUT, c.STYLE_COLUMNS)
        groups = self.get_tools_data()

        if layout_style == c.STYLE_GRID:
            self._render_grid(groups)
        else:  # COLUMNS
            self._render_columns(groups)

        # Footer Credits
        footer = QLabel(c.t("CREDITOS"))
        footer.setStyleSheet(f"color: {self._muted()}; font-size: 11px;")
        footer.setAlignment(Qt.AlignCenter)
        self.scroll_layout.addWidget(footer)

    def _group_header(self, group):
        """Return a centered group header row with a vector icon and title."""
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        h.setAlignment(Qt.AlignCenter)

        icon = QLabel()
        icon.setPixmap(tool_icon(group["icon_kind"], self._accent(), 26).pixmap(26, 26))
        h.addWidget(icon)

        title = QLabel(group["title"])
        title.setObjectName("HeaderLabel")
        title.setAlignment(Qt.AlignCenter)
        title.setFixedHeight(32)
        h.addWidget(title)
        return row

    def _make_status_badge(self, dot_color, text):
        """Return (container, text_label) for a status badge with a colored dot."""
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.setAlignment(Qt.AlignCenter)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {dot_color}; font-size: 12px; background: transparent;")
        h.addWidget(dot)

        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {dot_color}; font-size: 11px; font-weight: bold; background: transparent;")
        lbl.setAlignment(Qt.AlignCenter)
        h.addWidget(lbl)
        return container, lbl

    def _attach_status_badge(self, tool, card_layout):
        """Add a status badge to the card based on the tool's status type."""
        if tool.get("show_compat"):
            range_text = self.app.logic.get_compatibility_range(self.app)
            container, _lbl = self._make_status_badge(c.COLOR_PRIMARY_GREEN, range_text)
            card_layout.addWidget(container)
            return

        if tool.get("show_drm_status"):
            status = self.app.logic.get_drm_mod_status(self.app)
            colors = {
                "installed": c.COLOR_PRIMARY_GREEN,
                "disabled": c.COLOR_YELLOW_BUTTON,
                "missing": c.COLOR_RED_BUTTON,
            }
            texts = {
                "installed": c.t("UI_DRM_MOD_STATUS_INSTALLED"),
                "disabled": c.t("UI_DRM_MOD_STATUS_DISABLED"),
                "missing": c.t("UI_DRM_MOD_STATUS_MISSING"),
            }
            container, _lbl = self._make_status_badge(
                colors.get(status, "#888888"), texts.get(status, status))
            card_layout.addWidget(container)
            return

        if tool.get("show_status"):  # shaders
            container, lbl = self._make_status_badge(c.COLOR_PRIMARY_GREEN, c.t("UI_LABEL_SHADERS_STATUS"))
            self.lbl_shader_status = lbl
            card_layout.addWidget(container)
            self.app.logic.update_shader_status_label(self.app)

    def _create_tool_card(self, parent_layout, tool, fixed_size=None):
        """Build a unified tool card (vector icon, title, micro-copy, optional status badge)."""
        card = ClickableCard()
        card.setObjectName("ToolCard")
        if fixed_size:
            card.setFixedSize(*fixed_size)
        else:
            card.setMinimumHeight(150)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 14, 12, 12)
        lay.setSpacing(6)
        lay.setAlignment(Qt.AlignCenter)

        icon = QLabel()
        icon.setPixmap(tool_icon(tool.get("kind", "block"), self._accent(), 40).pixmap(40, 40))
        icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon)

        title = QLabel(tool["text"])
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 12px; background: transparent;")
        lay.addWidget(title)

        if tool.get("desc"):
            d = QLabel(tool["desc"])
            d.setWordWrap(True)
            d.setAlignment(Qt.AlignCenter)
            d.setStyleSheet(f"font-size: 10px; color: {self._muted()}; background: transparent;")
            lay.addWidget(d)

        self._attach_status_badge(tool, lay)

        if tool.get("cmd"):
            card.setCursor(Qt.PointingHandCursor)
            card.clicked.connect(tool["cmd"])

        if parent_layout is not None:
            parent_layout.addWidget(card)
        return card

    def _render_columns(self, groups):
        grid = QGridLayout()
        grid.setSpacing(16)
        self.scroll_layout.addLayout(grid)

        for i, group in enumerate(groups):
            frame = QFrame()
            frame.setObjectName("GroupFrame")
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(15, 13, 15, 13)
            layout.setSpacing(10)

            layout.addWidget(self._group_header(group))

            for tool in group["tools"]:
                self._create_tool_card(layout, tool)

            layout.addStretch(1)

            grid.addWidget(frame, i // 2, i % 2)

    def _render_grid(self, groups):
        grid = QGridLayout()
        grid.setSpacing(16)
        self.scroll_layout.addLayout(grid)

        all_tools = []
        for group in groups:
            for tool in group["tools"]:
                all_tools.append(tool)

        card_w = max(170, self.width() // 3 - 24)
        card_h = 170
        for i, tool in enumerate(all_tools):
            card = self._create_tool_card(None, tool, fixed_size=(card_w, card_h))
            grid.addWidget(card, i // 3, i % 3)
