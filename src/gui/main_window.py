from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QTabWidget, QPushButton, QFrame, QScrollArea,
                             QComboBox, QApplication, QSystemTrayIcon, QMenu,
                             QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPainterPath, QAction
import os
import re
import sys
import time



from src import constants as c
from src.utils.resource_path import resource_path
from src.utils.image_manager import ImageManager
from src.core.config_manager import ConfigManager
from src.core import language_manager
from src.gui import custom_dialogs as messagebox
from src.gui.install_dialog import InstallDialog
from src.gui.skin_pack_tool import SkinPackTool
from src.gui.addon_manager_dialog import AddonManagerDialog
from src.gui.migration_wizard import MigrationWizard
from src.gui.game_config_dialog import GameConfigDialog
from src.core import app_logic
from src.core.discord_rpc import DiscordRPC
from src.core.update_checker import UpdateChecker
from src.gui.tabs.play_tab import PlayTab
from src.gui.tabs.tools_tab import ToolsTab
from src.gui.tabs.settings_tab import SettingsTab
from src.gui.tabs.about_tab import AboutTab
from src.gui.tabs.logs_tab import LogsTab
from src.utils.logger import logger

class VisualLabel(QLabel):
    """A transparent overlay label used for background and sticker display."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent; border: none;")

class CianovaLauncherApp(QMainWindow):
    """Main application window managing tabs, theming, and top-level logic."""
    def __init__(self, launcher_path=".", force_flatpak_ui=False, force_nvidia_ui=False):
        super().__init__()

        logger.info("Initializing Main Window...")
        self.logic = app_logic
        self.launcher_path = launcher_path
        self.home = c.HOME_DIR
        self.force_flatpak_ui = force_flatpak_ui
        self.force_nvidia_ui = force_nvidia_ui

        self.running_in_flatpak = self.logic.is_running_in_flatpak() or self.force_flatpak_ui

        self.our_flatpak_id = self.logic.get_flatpak_app_id() if self.running_in_flatpak else None

        if self.running_in_flatpak:
            app_id = self.our_flatpak_id if self.our_flatpak_id else c.DEFAULT_FLATPAK_ID
            self.our_data_path = os.path.join(self.home, f"{c.FLATPAK_DATA_DIR}/{app_id}/{c.MCPELAUNCHER_DATA_SUBDIR}")
            self.compiled_path = self.our_data_path
            self.flatpak_path = os.path.join(self.home, f"{c.FLATPAK_DATA_DIR}/{c.MCPELAUNCHER_FLATPAK_ID}/{c.MCPELAUNCHER_DATA_SUBDIR}")
        else:
            self.flatpak_path = os.path.join(self.home, f"{c.FLATPAK_DATA_DIR}/{c.MCPELAUNCHER_FLATPAK_ID}/{c.MCPELAUNCHER_DATA_SUBDIR}")
            self.compiled_path = os.path.join(self.home, c.LOCAL_SHARE_DIR)

        self.active_path = None
        self.is_flatpak = False
        self.version_cards = {}
        self._bg_cache = {"path": None, "pixmap": None}
        self._sticker_cache = {"path": None, "pixmap": None, "zoom": None}
        self._last_qss_params = None

        # Config
        if self.running_in_flatpak:
            app_id = self.our_flatpak_id if self.our_flatpak_id else c.DEFAULT_FLATPAK_ID
            data_dir = os.path.join(self.home, f"{c.FLATPAK_DATA_DIR}/{app_id}/data")
            config_path = os.path.join(data_dir, c.CONFIG_FILE_NAME)
            old_config_path = os.path.join(self.compiled_path, c.OLD_CONFIG_FILE_NAME)
        else:
            config_path = os.path.join(self.compiled_path, c.CONFIG_FILE_NAME)
            old_config_path = os.path.join(self.compiled_path, c.OLD_CONFIG_FILE_NAME)

        self.config_manager = ConfigManager(config_path, old_config_file=old_config_path)
        self.config = self.config_manager.config

        # Lang
        lang = self.config.get(c.CONFIG_KEY_LANGUAGE, "en")
        language_manager.load_language(lang)

        # UI Setup
        self.setWindowTitle(c.t("UI_TITLE_VERSION"))
        size_str = self.config.get(c.CONFIG_KEY_WINDOW_SIZE, "700x550")
        try:
            w, h = map(int, size_str.split('x'))
            self.resize(w, h)
        except (ValueError, AttributeError) as e:
            logger.debug(f"Invalid window size '{size_str}', using default: {e}")
            self.resize(700, 550)
        self.setMinimumSize(600, 450)

        self.setWindowIcon(ImageManager.get_icon("icon.png"))

        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("MainTabs")
        self.tab_widget.setDocumentMode(True)
        # Native drawBase line renders as a dark horizontal line above the
        # tab bar in light mode; the QSS already styles the tabs, so disable it.
        self.tab_widget.tabBar().setDrawBase(False)
        self.main_layout.addWidget(self.tab_widget)

        self.play_tab = PlayTab(self.tab_widget, self)
        self.play_tab.setObjectName("PlayTab")
        self.tools_tab = ToolsTab(self.tab_widget, self)
        self.tools_tab.setObjectName("ToolsTab")
        self.settings_tab = SettingsTab(self.tab_widget, self)
        self.settings_tab.setObjectName("SettingsTab")
        self.about_tab = AboutTab(self.tab_widget, self)
        self.about_tab.setObjectName("AboutTab")
        self.logs_tab = LogsTab(self.tab_widget, self)
        self.logs_tab.setObjectName("LogsTab")

        self.tab_widget.addTab(self.play_tab, c.t("UI_TAB_PLAY"))
        self.tab_widget.addTab(self.tools_tab, c.t("UI_TAB_TOOLS"))
        self.tab_widget.addTab(self.settings_tab, c.t("UI_TAB_SETTINGS"))
        self.tab_widget.addTab(self.about_tab, c.t("UI_TAB_ABOUT"))
        self.tab_widget.addTab(self.logs_tab, c.t("UI_TAB_LOGS"))

        # Visuals (BG and Sticker)
        self.bg_label = VisualLabel(self.central_widget)
        self.bg_label.setScaledContents(True)
        self.sticker_label = VisualLabel(self.central_widget)
        self.game_status_label = VisualLabel(self.central_widget)
        self.game_status_label.setStyleSheet(
            "background-color: rgba(0,0,0,0.75); color: #4CAF50; "
            "font-size: 12px; font-weight: bold; padding: 4px 10px; "
            "border-radius: 10px;"
        )
        self.game_status_label.hide()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # Debounce timer for personalization and resizing
        self.personalization_timer = QTimer()
        self.personalization_timer.setSingleShot(True)
        self.personalization_timer.setInterval(50) # 50ms debounce
        self.personalization_timer.timeout.connect(self._apply_debounced_personalization)

        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(50) # 50ms for resize debounce (smoother tracking)
        self.resize_timer.timeout.connect(self._handle_resize_finished)

        # Logic init
        self.logic.detect_installation(self)
        if self.running_in_flatpak:
            self.logic.setup_flatpak_environment(self)
            self.logic.check_migration_needed(self)

        # Discord Rich Presence (lazy start on first show)
        self._discord_rpc = DiscordRPC(self)
        if self.config.get(c.CONFIG_KEY_DISCORD_RPC_ENABLED, False):
            self._discord_rpc.start()
            self._discord_rpc.set_idle()

        # Game process monitoring
        self._game_process = None
        self._game_monitor = QTimer()
        self._game_monitor.setInterval(2000)
        self._game_monitor.timeout.connect(self._check_game_process)

        # System Tray
        self._tray_icon = None
        self._setup_tray_icon()

        # Apply initial theme settings
        self.apply_theme_settings()
        self.update_floating_labels()

        # Process args
        if "--version" in sys.argv:
            try:
                idx = sys.argv.index("--version")
                if idx + 1 < len(sys.argv):
                    target_version = sys.argv[idx + 1]
                    QTimer.singleShot(500, lambda: self.logic.launch_from_args(self, target_version))
            except Exception as e:
                logger.warning(f"Failed to handle --version argument: {e}")

    def resizeEvent(self, event):
        self.resize_timer.start()
        super().resizeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._handle_first_show_layout)

    def _handle_first_show_layout(self):
        """Recompute the tab bar alignment once the window is laid out on first show."""
        self._update_tab_bar_qss()
        self.update_background()
        self.update_sticker()
        self.update_floating_labels()

    def _handle_resize_finished(self):
        size = f"{self.width()}x{self.height()}"
        self.config_manager.set(c.CONFIG_KEY_WINDOW_SIZE, size)
        self.update_background()
        self.update_sticker()
        self.update_floating_labels()
        self._update_tab_bar_qss()
        if self.game_status_label.isVisible():
            w = self.width() - self.game_status_label.width() - 20
            y = self.tab_widget.tabBar().height() + 14
            self.game_status_label.move(w, y)

    def _update_tab_bar_qss(self):
        """Recompute the tab bar width so it stays aligned after a resize."""
        inset = c.SECTION_PADDING
        width = max(120, self.tab_widget.width() - 2 * inset)
        block = (
            f"QTabWidget#MainTabs::tab-bar {{\n"
            f"                top: 0px;\n"
            f"                left: {inset}px;\n"
            f"                width: {width}px;\n"
            f"                border: none;\n"
            f"            }}"
        )
        app = QApplication.instance()
        ss = app.styleSheet()
        new_ss, n = re.subn(r"QTabWidget#MainTabs::tab-bar\s*\{[^}]*\}", lambda m: block, ss, count=1)
        if n and new_ss != ss:
            app.setStyleSheet(new_ss)

    def update_sticker_visibility(self, index):
        """Show or hide the sticker based on the current tab index."""
        # Sticker visible in Play (0) and Tools (1)
        self.sticker_label.setVisible(index in [0, 1])

    def on_tab_changed(self, index):
        """Handle tab change - update sticker visibility"""
        self.update_sticker_visibility(index)

        # Clear some caches to save RAM when not in specific tabs
        if index != 0: # Not in Play tab
            # We don't clear version_cards yet as they are recreated on refresh anyway,
            # but we could potentially hide them or clear their pixmaps if RAM is critical.
            pass

    def update_background(self):
        """Update the background image position, zoom, and opacity from config."""
        bg_path = self.config.get(c.CONFIG_KEY_BG_PATH)
        if not bg_path or not os.path.exists(bg_path):
            self.bg_label.clear()
            self.bg_label.hide()
            return

        try:
            if self._bg_cache["path"] == bg_path:
                pix = self._bg_cache["pixmap"]
            else:
                pix = QPixmap(bg_path)
                if pix.isNull(): return
                self._bg_cache["path"] = bg_path
                self._bg_cache["pixmap"] = pix

            zoom = self.config.get(c.CONFIG_KEY_BG_ZOOM, 100) / 100.0
            opacity = self.config.get(c.CONFIG_KEY_BG_OPACITY, 100) / 100.0
            x_off = self.config.get(c.CONFIG_KEY_BG_X, 0)
            y_off = self.config.get(c.CONFIG_KEY_BG_Y, 0)

            w, h = int(pix.width() * zoom), int(pix.height() * zoom)
            if self.bg_label.pixmap() != pix:
                self.bg_label.setPixmap(pix)

            if self.bg_label.width() != w or self.bg_label.height() != h:
                self.bg_label.setFixedSize(w, h)

            self.bg_label.move(x_off, y_off)
            if self.bg_label.isHidden():
                self.bg_label.show()

            # Opacity - avoid creating new effect if possible
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            effect = self.bg_label.graphicsEffect()
            if not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(self.bg_label)
                self.bg_label.setGraphicsEffect(effect)

            if effect.opacity() != opacity:
                effect.setOpacity(opacity)

            self.bg_label.lower()
        except Exception as e:
            logger.debug(f"Failed to apply background opacity effect: {e}")

    def update_sticker(self):
        """Update the sticker (image or text) based on current configuration."""
        mode = self.config.get(c.CONFIG_KEY_STICKER_MODE, "none")
        if mode == "none":
            self.sticker_label.clear()
            self.sticker_label.hide()
            return

        content = self.config.get(c.CONFIG_KEY_STICKER_CONTENT, "")
        opacity = self.config.get(c.CONFIG_KEY_STICKER_OPACITY, 100) / 100.0
        corner = self.config.get(c.CONFIG_KEY_STICKER_CORNER, "bottom-right")
        x_dist = self.config.get(c.CONFIG_KEY_STICKER_X, 10)
        y_dist = self.config.get(c.CONFIG_KEY_STICKER_Y, 10)
        zoom = self.config.get(c.CONFIG_KEY_STICKER_ZOOM, 100) / 100.0

        if mode == "image":
            if not os.path.exists(content):
                self.sticker_label.clear()
                self.sticker_label.hide()
                return

            if (self._sticker_cache["path"] == content and
                self._sticker_cache["zoom"] == zoom and
                self._sticker_cache["pixmap"] is not None):
                pix = self._sticker_cache["pixmap"]
            else:
                pix = QPixmap(content)
                if not pix.isNull():
                    if zoom != 1.0:
                        pix = pix.scaled(int(pix.width() * zoom), int(pix.height() * zoom),
                                        Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self._sticker_cache["path"] = content
                    self._sticker_cache["zoom"] = zoom
                    self._sticker_cache["pixmap"] = pix

            if pix and not pix.isNull():
                self.sticker_label.setPixmap(pix)
                self.sticker_label.setFixedSize(pix.size())
                self.sticker_label.show()
            else:
                self.sticker_label.hide()
                return
        elif mode == "text":
            self.sticker_label.clear()
            self.sticker_label.setText(content)
            self.sticker_label.setStyleSheet(f"color: white; font-weight: bold; font-size: {int(16 * zoom)}px; background: transparent; border: none;")
            self.sticker_label.adjustSize()
            self.sticker_label.show()
        else:
            self.sticker_label.hide()
            return

        self.update_sticker_visibility(self.tab_widget.currentIndex())

        # Position based on corner
        w, h = self.width(), self.height()
        sw, sh = self.sticker_label.width(), self.sticker_label.height()

        if corner == "top-left": self.sticker_label.move(x_dist, y_dist)
        elif corner == "top-right": self.sticker_label.move(w - sw - x_dist, y_dist)
        elif corner == "bottom-left": self.sticker_label.move(x_dist, h - sh - y_dist)
        else: self.sticker_label.move(w - sw - x_dist, h - sh - y_dist)

        # Opacity - reuse effect
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        effect = self.sticker_label.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(self.sticker_label)
            self.sticker_label.setGraphicsEffect(effect)

        if effect.opacity() != opacity:
            effect.setOpacity(opacity)

        self.sticker_label.raise_()

    def restore_default_settings(self):
        """Restore all settings to factory defaults after user confirmation."""
        if messagebox.askyesno(self, c.t("UI_CONFIRM_TITLE"), c.t("UI_RESTORE_DEFAULTS_CONFIRM")):
            self.config_manager.restore_defaults()
            messagebox.showinfo(self, c.t("UI_RESTORE_DEFAULTS_SUCCESS_TITLE"), c.t("UI_RESTORE_DEFAULTS_SUCCESS_MSG"))
            self.close()

    def change_appearance(self, type_change, value):
        """Change a visual setting (e.g. color theme) and update the UI."""
        if type_change == "color":
            self.config_manager.set(c.CONFIG_KEY_COLOR_THEME, value)
            # Dynamic color change is complex with current QSS setup, usually requires reload
            messagebox.showinfo(self, c.t("UI_RESTART_REQUIRED_TITLE"), c.t("UI_RESTART_MSG"))
            return
        self.config_manager.save_config()
        self.apply_theme_settings()

    def apply_theme_settings(self):
        """Apply global theme settings using selectors to avoid re-applying QSS on tab change."""
        mode = self.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        theme_color = self.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
        accent = c.THEME_COLOR_MAP.get(theme_color, "#1f6aa5")
        section_opacity_val = self.config.get(c.CONFIG_KEY_SECTION_OPACITY, 100)
        bg_path = self.config.get(c.CONFIG_KEY_BG_PATH)
        has_bg = bool(bg_path and os.path.exists(bg_path))

        # Update visuals regardless of QSS cache
        self.update_background()
        self.update_sticker()

        # Optimization: skip reapplying the exact same QSS
        params = (mode, theme_color, section_opacity_val, has_bg)
        if self._last_qss_params == params:
            return
        self._last_qss_params = params

        bg = "#242424" if mode == "Dark" else "#eef1f5"
        text = "#DCE4EE" if mode == "Dark" else "#1a1a1a"
        tab_bg = "#333333" if mode == "Dark" else "#cfd6e0"

        # Tab bar inset to match the content panels below (SECTION_PADDING each side)
        tab_inset = c.SECTION_PADDING
        tab_bar_width = max(120, self.tab_widget.width() - 2 * tab_inset)

        input_bg = "#2a2a2a" if mode == "Dark" else "#ffffff"
        input_text = "#ffffff" if mode == "Dark" else "#1a1a1a"
        input_border = "#555555" if mode == "Dark" else "#c1c9d4"

        section_opacity = section_opacity_val / 100.0
        from src.utils.colors import hex_to_rgba, adjust_color

        frame_bg_base = "#3a3a3a" if mode == "Dark" else "#e8e8e8"
        frame_bg_opaque = hex_to_rgba(frame_bg_base, 1.0)
        
        # Section opacity should only affect Settings and Tools tabs
        frame_bg_transparent = hex_to_rgba(frame_bg_base, section_opacity)

        # Tool cards get a more solid background so they read as buttons even
        # when section opacity is low, plus an accent-tinted hover "illumination"
        # in both themes so the accent color clearly shows on mouse over.
        tool_card_bg = hex_to_rgba(frame_bg_base, max(section_opacity, 0.92))
        _base = QColor(frame_bg_base)
        _acc = QColor(accent)
        if mode == "Dark":
            # Dark: keep most of the base but add a clear accent glow.
            _hr = int(_base.red() * 0.82 + _acc.red() * 0.18)
            _hg = int(_base.green() * 0.82 + _acc.green() * 0.18)
            _hb = int(_base.blue() * 0.82 + _acc.blue() * 0.18)
        else:
            # Light: a softer accent tint so it reads as a warm highlight.
            _hr = int(_base.red() * 0.85 + _acc.red() * 0.15)
            _hg = int(_base.green() * 0.85 + _acc.green() * 0.15)
            _hb = int(_base.blue() * 0.85 + _acc.blue() * 0.15)
        tool_card_hover_bg = QColor(_hr, _hg, _hb).name()
        tool_card_hover_border = hex_to_rgba(accent, 0.85)

        if has_bg:
            bg_qss = f"background: transparent;"
        else:
            bg_qss = f"background-color: {bg};"

        # Background image rendered inside Play/Tools scroll content so the
        # configured background stays visible behind the version list/cards.
        if has_bg:
            bg_path_escaped = bg_path.replace("\\", "/").replace('"', '\\"')
            bg_image_qss = (
                f'background-image: url("{bg_path_escaped}");\n'
                f"                background-repeat: no-repeat;\n"
                f"                background-position: center;\n"
            )
        else:
            bg_image_qss = ""

        # Generate down-arrow pixmap for QComboBox (stylesheets suppress native arrow)
        arrow_size = 12
        arrow_path = os.path.join(c.HOME_DIR, ".local", "share", "cianovalauncher", "combo_arrow.png")
        os.makedirs(os.path.dirname(arrow_path), exist_ok=True)
        arrow_pixmap = QPixmap(arrow_size, arrow_size)
        arrow_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(arrow_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.moveTo(arrow_size // 2, arrow_size - 1)
        path.lineTo(1, 2)
        path.lineTo(arrow_size - 1, 2)
        path.closeSubpath()
        painter.fillPath(path, QColor(input_text))
        painter.end()
        arrow_pixmap.save(arrow_path)

        # Fixed semi-transparent background for floating labels
        floating_label_bg = hex_to_rgba("#555555" if mode == "Dark" else "#dddddd", 0.85)
        floating_label_border = f"1px solid {hex_to_rgba('#ffffff' if mode == 'Dark' else '#000000', 0.25)}"

        # Accent-tinted "pill" style for header indicators (status, profile,
        # installation, mode, section titles). Reads clearly in both themes.
        pill_bg = hex_to_rgba(accent, 0.16) if mode == "Dark" else hex_to_rgba(accent, 0.10)
        pill_border = f"1px solid {hex_to_rgba(accent, 0.55)}"
        pill_text = text if mode == "Dark" else "#1a1a1a"

        qss = f"""
            QMainWindow, QWidget#centralWidget {{
                {bg_qss}
                color: {text};
                font-family: 'Roboto', 'Segoe UI', sans-serif;
            }}
            QLabel {{
                color: {text};
            }}
            QDialog {{
                background-color: {bg};
            }}
            #VersionManagerDialog, #InstallDialog, #AddonManagerDialog, #MigrationDialog, #GameConfigDialog {{
                background-color: {bg};
            }}
            QTabWidget::pane {{
                border: 1px solid {hex_to_rgba(input_border, 0.4)};
                background: transparent;
                border-radius: {c.CORNER_RADIUS}px;
                top: -1px;
            }}
            QTabBar {{
                alignment: center;
                background: {tab_bg};
                border-radius: {c.CORNER_RADIUS}px;
                padding: 2px;
                border: none;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {text};
                padding: 10px 25px;
                border-radius: {c.RADIUS_BUTTON}px;
                font-weight: bold;
                margin: 2px;
                border: none;
                outline: none;
            }}
            QTabBar::tab:selected {{
                background: {accent};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: {hex_to_rgba("#ffffff" if mode == "Dark" else "#000000", 0.08)};
            }}
            QTabWidget#MainTabs::tab-bar {{
                top: 0px;
                left: {tab_inset}px;
                width: {tab_bar_width}px;
                border: none;
            }}
            QPushButton {{
                background-color: {accent};
                color: white;
                border: 1px solid {accent};
                border-radius: {c.RADIUS_BUTTON}px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {adjust_color(accent, 25)};
                border: 1px solid {adjust_color(accent, 25)};
            }}
            QPushButton:pressed {{
                background-color: {adjust_color(accent, -15)};
                border: 1px solid {adjust_color(accent, -15)};
            }}
            QPushButton:disabled {{
                background-color: {"#444444" if mode == "Dark" else "#dcdce0"};
                color: {"#666666" if mode == "Dark" else "#9a9aa0"};
                border: 1px solid {"#444444" if mode == "Dark" else "#c8c8cd"};
            }}
            QPushButton:flat {{
                background-color: {accent};
                color: white;
                border: none;
            }}
            QPushButton:flat:disabled {{
                background-color: {"#444444" if mode == "Dark" else "#dcdce0"};
                color: {"#666666" if mode == "Dark" else "#9a9aa0"};
                border: none;
            }}
            QLineEdit, QComboBox, QSpinBox, QTextEdit {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: {c.RADIUS_INPUT}px;
                padding: 6px 8px;
            }}
            QComboBox::drop-down {{ 
                border: none; 
                width: 25px; 
                border-top-right-radius: {c.RADIUS_INPUT}px;
                border-bottom-right-radius: {c.RADIUS_INPUT}px;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: url("{arrow_path}");
                width: {arrow_size}px;
                height: {arrow_size}px;
                margin-right: 4px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                selection-background-color: {accent};
                selection-color: white;
                border-radius: {c.RADIUS_INPUT}px;
                padding: 2px;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 30px;
                padding: 4px 8px;
                border-radius: {c.RADIUS_TINY}px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {hex_to_rgba(accent, 0.3)};
            }}
            QCheckBox, QRadioButton {{
                color: {text};
                spacing: 6px;
            }}
            QCheckBox::indicator, QRadioButton::indicator {{
                width: 18px; height: 18px; border-radius: {c.RADIUS_TINY}px;
                border: 2px solid {accent}; background: {input_bg};
            }}
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
                background: {accent};
            }}
            QPushButton#PlayButton, QPushButton#SaveButton, QPushButton#ActionButton {{
                background-color: {accent};
                color: white;
                border-radius: {c.CORNER_RADIUS}px;
                font-size: 16px;
                font-weight: bold;
                border: 1px solid rgba(255,255,255,0.2);
            }}
            QPushButton#PlayButton:hover, QPushButton#SaveButton:hover, QPushButton#ActionButton:hover {{
                background-color: {adjust_color(accent, 20)};
            }}
            QPushButton#PlayButton:disabled, QPushButton#SaveButton:disabled, QPushButton#ActionButton:disabled {{
                background-color: {"#444444" if mode == "Dark" else "#dcdce0"};
                color: {"#888888" if mode == "Dark" else "#9a9aa0"};
                border: 1px solid {"#444444" if mode == "Dark" else "#c8c8cd"};
            }}
            QPushButton#ToolButton {{
                background-color: {accent};
                color: white;
                border: none;
                border-radius: {c.RADIUS_BUTTON}px;
                font-weight: bold;
                min-width: 22px;
                min-height: 22px;
            }}
            QPushButton#ToolButton:hover {{
                background-color: {adjust_color(accent, 20)};
            }}
            QPushButton#ToolButton:disabled {{
                background-color: {"#444444" if mode == "Dark" else "#dcdce0"};
                color: {"#888888" if mode == "Dark" else "#9a9aa0"};
            }}
            QFrame#ToolCard, QFrame#GroupFrame, QFrame#VersionCard {{
                border-radius: {c.CORNER_RADIUS}px;
                border: 1px solid {hex_to_rgba(input_border, 0.5)};
                background-color: {frame_bg_opaque};
            }}

            #PlayTab QFrame#GroupFrame, #PlayTab QFrame#VersionCard, #AboutTab QFrame#GroupFrame {{
                background-color: {frame_bg_opaque};
            }}

            #SettingsTab, #LogsTab {{
                background-color: {bg};
            }}
            #PlayTab, #ToolsTab {{
                background-color: transparent;
            }}
            #SettingsTab QStackedWidget, #SettingsTab QStackedWidget > QWidget {{
                background-color: {bg};
            }}
            #AboutTab {{
                background-color: {frame_bg_opaque};
            }}

            #ToolsTab QFrame#GroupFrame, #ToolsTab QFrame#ToolCard,
            #SettingsTab QFrame#GroupFrame {{
                background-color: {frame_bg_transparent};
            }}

            #ToolsTab QFrame#ToolCard {{
                background-color: {tool_card_bg};
            }}

            QScrollArea#GroupFrame {{
                background-color: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget#SettingsPageContent {{
                background-color: {bg};
            }}
            #PlayTab QScrollArea > QWidget > QWidget#VersionList,
            #ToolsTab QScrollArea > QWidget > QWidget#ScrollContent {{
                background-color: {bg};
                {bg_image_qss}
            }}
            #AboutTab QScrollArea {{
                background-color: {frame_bg_opaque};
            }}
            #AboutTab QScrollArea > QWidget > QWidget#ScrollContent {{
                background-color: {frame_bg_opaque};
            }}
            #SettingsTab QScrollArea {{
                background-color: {bg};
            }}
            #ToolsTab QFrame#ToolCard:hover, QFrame#VersionCard:hover,
            #ToolsTab QFrame#GroupFrame:hover {{
                border: 1px solid {tool_card_hover_border};
            }}
            #ToolsTab QFrame#ToolCard:hover {{
                background-color: {tool_card_hover_bg};
                border: 1px solid {accent};
            }}
            QLabel#HeaderLabel {{
                color: {accent};
                font-size: 18px;
                font-weight: bold;
                background: transparent;
                margin-bottom: 5px;
            }}
            QLabel#FloatingLabel {{
                background-color: {floating_label_bg};
                color: {text};
                padding: 5px 15px;
                border-radius: 4px;
                border: {floating_label_border};
                qproperty-alignment: 'AlignCenter';
            }}
            QLabel#IndicatorPill {{
                background-color: {pill_bg};
                color: {pill_text};
                padding: 4px 13px;
                border-radius: 13px;
                border: {pill_border};
                font-weight: bold;
                qproperty-alignment: 'AlignCenter';
            }}
            QSlider:horizontal {{
                min-height: 24px;
            }}
            QSlider::groove:horizontal {{
                background: {"#4a4a4a" if mode == "Dark" else "#c9c9c9"};
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
            QSlider::handle:horizontal:hover {{
                background: {adjust_color(accent, 20)};
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 3px;
            }}
            QComboBox::item:selected {{
                background-color: {accent};
                color: white;
            }}
            QScrollBar:vertical {{
                background: {tab_bg};
                width: 12px;
                margin: 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {accent};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {adjust_color(accent, 30)};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {tab_bg};
                height: 12px;
                margin: 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {accent};
                min-width: 20px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            /* ── Settings sidebar ── */
            QFrame#SettingsSidebar {{
                background-color: {hex_to_rgba(frame_bg_base, 0.5)};
                border-right: 1px solid {hex_to_rgba(input_border, 0.4)};
                border-top-left-radius: {c.CORNER_RADIUS}px;
                border-bottom-left-radius: {c.CORNER_RADIUS}px;
            }}
            QPushButton#SidebarButton {{
                background: transparent;
                color: {"#333333" if mode == "Light" else "#cccccc"};
                border: none;
                border-radius: 4px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: bold;
                text-align: left;
                min-width: 35px;
                min-height: 42px;
            }}
            QPushButton#SidebarButton:hover {{
                background: {"#d8d8d8" if mode == "Light" else "#333333"};
                color: {"#000000" if mode == "Light" else "white"};
            }}
            QPushButton#SidebarButton:disabled {{
                background: transparent;
                color: {"#9a9aa0" if mode == "Light" else "#666666"};
            }}
            QPushButton#SidebarButton[active="true"] {{
                background: {"#cccccc" if mode == "Light" else "#2a2a2a"};
                color: {accent};
                border-left: 4px solid {accent};
                border-radius: 0px;
            }}
            QPushButton#SidebarToggle {{
                background: transparent;
                color: {"#333333" if mode == "Light" else "#cccccc"};
                border: none;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
                min-height: 38px;
            }}
            QPushButton#SidebarToggle:hover {{
                background: {"#d8d8d8" if mode == "Light" else "#333333"};
                color: {"#000000" if mode == "Light" else "white"};
            }}
            QPushButton#SidebarToggle:disabled {{
                background: transparent;
                color: {"#9a9aa0" if mode == "Light" else "#666666"};
            }}
            /* ── QGroupBox in Settings ── */
            #SettingsTab QGroupBox {{
                border: 1px solid {hex_to_rgba(input_border, 0.35)};
                border-radius: 4px;
                margin-top: 1.5ex;
                padding: 18px 10px 10px 10px;
                background-color: {frame_bg_transparent};
            }}
            #SettingsTab QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: {text};
                font-weight: bold;
            }}
            #SettingsTab QGroupBox:hover {{
                border: 1px solid {accent};
            }}
            /* ── Settings footer bar ── */
            QFrame#SettingsFooterBar {{
                background-color: {frame_bg_opaque};
                border-top: 1px solid {hex_to_rgba(input_border, 0.4)};
            }}
            /* Generic scroll areas remain transparent */
            QScrollArea, QScrollArea > QWidget {{
                background: transparent;
                border: none;
            }}
        """
        try:
            QApplication.instance().setStyleSheet(qss)
        except Exception as e:
            logger.warning(f"Failed to apply global stylesheet: {e}")

        if hasattr(self, "settings_tab"):
            self.settings_tab._refresh_per_widget_styles()

        from src.core.install_ops import refresh_version_cards_theme
        try:
            refresh_version_cards_theme(self)
        except Exception:
            pass

        # Apply drop shadow to all card-type frames
        shadow_color = QColor(0, 0, 0, 60) if mode == "Dark" else QColor(0, 0, 0, 30)
        for frame in self.findChildren(QFrame):
            if frame.objectName() in ("GroupFrame", "ToolCard", "VersionCard"):
                existing = frame.graphicsEffect()
                if existing is None:
                    shadow = QGraphicsDropShadowEffect()
                    shadow.setBlurRadius(12)
                    shadow.setOffset(0, 2)
                    shadow.setColor(shadow_color)
                    frame.setGraphicsEffect(shadow)

    def _apply_debounced_personalization(self):
        self.apply_theme_settings()

    def update_floating_labels(self):
        """Hide or show floating status labels based on their text content."""
        # In PySide6, we can iterate over widgets to hide empty FloatingLabels
        for widget in self.findChildren(QLabel, "FloatingLabel") + self.findChildren(QLabel, "IndicatorPill"):
            text = widget.text().strip()
            # If it's a profile or install label, it might have icons/prefixes
            if not text or text in ["●", "👤", "● Searching...", "● Buscando..."]:
                if "Searching" not in text and "Buscando" not in text:
                    widget.hide()
                else:
                    widget.show()
            else:
                widget.show()

    def retranslate_all(self):
        self.setWindowTitle(c.t("UI_TITLE_VERSION"))
        self.tab_widget.setTabText(0, c.t("UI_TAB_PLAY"))
        self.tab_widget.setTabText(1, c.t("UI_TAB_TOOLS"))
        self.tab_widget.setTabText(2, c.t("UI_TAB_SETTINGS"))
        self.tab_widget.setTabText(3, c.t("UI_TAB_ABOUT"))
        self.tab_widget.setTabText(4, c.t("UI_TAB_LOGS"))
        for tab in (self.play_tab, self.tools_tab, self.settings_tab, self.about_tab, self.logs_tab):
            if hasattr(tab, "retranslate_ui"):
                tab.retranslate_ui()
        self.update_floating_labels()

    def show_info(self, title, msg):
        """Show an information dialog with the given title and message."""
        messagebox.showinfo(self, title, msg)

    # Tool openers
    def install_apk_dialog(self):
        """Open the APK installation dialog."""
        InstallDialog(self).exec()
    def open_skin_tool(self):
        """Open the skin pack creator tool."""
        SkinPackTool(self).exec()
    def open_migration_tool(self):
        """Open the data migration tool dialog."""
        try: MigrationWizard(self).exec()
        except Exception as e: messagebox.showerror(self, c.t("UI_ERROR_TITLE"), f"Error: {e}")
    def open_game_config_tool(self):
        """Open the Minecraft game options editor dialog."""
        try: GameConfigDialog(self).exec()
        except Exception as e: messagebox.showerror(self, c.t("UI_ERROR_TITLE"), f"Error: {e}")
    def open_addon_manager(self):
        """Open the addon (worlds, resource packs, behavior packs) manager dialog."""
        try: AddonManagerDialog(self).exec()
        except Exception as e: messagebox.showerror(self, c.t("UI_ERROR_TITLE"), f"Error: {e}")

    def open_version_manager(self):
        """Open the version manager dialog for renaming, deleting, and shortcuts."""
        from src.gui.version_manager_dialog import VersionManagerDialog
        try: VersionManagerDialog(self, self).exec()
        except Exception as e: messagebox.showerror(self, c.t("UI_ERROR_TITLE"), f"Error: {e}")

    def sync_gamemode_ui(self, value):
        """Synchronize the gamemode toggle between Play and Settings tabs."""
        self.config_manager.set(c.CONFIG_KEY_GAMEMODE_ENABLED, value)
        if hasattr(self.play_tab, "check_gamemode"):
            self.play_tab.check_gamemode.blockSignals(True)
            self.play_tab.check_gamemode.setChecked(value)
            self.play_tab.check_gamemode.blockSignals(False)
        if hasattr(self.settings_tab, "checks"):
            cb = self.settings_tab.checks.get(c.CONFIG_KEY_GAMEMODE_ENABLED)
            if cb:
                cb.blockSignals(True)
                cb.setChecked(value)
                cb.blockSignals(False)

    def sync_discord_rpc_ui(self, value):
        """Synchronize the Discord RPC toggle between Play and Settings tabs."""
        self.config_manager.set(c.CONFIG_KEY_DISCORD_RPC_ENABLED, value)
        self._sync_discord_play(value)
        self._sync_discord_settings(value)
        if value:
            self._discord_rpc.start()
            self._discord_rpc.set_idle()
        else:
            self._discord_rpc.stop()

    def _sync_discord_play(self, value):
        if hasattr(self.play_tab, "check_discord"):
            blocked = self.play_tab.check_discord.blockSignals(True)
            self.play_tab.check_discord.setChecked(value)
            self.play_tab.check_discord.blockSignals(blocked)

    def _sync_discord_settings(self, value):
        if hasattr(self.settings_tab, "check_discord_rpc"):
            blocked = self.settings_tab.check_discord_rpc.blockSignals(True)
            self.settings_tab.check_discord_rpc.setChecked(value)
            self.settings_tab.check_discord_rpc.blockSignals(blocked)

    def sync_launch_action_ui(self, action_key):
        """Synchronize the launch-action combo between Play and Settings tabs."""
        self.config_manager.set(c.CONFIG_KEY_LAUNCH_ACTION, action_key)
        for tab in (self.play_tab, self.settings_tab):
            if hasattr(tab, "combo_launch_action"):
                blocked = tab.combo_launch_action.blockSignals(True)
                idx = tab.combo_launch_action.findData(action_key)
                if idx >= 0:
                    tab.combo_launch_action.setCurrentIndex(idx)
                tab.combo_launch_action.blockSignals(blocked)

    def _setup_tray_icon(self):
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setIcon(self.windowIcon())
        self._tray_icon.setToolTip(c.t("UI_TITLE_VERSION"))
        tray_menu = QMenu()
        show_act = QAction(c.t("UI_TRAY_SHOW"), self)
        show_act.triggered.connect(self.show)
        quit_act = QAction(c.t("UI_TRAY_QUIT"), self)
        quit_act.triggered.connect(self.close)
        tray_menu.addAction(show_act)
        tray_menu.addAction(quit_act)
        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()
            self.raise_()

    def hide_to_tray(self):
        self._tray_icon.show()
        self.hide()
        self._game_monitor.start()

    def on_game_launched(self):
        self._game_monitor.start()
        self._set_persistent_game_indicator(True)
        if hasattr(self.play_tab, "set_game_status"):
            self.play_tab.set_game_status(True)

    def _set_persistent_game_indicator(self, running):
        """Show/hide a global 'game running' badge visible on every tab."""
        if running:
            self.game_status_label.setText(f"● {c.t('UI_GAME_STATUS_RUNNING')}")
            self.game_status_label.adjustSize()
            x = self.width() - self.game_status_label.width() - 20
            y = self.tab_widget.tabBar().height() + 14
            self.game_status_label.move(x, y)
            self.game_status_label.raise_()
            self.game_status_label.show()
        else:
            self.game_status_label.hide()

    def _check_game_process(self):
        if self._game_process is None:
            self._game_monitor.stop()
            return
        rc = self._game_process.poll()
        if rc is not None:
            self._game_process = None
            self._game_monitor.stop()
            if hasattr(self, '_tray_icon') and self._tray_icon and self.isHidden():
                self._tray_icon.hide()
                self.show()
                self.activateWindow()
                self.raise_()
            if hasattr(self.play_tab, "set_game_status"):
                self.play_tab.set_game_status(False)
            self._set_persistent_game_indicator(False)

    def manage_desktop_shortcut(self):
        """Open the version manager to manage desktop shortcuts."""
        self.open_version_manager()

    def closeEvent(self, event):
        self._game_monitor.stop()
        self.config_manager.flush()
        if self._tray_icon:
            self._tray_icon.hide()
        if hasattr(self, '_discord_rpc') and self._discord_rpc:
            self._discord_rpc.stop()
        super().closeEvent(event)

    def check_version_update(self):
        """Compare stored version with current launcher version and show changelog on update.
        Also schedules a remote update check if enough time has passed."""
        config_ver = self.config.get(c.CONFIG_KEY_VERSION, "0.0.0")
        current_ver = c.VERSION_LAUNCHER

        try:
            def ver_to_tuple(v): return tuple(map(int, (v.split('.') + ['0','0'])[:3]))
            cv_tuple = ver_to_tuple(config_ver)
            rv_tuple = ver_to_tuple(current_ver)

            if rv_tuple > cv_tuple:
                logger.info(f"Update detected: {config_ver} -> {current_ver}")
                self.show_update_changelog(current_ver)
            elif rv_tuple < cv_tuple:
                logger.warning(f"Downgrade detected: {config_ver} -> {current_ver}")
                messagebox.showwarning(self, c.t("UI_DOWNGRADE_WARNING_TITLE"),
                                     c.t("UI_DOWNGRADE_WARNING_MSG", old=config_ver))

            self.config_manager.set(c.CONFIG_KEY_VERSION, current_ver)
        except Exception as e:
            logger.error(f"Error comparing versions: {e}")

        QTimer.singleShot(3000, self._check_remote_update)

    def _check_remote_update(self):
        """Fetch version.json from GitHub Pages and notify if a newer version exists."""
        last_check = self.config.get(c.CONFIG_KEY_UPDATE_LAST_CHECK, 0)
        ignored = self.config.get(c.CONFIG_KEY_UPDATE_IGNORE, "")
        now = int(time.time())

        if now - last_check < c.UPDATE_CHECK_INTERVAL:
            return

        self._update_checker = UpdateChecker(self)
        self._update_checker.check(on_result=lambda ok, ver, hf, err: self._on_remote_check(ok, ver, hf, ignored))

        self.config_manager.set(c.CONFIG_KEY_UPDATE_LAST_CHECK, now)

    def _on_remote_check(self, available, remote_ver, hotfix, ignored):
        """Handle the remote check result. Show the update and/or hotfix dialog.

        A hotfix is a re-release of the same version (same version string) that
        must reach users even though their version number already matches.
        """
        if hotfix:
            self._handle_hotfix(hotfix)

        if available and remote_ver != ignored:
            messagebox.showinfo(self, c.t("UI_INFO_TITLE"),
                              c.t("UI_UPDATE_AVAILABLE", version=remote_ver))

    def _handle_hotfix(self, hotfix):
        """Show the hotfix dialog unless its id was already acknowledged/ignored."""
        if not isinstance(hotfix, dict):
            return
        hf_id = hotfix.get("id", "")
        if not hf_id:
            return
        ignored_hf = self.config.get(c.CONFIG_KEY_UPDATE_IGNORE_HOTFIX, "")
        if hf_id == ignored_hf:
            return

        title = hotfix.get("title") or c.t("UI_HOTFIX_TITLE")
        body = hotfix.get("body") or ""
        force = bool(hotfix.get("force", False))
        msg = c.t("UI_HOTFIX_MSG", body=body) if body else c.t("UI_HOTFIX_MSG")

        if force:
            # Mandatory hotfix: only an acknowledgement button, cannot be ignored.
            messagebox.showwarning(self, title, msg)
            return

        dialog = messagebox.CustomDialog(
            self, title, msg, icon_type="warning",
            options=[c.t("UI_HOTFIX_UPDATE"), c.t("UI_HOTFIX_IGNORE")])
        dialog.exec()
        if dialog.result_value == c.t("UI_HOTFIX_IGNORE"):
            self.config_manager.set(c.CONFIG_KEY_UPDATE_IGNORE_HOTFIX, hf_id)

    def show_update_changelog(self, version):
        """Display the changelog dialog for the given version."""
        from src.gui.changelog_dialog import ChangelogDialog
        dialog = ChangelogDialog(self, version)
        dialog.exec()

    def check_drm_alert(self):
        """Warn the user if the latest installed version needs the DRM mod and it's missing."""
        if not self.active_path:
            return
        latest = self.logic.get_latest_version_needs_drm(self)
        if latest and not self.logic.check_drm_mod_installed(self):
            messagebox.showwarning(self, c.t("UI_DRM_ALERT_TITLE"),
                                  c.t("UI_DRM_ALERT_MSG", version=latest))
