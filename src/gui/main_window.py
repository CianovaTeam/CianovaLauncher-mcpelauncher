import customtkinter as ctk
from src.gui import custom_dialogs as messagebox
import os
import sys
from PIL import Image, ImageTk
import subprocess

from src import constants as c
from src.utils.dialogs import ask_open_filename_native
from src.utils.resource_path import resource_path
from src.utils.image_manager import ImageManager
from src.core.config_manager import ConfigManager
from src.core import language_manager
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

        self.config_manager = ConfigManager(
            config_path, old_config_file=old_config_path
        )
        self.config = self.config_manager.config

        # ==========================================
        # 2.5. INICIALIZACIÓN DE IDIOMA
        # ==========================================
        lang = self.config.get(c.CONFIG_KEY_LANGUAGE, "en")
        language_manager.load_language(lang)

        # Aplicar Tema de Configuración
        try:
            ctk.set_appearance_mode(self.config.get(c.CONFIG_KEY_APPEARANCE, "Dark"))

            theme_name = self.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
            if theme_name in ["blue", "green", "dark-blue"]:
                ctk.set_default_color_theme(theme_name)
            else:
                # Cargar tema personalizado desde src/themes/ usando resource_path
                theme_path = resource_path(os.path.join("src", "themes", f"{theme_name}.json"))
                if os.path.exists(theme_path):
                    ctk.set_default_color_theme(theme_path)
                else:
                    ctk.set_default_color_theme("blue")
        except Exception as e:
            print(f"Error aplicando tema: {e}")

        # ==========================================
        # 3. WINDOW SETUP & ICON
        # ==========================================
        self.title(c.UI_TITLE_VERSION)
        self.geometry(self.config.get(c.CONFIG_KEY_WINDOW_SIZE, "700x550"))
        self.bind("<Configure>", self.save_window_size)

        self.app_icon_image = ImageManager.get_image("icon.png", size=(32, 32))
        try:
            # Configurar icono nativo de la ventana
            if self.app_icon_image:
                icon_pil = self.app_icon_image._light_image
                icon_photo = ImageTk.PhotoImage(icon_pil)
                self.wm_iconbitmap()
                self.iconphoto(False, icon_photo)
        except Exception as e:
            print(f"No se pudo cargar el icono de ventana: {e}")

        # ==========================================
        # INTERFAZ PRINCIPAL (LAYOUT)
        # ==========================================
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) # Fila principal se expande

        # Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=c.CORNER_RADIUS)
        self.tabview.grid(row=0, column=0, padx=c.SECTION_PADDING, pady=(5, c.SECTION_PADDING), sticky="nsew")

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
    # PESTAÑA 4: ACERCA DE (LEGAL)
    # ==========================================
    def restore_default_settings(self):
        if messagebox.askyesno(self, c.UI_CONFIRM_TITLE, c.UI_RESTORE_DEFAULTS_CONFIRM):
            self.config_manager.restore_defaults()
            messagebox.showinfo(self, c.UI_RESTORE_DEFAULTS_SUCCESS_TITLE, c.UI_RESTORE_DEFAULTS_SUCCESS_MSG)
            self.destroy()

    def change_appearance(self, type_change, value):
        if type_change == "color":
            self.config[c.CONFIG_KEY_COLOR_THEME] = value
            messagebox.showinfo(
                self,
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
            scroll, text=c.UI_MAIN_LAUNCHER_LABEL, font=c.FONT_SUBTITLE
        ).pack(pady=(c.SECTION_PADDING, c.ELEMENT_SPACING))

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
            font=c.FONT_BOLD,
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
                if messagebox.askyesno(self, c.UI_CONFIRM_TITLE, c.UI_CONFIRM_DELETE_SHORTCUT_MSG):
                    try:
                        os.remove(shortcut_path)
                        messagebox.showinfo(self, c.UI_SUCCESS_TITLE, c.UI_SHORTCUT_DELETED_MSG)
                        dialog.destroy()
                        self.manage_desktop_shortcut()
                    except Exception as e:
                        messagebox.showerror(self, c.UI_ERROR_TITLE, str(e))
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

            name = c.APP_NAME
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
Comment={c.UI_SHORTCUT_COMMENT}
Exec={exec_cmd}
Icon={icon_path}
Terminal=false
Type=Application
Categories=Game;
"""
            # En Flatpak, el archivo .desktop principal se gestiona de forma diferente
            if self.running_in_flatpak and not version:
                messagebox.showinfo(
                    self,
                    c.UI_FLATPAK_SHORTCUT_INFO_TITLE,
                    c.UI_FLATPAK_SHORTCUT_INFO_MSG
                )
                return

            target = os.path.join(desktop_folder, f"{filename}.desktop")
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "w") as f:
                    f.write(desktop_content)
                os.chmod(target, 0o755)
                messagebox.showinfo(self, c.UI_SUCCESS_TITLE, c.UI_SHORTCUT_CREATED_MSG.format(name=name))
                dialog.destroy()
                self.manage_desktop_shortcut()
            except Exception as e:
                messagebox.showerror(self, c.UI_ERROR_TITLE, c.UI_SHORTCUT_CREATION_ERROR_MSG.format(e=e))

        ctk.CTkButton(
            scroll,
            text=c.UI_BUTTON_DELETE_MAIN if target_exists else c.UI_BUTTON_CREATE_MAIN,
            fg_color=c.COLOR_RED_BUTTON if target_exists else c.COLOR_GREEN_BUTTON,
            command=toggle_main,
            font=c.FONT_BOLD,
        ).pack(pady=10)

        # --- SECCIÓN 2: VERSIONES ESPECÍFICAS ---
        ctk.CTkLabel(
            scroll,
            text=c.UI_SECTION_VERSION_SHORTCUTS,
            font=c.FONT_SUBTITLE,
        ).pack(pady=(20, 5))

        # Frame para creación
        create_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        create_frame.pack(fill="x", padx=10, pady=5)

        versions = self.logic.get_installed_versions(self)
        if versions:
            combo_ver = ctk.CTkComboBox(create_frame, values=versions, width=150, font=c.FONT_NORMAL)
            combo_ver.pack(side="left", padx=5)
            ctk.CTkButton(
                create_frame,
                text=c.UI_BUTTON_ADD,
                width=80,
                command=lambda: create_shortcut_logic(combo_ver.get()),
                font=c.FONT_NORMAL,
            ).pack(side="left", padx=5)
        else:
            ctk.CTkLabel(
                create_frame, text=c.UI_NO_VERSIONS_INSTALLED, text_color="gray"
            ).pack()

        # Listado de versiones existentes para borrar
        ctk.CTkLabel(
            scroll,
            text=c.UI_MANAGE_EXISTING_SHORTCUTS,
            font=c.FONT_SMALL,
        ).pack(pady=(10, 0))

        found_any = False
        if os.path.exists(desktop_folder):
            for f in os.listdir(desktop_folder):
                if f.startswith("cianova-launcher-") and f.endswith(".desktop"):
                    found_any = True
                    ver_name = f.replace("cianova-launcher-", "").replace(
                        ".desktop", ""
                    )
                    ver_frame = ctk.CTkFrame(scroll, corner_radius=c.CORNER_RADIUS)
                    ver_frame.pack(fill="x", padx=20, pady=2)
                    ctk.CTkLabel(
                        ver_frame, text=f"{c.UI_VERSION_TEXT} {ver_name}", font=c.FONT_NORMAL
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
                        text=c.UI_BUTTON_DELETE,
                        width=60,
                        fg_color="red",
                        command=delete_ver,
                        font=c.FONT_NORMAL,
                    ).pack(side="right", padx=5, pady=2)

        if not found_any:
            ctk.CTkLabel(
                scroll,
                text=c.UI_NO_SHORTCUTS_DETECTED,
                text_color="gray",
                font=c.FONT_SMALL,
            ).pack()

        ctk.CTkButton(dialog, text=c.UI_BUTTON_CLOSE, command=dialog.destroy, font=c.FONT_NORMAL).pack(pady=10)

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
            messagebox.showerror(self, c.UI_ERROR_TITLE, c.UI_ERROR_MIGRATION_TOOL.format(e=e))

    def open_game_config_tool(self):
        try:
            GameConfigDialog(self)
        except Exception as e:
            messagebox.showerror(self, c.UI_ERROR_TITLE, f"Error: {e}")

    def open_addon_manager(self):
        try:
            AddonManagerDialog(self)
        except Exception as e:
            messagebox.showerror(self, c.UI_ERROR_TITLE, f"Error: {e}")

    def sync_gamemode_ui(self, value):
        """Sincroniza el estado de GameMode entre pestañas"""
        self.config[c.CONFIG_KEY_GAMEMODE_ENABLED] = value

        # Actualizar pestaña Jugar
        if hasattr(self, "play_tab") and hasattr(self.play_tab, "var_gamemode"):
            if self.play_tab.var_gamemode.get() != value:
                self.play_tab.var_gamemode.set(value)

        # Actualizar pestaña Ajustes
        if hasattr(self, "settings_tab") and hasattr(self.settings_tab, "var_gamemode"):
            if self.settings_tab.var_gamemode.get() != value:
                self.settings_tab.var_gamemode.set(value)

    def sync_close_on_launch_ui(self, value):
        """Sincroniza el estado de Cerrar al Jugar entre pestañas"""
        self.config[c.CONFIG_KEY_CLOSE_ON_LAUNCH] = value

        # Actualizar pestaña Jugar
        if hasattr(self, "play_tab") and hasattr(self.play_tab, "var_close_on_launch"):
            if self.play_tab.var_close_on_launch.get() != value:
                self.play_tab.var_close_on_launch.set(value)

        # Actualizar pestaña Ajustes
        if hasattr(self, "settings_tab") and hasattr(self.settings_tab, "var_close_on_launch"):
            if self.settings_tab.var_close_on_launch.get() != value:
                self.settings_tab.var_close_on_launch.set(value)
