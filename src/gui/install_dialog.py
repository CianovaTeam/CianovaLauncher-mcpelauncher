import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import platform
import zipfile
from src.utils.dialogs import ask_open_filename_native
from src import constants as c

class InstallDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title(c.UI_INSTALL_NEW_VERSION_TITLE)
        self.geometry("550x620")
        self.resizable(False, False)

        self.transient(parent)

        # Variables
        self.apk_path = ctk.StringVar()
        self.ver_name = ctk.StringVar()
        self.target_mode = ctk.StringVar(
            value=c.MODE_INSTALL_FLATPAK if parent.is_flatpak else c.MODE_INSTALL_LOCAL
        )
        self.arch_status_text = ctk.StringVar(value="")
        self.arch_compatible = False

        # Layout
        self.grid_columnconfigure(0, weight=1)

        # 1. Selección de APK
        frame_apk = ctk.CTkFrame(self, corner_radius=c.CORNER_RADIUS)
        frame_apk.pack(fill="x", padx=25, pady=(25, 15))
        ctk.CTkLabel(frame_apk, text=c.UI_APK_FILE_LABEL, font=c.FONT_SUBTITLE).pack(anchor="w", padx=15, pady=(10, 5))

        self.entry_apk = ctk.CTkEntry(
            frame_apk,
            textvariable=self.apk_path,
            placeholder_text=c.UI_SELECT_APK_PLACEHOLDER,
            font=c.FONT_NORMAL,
        )
        self.entry_apk.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=5)
        ctk.CTkButton(frame_apk, text="...", width=40, command=self.browse_apk).pack(
            side="right", padx=(0, 10), pady=5
        )

        # Label de Estado de Arquitectura
        self.lbl_arch = ctk.CTkLabel(
            self,
            textvariable=self.arch_status_text,
            font=c.FONT_BOLD,
            wraplength=500
        )
        self.lbl_arch.pack(pady=(0, 15), padx=20)

        # 2. Nombre de la Versión
        frame_name = ctk.CTkFrame(self, corner_radius=c.CORNER_RADIUS)
        frame_name.pack(fill="x", padx=25, pady=15)
        ctk.CTkLabel(frame_name, text=c.UI_VERSION_NAME_LABEL, font=c.FONT_SUBTITLE).pack(
            anchor="w", padx=15, pady=(10, 5)
        )
        self.entry_name = ctk.CTkEntry(
            frame_name, textvariable=self.ver_name, placeholder_text=c.UI_VERSION_NAME_PLACEHOLDER, font=c.FONT_NORMAL
        )
        self.entry_name.pack(fill="x", padx=10, pady=5)

        # 3. Modo de Instalación (CRÍTICO)
        frame_mode = ctk.CTkFrame(self, corner_radius=c.CORNER_RADIUS)
        frame_mode.pack(fill="x", padx=25, pady=15)
        ctk.CTkLabel(frame_mode, text=c.UI_INSTALL_MODE_DEST_LABEL, font=c.FONT_SUBTITLE).pack(
            anchor="w", padx=15, pady=(10, 5)
        )

        self.flatpak_config_id = parent.config.get(
            c.CONFIG_KEY_FLATPAK_ID,
            c.DEFAULT_FLATPAK_ID,
        )

        # Opciones de destino según contexto
        if parent.running_in_flatpak:
            # Dentro de Flatpak: ofrecer Local Propio, Local Compartido y Flatpak Personalizado
            modes_available = [
                (c.MODE_INSTALL_OWN, c.UI_INSTALL_MODE_OWN),
                (c.MODE_INSTALL_SHARED, c.UI_INSTALL_MODE_SHARED),
                (c.MODE_INSTALL_FLATPAK, c.UI_INSTALL_MODE_FLATPAK_DESC),
            ]
            default_mode = c.MODE_INSTALL_OWN
        else:
            # Fuera de Flatpak: ofrecer Local y Flatpak Personalizado
            modes_available = [
                (c.MODE_INSTALL_LOCAL, c.UI_INSTALL_MODE_LOCAL),
                (c.MODE_INSTALL_FLATPAK, c.UI_INSTALL_MODE_FLATPAK_DESC),
            ]
            default_mode = c.MODE_INSTALL_LOCAL

        self.target_mode.set(default_mode)

        # Callback para habilitar/deshabilitar entrada ID
        def toggle_flatpak_entry():
            if self.target_mode.get() == c.MODE_INSTALL_FLATPAK:
                self.entry_flatpak_id.configure(
                    state="normal", fg_color=["#F9F9FA", "#343638"]
                )
            else:
                self.entry_flatpak_id.configure(state="disabled", fg_color="gray30")

        # Crear opciones dinámicamente
        for mode_key, mode_display in modes_available:
            if mode_key == c.MODE_INSTALL_FLATPAK:
                # Opción Flatpak con entrada de ID
                ctk.CTkRadioButton(
                    frame_mode,
                    text=c.UI_FLATPAK_CUSTOM_ID_LABEL,
                    variable=self.target_mode,
                    value=mode_key,
                    command=toggle_flatpak_entry,
                    font=c.FONT_NORMAL
                ).pack(anchor="w", padx=20, pady=5)

                # Entrada ID Flatpak (debajo del radio)
                self.entry_flatpak_id = ctk.CTkEntry(
                    frame_mode, placeholder_text=c.DEFAULT_FLATPAK_ID, font=c.FONT_NORMAL
                )
                self.entry_flatpak_id.pack(anchor="w", padx=45, pady=(0, 10), fill="x")
                self.entry_flatpak_id.insert(0, self.flatpak_config_id)
                if self.target_mode.get() != mode_key:
                    self.entry_flatpak_id.configure(state="disabled", fg_color="gray30")
            else:
                # Otras opciones
                ctk.CTkRadioButton(
                    frame_mode,
                    text=mode_display,
                    variable=self.target_mode,
                    value=mode_key,
                    command=toggle_flatpak_entry,
                    font=c.FONT_NORMAL
                ).pack(anchor="w", padx=20, pady=5)

        # Botón de Acción
        self.btn_install = ctk.CTkButton(
            self,
            text=c.UI_BUTTON_INSTALL_NOW,
            height=40,
            command=self.start_install,
            state="disabled",
            font=c.FONT_TITLE,
        )
        self.btn_install.pack(pady=(20, 30), padx=50, fill="x", side="bottom")

        # Centrar y hacer modal
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        self.grab_set()

    def browse_apk(self):
        path = ask_open_filename_native(self, title=c.UI_SELECT_APK_TITLE, filetypes=[(c.UI_APK_FILES_TYPE, "*.apk")])
        if path:
            self.apk_path.set(path)
            # Intentar adivinar versión
            try:
                base = os.path.basename(path)
                import re

                match = re.search(r"(\d+\.\d+(\.\d+)?)", base)
                if match:
                    self.ver_name.set(match.group(1))
            except Exception:
                pass

            # VERIFICAR ARQUITECTURA
            self.check_architecture(path)

    def check_architecture(self, apk_path):
        found_x86 = False
        found_x64 = False
        found_arm = False
        has_assets = False
        has_lib = False

        try:
            with zipfile.ZipFile(apk_path, "r") as z:
                for n in z.namelist():
                    if n.startswith("assets/"):
                        has_assets = True
                    if n.startswith("lib/"):
                        has_lib = True
                    if "lib/x86/" in n:
                        found_x86 = True
                    if "lib/x86_64/" in n:
                        found_x64 = True
                    if "lib/armeabi" in n or "lib/arm64" in n:
                        found_arm = True
        except Exception as e:
            self.arch_status_text.set(c.UI_ERROR_READING_APK.format(e=e))
            self.lbl_arch.configure(text_color="red")
            self.btn_install.configure(state="disabled")
            return

        # Lógica de compatibilidad
        is_compatible = False
        msg = ""
        color = "gray"

        if not has_assets or not has_lib:
            msg = c.UI_APK_INVALID
            color = "red"
            is_compatible = False
        elif found_x86 or found_x64:
            msg = c.UI_APK_COMPATIBLE_X86
            color = "green"
            is_compatible = True
        elif found_arm:
            msg = c.UI_APK_INCOMPATIBLE_ARM
            color = "red"
            is_compatible = False
        else:
            msg = c.UI_APK_INVALID
            color = "orange"
            is_compatible = False

        self.arch_status_text.set(msg)
        self.lbl_arch.configure(text_color=color)

        if is_compatible:
            self.btn_install.configure(state="normal")
        else:
            self.btn_install.configure(state="disabled")

    def start_install(self):
        apk = self.apk_path.get()
        name = self.ver_name.get()
        mode_key = self.target_mode.get()

        if not apk or not os.path.exists(apk):
            messagebox.showerror(c.UI_ERROR_TITLE, c.UI_ERROR_SELECT_VALID_APK)
            return
        if not name:
            messagebox.showerror(c.UI_ERROR_TITLE, c.UI_ERROR_WRITE_VERSION_NAME)
            return

        # Determinar rutas y modo sin cambiar el estado global de la app
        target_root = None
        is_target_flatpak = False

        if mode_key == c.MODE_INSTALL_FLATPAK:
            # Flatpak Personalizado: usar ID especificado
            is_target_flatpak = True
            custom_id = self.entry_flatpak_id.get().strip()
            if not custom_id:
                custom_id = c.DEFAULT_FLATPAK_ID

            target_root = os.path.join(
                self.parent.home, f".var/app/{custom_id}/data/mcpelauncher"
            )

        elif mode_key == c.MODE_INSTALL_OWN:
            # Local propio del Flatpak
            is_target_flatpak = False
            target_root = (
                self.parent.our_data_path
                if self.parent.running_in_flatpak
                else self.parent.compiled_path
            )

        elif mode_key == c.MODE_INSTALL_SHARED:
            # Local compartido en .local/share
            is_target_flatpak = False
            target_root = os.path.join(self.parent.home, c.LOCAL_SHARE_DIR)

        else:  # MODE_INSTALL_LOCAL o cualquier otro
            is_target_flatpak = False
            target_root = self.parent.compiled_path

        # Iniciar proceso
        self.destroy()
        # Pasamos flatpak_id explícitamente
        f_id = self.entry_flatpak_id.get().strip() if is_target_flatpak else None
        self.parent.logic.process_apk(
            self.parent,
            apk,
            name,
            target_root=target_root,
            is_target_flatpak=is_target_flatpak,
            flatpak_id=f_id,
        )
