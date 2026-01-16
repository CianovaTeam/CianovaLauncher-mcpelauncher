import customtkinter as ctk
from tkinter import messagebox
import os
import sys
from PIL import Image, ImageTk
import subprocess

from src import constants as c
from src.utils.dialogs import ask_open_filename_native
from src.utils.resource_path import resource_path
from src.core.config_manager import ConfigManager
from src.gui.install_dialog import InstallDialog
from src.gui.skin_pack_tool import SkinPackTool
from src.gui.migration_dialog import MigrationDialog
from src.core import app_logic
from src.gui.tabs.play_tab import PlayTab
from src.gui.tabs.tools_tab import ToolsTab
from src.gui.tabs.settings_tab import SettingsTab
from src.gui.tabs.about_tab import AboutTab

class CianovaLauncherApp(ctk.CTk):
    def __init__(self, launcher_path=".", force_flatpak_ui=False, force_nvidia_ui=False):
        super().__init__()

        # Lógica de la aplicación
        self.logic = app_logic

        # ==========================================
        # 1. RUTAS Y DETECCIÓN (MOVIDO AL INICIO)
        # ==========================================
        self.launcher_path = launcher_path
        self.home = c.HOME_DIR
        self.force_flatpak_ui = force_flatpak_ui
        self.force_nvidia_ui = force_nvidia_ui

        # Detectar si estamos en Flatpak
        self.running_in_flatpak = self.logic.is_running_in_flatpak() or self.force_flatpak_ui

        # DEBUG LOGS
        print(f"DEBUG: Home: {self.home}")
        print(f"DEBUG: Running in Flatpak: {self.running_in_flatpak}")

        self.our_flatpak_id = (
            self.logic.get_flatpak_app_id() if self.running_in_flatpak else None
        )
        if self.our_flatpak_id:
            print(f"DEBUG: Flatpak ID: {self.our_flatpak_id}")

        # Configurar rutas según contexto
        if self.running_in_flatpak:
            # Dentro de Flatpak, usar nuestra propia ruta de datos
            # Fallback si ID es None (puede pasar si no lee .flatpak-info bien)
            app_id = self.our_flatpak_id if self.our_flatpak_id else c.DEFAULT_FLATPAK_ID
            print(f"DEBUG: Using App ID: {app_id}")
            self.our_data_path = os.path.join(
                self.home, f"{c.FLATPAK_DATA_DIR}/{app_id}/{c.MCPELAUNCHER_DATA_SUBDIR}"
            )
            self.compiled_path = (
                self.our_data_path
            )  # En Flatpak, "compilado" es nuestros datos
            self.flatpak_path = os.path.join(
                self.home, f"{c.FLATPAK_DATA_DIR}/{c.MCPELAUNCHER_FLATPAK_ID}/{c.MCPELAUNCHER_DATA_SUBDIR}"
            )
        else:
            # Ejecución normal
            self.flatpak_path = os.path.join(
                self.home, f"{c.FLATPAK_DATA_DIR}/{c.MCPELAUNCHER_FLATPAK_ID}/{c.MCPELAUNCHER_DATA_SUBDIR}"
            )
            self.compiled_path = os.path.join(self.home, c.LOCAL_SHARE_DIR)

        print(f"DEBUG: Data Path: {self.compiled_path}")
        self.active_path = None
        self.is_flatpak = False
        self.version_cards = {}

        # ==========================================
        # 2. INICIALIZACIÓN DE CONFIGURACIÓN
        # ==========================================
        # Configurar rutas de config según contexto
        if self.running_in_flatpak:
            # En Flatpak: guardar en /data/ directamente, NO en /data/mcpelauncher/
            app_id = self.our_flatpak_id if self.our_flatpak_id else c.DEFAULT_FLATPAK_ID
            data_dir = os.path.join(self.home, f"{c.FLATPAK_DATA_DIR}/{app_id}/data")
            config_path = os.path.join(data_dir, c.CONFIG_FILE_NAME)
            old_config_path = os.path.join(
                self.compiled_path, c.OLD_CONFIG_FILE_NAME
            )  # Ruta antigua para migración
        else:
            # En local: guardar en .local/share/mcpelauncher/
            config_path = os.path.join(
                self.compiled_path, c.CONFIG_FILE_NAME
            )
            old_config_path = os.path.join(
                self.compiled_path, c.OLD_CONFIG_FILE_NAME
            )  # Ruta antigua para migración

        print(f"DEBUG: Config Path: {config_path}")
        print(f"DEBUG: Old Config Path (for migration): {old_config_path}")

        self.config_manager = ConfigManager(
            config_path, old_config_file=old_config_path
        )
        self.config = self.config_manager.config

        # Aplicar Tema de Configuración
        try:
            ctk.set_appearance_mode(self.config.get(c.CONFIG_KEY_APPEARANCE, "Dark"))
            ctk.set_default_color_theme(self.config.get(c.CONFIG_KEY_COLOR_THEME, "blue"))
        except Exception as e:
            print(f"Error aplicando tema: {e}")

        # ==========================================
        # 3. WINDOW SETUP & ICON
        # ==========================================
        self.title(c.UI_TITLE_VERSION)
        self.geometry(self.config.get(c.CONFIG_KEY_WINDOW_SIZE, "700x550"))
        self.bind("<Configure>", self.save_window_size)

        self.app_icon_image = None
        try:
            # Si estamos en flatpak y no existe resource_path, usar path local o /app/bin
            icon_path = resource_path("icon.png")
            if self.running_in_flatpak:
                if os.path.exists("/app/bin/icon.png"):
                    icon_path = "/app/bin/icon.png"
            elif os.path.exists(resource_path("icon.png")):
                icon_path = resource_path("icon.png")

            if os.path.exists(icon_path):
                if ImageTk:  # Verificar PIL
                    icon_pil = Image.open(icon_path)
                    icon_photo = ImageTk.PhotoImage(icon_pil)
                    self.wm_iconbitmap()
                    self.iconphoto(False, icon_photo)
                    self.app_icon_image = ctk.CTkImage(
                        light_image=icon_pil, dark_image=icon_pil, size=(32, 32)
                    )
            else:
                print(f"Icono no encontrado en: {icon_path}")
        except Exception as e:
            print(f"No se pudo cargar el icono: {e}")

        # ==========================================
        # INTERFAZ PRINCIPAL (LAYOUT)
        # ==========================================
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) # Fila principal se expande

        # Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="nsew")

        self.tab_launcher = self.tabview.add(c.UI_TAB_PLAY)
        self.tab_tools = self.tabview.add(c.UI_TAB_TOOLS)
        self.tab_settings = self.tabview.add(c.UI_TAB_SETTINGS)
        self.tab_about = self.tabview.add(c.UI_TAB_ABOUT)

        # Inicializar Componentes
        self.play_tab = PlayTab(self.tab_launcher, self)
        self.tools_tab = ToolsTab(self.tab_tools, self)
        self.settings_tab = SettingsTab(self.tab_settings, self)
        self.about_tab = AboutTab(self.tab_about, self)

        # Detectar instalación al inicio (usando nueva lógica)
        self.logic.detect_installation(self)

        # Auto-configurar y migrar si es primera ejecución en Flatpak
        if self.running_in_flatpak:
            self.logic.setup_flatpak_environment(self)
            self.logic.check_migration_needed(self)

        # Procesar argumentos de lanzamiento (ej. --version "1.20")
        if "--version" in sys.argv:
            try:
                idx = sys.argv.index("--version")
                if idx + 1 < len(sys.argv):
                    target_version = sys.argv[idx + 1]
                    # Esperar brevemente a que todo esté inicializado
                    self.after(500, lambda: self.logic.launch_from_args(self, target_version))
            except Exception as e:
                print(f"Error procesando argumentos: {e}")

    def save_window_size(self, event=None):
        # Guardar geometría solo si es un evento de la ventana principal
        if event and event.widget == self:
            size = self.geometry().split("+")[0]  # Obtener solo WxH
            if size != self.config.get(c.CONFIG_KEY_WINDOW_SIZE):
                self.config_manager.set(c.CONFIG_KEY_WINDOW_SIZE, size)

    # ==========================================
    # PESTAÑA 2: HERRAMIENTAS (ORGANIZADO)
    # ==========================================
    # ==========================================
    # PESTAÑA 3: AJUSTES (CONFIGURACIÓN)
    # ==========================================
    # ==========================================
    # PESTAÑA 4: ACERCA DE (LEGAL)
    # ==========================================
    def restore_default_settings(self):
        if messagebox.askyesno("Confirmar", "¿Estás seguro de que quieres restaurar todos los ajustes a sus valores por defecto? La aplicación se cerrará."):
            self.config_manager.restore_defaults()
            messagebox.showinfo("Ajustes restaurados", "Los ajustes se han restaurado. La aplicación se cerrará ahora.")
            self.destroy()

    def change_appearance(self, type_change, value):
        if type_change == "color":
            self.config[c.CONFIG_KEY_COLOR_THEME] = value
            messagebox.showinfo(
                c.UI_RESTART_REQUIRED_TITLE,
                c.UI_RESTART_MSG,
            )

        self.config_manager.save_config()

    def manage_desktop_shortcut(self):
        """Muestra diálogo avanzado para gestionar accesos directos"""
        desktop_folder = os.path.join(c.HOME_DIR, c.APPLICATIONS_DIR)
        main_desktop_file = os.path.join(desktop_folder, c.DESKTOP_SHORTCUT_NAME)

        dialog = ctk.CTkToplevel(self)
        dialog.title(c.UI_MANAGE_SHORTCUT_TITLE)
        dialog.geometry("500x480")
        dialog.transient(self)
        dialog.resizable(False, False)

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # --- SECCIÓN 1: LANZADOR PRINCIPAL ---
        ctk.CTkLabel(
            scroll, text="Lanzador Principal", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 5))

        # Detección inicial
        target_exists = os.path.exists(main_desktop_file)
        if self.running_in_flatpak:
            # En Flatpak, el .desktop se crea en una ruta diferente.
            flatpak_desktop_name = f"{self.our_flatpak_id}.desktop"
            flatpak_desktop_path = os.path.join(c.HOME_DIR, ".local/share/flatpak/exports/share/applications/", flatpak_desktop_name)
            target_exists = os.path.exists(flatpak_desktop_path)

        status_color = "green" if target_exists else "orange"
        status_text = c.UI_SHORTCUT_ACTIVE_MSG if target_exists else c.UI_SHORTCUT_INACTIVE_MSG
        ctk.CTkLabel(
            scroll,
            text=status_text,
            text_color=status_color,
            font=ctk.CTkFont(weight="bold"),
        ).pack()

        def toggle_main():
            # La lógica de creación/borrado ahora debe ser consciente del entorno
            is_flatpak = self.running_in_flatpak

            # Determinar la ruta correcta del archivo .desktop
            if is_flatpak:
                flatpak_desktop_name = f"{self.our_flatpak_id}.desktop"
                shortcut_path = os.path.join(c.HOME_DIR, ".local/share/flatpak/exports/share/applications/", flatpak_desktop_name)
            else:
                shortcut_path = main_desktop_file

            exists_now = os.path.exists(shortcut_path)

            if exists_now:
                if messagebox.askyesno("Confirmar", c.UI_CONFIRM_DELETE_SHORTCUT_MSG):
                    try:
                        os.remove(shortcut_path)
                        messagebox.showinfo(c.UI_SUCCESS_TITLE, c.UI_SHORTCUT_DELETED_MSG)
                        dialog.destroy()
                        self.manage_desktop_shortcut()
                    except Exception as e:
                        messagebox.showerror(c.UI_ERROR_TITLE, str(e))
            else:
                create_shortcut_logic()

        def create_shortcut_logic(version=None):
            # Determinar Exec
            if self.running_in_flatpak:
                app_id = (
                    self.our_flatpak_id
                    if self.our_flatpak_id
                    else c.DEFAULT_FLATPAK_ID
                )
                exec_cmd = f"flatpak run {app_id}"
            else:
                if getattr(sys, "frozen", False):
                    exec_cmd = sys.executable
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    exec_cmd = (
                        os.path.join(base_dir, "cianova-launcher.sh")
                        if os.path.exists(os.path.join(base_dir, "cianova-launcher.sh"))
                        else f"python3 {os.path.abspath(__file__)}"
                    )

            name = "CianovaLauncher MCPE"
            filename = "cianova-launcher"

            if version:
                exec_cmd += f' --version "{version}"'
                name += f" ({version})"
                filename += f"-{version}"

            icon_path = resource_path("icon.png")
            if self.running_in_flatpak:
                icon_path = c.DEFAULT_FLATPAK_ID

            desktop_content = f"""[Desktop Entry]
Name={name}
Comment=Lanzador de Minecraft PE para Linux
Exec={exec_cmd}
Icon={icon_path}
Terminal=false
Type=Application
Categories=Game;
"""
            # En Flatpak, el archivo .desktop principal se gestiona de forma diferente
            if self.running_in_flatpak and not version:
                messagebox.showinfo(
                    "Información",
                    "El acceso directo principal de la aplicación Flatpak se crea automáticamente al instalar.\n\n"
                    "Puedes gestionarlo desde tu tienda de aplicaciones (ej. Discover, GNOME Software)."
                )
                return

            target = os.path.join(desktop_folder, f"{filename}.desktop")
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "w") as f:
                    f.write(desktop_content)
                os.chmod(target, 0o755)
                messagebox.showinfo(c.UI_SUCCESS_TITLE, c.UI_SHORTCUT_CREATED_MSG.format(name=name))
                dialog.destroy()
                self.manage_desktop_shortcut()
            except Exception as e:
                messagebox.showerror(c.UI_ERROR_TITLE, c.UI_SHORTCUT_CREATION_ERROR_MSG.format(e=e))

        ctk.CTkButton(
            scroll,
            text=c.UI_BUTTON_DELETE_MAIN if target_exists else c.UI_BUTTON_CREATE_MAIN,
            fg_color=c.COLOR_RED_BUTTON if target_exists else c.COLOR_GREEN_BUTTON,
            command=toggle_main,
        ).pack(pady=10)

        # --- SECCIÓN 2: VERSIONES ESPECÍFICAS ---
        ctk.CTkLabel(
            scroll,
            text=c.UI_SECTION_VERSION_SHORTCUTS,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(20, 5))

        # Frame para creación
        create_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        create_frame.pack(fill="x", padx=10, pady=5)

        versions = self.logic.get_installed_versions(self)
        if versions:
            combo_ver = ctk.CTkComboBox(create_frame, values=versions, width=150)
            combo_ver.pack(side="left", padx=5)
            ctk.CTkButton(
                create_frame,
                text="Añadir",
                width=80,
                command=lambda: create_shortcut_logic(combo_ver.get()),
            ).pack(side="left", padx=5)
        else:
            ctk.CTkLabel(
                create_frame, text=c.UI_NO_VERSIONS_INSTALLED, text_color="gray"
            ).pack()

        # Listado de versiones existentes para borrar
        ctk.CTkLabel(
            scroll,
            text=c.UI_MANAGE_EXISTING_SHORTCUTS,
            font=ctk.CTkFont(size=12, slant="italic"),
        ).pack(pady=(10, 0))

        found_any = False
        if os.path.exists(desktop_folder):
            for f in os.listdir(desktop_folder):
                if f.startswith("cianova-launcher-") and f.endswith(".desktop"):
                    found_any = True
                    ver_name = f.replace("cianova-launcher-", "").replace(
                        ".desktop", ""
                    )
                    ver_frame = ctk.CTkFrame(scroll)
                    ver_frame.pack(fill="x", padx=20, pady=2)
                    ctk.CTkLabel(
                        ver_frame, text=f"Versión {ver_name}", font=ctk.CTkFont(size=12)
                    ).pack(side="left", padx=10)

                    def delete_ver(fname=f):
                        try:
                            os.remove(os.path.join(desktop_folder, fname))
                            dialog.destroy()
                            self.manage_desktop_shortcut()
                        except:
                            pass

                    ctk.CTkButton(
                        ver_frame,
                        text="Borrar",
                        width=60,
                        fg_color="red",
                        command=delete_ver,
                    ).pack(side="right", padx=5, pady=2)

        if not found_any:
            ctk.CTkLabel(
                scroll,
                text=c.UI_NO_SHORTCUTS_DETECTED,
                text_color="gray",
                font=ctk.CTkFont(size=11),
            ).pack()

        ctk.CTkButton(dialog, text=c.UI_BUTTON_CLOSE, command=dialog.destroy).pack(pady=10)

        dialog.grab_set()

    # ==========================================
    # LÓGICA: HERRAMIENTAS
    # ==========================================
    def install_apk_dialog(self):
        InstallDialog(self)

    def open_skin_tool(self):
        SkinPackTool(self)

    def open_migration_tool(self):
        try:
            MigrationDialog(self)
        except Exception as e:
            messagebox.showerror(c.UI_ERROR_TITLE, c.UI_ERROR_MIGRATION_TOOL.format(e=e))
