import customtkinter as ctk
from src.gui import custom_dialogs as messagebox
import os
from src import constants as c

class GameConfigDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title(c.UI_GAME_CONFIG_TITLE)
        self.geometry("650x700")
        self.resizable(True, True)
        self.transient(parent)

        self.options_path = os.path.join(self.parent.active_path, c.MINECRAFT_PE_DIR_ALT, c.OPTIONS_FILE)
        self.options_data = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.tab_visual = self.tabview.add(c.UI_TAB_VISUAL)
        self.tab_editor = self.tabview.add(c.UI_TAB_EDITOR)

        self.setup_visual_tab()
        self.setup_editor_tab()

        self.load_options()

        self.grab_set()

    def load_options(self):
        if not os.path.exists(self.options_path):
            messagebox.showwarning(self, c.UI_INFO_TITLE, c.UI_FILE_NOT_FOUND_WARN)
            return

        try:
            with open(self.options_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.text_editor.insert("1.0", content)

                # Parse for visual tab
                lines = content.splitlines()
                for line in lines:
                    if ":" in line:
                        key, val = line.split(":", 1)
                        self.options_data[key.strip()] = val.strip()

            self.update_visual_ui()
        except Exception as e:
            messagebox.showerror(self, c.UI_ERROR_TITLE, c.UI_ERROR_READING_FILE.format(e=e))

    def save_options(self, from_editor=False):
        try:
            if from_editor:
                content = self.text_editor.get("1.0", "end-1c")
            else:
                self.sync_data_from_ui()
                # We want to preserve other keys, so we read the file again and replace only what we know
                if os.path.exists(self.options_path):
                    with open(self.options_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    new_lines = []
                    processed_keys = set()
                    for line in lines:
                        if ":" in line:
                            key = line.split(":", 1)[0].strip()
                            if key in self.options_data:
                                new_lines.append(f"{key}:{self.options_data[key]}\n")
                                processed_keys.add(key)
                            else:
                                new_lines.append(line)
                        else:
                            new_lines.append(line)

                    # Add keys that were not in the file but are in our data (shouldn't happen with standard keys but just in case)
                    for key, val in self.options_data.items():
                        if key not in processed_keys:
                            new_lines.append(f"{key}:{val}\n")

                    content = "".join(new_lines)
                else:
                    content = "\n".join([f"{k}:{v}" for k, v in self.options_data.items()])

            os.makedirs(os.path.dirname(self.options_path), exist_ok=True)
            with open(self.options_path, "w", encoding="utf-8") as f:
                f.write(content)

            messagebox.showinfo(self, c.UI_SUCCESS_TITLE, c.UI_SAVE_FILE_SUCCESS)

            # Actualizar el indicador de shaders en la pestaña Herramientas
            self.parent.logic.check_shader_status(self.parent)

            # Reload to sync both tabs
            if from_editor:
                # Reload data from text
                self.options_data = {}
                lines = content.splitlines()
                for line in lines:
                    if ":" in line:
                        key, val = line.split(":", 1)
                        self.options_data[key.strip()] = val.strip()
                self.update_visual_ui()
            else:
                # Reload editor text
                self.text_editor.delete("1.0", "end")
                self.text_editor.insert("1.0", content)

        except Exception as e:
            messagebox.showerror(self, c.UI_ERROR_TITLE, c.UI_ERROR_SAVING_FILE.format(e=e))

    def setup_editor_tab(self):
        self.tab_editor.grid_columnconfigure(0, weight=1)
        self.tab_editor.grid_rowconfigure(0, weight=1)

        self.text_editor = ctk.CTkTextbox(self.tab_editor, font=("Courier New", 13))
        self.text_editor.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.btn_save_editor = ctk.CTkButton(self.tab_editor, text=c.UI_BUTTON_SAVE_FILE, height=c.BTN_HEIGHT, font=c.FONT_NORMAL, command=lambda: self.save_options(True))
        self.btn_save_editor.grid(row=1, column=0, pady=10)

    def setup_visual_tab(self):
        self.scroll_visual = ctk.CTkScrollableFrame(self.tab_visual, fg_color="transparent")
        self.scroll_visual.pack(fill="both", expand=True, padx=5, pady=5)

        # SECCIÓN 1: GRÁFICOS
        self.create_section_label(self.scroll_visual, c.UI_GC_GRAPHICS)

        self.view_distance_var = ctk.IntVar(value=6)
        self.create_slider_setting(self.scroll_visual, c.UI_GC_VIEW_DISTANCE, self.view_distance_var, 4, 32)

        self.max_fps_var = ctk.IntVar(value=60)
        self.create_entry_setting(self.scroll_visual, c.UI_GC_MAX_FPS, self.max_fps_var)

        self.vsync_var = ctk.BooleanVar(value=False)
        self.create_switch_setting(self.scroll_visual, c.UI_GC_VSYNC, self.vsync_var)

        self.gamma_var = ctk.DoubleVar(value=0.5)
        self.create_slider_setting(self.scroll_visual, c.UI_GC_GAMMA, self.gamma_var, 0.0, 1.0)

        self.fullscreen_var = ctk.BooleanVar(value=False)
        self.create_switch_setting(self.scroll_visual, c.UI_GC_FULLSCREEN, self.fullscreen_var)

        self.fancyskies_var = ctk.BooleanVar(value=True)
        self.create_switch_setting(self.scroll_visual, c.UI_GC_FANCY_SKIES, self.fancyskies_var)

        self.smoothlighting_var = ctk.BooleanVar(value=True)
        self.create_switch_setting(self.scroll_visual, c.UI_GC_SMOOTH_LIGHTING, self.smoothlighting_var)

        self.graphics_mode_var = ctk.StringVar(value=c.UI_GC_GRAPHICS_MODE_MAP[0])
        self.create_option_setting(self.scroll_visual, c.UI_GC_GRAPHICS_MODE, self.graphics_mode_var, c.UI_GC_GRAPHICS_MODE_MAP)

        # SECCIÓN 2: JUGABILIDAD
        self.create_section_label(self.scroll_visual, c.UI_GC_GAMEPLAY)

        self.difficulty_var = ctk.StringVar(value=c.UI_GC_DIFFICULTY_MAP[2])
        self.create_option_setting(self.scroll_visual, c.UI_GC_DIFFICULTY, self.difficulty_var, c.UI_GC_DIFFICULTY_MAP)

        self.perspective_var = ctk.StringVar(value=c.UI_GC_PERSPECTIVE_MAP[0])
        self.create_option_setting(self.scroll_visual, c.UI_GC_PERSPECTIVE, self.perspective_var, c.UI_GC_PERSPECTIVE_MAP)

        self.game_lang_var = ctk.StringVar(value="en_US")
        self.create_entry_setting(self.scroll_visual, c.UI_GC_LANGUAGE, self.game_lang_var)

        # SECCIÓN 3: CONTROLES
        self.create_section_label(self.scroll_visual, c.UI_GC_CONTROLS)

        self.sensitivity_var = ctk.DoubleVar(value=0.5)
        self.create_slider_setting(self.scroll_visual, c.UI_GC_SENSITIVITY, self.sensitivity_var, 0.01, 2.0)

        self.invert_mouse_var = ctk.BooleanVar(value=False)
        self.create_switch_setting(self.scroll_visual, c.UI_GC_INVERT_MOUSE, self.invert_mouse_var)

        self.autojump_var = ctk.BooleanVar(value=True)
        self.create_switch_setting(self.scroll_visual, c.UI_GC_AUTO_JUMP, self.autojump_var)

        self.lefthanded_var = ctk.BooleanVar(value=False)
        self.create_switch_setting(self.scroll_visual, c.UI_GC_LEFT_HANDED, self.lefthanded_var)

        self.swapjumpsneak_var = ctk.BooleanVar(value=False)
        self.create_switch_setting(self.scroll_visual, c.UI_GC_SWAP_JUMP_SNEAK, self.swapjumpsneak_var)

        # SECCIÓN 4: AUDIO
        self.create_section_label(self.scroll_visual, c.UI_GC_AUDIO)

        self.sound_vol_var = ctk.DoubleVar(value=1.0)
        self.create_slider_setting(self.scroll_visual, c.UI_GC_SOUND_VOLUME, self.sound_vol_var, 0.0, 1.0)

        self.music_vol_var = ctk.DoubleVar(value=1.0)
        self.create_slider_setting(self.scroll_visual, c.UI_GC_MUSIC_VOLUME, self.music_vol_var, 0.0, 1.0)

        # SECCIÓN 5: PRIVACIDAD
        self.create_section_label(self.scroll_visual, c.UI_GC_PRIVACY)

        self.server_visible_var = ctk.BooleanVar(value=True)
        self.create_switch_setting(self.scroll_visual, c.UI_GC_SERVER_VISIBLE, self.server_visible_var)

        self.xbox_visible_var = ctk.BooleanVar(value=True)
        self.create_switch_setting(self.scroll_visual, c.UI_GC_XBOX_VISIBLE, self.xbox_visible_var)

        self.autoupdate_var = ctk.BooleanVar(value=True)
        self.create_switch_setting(self.scroll_visual, c.UI_GC_AUTO_UPDATE, self.autoupdate_var)

        self.btn_save_visual = ctk.CTkButton(self.scroll_visual, text=c.UI_BUTTON_SAVE_SETTINGS,
                                            command=lambda: self.save_options(False))
        self.btn_save_visual.pack(pady=20)

    def create_section_label(self, parent, text):
        lbl = ctk.CTkLabel(parent, text=text, font=c.FONT_SUBTITLE, text_color=c.COLOR_BLUE_BUTTON)
        lbl.pack(anchor="w", padx=10, pady=(15, 5))

    def create_slider_setting(self, parent, label, var, min_val, max_val):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(frame, text=label, font=c.FONT_NORMAL).pack(side="left")

        val_lbl = ctk.CTkLabel(frame, text=f"{var.get():.2f}" if isinstance(var.get(), float) else str(var.get()), font=c.FONT_BOLD)
        val_lbl.pack(side="right", padx=5)

        def update_lbl(val):
            if isinstance(var, ctk.DoubleVar):
                val_lbl.configure(text=f"{float(val):.2f}")
            else:
                val_lbl.configure(text=str(int(val)))
            var.set(val)

        slider = ctk.CTkSlider(frame, from_=min_val, to=max_val, variable=var, command=update_lbl)
        slider.pack(side="right", fill="x", expand=True, padx=10)

    def create_switch_setting(self, parent, label, var):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(frame, text=label, font=c.FONT_NORMAL).pack(side="left")
        switch = ctk.CTkSwitch(frame, text="", variable=var)
        switch.pack(side="right")

    def create_entry_setting(self, parent, label, var):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(frame, text=label, font=c.FONT_NORMAL).pack(side="left")
        entry = ctk.CTkEntry(frame, textvariable=var, width=150, font=c.FONT_NORMAL)
        entry.pack(side="right")

    def create_option_setting(self, parent, label, var, options):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(frame, text=label, font=c.FONT_NORMAL).pack(side="left")
        om = ctk.CTkOptionMenu(frame, variable=var, values=options, font=c.FONT_NORMAL)
        om.pack(side="right")

    def update_visual_ui(self):
        # Update variables from self.options_data
        try:
            if "gfx_viewdistance" in self.options_data:
                self.view_distance_var.set(int(self.options_data["gfx_viewdistance"]) // 16)

            if "gfx_max_framerate" in self.options_data:
                self.max_fps_var.set(int(self.options_data["gfx_max_framerate"]))

            if "gfx_vsync" in self.options_data:
                self.vsync_var.set(self.options_data["gfx_vsync"] == "1")

            if "gfx_gamma" in self.options_data:
                self.gamma_var.set(float(self.options_data["gfx_gamma"]))

            if "gfx_fullscreen" in self.options_data:
                self.fullscreen_var.set(self.options_data["gfx_fullscreen"] == "1")

            if "gfx_fancyskies" in self.options_data:
                self.fancyskies_var.set(self.options_data["gfx_fancyskies"] == "1")

            if "gfx_smoothlighting" in self.options_data:
                self.smoothlighting_var.set(self.options_data["gfx_smoothlighting"] == "1")

            if "graphics_mode" in self.options_data:
                idx = int(self.options_data["graphics_mode"])
                if 0 <= idx < len(c.UI_GC_GRAPHICS_MODE_MAP):
                    self.graphics_mode_var.set(c.UI_GC_GRAPHICS_MODE_MAP[idx])

            if "game_difficulty_new" in self.options_data:
                idx = int(self.options_data["game_difficulty_new"])
                if 0 <= idx < len(c.UI_GC_DIFFICULTY_MAP):
                    self.difficulty_var.set(c.UI_GC_DIFFICULTY_MAP[idx])

            if "game_thirdperson" in self.options_data:
                idx = int(self.options_data["game_thirdperson"])
                if 0 <= idx < len(c.UI_GC_PERSPECTIVE_MAP):
                    self.perspective_var.set(c.UI_GC_PERSPECTIVE_MAP[idx])

            if "game_language" in self.options_data:
                self.game_lang_var.set(self.options_data["game_language"].strip('"'))

            if "ctrl_sensitivity2_mouse" in self.options_data:
                self.sensitivity_var.set(float(self.options_data["ctrl_sensitivity2_mouse"]))

            if "ctrl_invertmouse_mouse" in self.options_data:
                self.invert_mouse_var.set(self.options_data["ctrl_invertmouse_mouse"] == "1")

            if "ctrl_autojump_mouse" in self.options_data:
                self.autojump_var.set(self.options_data["ctrl_autojump_mouse"] == "1")

            if "ctrl_islefthanded" in self.options_data:
                self.lefthanded_var.set(self.options_data["ctrl_islefthanded"] == "1")

            if "ctrl_swapjumpandsneak" in self.options_data:
                self.swapjumpsneak_var.set(self.options_data["ctrl_swapjumpandsneak"] == "1")

            if "audio_sound" in self.options_data:
                self.sound_vol_var.set(float(self.options_data["audio_sound"]))

            if "audio_music" in self.options_data:
                self.music_vol_var.set(float(self.options_data["audio_music"]))

            if "mp_server_visible" in self.options_data:
                self.server_visible_var.set(self.options_data["mp_server_visible"] == "1")

            if "mp_xboxlive_visible" in self.options_data:
                self.xbox_visible_var.set(self.options_data["mp_xboxlive_visible"] == "1")

            if "auto_update_enabled" in self.options_data:
                self.autoupdate_var.set(self.options_data["auto_update_enabled"] == "1")

            # Update labels of sliders
            for widget in self.scroll_visual.winfo_children():
                if isinstance(widget, ctk.CTkFrame):
                    lbls = [w for w in widget.winfo_children() if isinstance(w, ctk.CTkLabel)]
                    # This is a bit hacky, but should work if we find the correct label
                    # Actually, the create_slider_setting stores its own label reference if we wanted to
                    pass

        except Exception as e:
            print(f"Error updating visual UI: {e}")

    def sync_data_from_ui(self):
        self.options_data["gfx_viewdistance"] = str(int(self.view_distance_var.get()) * 16)
        self.options_data["gfx_max_framerate"] = str(int(self.max_fps_var.get()))
        self.options_data["gfx_vsync"] = "1" if self.vsync_var.get() else "0"
        self.options_data["gfx_gamma"] = f"{self.gamma_var.get():.6f}"
        self.options_data["gfx_fullscreen"] = "1" if self.fullscreen_var.get() else "0"
        self.options_data["gfx_fancyskies"] = "1" if self.fancyskies_var.get() else "0"
        self.options_data["gfx_smoothlighting"] = "1" if self.smoothlighting_var.get() else "0"
        self.options_data["graphics_mode"] = str(c.UI_GC_GRAPHICS_MODE_MAP.index(self.graphics_mode_var.get()))

        self.options_data["game_difficulty_new"] = str(c.UI_GC_DIFFICULTY_MAP.index(self.difficulty_var.get()))
        self.options_data["game_thirdperson"] = str(c.UI_GC_PERSPECTIVE_MAP.index(self.perspective_var.get()))
        self.options_data["game_language"] = f'"{self.game_lang_var.get()}"'

        self.options_data["ctrl_sensitivity2_mouse"] = f"{self.sensitivity_var.get():.6f}"
        self.options_data["ctrl_invertmouse_mouse"] = "1" if self.invert_mouse_var.get() else "0"
        self.options_data["ctrl_autojump_mouse"] = "1" if self.autojump_var.get() else "0"
        self.options_data["ctrl_islefthanded"] = "1" if self.lefthanded_var.get() else "0"
        self.options_data["ctrl_swapjumpandsneak"] = "1" if self.swapjumpsneak_var.get() else "0"

        self.options_data["audio_sound"] = f"{self.sound_vol_var.get():.6f}"
        self.options_data["audio_music"] = f"{self.music_vol_var.get():.6f}"

        self.options_data["mp_server_visible"] = "1" if self.server_visible_var.get() else "0"
        self.options_data["mp_xboxlive_visible"] = "1" if self.xbox_visible_var.get() else "0"
        self.options_data["auto_update_enabled"] = "1" if self.autoupdate_var.get() else "0"
