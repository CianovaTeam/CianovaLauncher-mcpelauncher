import customtkinter as ctk
from src.gui import custom_dialogs as messagebox
import os

from src import constants as c
from src.core import language_manager
from src.utils.dialogs import ask_open_filename_native
from src.utils.resource_path import resource_path


class SettingsTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app

        self.pack(fill="both", expand=True)

        # Usar ScrollableFrame
        self.scroll_settings = ctk.CTkScrollableFrame(
            self, fg_color="transparent"
        )
        self.scroll_settings.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Gestión de Perfiles (NUEVO) ---
        self.frame_profiles = ctk.CTkFrame(self.scroll_settings, corner_radius=12)
        self.frame_profiles.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            self.frame_profiles,
            text=c.UI_PROFILES_MANAGER_TITLE,
            font=c.FONT_SUBTITLE,
        ).pack(pady=(c.SECTION_PADDING, 5))

        self.f_profile_selector = ctk.CTkFrame(self.frame_profiles, fg_color="transparent")
        self.f_profile_selector.pack(pady=(0, 15))

        ctk.CTkLabel(self.f_profile_selector, text=c.UI_LABEL_PROFILE, font=c.FONT_NORMAL).pack(side="left", padx=5)

        self.profile_var = ctk.StringVar(value=self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.UI_PROFILE_DEFAULT))
        self.combo_profile = ctk.CTkComboBox(
            self.f_profile_selector,
            values=self.app.logic.get_profiles(self.app),
            command=self.on_profile_change,
            variable=self.profile_var,
            width=200,
            font=c.FONT_NORMAL,
        )
        self.combo_profile.pack(side="left", padx=5)

        self.btn_manage_profiles = ctk.CTkButton(
            self.f_profile_selector,
            text="⚙️",
            width=35,
            command=self.open_profile_manager,
            font=c.FONT_BOLD
        )
        self.btn_manage_profiles.pack(side="left", padx=5)

        # --- Configuración de Binarios ---
        self.frame_bin = ctk.CTkFrame(self.scroll_settings, corner_radius=12)
        self.frame_bin.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            self.frame_bin,
            text=c.UI_SECTION_BINARIES,
            font=c.FONT_SUBTITLE,
        ).pack(pady=c.SECTION_PADDING)

        # Selector de Modo
        if not self.app.running_in_flatpak:
            mode_keys = [c.MODE_BIN_SYSTEM, c.MODE_BIN_LOCAL, c.MODE_BIN_CUSTOM, c.MODE_BIN_FLATPAK]
        else:
            mode_keys = [c.MODE_BIN_SYSTEM, c.MODE_BIN_CUSTOM, c.MODE_BIN_FLATPAK]

        modes_display = [c.UI_BIN_MODES[k] for k in mode_keys]

        self.combo_settings_mode = ctk.CTkComboBox(
            self.frame_bin,
            values=modes_display,
            command=self.on_settings_mode_change,
            width=250,
            font=c.FONT_NORMAL,
        )
        self.combo_settings_mode.pack(pady=(0, 15))
        current_mode = self.app.config.get(c.CONFIG_KEY_MODE, c.UI_DEFAULT_MODE)
        self.combo_settings_mode.set(c.UI_BIN_MODES.get(current_mode, c.UI_BIN_MODES[c.MODE_BIN_SYSTEM]))

        # Flatpak Selector (Solo visible si es Flatpak)
        self.frame_flatpak_id = ctk.CTkFrame(self.frame_bin, fg_color="transparent")
        ctk.CTkLabel(
            self.frame_flatpak_id, text=c.UI_LABEL_FLATPAK_ID, width=150, anchor="w"
        ).pack(side="left")
        self.entry_flatpak_id = ctk.CTkEntry(self.frame_flatpak_id)
        self.entry_flatpak_id.pack(side="left", fill="x", expand=True)
        self.entry_flatpak_id.insert(
            0, self.app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.MCPELAUNCHER_FLATPAK_ID)
        )
        self.btn_flatpak_custom = ctk.CTkButton(
            self.frame_flatpak_id,
            text="?",
            width=30,
            command=lambda: messagebox.showinfo(
                self, c.UI_INFO_TITLE, c.UI_FLATPAK_ID_EXAMPLE
            ),
        )
        self.btn_flatpak_custom.pack(side="right", padx=5)

        # Helper
        def create_path_input(parent, label, key, file_types):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(f, text=label, width=150, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(f)
            entry.pack(side="left", fill="x", expand=True, padx=5)
            entry.insert(0, self.app.config[c.CONFIG_KEY_BINARY_PATHS].get(key, ""))

            def browse():
                path = ask_open_filename_native(self.app, title=f"{c.UI_OPEN_FILE_TITLE} {label}", filetypes=file_types)
                if path:
                    entry.delete(0, "end")
                    entry.insert(0, path)

            btn = ctk.CTkButton(f, text="...", width=40, command=browse)
            btn.pack(side="right")
            return entry, btn, f

        # Inputs
        self.entry_client, self.btn_client, self.f_client = create_path_input(
            self.frame_bin, c.UI_LABEL_CLIENT_GAME, c.CONFIG_KEY_CLIENT, [(c.UI_ALL_FILES_TYPE, "*")]
        )
        self.entry_extract, self.btn_extract, self.f_extract = create_path_input(
            self.frame_bin, c.UI_LABEL_EXTRACTOR_APK, c.CONFIG_KEY_EXTRACT, [(c.UI_ALL_FILES_TYPE, "*")]
        )
        self.entry_webview, self.btn_webview, self.f_webview = create_path_input(
            self.frame_bin, c.UI_LABEL_WEBVIEW_OPTIONAL, c.CONFIG_KEY_WEBVIEW, [(c.UI_ALL_FILES_TYPE, "*")]
        )
        self.entry_error, self.btn_error, self.f_error = create_path_input(
            self.frame_bin, c.UI_LABEL_ERROR_HANDLER_OPTIONAL, c.CONFIG_KEY_ERROR, [(c.UI_ALL_FILES_TYPE, "*")]
        )

        # Botones de Acción
        frame_actions = ctk.CTkFrame(self.scroll_settings, fg_color="transparent")
        frame_actions.pack(pady=c.SECTION_PADDING)

        ctk.CTkButton(
            frame_actions,
            text=c.UI_BUTTON_SAVE_SETTINGS,
            height=c.BTN_HEIGHT,
            command=self.save_settings,
            font=c.FONT_NORMAL,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            frame_actions,
            text=c.UI_BUTTON_RESTORE_DEFAULTS,
            height=c.BTN_HEIGHT,
            command=self.app.restore_default_settings,
            font=c.FONT_NORMAL,
        ).pack(side="left", padx=10)

        # --- Opciones de Compatibilidad ---
        frame_compat = ctk.CTkFrame(self.scroll_settings, corner_radius=c.CORNER_RADIUS)
        frame_compat.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            frame_compat,
            text=c.UI_SECTION_COMPATIBILITY,
            font=c.FONT_SUBTITLE,
        ).pack(pady=c.SECTION_PADDING)

        # Nvidia Prime
        f_nvidia = ctk.CTkFrame(frame_compat, fg_color="transparent")
        f_nvidia.pack(fill="x", padx=15, pady=2)
        self.var_nvidia_prime = ctk.BooleanVar(value=self.app.config.get(c.CONFIG_KEY_NVIDIA_PRIME, False))
        self.check_nvidia_prime = ctk.CTkCheckBox(f_nvidia, text=c.UI_NVIDIA_PRIME_CHECKBOX, variable=self.var_nvidia_prime)
        self.check_nvidia_prime.pack(side="left")
        ctk.CTkButton(f_nvidia, text="?", width=30, command=lambda: messagebox.showinfo(self, c.UI_NVIDIA_PRIME_CHECKBOX, c.UI_NVIDIA_PRIME_TOOLTIP)).pack(side="right", padx=5)

        # Zink
        f_zink = ctk.CTkFrame(frame_compat, fg_color="transparent")
        f_zink.pack(fill="x", padx=15, pady=2)
        self.var_zink = ctk.BooleanVar(value=self.app.config.get(c.CONFIG_KEY_ZINK_MODE, False))
        self.check_zink = ctk.CTkCheckBox(f_zink, text=c.UI_ZINK_CHECKBOX, variable=self.var_zink)
        self.check_zink.pack(side="left")
        ctk.CTkButton(f_zink, text="?", width=30, command=lambda: messagebox.showinfo(self, c.UI_ZINK_CHECKBOX, c.UI_ZINK_TOOLTIP)).pack(side="right", padx=5)

        # Custom Env
        f_custom_env = ctk.CTkFrame(frame_compat, fg_color="transparent")
        f_custom_env.pack(fill="x", padx=15, pady=2)
        self.var_custom_env = ctk.BooleanVar(value=self.app.config.get(c.CONFIG_KEY_CUSTOM_ENV_ENABLED, False))
        self.check_custom_env = ctk.CTkCheckBox(f_custom_env, text=c.UI_CUSTOM_ARGS_CHECKBOX, variable=self.var_custom_env, command=self.toggle_custom_env)
        self.check_custom_env.pack(side="left")
        ctk.CTkButton(f_custom_env, text="?", width=30, command=lambda: messagebox.showinfo(self, c.UI_CUSTOM_ARGS_CHECKBOX, c.UI_CUSTOM_ARGS_TOOLTIP)).pack(side="right", padx=5)

        # GameMode
        f_gamemode = ctk.CTkFrame(frame_compat, fg_color="transparent")
        f_gamemode.pack(fill="x", padx=15, pady=2)
        self.var_gamemode = ctk.BooleanVar(value=self.app.config.get(c.CONFIG_KEY_GAMEMODE_ENABLED, False))
        self.check_gamemode = ctk.CTkCheckBox(
            f_gamemode,
            text=c.UI_GAMEMODE_CHECKBOX,
            variable=self.var_gamemode,
            command=lambda: self.app.sync_gamemode_ui(self.var_gamemode.get())
        )
        self.check_gamemode.pack(side="left")
        ctk.CTkButton(f_gamemode, text="?", width=30, command=lambda: messagebox.showinfo(self, c.UI_GAMEMODE_CHECKBOX, c.UI_GAMEMODE_TOOLTIP)).pack(side="right", padx=5)

        # Cerrar al Jugar
        f_close = ctk.CTkFrame(frame_compat, fg_color="transparent")
        f_close.pack(fill="x", padx=15, pady=2)
        self.var_close_on_launch = ctk.BooleanVar(value=self.app.config.get(c.CONFIG_KEY_CLOSE_ON_LAUNCH, False))
        self.check_close_on_launch = ctk.CTkCheckBox(
            f_close,
            text=c.UI_CHECKBOX_CLOSE_ON_LAUNCH,
            variable=self.var_close_on_launch,
            command=lambda: self.app.sync_close_on_launch_ui(self.var_close_on_launch.get())
        )
        self.check_close_on_launch.pack(side="left")

        # Custom Env Entry
        self.f_custom_vars = ctk.CTkFrame(frame_compat, fg_color="transparent")
        self.f_custom_vars.pack(fill="x", padx=15, pady=(2, 10))
        ctk.CTkLabel(self.f_custom_vars, text=c.UI_CUSTOM_ARGS_LABEL).pack(side="left", padx=5)
        self.entry_custom_vars = ctk.CTkEntry(self.f_custom_vars)
        self.entry_custom_vars.pack(side="left", fill="x", expand=True, padx=5)
        self.entry_custom_vars.insert(0, self.app.config.get(c.CONFIG_KEY_CUSTOM_ENV_VARS, ""))


        # --- Configuración de Apariencia (Movida al final) ---
        frame_appearance = ctk.CTkFrame(self.scroll_settings, corner_radius=c.CORNER_RADIUS)
        frame_appearance.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            frame_appearance,
            text=c.UI_SECTION_APPEARANCE,
            font=c.FONT_SUBTITLE,
        ).pack(pady=c.SECTION_PADDING)

        f_appearance_opts = ctk.CTkFrame(frame_appearance, fg_color="transparent")
        f_appearance_opts.pack(pady=5)

        # Color Tema
        ctk.CTkLabel(f_appearance_opts, text=c.UI_LABEL_COLOR_THEME).grid(row=0, column=0, padx=5, pady=5)

        # Combinar temas estáticos y dinámicos
        theme_keys = list(c.UI_THEME_NAMES.keys())
        themes_dir = resource_path(os.path.join("src", "themes"))
        if os.path.exists(themes_dir):
            for f in os.listdir(themes_dir):
                if f.endswith(".json"):
                    t_name = f[:-5]
                    if t_name not in theme_keys:
                        theme_keys.append(t_name)

        # Obtener nombres para mostrar (traducidos si están en el diccionario, sino capitalizados)
        self.theme_map = {c.UI_THEME_NAMES.get(k, k.capitalize()): k for k in theme_keys}

        self.option_color = ctk.CTkOptionMenu(
            f_appearance_opts,
            values=list(self.theme_map.keys()),
            command=self.on_theme_change
        )
        self.option_color.grid(row=0, column=1, padx=10, pady=5)
        current_theme = self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")

        # Encontrar el nombre a mostrar para el tema actual
        current_display = next((display for display, key in self.theme_map.items() if key == current_theme), "Blue")
        self.option_color.set(current_display)

        # Modo de Apariencia
        ctk.CTkLabel(f_appearance_opts, text=c.UI_LABEL_APPEARANCE_MODE).grid(row=1, column=0, padx=5, pady=5)
        self.option_appearance = ctk.CTkOptionMenu(
            f_appearance_opts,
            values=list(c.UI_APPEARANCE_MODES.values()),
            command=self.on_appearance_mode_change
        )
        self.option_appearance.grid(row=1, column=1, padx=10, pady=5)
        current_app_mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        self.option_appearance.set(c.UI_APPEARANCE_MODES.get(current_app_mode, "Dark"))

        # Idioma
        ctk.CTkLabel(f_appearance_opts, text=c.UI_LABEL_LANGUAGE).grid(row=2, column=0, padx=5, pady=5)
        self.langs_dict = language_manager.get_available_languages()
        self.option_lang = ctk.CTkOptionMenu(
            f_appearance_opts,
            values=list(self.langs_dict.values()),
            command=self.on_language_change
        )
        self.option_lang.grid(row=2, column=1, padx=10, pady=5)
        current_lang = self.app.config.get(c.CONFIG_KEY_LANGUAGE, "en")
        self.option_lang.set(self.langs_dict.get(current_lang, "English"))

        # Estilo de Lista
        ctk.CTkLabel(f_appearance_opts, text=c.UI_LABEL_VERSION_LIST_STYLE).grid(row=3, column=0, padx=5, pady=5)
        self.option_list_style = ctk.CTkOptionMenu(
            f_appearance_opts,
            values=list(c.UI_LIST_STYLES.values()),
            command=self.on_appearance_setting_change
        )
        self.option_list_style.grid(row=3, column=1, padx=10, pady=5)
        current_style = self.app.config.get(c.CONFIG_KEY_VERSION_LIST_STYLE, c.STYLE_LIST)
        self.option_list_style.set(c.UI_LIST_STYLES.get(current_style, c.UI_LIST_STYLES[c.STYLE_LIST]))

        # Diseño de Herramientas
        ctk.CTkLabel(f_appearance_opts, text=c.UI_LABEL_TOOLS_LAYOUT).grid(row=4, column=0, padx=5, pady=5)
        self.option_tools_layout = ctk.CTkOptionMenu(
            f_appearance_opts,
            values=list(c.UI_TOOLS_LAYOUTS.values()),
            command=self.on_appearance_setting_change
        )
        self.option_tools_layout.grid(row=4, column=1, padx=10, pady=5)
        current_tools_layout = self.app.config.get(c.CONFIG_KEY_TOOLS_LAYOUT, c.STYLE_COLUMNS)
        self.option_tools_layout.set(c.UI_TOOLS_LAYOUTS.get(current_tools_layout, c.UI_TOOLS_LAYOUTS[c.STYLE_COLUMNS]))

        # Tamaño de Icono
        ctk.CTkLabel(f_appearance_opts, text=c.UI_LABEL_ICON_SIZE).grid(row=5, column=0, padx=5, pady=5)
        self.slider_icon_size = ctk.CTkSlider(
            f_appearance_opts,
            from_=16,
            to=128,
            number_of_steps=112,
            command=self.on_appearance_setting_change
        )
        self.slider_icon_size.grid(row=5, column=1, padx=10, pady=5)
        self.slider_icon_size.set(self.app.config.get(c.CONFIG_KEY_VERSION_ICON_SIZE, 32))

        self.lbl_icon_size_val = ctk.CTkLabel(f_appearance_opts, text=str(int(self.slider_icon_size.get())))
        self.lbl_icon_size_val.grid(row=5, column=2, padx=5)

        # Tamaño de Título
        ctk.CTkLabel(f_appearance_opts, text=c.UI_LABEL_TITLE_SIZE).grid(row=6, column=0, padx=5, pady=5)
        self.slider_title_size = ctk.CTkSlider(
            f_appearance_opts,
            from_=8,
            to=32,
            number_of_steps=24,
            command=self.on_appearance_setting_change
        )
        self.slider_title_size.grid(row=6, column=1, padx=10, pady=5)
        self.slider_title_size.set(self.app.config.get(c.CONFIG_KEY_VERSION_TITLE_SIZE, 13))

        self.lbl_title_size_val = ctk.CTkLabel(f_appearance_opts, text=str(int(self.slider_title_size.get())))
        self.lbl_title_size_val.grid(row=6, column=2, padx=5)

        ctk.CTkLabel(
            frame_appearance,
            text=c.UI_RESTART_REQUIRED_MSG,
            text_color="gray",
            font=c.FONT_SMALL,
        ).pack()

        ctk.CTkLabel(
            frame_appearance,
            text=c.UI_APPEARANCE_HINT,
            text_color="gray",
            font=c.FONT_SMALL,
        ).pack(pady=(0, 10))

        # Inicializar estado visual
        self.on_settings_mode_change(self.combo_settings_mode.get())
        self.toggle_custom_env()

    def toggle_custom_env(self):
        enabled = self.var_custom_env.get()
        if enabled:
            self.check_nvidia_prime.configure(state="disabled")
            self.check_zink.configure(state="disabled")
            self.entry_custom_vars.configure(state="normal", fg_color=["#F9F9FA", "#343638"])
        else:
            self.check_nvidia_prime.configure(state="normal")
            self.check_zink.configure(state="normal")
            self.entry_custom_vars.configure(state="disabled", fg_color="gray30")

    def on_settings_mode_change(self, display_name):
        # Encontrar la clave interna a partir del nombre mostrado
        mode_key = next((k for k, v in c.UI_BIN_MODES.items() if v == display_name), c.MODE_BIN_SYSTEM)

        # Lógica para ocultar/mostrar/deshabilitar inputs según modo
        is_flatpak_mode = mode_key == c.MODE_BIN_FLATPAK
        is_flatpak_custom = mode_key == c.MODE_BIN_FLATPAK
        is_custom_bin = mode_key == c.MODE_BIN_CUSTOM

        # 1. Selector de ID Flatpak
        if is_flatpak_mode:
            self.frame_flatpak_id.pack(fill="x", padx=10, pady=5, before=self.f_client)
            if is_flatpak_custom:
                self.entry_flatpak_id.configure(
                    state="normal", fg_color=["#F9F9FA", "#343638"]
                )
            else:
                self.entry_flatpak_id.configure(state="disabled", fg_color="gray30")
        else:
            self.frame_flatpak_id.pack_forget()

        # 2. Estado de Inputs de Binarios
        state = "normal" if is_custom_bin else "disabled"

        for e, b in [
            (self.entry_client, self.btn_client),
            (self.entry_extract, self.btn_extract),
            (self.entry_webview, self.btn_webview),
            (self.entry_error, self.btn_error),
        ]:
            if is_custom_bin:
                e.configure(state="normal", fg_color=["#F9F9FA", "#343638"])
            else:
                e.configure(state="disabled", fg_color="gray30")
            b.configure(state=state)

    def on_theme_change(self, display_name):
        theme_key = self.theme_map.get(display_name, "blue")
        self.app.change_appearance("color", theme_key)

    def on_appearance_mode_change(self, display_name):
        mode_key = next((k for k, v in c.UI_APPEARANCE_MODES.items() if v == display_name), "Dark")
        ctk.set_appearance_mode(mode_key)
        self.app.config[c.CONFIG_KEY_APPEARANCE] = mode_key
        self.app.config_manager.save_config()

    def on_language_change(self, display_name):
        # Encontrar código a partir de nombre
        lang_code = next((k for k, v in self.langs_dict.items() if v == display_name), "en")
        self.app.config[c.CONFIG_KEY_LANGUAGE] = lang_code
        messagebox.showinfo(
            self,
            c.UI_RESTART_REQUIRED_TITLE,
            c.UI_RESTART_MSG,
        )
        self.app.config_manager.save_config()

    def on_appearance_setting_change(self, *args):
        # Actualizar labels
        self.lbl_icon_size_val.configure(text=str(int(self.slider_icon_size.get())))
        self.lbl_title_size_val.configure(text=str(int(self.slider_title_size.get())))

        # Guardar valores
        display_style = self.option_list_style.get()
        style_key = next((k for k, v in c.UI_LIST_STYLES.items() if v == display_style), c.STYLE_LIST)

        display_tools = self.option_tools_layout.get()
        tools_key = next((k for k, v in c.UI_TOOLS_LAYOUTS.items() if v == display_tools), c.STYLE_COLUMNS)

        self.app.config[c.CONFIG_KEY_VERSION_LIST_STYLE] = style_key
        self.app.config[c.CONFIG_KEY_TOOLS_LAYOUT] = tools_key
        self.app.config[c.CONFIG_KEY_VERSION_ICON_SIZE] = int(self.slider_icon_size.get())
        self.app.config[c.CONFIG_KEY_VERSION_TITLE_SIZE] = int(self.slider_title_size.get())

        self.app.config_manager.save_config()

        # Refrescar lista de versiones si es posible
        if hasattr(self.app, "logic") and hasattr(self.app.logic, "refresh_version_list"):
            self.app.logic.refresh_version_list(self.app)

        # Refrescar herramientas
        if hasattr(self.app, "tools_tab") and hasattr(self.app.tools_tab, "refresh_tools_ui"):
            self.app.tools_tab.refresh_tools_ui()

    def on_profile_change(self, profile_name):
        self.app.logic.switch_profile(self.app, profile_name)
        # Sincronizar en otros sitios si es necesario
        if hasattr(self.app.play_tab, "update_profile_indicator"):
            self.app.play_tab.update_profile_indicator()

    def open_profile_manager(self):
        from src.gui.profile_manager_dialog import ProfileManagerDialog
        ProfileManagerDialog(self.app, self.app)
        self.refresh_profile_list()

    def refresh_profile_list(self):
        profiles = self.app.logic.get_profiles(self.app)
        self.combo_profile.configure(values=profiles)
        current = self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE)
        self.profile_var.set(current)

    def save_settings(self):
        display_name = self.combo_settings_mode.get()
        mode_key = next((k for k, v in c.UI_BIN_MODES.items() if v == display_name), c.MODE_BIN_SYSTEM)

        self.app.config[c.CONFIG_KEY_MODE] = mode_key
        self.app.config[c.CONFIG_KEY_FLATPAK_ID] = self.entry_flatpak_id.get()

        # Opciones de Compatibilidad
        self.app.config[c.CONFIG_KEY_NVIDIA_PRIME] = self.var_nvidia_prime.get()
        self.app.config[c.CONFIG_KEY_ZINK_MODE] = self.var_zink.get()
        self.app.config[c.CONFIG_KEY_CUSTOM_ENV_ENABLED] = self.var_custom_env.get()
        self.app.config[c.CONFIG_KEY_CUSTOM_ENV_VARS] = self.entry_custom_vars.get()
        self.app.config[c.CONFIG_KEY_GAMEMODE_ENABLED] = self.var_gamemode.get()

        # Solo guardar paths si es personalizado
        if mode_key == c.MODE_BIN_CUSTOM:
            self.app.config[c.CONFIG_KEY_BINARY_PATHS][c.CONFIG_KEY_CLIENT] = self.entry_client.get()
            self.app.config[c.CONFIG_KEY_BINARY_PATHS][c.CONFIG_KEY_EXTRACT] = self.entry_extract.get()
            self.app.config[c.CONFIG_KEY_BINARY_PATHS][c.CONFIG_KEY_WEBVIEW] = self.entry_webview.get()
            self.app.config[c.CONFIG_KEY_BINARY_PATHS][c.CONFIG_KEY_ERROR] = self.entry_error.get()

        self.app.config_manager.save_config()
        messagebox.showinfo(
            self,
            c.UI_SUCCESS_TITLE,
            c.UI_SAVE_SUCCESS_MSG,
        )
