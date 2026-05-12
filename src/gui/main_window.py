from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QTabWidget, QPushButton, QFrame, QScrollArea, QComboBox, QApplication)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
import os
import sys
import subprocess
import shlex

from src import constants as c
from src.utils.resource_path import resource_path
from src.utils.image_manager import ImageManager
from src.core.config_manager import ConfigManager
from src.core import language_manager
from src.gui import custom_dialogs as messagebox
from src.gui.install_dialog import InstallDialog
from src.gui.skin_pack_tool import SkinPackTool
from src.gui.addon_manager_dialog import AddonManagerDialog
from src.gui.migration_dialog import MigrationDialog
from src.gui.game_config_dialog import GameConfigDialog
from src.core import app_logic
from src.gui.tabs.play_tab import PlayTab
from src.gui.tabs.tools_tab import ToolsTab
from src.gui.tabs.settings_tab import SettingsTab
from src.gui.tabs.about_tab import AboutTab

class VisualLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent; border: none;")

class CianovaLauncherApp(QMainWindow):
    def __init__(self, launcher_path=".", force_flatpak_ui=False, force_nvidia_ui=False):
        super().__init__()

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
        self.setWindowTitle(c.UI_TITLE_VERSION)
        size_str = self.config.get(c.CONFIG_KEY_WINDOW_SIZE, "700x550")
        try:
            w, h = map(int, size_str.split('x'))
            self.resize(w, h)
        except: self.resize(700, 550)

        self.setWindowIcon(ImageManager.get_icon("icon.png"))

        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True) # Better for centering tabs usually
        self.main_layout.addWidget(self.tab_widget)

        self.play_tab = PlayTab(self.tab_widget, self)
        self.play_tab.setObjectName("PlayTab")
        self.tools_tab = ToolsTab(self.tab_widget, self)
        self.tools_tab.setObjectName("ToolsTab")
        self.settings_tab = SettingsTab(self.tab_widget, self)
        self.settings_tab.setObjectName("SettingsTab")
        self.about_tab = AboutTab(self.tab_widget, self)
        self.about_tab.setObjectName("AboutTab")

        self.tab_widget.addTab(self.play_tab, c.UI_TAB_PLAY)
        self.tab_widget.addTab(self.tools_tab, c.UI_TAB_TOOLS)
        self.tab_widget.addTab(self.settings_tab, c.UI_TAB_SETTINGS)
        self.tab_widget.addTab(self.about_tab, c.UI_TAB_ABOUT)

        # Visuals (BG and Sticker)
        self.bg_label = VisualLabel(self.central_widget)
        self.bg_label.setScaledContents(True)
        self.sticker_label = VisualLabel(self.central_widget)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # Debounce timer for personalization and resizing
        self.personalization_timer = QTimer()
        self.personalization_timer.setSingleShot(True)
        self.personalization_timer.setInterval(50) # 50ms debounce
        self.personalization_timer.timeout.connect(self._apply_debounced_personalization)

        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(100) # 100ms for resize debounce
        self.resize_timer.timeout.connect(self._handle_resize_finished)

        # Logic init
        self.logic.detect_installation(self)
        if self.running_in_flatpak:
            self.logic.setup_flatpak_environment(self)
            self.logic.check_migration_needed(self)

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
            except: pass

    def resizeEvent(self, event):
        self.resize_timer.start()
        super().resizeEvent(event)

    def _handle_resize_finished(self):
        size = f"{self.width()}x{self.height()}"
        self.config_manager.set(c.CONFIG_KEY_WINDOW_SIZE, size)
        self.update_background()
        self.update_sticker()
        self.update_floating_labels()

    def update_sticker_visibility(self, index):
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
        except: pass

    def update_sticker(self):
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
        if messagebox.askyesno(self, c.UI_CONFIRM_TITLE, c.UI_RESTORE_DEFAULTS_CONFIRM):
            self.config_manager.restore_defaults()
            messagebox.showinfo(self, c.UI_RESTORE_DEFAULTS_SUCCESS_TITLE, c.UI_RESTORE_DEFAULTS_SUCCESS_MSG)
            self.close()

    def change_appearance(self, type_change, value):
        if type_change == "color":
            self.config[c.CONFIG_KEY_COLOR_THEME] = value
            # Dynamic color change is complex with current QSS setup, usually requires reload
            messagebox.showinfo(self, c.UI_RESTART_REQUIRED_TITLE, c.UI_RESTART_MSG)
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

        bg = "#242424" if mode == "Dark" else "#ebebeb"
        text = "#DCE4EE" if mode == "Dark" else "#242424"
        tab_bg = "#333333" if mode == "Dark" else "#d0d0d0"

        input_bg = "#333333" if mode == "Dark" else "#ffffff"
        input_text = "white" if mode == "Dark" else "#242424"
        input_border = "#444444" if mode == "Dark" else "#cccccc"

        section_opacity = section_opacity_val / 100.0

        def hex_to_rgba(hex_color, opacity):
            if not hex_color or not hex_color.startswith("#"): return hex_color
            h = hex_color.lstrip('#')
            if len(h) == 3: h = "".join([x*2 for x in h])
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgba({r}, {g}, {b}, {int(opacity * 255)})"

        def adjust_color(hex_color, amount):
            if not hex_color or not hex_color.startswith("#"): return hex_color
            h = hex_color.lstrip('#')
            if len(h) == 3: h = "".join([x*2 for x in h])
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            r = max(0, min(255, r + amount))
            g = max(0, min(255, g + amount))
            b = max(0, min(255, b + amount))
            return f"#{r:02x}{g:02x}{b:02x}"

        frame_bg_base = "#3a3a3a" if mode == "Dark" else "#e8e8e8"
        frame_bg_opaque = hex_to_rgba(frame_bg_base, 1.0)
        
        # Section opacity should only affect Settings and Tools tabs
        frame_bg_transparent = hex_to_rgba(frame_bg_base, section_opacity)

        if has_bg:
            bg_qss = f"background: transparent;"
        else:
            bg_qss = f"background-color: {bg};"

        # Fixed semi-transparent background for floating labels
        floating_label_bg = "rgba(85, 85, 85, 180)"
        floating_label_border = f"1px solid {hex_to_rgba('#ffffff', 0.2)}"

        qss = f"""
            QMainWindow, QWidget#centralWidget {{
                {bg_qss}
                color: {text};
                font-family: 'Roboto', 'Segoe UI', sans-serif;
            }}
            QDialog {{
                background-color: {bg};
            }}
            #VersionManagerDialog, #InstallDialog, #AddonManagerDialog, #MigrationDialog, #GameConfigDialog {{
                background-color: {bg};
            }}
            QTabWidget::pane {{
                border: 1px solid {input_border};
                background: transparent;
                border-radius: {c.CORNER_RADIUS}px;
                top: -1px;
            }}
            QTabBar {{
                alignment: center;
                background: {tab_bg};
                border-radius: 12px;
                padding: 2px;
                border: none;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {text};
                padding: 10px 25px;
                border-radius: 10px;
                font-weight: bold;
                margin: 2px;
                border: none;
            }}
            QTabBar::tab:selected {{
                background: {accent};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: {"#444444" if mode == "Dark" else "#bbbbbb"};
            }}
            QTabWidget::tab-bar {{
                top: 0px;
                border: none;
            }}
            QPushButton {{
                background-color: {accent};
                color: white;
                border: 1px solid {accent};
                border-radius: 10px;
                padding: 8px 15px;
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
            QPushButton:flat {{
                background-color: {accent};
                color: white;
                border: none;
            }}
            QLineEdit, QComboBox, QSpinBox, QTextEdit {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 6px;
                padding: 6px 8px;
            }}
            QComboBox::drop-down {{ 
                border: none; 
                width: 25px; 
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {accent};
                width: 0; height: 0;
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                selection-background-color: {accent};
                selection-color: white;
                border-radius: 6px;
                padding: 2px;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 30px;
                padding: 4px 8px;
                border-radius: 4px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {hex_to_rgba(accent, 0.3)};
            }}
            QCheckBox::indicator, QRadioButton::indicator {{
                width: 18px; height: 18px; border-radius: 4px;
                border: 2px solid {accent}; background: {input_bg};
            }}
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
                background: {accent};
            }}
            QPushButton#PlayButton, QPushButton#SaveButton, QPushButton#ActionButton {{
                background-color: {accent};
                color: white;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                border: 1px solid rgba(255,255,255,0.2);
            }}
            QPushButton#PlayButton:hover, QPushButton#SaveButton:hover, QPushButton#ActionButton:hover {{
                background-color: {adjust_color(accent, 20)};
            }}
            QPushButton#ToolButton {{
                background-color: {accent};
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                min-width: 30px;
                min-height: 30px;
            }}
            QPushButton#ToolButton:hover {{
                background-color: {adjust_color(accent, 20)};
            }}
            QFrame#ToolCard, QFrame#GroupFrame, QFrame#VersionCard {{
                border-radius: {c.CORNER_RADIUS}px;
                border: 1px solid {hex_to_rgba(input_border, 0.5)};
            }}

            #PlayTab QFrame#VersionCard, #PlayTab QFrame#GroupFrame, #AboutTab QFrame#GroupFrame {{
                background-color: {frame_bg_opaque};
            }}

            #ToolsTab QFrame#GroupFrame, #ToolsTab QFrame#ToolCard,
            #SettingsTab QFrame#GroupFrame {{
                background-color: {frame_bg_transparent};
            }}

            QScrollArea#GroupFrame {{
                background-color: transparent;
                border: none;
            }}
            QFrame#ToolCard:hover, QFrame#VersionCard:hover, QFrame#GroupFrame:hover {{
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
                color: white;
                padding: 5px 15px;
                border-radius: 10px;
                border: {floating_label_border};
                qproperty-alignment: 'AlignCenter';
            }}
            QSlider::groove:horizontal {{
                border: none;
                height: 4px;
                background: {hex_to_rgba(input_bg, 0.5)};
                margin: 2px 0;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {accent};
                border: none;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {adjust_color(accent, 20)};
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 2px;
            }}
            QComboBox::item:selected {{
                background-color: {accent};
                color: white;
            }}
            QScrollBar:vertical {{
                background: {tab_bg};
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {accent};
                min-height: 20px;
                border-radius: 6px;
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
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal {{
                background: {accent};
                min-width: 20px;
                border-radius: 6px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
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
            # Silently catch stylesheet parsing errors to avoid log spam
            pass

    def _apply_debounced_personalization(self):
        self.apply_theme_settings()

    def update_floating_labels(self):
        # In PySide6, we can iterate over widgets to hide empty FloatingLabels
        for widget in self.findChildren(QLabel, "FloatingLabel"):
            text = widget.text().strip()
            # If it's a profile or install label, it might have icons/prefixes
            if not text or text in ["●", "👤", "● Searching...", "● Buscando..."]:
                if "Searching" not in text and "Buscando" not in text:
                    widget.hide()
                else:
                    widget.show()
            else:
                widget.show()

    def show_info(self, title, msg):
        messagebox.showinfo(self, title, msg)

    # Tool openers
    def install_apk_dialog(self): InstallDialog(self).exec()
    def open_skin_tool(self): SkinPackTool(self).exec()
    def open_migration_tool(self):
        try: MigrationDialog(self).exec()
        except Exception as e: messagebox.showerror(self, c.UI_ERROR_TITLE, f"Error: {e}")
    def open_game_config_tool(self):
        try: GameConfigDialog(self).exec()
        except Exception as e: messagebox.showerror(self, c.UI_ERROR_TITLE, f"Error: {e}")
    def open_addon_manager(self):
        try: AddonManagerDialog(self).exec()
        except Exception as e: messagebox.showerror(self, c.UI_ERROR_TITLE, f"Error: {e}")

    def open_version_manager(self):
        from src.gui.version_manager_dialog import VersionManagerDialog
        try: VersionManagerDialog(self, self).exec()
        except Exception as e: messagebox.showerror(self, c.UI_ERROR_TITLE, f"Error: {e}")

    def sync_gamemode_ui(self, value):
        self.config[c.CONFIG_KEY_GAMEMODE_ENABLED] = value
        if hasattr(self.play_tab, "check_gamemode"):
            if self.play_tab.check_gamemode.isChecked() != value:
                self.play_tab.check_gamemode.setChecked(value)
        if hasattr(self.settings_tab, "checks"):
            cb = self.settings_tab.checks.get(c.CONFIG_KEY_GAMEMODE_ENABLED)
            if cb and cb.isChecked() != value:
                cb.setChecked(value)

    def sync_close_on_launch_ui(self, value):
        self.config[c.CONFIG_KEY_CLOSE_ON_LAUNCH] = value
        if hasattr(self.play_tab, "check_close_on_launch"):
            if self.play_tab.check_close_on_launch.isChecked() != value:
                self.play_tab.check_close_on_launch.setChecked(value)
        if hasattr(self.settings_tab, "check_close_on_launch"):
            if self.settings_tab.check_close_on_launch.isChecked() != value:
                self.settings_tab.check_close_on_launch.setChecked(value)

    def manage_desktop_shortcut(self):
        self.open_version_manager()
