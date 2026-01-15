import customtkinter as ctk
from tkinter import messagebox

from src import constants as c
from src.utils.dialogs import ask_open_filename_native
from src.utils.system import is_nvidia_gpu_present


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

        # --- Configuración de Binarios ---
        self.frame_bin = ctk.CTkFrame(self.scroll_settings, corner_radius=12)
        self.frame_bin.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            self.frame_bin,
            text=c.UI_SECTION_BINARIES,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=10)

        # Selector de Modo
        if not self.app.running_in_flatpak:
            modes = c.UI_MODES_SETTINGS_NORMAL
        else:
            modes = c.UI_MODES_SETTINGS_FLATPAK

        self.combo_settings_mode = ctk.CTkComboBox(
            self.frame_bin,
            values=modes,
            command=self.on_settings_mode_change,
            width=250,
        )
        self.combo_settings_mode.pack(pady=(0, 15))
        self.combo_settings_mode.set(self.app.config.get(c.CONFIG_KEY_MODE, c.UI_DEFAULT_MODE))

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
                c.UI_INFO_TITLE, c.UI_FLATPAK_ID_EXAMPLE
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
                path = ask_open_filename_native(self.app, title=f"Seleccionar {label}", filetypes=file_types)
                if path:
                    entry.delete(0, "end")
                    entry.insert(0, path)

            btn = ctk.CTkButton(f, text="...", width=40, command=browse)
            btn.pack(side="right")
            return entry, btn, f

        # Inputs
        self.entry_client, self.btn_client, self.f_client = create_path_input(
            self.frame_bin, "Cliente (game):", c.CONFIG_KEY_CLIENT, [("Ejecutable", "*")]
        )
        self.entry_extract, self.btn_extract, self.f_extract = create_path_input(
            self.frame_bin, "Extractor APK:", c.CONFIG_KEY_EXTRACT, [("Ejecutable", "*")]
        )
        self.entry_webview, self.btn_webview, self.f_webview = create_path_input(
            self.frame_bin, "Webview (Opcional):", c.CONFIG_KEY_WEBVIEW, [("Ejecutable", "*")]
        )
        self.entry_error, self.btn_error, self.f_error = create_path_input(
            self.frame_bin, "Error Handler (Opcional):", c.CONFIG_KEY_ERROR, [("Ejecutable", "*")]
        )

        # Botones de Acción
        frame_actions = ctk.CTkFrame(self.scroll_settings, fg_color="transparent")
        frame_actions.pack(pady=10)

        ctk.CTkButton(
            frame_actions,
            text=c.UI_BUTTON_SAVE_SETTINGS,
            fg_color=c.COLOR_PRIMARY_GREEN,
            hover_color=c.COLOR_PRIMARY_GREEN_HOVER,
            command=self.save_settings,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            frame_actions,
            text="Restaurar valores",
            fg_color=c.COLOR_ORANGE_BUTTON,
            hover_color=c.COLOR_ORANGE_BUTTON_HOVER,
            command=self.app.restore_default_settings,
        ).pack(side="left", padx=10)

        # --- Opciones de Compatibilidad ---
        if self.app.running_in_flatpak and is_nvidia_gpu_present():
            frame_compat = ctk.CTkFrame(self.scroll_settings, corner_radius=12)
            frame_compat.pack(fill="x", padx=10, pady=10)

            ctk.CTkLabel(
                frame_compat,
                text="Compatibilidad",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(pady=10)

            f_nvidia = ctk.CTkFrame(frame_compat, fg_color="transparent")
            f_nvidia.pack(fill="x", padx=15, pady=5)

            self.check_nvidia_compat_var = ctk.BooleanVar(value=self.app.config.get(c.CONFIG_KEY_NVIDIA_COMPAT_MODE, False))
            self.check_nvidia_compat = ctk.CTkCheckBox(
                f_nvidia,
                text=c.UI_NVIDIA_COMPAT_MODE_CHECKBOX,
                variable=self.check_nvidia_compat_var
            )
            self.check_nvidia_compat.pack(side="left", anchor="w")

            btn_nvidia_help = ctk.CTkButton(
                f_nvidia,
                text="?",
                width=30,
                command=lambda: messagebox.showinfo(
                    "Modo de Compatibilidad Nvidia", c.UI_NVIDIA_COMPAT_MODE_TOOLTIP
                ),
            )
            btn_nvidia_help.pack(side="right", padx=5)


        # --- Configuración de Apariencia (Movida al final) ---
        frame_appearance = ctk.CTkFrame(self.scroll_settings, corner_radius=12)
        frame_appearance.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            frame_appearance,
            text=c.UI_SECTION_APPEARANCE,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=10)

        f_theme = ctk.CTkFrame(frame_appearance, fg_color="transparent")
        f_theme.pack(pady=5)

        # Solo Color Principal (eliminamos Light/Dark/System)
        ctk.CTkLabel(f_theme, text=c.UI_LABEL_COLOR_THEME).pack(side="left", padx=5)
        self.option_color = ctk.CTkOptionMenu(
            f_theme,
            values=c.UI_COLOR_THEMES,
            command=lambda color: self.app.change_appearance("color", color),
        )
        self.option_color.pack(side="left", padx=10)
        self.option_color.set(self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue"))

        ctk.CTkLabel(
            frame_appearance,
            text=c.UI_RESTART_REQUIRED_MSG,
            text_color="gray",
            font=ctk.CTkFont(size=10),
        ).pack()

        ctk.CTkLabel(
            frame_appearance,
            text="Esto solo cambia ligeramente la IU, no la cambia radicalmente.",
            text_color="gray",
            font=ctk.CTkFont(size=10),
        ).pack(pady=(0, 10))

        # Inicializar estado visual
        self.on_settings_mode_change(self.combo_settings_mode.get())

    def on_settings_mode_change(self, mode):
        # Lógica para ocultar/mostrar/deshabilitar inputs según modo
        is_flatpak_mode = "Flatpak" in mode
        is_flatpak_custom = mode == "Flatpak (Personalizado)"
        is_custom_bin = mode == "Personalizado"

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

    def save_settings(self):
        mode = self.combo_settings_mode.get()
        self.app.config[c.CONFIG_KEY_MODE] = mode
        self.app.config[c.CONFIG_KEY_FLATPAK_ID] = self.entry_flatpak_id.get()
        if hasattr(self, 'check_nvidia_compat'):
            self.app.config[c.CONFIG_KEY_NVIDIA_COMPAT_MODE] = self.check_nvidia_compat.get()

        # Solo guardar paths si es personalizado
        if "Personalizado" in mode:
            self.app.config[c.CONFIG_KEY_BINARY_PATHS][c.CONFIG_KEY_CLIENT] = self.entry_client.get()
            self.app.config[c.CONFIG_KEY_BINARY_PATHS][c.CONFIG_KEY_EXTRACT] = self.entry_extract.get()
            self.app.config[c.CONFIG_KEY_BINARY_PATHS][c.CONFIG_KEY_WEBVIEW] = self.entry_webview.get()
            self.app.config[c.CONFIG_KEY_BINARY_PATHS][c.CONFIG_KEY_ERROR] = self.entry_error.get()

        self.app.config_manager.save_config()
        messagebox.showinfo(
            c.UI_SUCCESS_TITLE,
            c.UI_SAVE_SUCCESS_MSG,
        )
