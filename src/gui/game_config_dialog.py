from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFrame, QTabWidget, QScrollArea, QWidget, QSlider, QCheckBox, QComboBox, QTextEdit)
from PySide6.QtCore import Qt
import os
from src.gui import custom_dialogs as messagebox
from src import constants as c

class GameConfigDialog(QDialog):
    """Dialog for editing Minecraft options.txt through a visual UI or raw text editor."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_app = parent
        self.setWindowTitle(c.t("UI_GAME_CONFIG_TITLE"))
        self.resize(650, 700)

        self.options_path = os.path.join(self.parent_app.active_path, c.MINECRAFT_PE_DIR_ALT, c.OPTIONS_FILE)
        self.options_data = {}

        self.setup_ui()
        self.load_options()

    def setup_ui(self):
        """Build the dialog with a tabbed interface (visual + raw editor)."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # Tabs
        self.tab_visual = QWidget()
        self.tab_editor = QWidget()
        self.tab_widget.addTab(self.tab_visual, c.t("UI_TAB_VISUAL"))
        self.tab_widget.addTab(self.tab_editor, c.t("UI_TAB_EDITOR"))

        self.setup_visual_tab()
        self.setup_editor_tab()

        self.setStyleSheet("background-color: #2b2b2b; color: white;")

    def setup_editor_tab(self):
        """Set up the raw text editor tab with a QTextEdit and save button."""
        layout = QVBoxLayout(self.tab_editor)
        self.text_editor = QTextEdit()
        self.text_editor.setStyleSheet("font-family: 'Courier New'; font-size: 13px; background-color: #1e1e1e; color: #d4d4d4;")
        layout.addWidget(self.text_editor)

        btn_save = QPushButton(c.t("UI_BUTTON_SAVE_FILE"))
        btn_save.setFixedHeight(c.BTN_HEIGHT)
        btn_save.clicked.connect(lambda: self.save_options(True))
        btn_save.setStyleSheet(f"background-color: {c.COLOR_BLUE_BUTTON}; color: white; font-weight: bold;")
        layout.addWidget(btn_save)

    def setup_visual_tab(self):
        """Set up the visual editor tab with categorized sliders, checkboxes, and combos."""
        layout = QVBoxLayout(self.tab_visual)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll)

        # Sections
        # Graphics
        self.create_section_label(c.t("UI_GC_GRAPHICS"))
        self.view_distance = self.create_slider_setting(c.t("UI_GC_VIEW_DISTANCE"), 4, 32)
        self.max_fps = self.create_entry_setting(c.t("UI_GC_MAX_FPS"))
        self.vsync = self.create_checkbox_setting(c.t("UI_GC_VSYNC"))
        self.gamma = self.create_slider_setting(c.t("UI_GC_GAMMA"), 0, 100, is_float=True) # 0 to 1.0 scaled to 0-100
        self.fullscreen = self.create_checkbox_setting(c.t("UI_GC_FULLSCREEN"))
        self.fancyskies = self.create_checkbox_setting(c.t("UI_GC_FANCY_SKIES"))
        self.smoothlighting = self.create_checkbox_setting(c.t("UI_GC_SMOOTH_LIGHTING"))
        self.graphics_mode = self.create_combo_setting(c.t("UI_GC_GRAPHICS_MODE"), c.t("UI_GC_GRAPHICS_MODE_MAP"))

        # Gameplay
        self.create_section_label(c.t("UI_GC_GAMEPLAY"))
        self.difficulty = self.create_combo_setting(c.t("UI_GC_DIFFICULTY"), c.t("UI_GC_DIFFICULTY_MAP"))
        self.perspective = self.create_combo_setting(c.t("UI_GC_PERSPECTIVE"), c.t("UI_GC_PERSPECTIVE_MAP"))
        self.game_lang = self.create_entry_setting(c.t("UI_GC_LANGUAGE"))

        # Controls
        self.create_section_label(c.t("UI_GC_CONTROLS"))
        self.sensitivity = self.create_slider_setting(c.t("UI_GC_SENSITIVITY"), 1, 200, is_float=True) # 0.01 to 2.0 scaled
        self.invert_mouse = self.create_checkbox_setting(c.t("UI_GC_INVERT_MOUSE"))
        self.autojump = self.create_checkbox_setting(c.t("UI_GC_AUTO_JUMP"))
        self.lefthanded = self.create_checkbox_setting(c.t("UI_GC_LEFT_HANDED"))
        self.swapjumpsneak = self.create_checkbox_setting(c.t("UI_GC_SWAP_JUMP_SNEAK"))

        # Audio
        self.create_section_label(c.t("UI_GC_AUDIO"))
        self.sound_vol = self.create_slider_setting(c.t("UI_GC_SOUND_VOLUME"), 0, 100, is_float=True)
        self.music_vol = self.create_slider_setting(c.t("UI_GC_MUSIC_VOLUME"), 0, 100, is_float=True)

        # Privacy
        self.create_section_label(c.t("UI_GC_PRIVACY"))
        self.server_visible = self.create_checkbox_setting(c.t("UI_GC_SERVER_VISIBLE"))
        self.xbox_visible = self.create_checkbox_setting(c.t("UI_GC_XBOX_VISIBLE"))
        self.autoupdate = self.create_checkbox_setting(c.t("UI_GC_AUTO_UPDATE"))

        btn_save = QPushButton(c.t("UI_BUTTON_SAVE_SETTINGS"))
        btn_save.setObjectName("ActionButton")
        btn_save.setFixedHeight(40)
        btn_save.clicked.connect(lambda: self.save_options(False))
        self.scroll_layout.addWidget(btn_save)

    def create_section_label(self, text):
        """Add a section header label to the visual tab."""
        lbl = QLabel(text)
        lbl.setObjectName("HeaderLabel")
        lbl.setStyleSheet("margin-top: 15px;")
        self.scroll_layout.addWidget(lbl)

    def create_slider_setting(self, label, min_val, max_val, is_float=False):
        """Create a labeled horizontal slider with a value readout."""
        f = QFrame()
        l = QHBoxLayout(f)
        l.addWidget(QLabel(label))
        s = QSlider(Qt.Horizontal)
        s.setRange(min_val, max_val)
        l.addWidget(s, 1)
        v = QLabel("0")
        v.setFixedWidth(50)
        v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        l.addWidget(v)

        if is_float:
            s.valueChanged.connect(lambda val: v.setText(f"{val/100:.2f}"))
        else:
            s.valueChanged.connect(lambda val: v.setText(str(val)))

        self.scroll_layout.addWidget(f)
        return (s, v, is_float)

    def create_checkbox_setting(self, label):
        """Create a labeled checkbox for boolean settings."""
        cb = QCheckBox(label)
        self.scroll_layout.addWidget(cb)
        return cb

    def create_entry_setting(self, label):
        """Create a labeled text entry for string settings."""
        f = QFrame()
        l = QHBoxLayout(f)
        l.addWidget(QLabel(label))
        e = QLineEdit()
        e.setFixedWidth(150)
        l.addWidget(e, 0, Qt.AlignRight)
        self.scroll_layout.addWidget(f)
        return e

    def create_combo_setting(self, label, options):
        """Create a labeled combo box for choice-based settings."""
        f = QFrame()
        l = QHBoxLayout(f)
        l.addWidget(QLabel(label))
        cb = QComboBox()
        cb.addItems(options)
        l.addWidget(cb, 0, Qt.AlignRight)
        self.scroll_layout.addWidget(f)
        return cb

    def load_options(self):
        """Read options.txt and populate the visual UI and text editor."""
        if not os.path.exists(self.options_path):
            messagebox.showwarning(self, c.t("UI_INFO_TITLE"), c.t("UI_FILE_NOT_FOUND_WARN"))
            return
        try:
            with open(self.options_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.text_editor.setPlainText(content)
                lines = content.splitlines()
                for line in lines:
                    if ":" in line:
                        key, val = line.split(":", 1)
                        self.options_data[key.strip()] = val.strip()
            self.update_visual_ui()
        except Exception as e:
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), c.t("UI_ERROR_READING_FILE", e=e))

    def update_visual_ui(self):
        """Sync the visual UI widgets with the currently loaded options data."""
        d = self.options_data
        if "gfx_viewdistance" in d: self.view_distance[0].setValue(int(d["gfx_viewdistance"]) // 16)
        if "gfx_max_framerate" in d: self.max_fps.setText(d["gfx_max_framerate"])
        if "gfx_vsync" in d: self.vsync.setChecked(d["gfx_vsync"] == "1")
        if "gfx_gamma" in d: self.gamma[0].setValue(int(float(d["gfx_gamma"]) * 100))
        if "gfx_fullscreen" in d: self.fullscreen.setChecked(d["gfx_fullscreen"] == "1")
        if "gfx_fancyskies" in d: self.fancyskies.setChecked(d["gfx_fancyskies"] == "1")
        if "gfx_smoothlighting" in d: self.smoothlighting.setChecked(d["gfx_smoothlighting"] == "1")
        if "graphics_mode" in d: self.graphics_mode.setCurrentIndex(int(d["graphics_mode"]))
        if "game_difficulty_new" in d: self.difficulty.setCurrentIndex(int(d["game_difficulty_new"]))
        if "game_thirdperson" in d: self.perspective.setCurrentIndex(int(d["game_thirdperson"]))
        if "game_language" in d: self.game_lang.setText(d["game_language"].strip('"'))
        if "ctrl_sensitivity2_mouse" in d: self.sensitivity[0].setValue(int(float(d["ctrl_sensitivity2_mouse"]) * 100))
        if "ctrl_invertmouse_mouse" in d: self.invert_mouse.setChecked(d["ctrl_invertmouse_mouse"] == "1")
        if "ctrl_autojump_mouse" in d: self.autojump.setChecked(d["ctrl_autojump_mouse"] == "1")
        if "ctrl_islefthanded" in d: self.lefthanded.setChecked(d["ctrl_islefthanded"] == "1")
        if "ctrl_swapjumpandsneak" in d: self.swapjumpsneak.setChecked(d["ctrl_swapjumpandsneak"] == "1")
        if "audio_sound" in d: self.sound_vol[0].setValue(int(float(d["audio_sound"]) * 100))
        if "audio_music" in d: self.music_vol[0].setValue(int(float(d["audio_music"]) * 100))
        if "mp_server_visible" in d: self.server_visible.setChecked(d["mp_server_visible"] == "1")
        if "mp_xboxlive_visible" in d: self.xbox_visible.setChecked(d["mp_xboxlive_visible"] == "1")
        if "auto_update_enabled" in d: self.autoupdate.setChecked(d["auto_update_enabled"] == "1")

    def save_options(self, from_editor=False):
        """Write the current options back to options.txt, either from visual UI or raw editor."""
        try:
            if from_editor:
                content = self.text_editor.toPlainText()
            else:
                self.sync_data_from_ui()
                if os.path.exists(self.options_path):
                    with open(self.options_path, "r", encoding="utf-8") as f: lines = f.readlines()
                    new_lines = []
                    processed = set()
                    for line in lines:
                        if ":" in line:
                            key = line.split(":", 1)[0].strip()
                            if key in self.options_data:
                                new_lines.append(f"{key}:{self.options_data[key]}\n")
                                processed.add(key)
                            else: new_lines.append(line)
                        else: new_lines.append(line)
                    for k, v in self.options_data.items():
                        if k not in processed: new_lines.append(f"{k}:{v}\n")
                    content = "".join(new_lines)
                else: content = "\n".join([f"{k}:{v}" for k, v in self.options_data.items()])

            os.makedirs(os.path.dirname(self.options_path), exist_ok=True)
            with open(self.options_path, "w", encoding="utf-8") as f: f.write(content)
            messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), c.t("UI_SAVE_FILE_SUCCESS"))
            self.parent_app.logic.check_shader_status(self.parent_app)
            self.load_options()
        except Exception as e:
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), c.t("UI_ERROR_SAVING_FILE", e=e))

    def sync_data_from_ui(self):
        """Copy all visual widget values into the internal options_data dict."""
        d = self.options_data
        d["gfx_viewdistance"] = str(self.view_distance[0].value() * 16)
        d["gfx_max_framerate"] = self.max_fps.text()
        d["gfx_vsync"] = "1" if self.vsync.isChecked() else "0"
        d["gfx_gamma"] = f"{self.gamma[0].value()/100:.6f}"
        d["gfx_fullscreen"] = "1" if self.fullscreen.isChecked() else "0"
        d["gfx_fancyskies"] = "1" if self.fancyskies.isChecked() else "0"
        d["gfx_smoothlighting"] = "1" if self.smoothlighting.isChecked() else "0"
        d["graphics_mode"] = str(self.graphics_mode.currentIndex())
        d["game_difficulty_new"] = str(self.difficulty.currentIndex())
        d["game_thirdperson"] = str(self.perspective.currentIndex())
        d["game_language"] = f'"{self.game_lang.text()}"'
        d["ctrl_sensitivity2_mouse"] = f"{self.sensitivity[0].value()/100:.6f}"
        d["ctrl_invertmouse_mouse"] = "1" if self.invert_mouse.isChecked() else "0"
        d["ctrl_autojump_mouse"] = "1" if self.autojump.isChecked() else "0"
        d["ctrl_islefthanded"] = "1" if self.lefthanded.isChecked() else "0"
        d["ctrl_swapjumpandsneak"] = "1" if self.swapjumpsneak.isChecked() else "0"
        d["audio_sound"] = f"{self.sound_vol[0].value()/100:.6f}"
        d["audio_music"] = f"{self.music_vol[0].value()/100:.6f}"
        d["mp_server_visible"] = "1" if self.server_visible.isChecked() else "0"
        d["mp_xboxlive_visible"] = "1" if self.xbox_visible.isChecked() else "0"
        d["auto_update_enabled"] = "1" if self.autoupdate.isChecked() else "0"
