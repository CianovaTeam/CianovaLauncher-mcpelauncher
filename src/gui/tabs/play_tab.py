import customtkinter as ctk

from src import constants as c


class PlayTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app

        self.pack(fill="both", expand=True)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Cabecera
        self.frame_header = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_header.grid(row=0, column=0, pady=(5, 5), sticky="ew")

        self.lbl_status = ctk.CTkLabel(
            self.frame_header,
            text=c.UI_LABEL_SEARCHING,
            font=c.FONT_MODO,
        )
        self.lbl_status.pack(side="left", padx=10)

        # Selector de modo con opciones según contexto
        if self.app.running_in_flatpak:
            mode_keys = [c.MODE_INSTALL_OWN, c.MODE_INSTALL_SHARED, c.MODE_INSTALL_FLATPAK]
        else:
            mode_keys = [c.MODE_INSTALL_LOCAL, c.MODE_INSTALL_FLATPAK]

        mode_values = [c.UI_INSTALL_MODES[k] for k in mode_keys]

        self.combo_mode = ctk.CTkComboBox(
            self.frame_header,
            values=mode_values,
            command=lambda mode: self.app.logic.change_mode_ui(self.app, mode),
            width=180,
            height=28,
            corner_radius=8,
            font=c.FONT_NORMAL,
        )
        self.combo_mode.pack(side="right", padx=10)
        ctk.CTkLabel(
            self.frame_header,
            text=c.UI_LABEL_INSTALLATION,
            text_color="gray",
            font=c.FONT_SMALL,
        ).pack(side="right", padx=5)

        # Lista (Card Style)
        self.version_listbox = ctk.CTkScrollableFrame(
            self, label_text=c.UI_LABEL_INSTALLED_VERSIONS, corner_radius=c.CORNER_RADIUS
        )
        self.version_listbox.grid(row=2, column=0, padx=15, pady=5, sticky="nsew")
        self.version_var = ctk.StringVar(value="")

        # Opciones
        self.frame_launch_opts = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_launch_opts.grid(row=3, column=0, pady=5)

        self.var_close_on_launch = ctk.BooleanVar(
            value=self.app.config.get(c.CONFIG_KEY_CLOSE_ON_LAUNCH, False)
        )
        self.check_close_on_launch = ctk.CTkCheckBox(
            self.frame_launch_opts,
            text=c.UI_CHECKBOX_CLOSE_ON_LAUNCH,
            variable=self.var_close_on_launch,
            corner_radius=15,
            font=c.FONT_NORMAL,
            command=self.save_quick_opts
        )
        self.check_close_on_launch.pack(side="left", padx=10)

        self.var_gamemode = ctk.BooleanVar(
            value=self.app.config.get(c.CONFIG_KEY_GAMEMODE_ENABLED, False)
        )
        self.check_gamemode = ctk.CTkCheckBox(
            self.frame_launch_opts,
            text=c.UI_CHECKBOX_GAMEMODE,
            variable=self.var_gamemode,
            corner_radius=15,
            font=c.FONT_NORMAL,
            command=self.save_quick_opts
        )
        self.check_gamemode.pack(side="left", padx=10)

        self.var_debug_log = ctk.BooleanVar(value=self.app.config.get(c.CONFIG_KEY_DEBUG_LOG, False))

        # Ocultar la opción de log en Flatpak
        if not self.app.running_in_flatpak:
            self.check_debug_log = ctk.CTkCheckBox(
                self.frame_launch_opts,
                text=c.UI_CHECKBOX_DEBUG_LOG,
                variable=self.var_debug_log,
                corner_radius=15,
                font=c.FONT_NORMAL,
            )
            self.check_debug_log.pack(side="left", padx=10)

        # Botón
        self.btn_launch = ctk.CTkButton(
            self,
            text=c.UI_BUTTON_PLAY_NOW,
            height=50,
            corner_radius=15,
            font=c.FONT_TITLE,
            command=lambda: self.app.logic.launch_game(self.app),
        )
        self.btn_launch.grid(row=4, column=0, padx=30, pady=15, sticky="ew")

    def save_quick_opts(self):
        self.app.config[c.CONFIG_KEY_CLOSE_ON_LAUNCH] = self.var_close_on_launch.get()
        self.app.sync_gamemode_ui(self.var_gamemode.get())
        self.app.config_manager.save_config()
