import json
import os
import platform
import shutil
import subprocess
import threading
import zipfile
from tkinter import filedialog, messagebox
import customtkinter as ctk
import tempfile
import time
import re

from src.gui.progress_dialog import ProgressDialog
from src import constants as c
from src.utils.dialogs import ask_directory_native
from src.utils.image_manager import ImageManager

def get_installed_versions(app):
    """Devuelve una lista de versiones instaladas detectadas"""
    if not app.active_path:
        detect_installation(app)
    if not app.active_path:
        return []
    versions_dir = os.path.join(app.active_path, c.VERSIONS_DIR)
    if not os.path.exists(versions_dir):
        return []
    try:
        return sorted(
            [d for d in os.listdir(versions_dir) if os.path.isdir(os.path.join(versions_dir, d))],
            reverse=True,
        )
    except:
        return []

def launch_from_args(app, version):
    """Helper para lanzar una versión directamente desde argumentos"""
    versions = get_installed_versions(app)
    if version in versions:
        app.play_tab.version_var.set(version)
        launch_game(app)
    else:
        messagebox.showerror(c.UI_ERROR_TITLE, c.UI_VERSION_NOT_INSTALLED_ERROR.format(version=version))

def process_apk(app, apk_path, ver_name, target_root=None, is_target_flatpak=None, flatpak_id=None):
    current_root = target_root if target_root else app.active_path
    if not current_root:
        messagebox.showerror(c.UI_ERROR_TITLE, c.UI_NO_TARGET_PATH_ERROR)
        return

    target_dir = os.path.join(current_root, c.VERSIONS_DIR, ver_name)
    use_flatpak_logic = is_target_flatpak if is_target_flatpak is not None else app.is_flatpak

    progress_dialog = ProgressDialog(app, c.UI_EXTRACTING_APK_TITLE, c.UI_EXTRACTING_APK_MSG)

    def run_extraction():
        try:
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            os.makedirs(target_dir, exist_ok=True)

            cmd = []
            custom_extract = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_EXTRACT)

            if custom_extract and os.path.exists(custom_extract):
                cmd = [custom_extract, apk_path, target_dir]
            elif use_flatpak_logic:
                app_id = flatpak_id if flatpak_id else app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.MCPELAUNCHER_FLATPAK_ID)
                base_cmd = ["flatpak", "run", "--command=mcpelauncher-extract", app_id, apk_path, target_dir]

                if app.running_in_flatpak:
                    flatpak_spawn_cmd = shutil.which("flatpak-spawn")
                    if flatpak_spawn_cmd:
                        cmd = [flatpak_spawn_cmd, "--host"] + base_cmd
                    else:
                        # Fallback a los binarios internos si flatpak-spawn no está disponible en el PATH del sandbox.
                        cmd = ["mcpelauncher-extract", apk_path, target_dir]
                else:
                    cmd = base_cmd
            else:
                cmd = ["mcpelauncher-extract", apk_path, target_dir]

            print(f"Ejecutando extractor: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, text=True)
            app.after(0, progress_dialog.close)

            if process.returncode == 0:
                app.after(0, lambda: messagebox.showinfo(c.UI_SUCCESS_TITLE, c.UI_EXTRACTION_SUCCESS_MSG.format(ver_name=ver_name)))
                if current_root == app.active_path:
                    app.after(0, lambda: refresh_version_list(app))
            else:
                err_msg = process.stderr
                print(f"Error extractor: {err_msg}")
                app.after(0, lambda: messagebox.showerror(c.UI_ERROR_TITLE, c.UI_EXTRACTION_ERROR_MSG.format(err_msg=err_msg)))
        except Exception as e:
            app.after(0, progress_dialog.close)
            app.after(0, lambda: messagebox.showerror(c.UI_ERROR_TITLE, c.UI_CRITICAL_ERROR_MSG.format(e=e)))

    threading.Thread(target=run_extraction).start()

def delete_version_dialog(app):
    version = app.play_tab.version_var.get()
    if not version:
        return

    dialog = ctk.CTkToplevel(app)
    dialog.title(c.UI_MANAGE_VERSION_TITLE)
    dialog.geometry("400x200")
    dialog.resizable(False, False)
    dialog.transient(app)

    ctk.CTkLabel(dialog, text=c.UI_MANAGE_VERSION_PROMPT.format(version=version), font=c.FONT_NORMAL).pack(pady=20)

    def do_move():
        try:
            backup_dir = os.path.join(app.home, c.BACKUP_DIR)
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            src = os.path.join(app.active_path, c.VERSIONS_DIR, version)
            dst = os.path.join(backup_dir, version)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.move(src, backup_dir)
            refresh_version_list(app)
            messagebox.showinfo(c.UI_SUCCESS_TITLE, c.UI_VERSION_MOVED_MSG)
            dialog.destroy()
        except Exception as e:
            messagebox.showerror(c.UI_ERROR_TITLE, str(e))

    def do_delete():
        if messagebox.askyesno(c.UI_CONFIRM_DELETE_TITLE, c.UI_CONFIRM_PERMANENT_DELETE.format(version=version)):
            try:
                src = os.path.join(app.active_path, c.VERSIONS_DIR, version)
                shutil.rmtree(src)
                refresh_version_list(app)
                messagebox.showinfo(c.UI_SUCCESS_TITLE, c.UI_VERSION_DELETED_MSG)
                dialog.destroy()
            except Exception as e:
                messagebox.showerror(c.UI_ERROR_TITLE, str(e))

    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack(fill="x", padx=20, pady=10)

    ctk.CTkButton(btn_frame, text=c.UI_MOVE_TO_BACKUP, fg_color=c.COLOR_ORANGE_BUTTON, hover_color=c.COLOR_ORANGE_BUTTON_HOVER, command=do_move, font=c.FONT_NORMAL).pack(side="left", fill="x", expand=True, padx=5)
    ctk.CTkButton(btn_frame, text=c.UI_DELETE_PERMANENTLY, fg_color=c.COLOR_RED_BUTTON, hover_color=c.COLOR_RED_BUTTON_HOVER, command=do_delete, font=c.FONT_NORMAL).pack(side="right", fill="x", expand=True, padx=5)

    dialog.update_idletasks()
    x = app.winfo_x() + (app.winfo_width() // 2) - (dialog.winfo_width() // 2)
    y = app.winfo_y() + (app.winfo_height() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    dialog.grab_set()

def disable_shaders(app):
    if not app.active_path:
        return
    options_path = os.path.join(app.active_path, c.MINECRAFT_PE_DIR_ALT, c.OPTIONS_FILE)

    try:
        with open(options_path, "r") as f:
            content = f.read()
        new_content = content.replace("graphics_mode:2", "graphics_mode:0").replace("graphics_mode:1", "graphics_mode:0")
        with open(options_path, "w") as f:
            f.write(new_content)
        check_shader_status(app)
        messagebox.showinfo(c.UI_SUCCESS_TITLE, c.UI_SHADERS_DISABLED_MSG)
    except Exception as e:
        messagebox.showerror(c.UI_ERROR_TITLE, str(e))

def open_data_folder(app):
    if app.active_path:
        subprocess.Popen(["xdg-open", app.active_path])

def detect_installation(app):
    config_mode = app.config.get(c.CONFIG_KEY_MODE, c.UI_DEFAULT_MODE)

    install_mode = app.config.get(c.CONFIG_KEY_INSTALL_MODE, c.MODE_INSTALL_LOCAL)

    flatpak_id = app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.DEFAULT_FLATPAK_ID)

    std_local_path = app.compiled_path
    std_local_shared = os.path.join(app.home, c.LOCAL_SHARE_DIR)

    status_text, status_color = "", "gray"
    app.is_flatpak = False # Resetear estado

    # Lógica de detección de ruta para Flatpak
    if app.running_in_flatpak and install_mode in [c.MODE_INSTALL_OWN, c.MODE_INSTALL_SHARED]:
        own_path = app.our_data_path
        shared_path = std_local_shared

        # Prioridad: Propio > Compartido. Si no existe ninguno, default a Propio.
        if os.path.exists(os.path.join(own_path, c.VERSIONS_DIR)):
            install_mode = c.MODE_INSTALL_OWN
            app.active_path = own_path
            status_text, status_color = c.UI_STATUS_LOCAL_OWN, "#27ae60"
        elif os.path.exists(os.path.join(shared_path, c.VERSIONS_DIR)):
            install_mode = c.MODE_INSTALL_SHARED
            app.active_path = shared_path
            status_text, status_color = c.UI_STATUS_LOCAL_SHARED, "#27ae60"
        else:
            # Por defecto a Propio si no se encuentra nada
            install_mode = c.MODE_INSTALL_OWN
            app.active_path = own_path
            status_text, status_color = c.UI_STATUS_LOCAL_OWN, "#27ae60"
        app.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, install_mode)
    else:
        # Lógica original para fuera de Flatpak o modo Flatpak (Personalizado)
        if install_mode == c.MODE_INSTALL_OWN:
            status_text, status_color = c.UI_STATUS_LOCAL_OWN, "#27ae60"
            app.active_path = app.our_data_path if app.running_in_flatpak else std_local_path
        elif install_mode == c.MODE_INSTALL_SHARED:
            status_text, status_color = c.UI_STATUS_LOCAL_SHARED, "#27ae60"
            app.active_path = std_local_shared
        elif install_mode == c.MODE_INSTALL_LOCAL:
            status_text, status_color = c.UI_STATUS_LOCAL, "#27ae60"
            app.active_path = std_local_path
        elif install_mode == c.MODE_INSTALL_FLATPAK:
            status_text, status_color = c.UI_STATUS_FLATPAK_CUSTOM.format(flatpak_id=flatpak_id), "#3498db"
            app.is_flatpak = True
            std_flatpak_path = os.path.join(app.home, f"{c.FLATPAK_DATA_DIR}/{flatpak_id}/{c.MCPELAUNCHER_DATA_SUBDIR}")
            app.active_path = std_flatpak_path
            app.flatpak_path = std_flatpak_path
            if not os.path.exists(app.active_path):
                status_text, status_color = c.UI_STATUS_FLATPAK_NO_DATA, "orange"

    # Si después de toda la lógica, la ruta activa no tiene versiones, mostrarlo
    if app.active_path and not os.path.exists(os.path.join(app.active_path, c.VERSIONS_DIR)):
         if install_mode != c.MODE_INSTALL_FLATPAK:
            status_text, status_color = c.UI_STATUS_LOCAL_NO_VERSIONS, "gray"

    # Actualizar UI
    app.play_tab.lbl_status.configure(text=status_text, text_color=status_color)

    if app.active_path and not app.is_flatpak:
        try:
            os.makedirs(app.active_path, exist_ok=True)
        except OSError: pass

    refresh_version_list(app)
    check_shader_status(app)

    # Sincronizar selectores y estado
    try:
        app.play_tab.combo_mode.set(c.UI_INSTALL_MODES[install_mode]) # El selector de Jugar muestra el modo de instalación
        app.settings_tab.combo_settings_mode.set(c.UI_BIN_MODES[config_mode]) # El selector de Ajustes muestra el modo de binarios
        app.settings_tab.on_settings_mode_change(c.UI_BIN_MODES[config_mode])

        # Ajustar texto del botón de dependencias
        if app.is_flatpak:
             app.tools_tab.btn_verify_deps.configure(text=c.UI_BUTTON_VERIFY_DEPS_FLATPAK)
        else:
             app.tools_tab.btn_verify_deps.configure(text=c.UI_BUTTON_VERIFY_DEPS_LOCAL)
    except Exception: pass

    try:
        app.tools_tab.lbl_tools_status.configure(text=status_text, text_color=status_color)
    except Exception as e:
        pass


def change_mode_ui(app, display_name):
    # Encontrar la clave interna a partir del nombre mostrado
    mode_key = next((k for k, v in c.UI_INSTALL_MODES.items() if v == display_name), c.MODE_INSTALL_LOCAL)

    # Guardar siempre el modo de instalación seleccionado
    app.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, mode_key)

    if mode_key == c.MODE_INSTALL_FLATPAK:
        dialog = ctk.CTkToplevel(app)
        dialog.title(c.UI_CONFIG_FLATPAK_CUSTOM_TITLE)
        dialog.geometry("400x180")
        dialog.transient(app)
        dialog.resizable(False, False)

        ctk.CTkLabel(dialog, text=c.UI_FLATPAK_ID_LABEL, font=ctk.CTkFont(size=13)).pack(pady=(20, 5))
        entry_id = ctk.CTkEntry(dialog, width=300)
        entry_id.pack(pady=5)
        current_id = app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.MCPELAUNCHER_FLATPAK_ID)
        entry_id.insert(0, current_id)
        ctk.CTkLabel(dialog, text=c.UI_FLATPAK_ID_EXAMPLE, text_color="gray", font=ctk.CTkFont(size=10)).pack(pady=2)

        def save_and_apply():
            new_id = entry_id.get().strip()
            if new_id:
                app.config_manager.set(c.CONFIG_KEY_FLATPAK_ID, new_id)
                dialog.destroy()
                detect_installation(app)
            else:
                messagebox.showwarning(c.UI_INFO_TITLE, c.UI_FLATPAK_ID_REQUIRED_MSG)

        ctk.CTkButton(dialog, text=c.UI_BUTTON_USE_ID, command=save_and_apply).pack(pady=10)
        dialog.grab_set()
    else:
        detect_installation(app)

def is_running_in_flatpak():
    return os.path.exists(c.FLATPAK_INFO_FILE)

def get_flatpak_app_id():
    if not is_running_in_flatpak():
        return None
    try:
        with open(c.FLATPAK_INFO_FILE, "r") as f:
            for line in f:
                if line.startswith("app="):
                    return line.split("=")[1].strip()
    except:
        return None
    return None

def setup_flatpak_environment(app):
    if not app.running_in_flatpak:
        return

    # En Flatpak, si el modo no está establecido o es la primera ejecución,
    # el modo de binarios por defecto debería ser 'Sistema' para usar los binarios empaquetados.
    if app.config.get(c.CONFIG_KEY_MODE) is None or app.config.get(c.CONFIG_KEY_FIRST_RUN_FLATPAK, True):
        app.config[c.CONFIG_KEY_MODE] = c.MODE_BIN_SYSTEM
        # A diferencia del modo "Personalizado", "Sistema" no necesita rutas explícitas
        # ya que se asume que los binarios están en el PATH del sistema (o del sandbox).
        # Sin embargo, los guardamos para el fallback de `execve`.
        if os.path.exists("/app/bin/mcpelauncher-client"):
            app.config[c.CONFIG_KEY_BINARY_PATHS] = {
                c.CONFIG_KEY_CLIENT: "/app/bin/mcpelauncher-client",
                c.CONFIG_KEY_EXTRACT: "/app/bin/mcpelauncher-extract",
                c.CONFIG_KEY_WEBVIEW: "/app/bin/mcpelauncher-webview",
                c.CONFIG_KEY_ERROR: "/app/bin/mcpelauncher-error",
            }
            app.config[c.CONFIG_KEY_FIRST_RUN_FLATPAK] = False
            app.config_manager.save_config()

def check_migration_needed(app):
    if not app.running_in_flatpak:
        return
    old_local_path = os.path.join(app.home, c.LOCAL_SHARE_DIR)
    if app.config.get(c.CONFIG_KEY_MIGRATION_NOTIFIED, False) or not os.path.exists(old_local_path):
        return
    old_versions = os.path.join(old_local_path, c.VERSIONS_DIR)
    if not os.path.exists(old_versions) or not os.listdir(old_versions):
        return
    messagebox.showinfo(c.UI_DATA_DETECTED_TITLE, c.UI_MIGRATION_PROMPT_MSG)
    app.config[c.CONFIG_KEY_MIGRATION_NOTIFIED] = True
    app.config_manager.save_config()

def resolve_version(version_path):
    # This function's internal strings relate to game data structure, not app UI/paths.
    # Keeping them here for clarity and separation of concerns.
    if os.path.islink(version_path):
        try:
            return os.path.basename(os.readlink(version_path))
        except OSError: pass

    try:
        v_txt = os.path.join(version_path, "version_name.txt")
        if os.path.exists(v_txt):
            with open(v_txt, "r") as f: return f.read().strip()
    except OSError: pass

    possible_manifests = [
        "assets/packs/vanilla/manifest.json", "assets/resource_packs/vanilla/manifest.json",
        "assets/behavior_packs/vanilla/manifest.json", "assets/resource_packs/vanilla_1.20/manifest.json",
        "assets/resource_packs/vanilla_1.19/manifest.json"
    ]
    for rel_path in possible_manifests:
        try:
            manifest = os.path.join(version_path, rel_path)
            if os.path.exists(manifest):
                with open(manifest, "r") as f: data = json.load(f)
                ver_list = data.get("header", {}).get("version", [])
                if ver_list: return ".".join(map(str, ver_list))
        except (OSError, json.JSONDecodeError): pass
    return None

def refresh_version_list(app):
    for widget in app.play_tab.version_listbox.winfo_children():
        widget.destroy()
    app.version_cards = {}
    if not app.active_path:
        return

    versions_dir = os.path.join(app.active_path, c.VERSIONS_DIR)
    if not os.path.exists(versions_dir):
        ctk.CTkLabel(app.play_tab.version_listbox, text=c.UI_NO_VERSIONS_FOLDER_MSG).pack()
        return

    # Configuraciones de apariencia
    style = app.config.get(c.CONFIG_KEY_VERSION_LIST_STYLE, c.STYLE_LIST)
    icon_size = app.config.get(c.CONFIG_KEY_VERSION_ICON_SIZE, 32)
    title_size = app.config.get(c.CONFIG_KEY_VERSION_TITLE_SIZE, 13)
    version_font = ctk.CTkFont(family="Roboto", size=title_size, weight="bold")

    icon_image = ImageManager.get_image("icon.png", size=(icon_size, icon_size))

    try:
        versions = sorted([d for d in os.listdir(versions_dir) if os.path.isdir(os.path.join(versions_dir, d))])
        if not versions:
            ctk.CTkLabel(app.play_tab.version_listbox, text=c.UI_NO_VERSIONS_INSTALLED).pack()
            return

        if style == c.STYLE_GRID:
            # Configurar columnas para cuadrícula
            app.play_tab.version_listbox.grid_columnconfigure((0, 1, 2), weight=1)

        for i, v in enumerate(versions):
            display_name = v
            if v == "current":
                real_ver = resolve_version(os.path.join(versions_dir, v))
                if real_ver: display_name = f"current ({c.UI_DETECTED_LABEL.format(version=real_ver)})"

            card = ctk.CTkFrame(app.play_tab.version_listbox, corner_radius=c.CORNER_RADIUS, fg_color=("gray85", "gray25"))

            if style == c.STYLE_GRID:
                card.grid(row=i // 3, column=i % 3, padx=5, pady=5, sticky="nsew")
                # En cuadrícula: Icono arriba, texto abajo
                if icon_image:
                    lbl_icon = ctk.CTkLabel(card, text="", image=icon_image)
                    lbl_icon.pack(side="top", pady=(10, 5))
                    lbl_icon.bind("<Button-1>", lambda e, ver=v: select_version(app, ver))
                lbl_text = ctk.CTkLabel(card, text=display_name, font=version_font, wraplength=120)
                lbl_text.pack(side="top", pady=(0, 10), padx=5)
            else:
                card.pack(fill="x", pady=5, padx=5)
                # En lista: Icono izquierda, texto derecha
                if icon_image:
                    lbl_icon = ctk.CTkLabel(card, text="", image=icon_image)
                    lbl_icon.pack(side="left", padx=10, pady=10)
                    lbl_icon.bind("<Button-1>", lambda e, ver=v: select_version(app, ver))
                lbl_text = ctk.CTkLabel(card, text=display_name, font=version_font)
                lbl_text.pack(side="left", padx=10)

            card.bind("<Button-1>", lambda e, ver=v: select_version(app, ver))
            lbl_text.bind("<Button-1>", lambda e, ver=v: select_version(app, ver))
            app.version_cards[v] = card

        last_ver = app.config.get(c.CONFIG_KEY_LAST_VERSION)
        if last_ver and last_ver in versions:
            select_version(app, last_ver)
        elif versions and not app.play_tab.version_var.get():
            select_version(app, versions[0])
    except Exception as e:
        ctk.CTkLabel(app.play_tab.version_listbox, text=c.UI_ERROR_LISTING_VERSIONS.format(e=e)).pack()

def select_version(app, version):
    app.play_tab.version_var.set(version)
    # Obtener el color primario del tema actual para resaltar la selección
    try:
        selected_color = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
    except:
        selected_color = ("#3B8ED0", "#1F6AA5") # Fallback a azul si algo falla

    for v, card in app.version_cards.items():
        if v == version:
            card.configure(fg_color=selected_color)
        else:
            # Color base para tarjetas no seleccionadas (adaptable a Light/Dark)
            card.configure(fg_color=("gray85", "gray25"))

def check_shader_status(app):
    if not app.active_path:
        return
    options_path = os.path.join(app.active_path, c.MINECRAFT_PE_DIR_ALT, c.OPTIONS_FILE)
    status, color = c.UI_SHADER_STATUS_UNKNOWN, "gray"
    if os.path.exists(options_path):
        try:
            with open(options_path, "r") as f:
                for line in f:
                    if "graphics_mode:" in line:
                        val = line.strip().split(":")[1]
                        if val == "0": status, color = c.UI_SHADER_STATUS_SIMPLE, "green"
                        elif val == "1": status, color = c.UI_SHADER_STATUS_FANCY, "orange"
                        elif val == "2": status, color = c.UI_SHADER_STATUS_VIBRANT, "red"
                        break
        except OSError: pass

    # Intentar actualizar el label en ToolsTab si existe
    try:
        if hasattr(app.tools_tab, "lbl_shader_status"):
            app.tools_tab.lbl_shader_status.configure(text=c.UI_SHADER_STATUS_LABEL.format(status=status), text_color=color)
    except:
        pass

def update_shader_status_label(app):
    """Alias para check_shader_status para mejor legibilidad"""
    check_shader_status(app)

def _launch_with_execve_fallback(app, cmd, env):
    """
    Muestra una notificación y luego reemplaza el proceso actual con el juego.
    Este es el último recurso si subprocess.Popen falla.
    """
    dialog = ctk.CTkToplevel(app)
    dialog.overrideredirect(True)
    dialog.geometry("350x100")
    dialog.configure(fg_color="#333333")

    # Centrar la ventana
    x = app.winfo_x() + (app.winfo_width() // 2) - (350 // 2)
    y = app.winfo_y() + (app.winfo_height() // 2) - (100 // 2)
    dialog.geometry(f"+{x}+{y}")

    ctk.CTkLabel(dialog, text=c.UI_CLOSING_FOR_GAME,
                 font=c.FONT_NORMAL, wraplength=330).pack(pady=20, padx=10, fill="both", expand=True)

    dialog.grab_set()
    dialog.update()

    def do_exec():
        try:
            # Comprobación de seguridad para evitar bucle de reinicio.
            # Compara la ruta del binario del juego con la ruta del propio lanzador.
            game_binary_path = os.path.abspath(cmd[0])
            launcher_script_path = os.path.abspath(app.launcher_path)

            if game_binary_path == launcher_script_path:
                messagebox.showerror(
                    c.UI_CONFIG_ERROR_TITLE,
                    c.UI_SELF_LAUNCH_ERROR_MSG
                )
                app.destroy()
                return

            os.execve(cmd[0], cmd, env)
        except Exception as e:
            messagebox.showerror(c.UI_CRITICAL_LAUNCH_ERROR_TITLE,
                                 c.UI_EXECVE_ERROR_MSG.format(e=e))
            app.destroy()

    app.after(1500, do_exec)


def launch_game(app):
    version = app.play_tab.version_var.get()
    if not version:
        messagebox.showwarning(c.UI_INFO_TITLE, c.UI_PLEASE_SELECT_VERSION_MSG)
        return

    version_path = os.path.join(app.active_path, c.VERSIONS_DIR, version)
    cmd = []
    mode = app.config.get(c.CONFIG_KEY_MODE, c.UI_DEFAULT_MODE)
    flatpak_id = app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.MCPELAUNCHER_FLATPAK_ID)

    gamemode_enabled = app.config.get(c.CONFIG_KEY_GAMEMODE_ENABLED, False)

    # Helper para aplicar GameMode
    def apply_gamemode(command_list):
        if not gamemode_enabled:
            return command_list

        # 1. Intentar usar gamemoderun dentro del entorno actual (nativo o sandbox)
        if shutil.which("gamemoderun"):
            return ["gamemoderun"] + command_list

        # 2. Si estamos en Flatpak y no hay gamemoderun interno, intentar vía host como fallback
        if app.running_in_flatpak:
            flatpak_spawn_cmd = shutil.which("flatpak-spawn")
            if flatpak_spawn_cmd:
                # Nota: Si el comando ya empieza por flatpak-spawn --host, esto podría duplicarlo
                # pero la lógica de abajo maneja los comandos base.
                return [flatpak_spawn_cmd, "--host", "gamemoderun"] + command_list

        return command_list

    if mode == c.MODE_BIN_CUSTOM:
        client = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_CLIENT)
        if not client or not os.path.exists(client):
            messagebox.showerror(c.UI_ERROR_TITLE, c.UI_CLIENT_PATH_ERROR)
            return
        cmd = apply_gamemode([client, "-dg", version_path])

    elif mode == c.MODE_BIN_FLATPAK:
        base_cmd = ["flatpak", "run", flatpak_id, "-dg", version_path]
        if app.running_in_flatpak:
            flatpak_spawn_cmd = shutil.which("flatpak-spawn")
            if flatpak_spawn_cmd:
                # Si usamos GameMode, intentamos invocarlo antes del flatpak run si es posible,
                # o dejar que apply_gamemode decida.
                # Para Flatpak Custom (binario en host), lo mejor es envolverlo todo.
                cmd = [flatpak_spawn_cmd, "--host"]
                if gamemode_enabled:
                    cmd += ["gamemoderun"]
                cmd += base_cmd
            else:
                # Fallback a los binarios internos si flatpak-spawn no está disponible
                client_path = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_CLIENT)
                if client_path and os.path.exists(client_path):
                    cmd = apply_gamemode([client_path, "-dg", version_path])
                else:
                    messagebox.showerror(c.UI_ERROR_TITLE, c.UI_CLIENT_PATH_ERROR)
                    return
        else:
            cmd = apply_gamemode(base_cmd)

    elif mode == c.MODE_BIN_LOCAL:
        local_bin = os.path.join(os.getcwd(), "bin", "mcpelauncher-client")
        if not os.path.exists(local_bin):
            messagebox.showerror(c.UI_ERROR_TITLE, c.UI_LOCAL_BINARY_NOT_FOUND.format(local_bin=local_bin))
            return
        cmd = apply_gamemode([local_bin, "-dg", version_path])

    elif mode == c.MODE_BIN_SYSTEM:
        sys_bin = "/usr/local/bin/mcpelauncher-client"
        if not os.path.exists(sys_bin) and not shutil.which("mcpelauncher-client"):
            messagebox.showerror(c.UI_ERROR_TITLE, c.UI_SYSTEM_BINARY_NOT_FOUND)
            return
        target_bin = sys_bin if os.path.exists(sys_bin) else "mcpelauncher-client"
        cmd = apply_gamemode([target_bin, "-dg", version_path])

    # Comprobación de seguridad final y robusta.
    if cmd:
        try:
            resolved_game_binary_path = shutil.which(cmd[0])
            if resolved_game_binary_path:
                game_binary_abs_path = os.path.abspath(resolved_game_binary_path)
                launcher_script_abs_path = os.path.abspath(app.launcher_path)

                if game_binary_abs_path == launcher_script_abs_path:
                    messagebox.showerror(
                        c.UI_CONFIG_ERROR_TITLE,
                        c.UI_SELF_LAUNCH_ERROR_MSG
                    )
                    return
        except Exception as e:
            print(f"Error en la comprobación de seguridad de la ruta: {e}")

    try:
        print(f"Ejecutando ({mode}): {' '.join(cmd)}")
        app.config[c.CONFIG_KEY_LAST_VERSION] = version
        app.config[c.CONFIG_KEY_DEBUG_LOG] = app.play_tab.var_debug_log.get()
        app.config[c.CONFIG_KEY_CLOSE_ON_LAUNCH] = app.play_tab.var_close_on_launch.get()
        app.config_manager.save_config()

        env = os.environ.copy()

        # Opciones de Compatibilidad / Argumentos Personalizados
        if app.config.get(c.CONFIG_KEY_CUSTOM_ENV_ENABLED, False):
            custom_vars = app.config.get(c.CONFIG_KEY_CUSTOM_ENV_VARS, "")
            import shlex
            try:
                parts = shlex.split(custom_vars)
                for part in parts:
                    if "=" in part:
                        k, v = part.split("=", 1)
                        env[k] = v
                    else:
                        cmd.append(part)
            except Exception as e:
                print(f"Error parseando argumentos personalizados: {e}")
        else:
            if app.config.get(c.CONFIG_KEY_NVIDIA_PRIME, False):
                env["__NV_PRIME_RENDER_OFFLOAD"] = "1"
                env["__GLX_VENDOR_LIBRARY_NAME"] = "nvidia"
                env["__VK_LAYER_NV_optimus"] = "NVIDIA_only"
                env["DRI_PRIME"] = "1"
                env["__GL_THREADED_OPTIMIZATIONS"] = "1"
                env["__GL_GSYNC_ALLOWED"] = "1"
                env["__GL_VRR_ALLOWED"] = "1"
            if app.config.get(c.CONFIG_KEY_ZINK_MODE, False):
                env["MESA_LOADER_DRIVER_OVERRIDE"] = "zink"

        if mode == c.MODE_BIN_CUSTOM:
            bin_dirs = {os.path.dirname(p) for k, p in app.config[c.CONFIG_KEY_BINARY_PATHS].items() if p and os.path.exists(p)}
            if bin_dirs:
                path_additions = ":".join(bin_dirs)
                env["PATH"] = f"{path_additions}:{env.get('PATH', '')}"
                env["LD_LIBRARY_PATH"] = f"{path_additions}:{env.get('LD_LIBRARY_PATH', '')}"

        try:
            if app.play_tab.var_debug_log.get():
                terms = ["gnome-terminal", "konsole", "xfce4-terminal", "mate-terminal", "lxterminal", "tilix", "alacritty", "kitty", "x-terminal-emulator", "xterm"]
                selected_term = next((t for t in terms if shutil.which(t)), None)
                if selected_term:
                    bash_cmd = f"{' '.join(cmd)}; echo; read -p '{c.UI_TERMINAL_PROMPT_CLOSE}'"
                    popen_args = [selected_term, "--", "bash", "-c", bash_cmd] if selected_term == "gnome-terminal" else [selected_term, "-e", f'bash -c "{bash_cmd}"']
                    if app.running_in_flatpak:
                        flatpak_spawn_cmd = shutil.which("flatpak-spawn")
                        if flatpak_spawn_cmd:
                            popen_args = [flatpak_spawn_cmd, "--host"] + popen_args
                        else:
                            messagebox.showerror(c.UI_ERROR_TITLE, c.UI_ERROR_FLATPAK_SPAWN_NOT_FOUND)
                            return
                    subprocess.Popen(popen_args)
                else:
                    messagebox.showerror(c.UI_ERROR_TITLE, c.UI_NO_COMPATIBLE_TERMINAL)
                    subprocess.Popen(cmd, cwd=app.active_path, env=env)
            else:
                subprocess.Popen(cmd, cwd=app.active_path, env=env)

            if app.play_tab.check_close_on_launch.get():
                app.destroy()
        except OSError as e:
            if app.running_in_flatpak:
                print(f"Subprocess failed with OSError: {e}. Attempting execve fallback.")
                _launch_with_execve_fallback(app, cmd, env)
            else:
                messagebox.showerror(c.UI_ERROR_TITLE, c.UI_LAUNCH_ERROR.format(e=e))
    except Exception as e:
        messagebox.showerror(c.UI_ERROR_TITLE, c.UI_LAUNCH_ERROR.format(e=e))

def export_worlds_dialog(app):
    if not app.active_path: return
    worlds_path = os.path.join(app.active_path, c.WORLDS_DIR)
    if not os.path.exists(worlds_path):
        messagebox.showinfo(c.UI_INFO_TITLE, c.UI_NO_WORLDS_FOUND)
        return

    worlds = [d for d in os.listdir(worlds_path) if os.path.isdir(os.path.join(worlds_path, d))]
    if not worlds: return

    top = ctk.CTkToplevel(app)
    top.title(c.UI_EXPORT_WORLDS_TITLE)
    top.geometry("500x600")
    top.transient(app)

    scroll = ctk.CTkScrollableFrame(top, label_text=c.UI_SELECT_WORLDS_LABEL, corner_radius=c.CORNER_RADIUS, label_font=c.FONT_BOLD)
    scroll.pack(fill="both", expand=True, padx=10, pady=10)

    vars = []
    for w in worlds:
        display_name = w
        try:
            with open(os.path.join(worlds_path, w, "levelname.txt"), "r") as f: display_name = f"{f.read().strip()} ({w})"
        except OSError: pass
        v = ctk.IntVar()
        vars.append((w, v))
        ctk.CTkCheckBox(scroll, text=display_name, variable=v, font=c.FONT_NORMAL).pack(anchor="w", pady=2)

    def do_export():
        selected = [w for w, v in vars if v.get() == 1]
        if not selected: return
        dest_dir = ask_directory_native(top, title=c.UI_SELECT_DEST_FOLDER_TITLE)
        if not dest_dir: return
        count = 0
        for w_code in selected:
            try:
                src = os.path.join(worlds_path, w_code)
                name = w_code
                try:
                    with open(os.path.join(src, "levelname.txt"), "r") as f: name = "".join(x for x in f.read().strip() if x.isalnum() or x in " -_")
                except OSError: pass
                save_path = os.path.join(dest_dir, f"{name}.mcworld")
                temp_base = os.path.join(dest_dir, f"{name}_temp")
                created_zip = shutil.make_archive(temp_base, "zip", src)
                shutil.move(created_zip, save_path)
                if os.path.exists(temp_base + ".zip"): os.remove(temp_base + ".zip")
                count += 1
            except Exception as e:
                print(f"Error exportando {w_code}: {e}")
        messagebox.showinfo(c.UI_SUCCESS_TITLE, c.UI_WORLDS_EXPORTED_SUCCESS.format(count=count, dest_dir=dest_dir))
        top.destroy()

    btn_frame = ctk.CTkFrame(top, corner_radius=c.CORNER_RADIUS)
    btn_frame.pack(fill="x", pady=10, padx=10)
    ctk.CTkButton(btn_frame, text=c.UI_BUTTON_SELECT_ALL, command=lambda: [v.set(1) for _, v in vars], font=c.FONT_NORMAL).pack(side="left", padx=10, pady=10)
    ctk.CTkButton(btn_frame, text=c.UI_BUTTON_EXPORT_SELECTED, command=do_export, font=c.FONT_BOLD).pack(side="right", padx=10, pady=10)

    top.grab_set()

def export_screenshots_dialog(app):
    base_paths = list(set([p for p in [app.flatpak_path, app.compiled_path, app.active_path] if p]))
    possible_subpaths = [c.SCREENSHOTS_DIR, c.SCREENSHOTS_DIR_ALT, os.path.join(c.MINECRAFT_PE_DIR_ALT, c.SCREENSHOTS_DIR_ALT), os.path.join(c.MINECRAFT_PE_DIR_ALT, c.SCREENSHOTS_DIR)]
    screens_path = next((os.path.join(base, sub) for base in base_paths for sub in possible_subpaths if os.path.exists(os.path.join(base, sub))), None)

    if not screens_path:
        fallback_path = os.path.join(app.active_path, "games/com.mojang") if app.active_path else None
        msg = c.UI_SCREENSHOTS_NOT_FOUND_MSG
        if fallback_path and os.path.exists(fallback_path):
            if messagebox.askyesno(c.UI_INFO_TITLE, c.UI_OPEN_COMOJANG_FOLDER_PROMPT.format(msg=msg)):
                subprocess.Popen(["xdg-open", fallback_path])
        else:
            messagebox.showinfo(c.UI_INFO_TITLE, msg)
        return
    try:
        subprocess.Popen(["xdg-open", screens_path])
    except Exception as e:
        messagebox.showerror(c.UI_ERROR_TITLE, c.UI_CANNOT_OPEN_FOLDER_ERROR.format(e=e))

def show_flatpak_runtime_info(app):
    dialog = ctk.CTkToplevel(app)
    dialog.title(c.UI_FLATPAK_RUNTIME_INFO_TITLE)
    dialog.geometry("550x400")
    dialog.resizable(False, False)
    dialog.transient(app)
    ctk.CTkLabel(dialog, text=c.UI_INFO_TITLE + " Runtimes", font=c.FONT_SUBTITLE).pack(pady=15)
    text_frame = ctk.CTkFrame(dialog, corner_radius=c.CORNER_RADIUS)
    text_frame.pack(fill="both", expand=True, padx=20, pady=10)
    textbox = ctk.CTkTextbox(text_frame, font=("Courier", 12), wrap="word", fg_color=["#F5F5F5", "#2B2B2B"])
    textbox.pack(fill="both", expand=True, padx=5, pady=5)
    textbox.insert("1.0", c.UI_FLATPAK_RUNTIME_INFO_TEXT)
    textbox.configure(state="disabled")
    ctk.CTkButton(dialog, text=c.UI_BUTTON_CLOSE, command=dialog.destroy, height=35, width=120, font=c.FONT_NORMAL).pack(pady=10)
    dialog.grab_set()

def verify_dependencies(app):
    if app.running_in_flatpak:
        show_flatpak_runtime_info(app)
        return

    # --- Detección y Mapeo ---
    manager_map = {
        "APT": (["dpkg", "-s"], "apt install -y"),
        "DNF": (["rpm", "-q"], "dnf install -y"),
        "PACMAN": (["pacman", "-Q"], "pacman -S --noconfirm --needed")
    }

    detected_manager_name = None
    if shutil.which("apt"):
        detected_manager_name = "APT"
    elif shutil.which("dnf"):
        detected_manager_name = "DNF"
    elif shutil.which("pacman"):
        detected_manager_name = "PACMAN"
    else:
        messagebox.showerror(c.UI_ERROR_TITLE, c.UI_PKG_MANAGER_NOT_SUPPORTED)
        return

    # Usar el mapa de dependencias de constants.py
    if detected_manager_name not in c.DEPENDENCY_MAP:
        messagebox.showerror(c.UI_ERROR_TITLE, f"No dependency map for '{detected_manager_name}'")
        return

    check_cmd, install_cmd = manager_map[detected_manager_name]
    pkg_list = sorted(list(set(c.DEPENDENCY_MAP[detected_manager_name]))) # Limpiar y ordenar

    prog = ctk.CTkToplevel(app)
    prog.title(c.UI_VERIFYING_TITLE)
    prog.geometry("300x120")
    lbl_prog = ctk.CTkLabel(prog, text=c.UI_STARTING_MSG, font=c.FONT_NORMAL)
    lbl_prog.pack(pady=20)
    bar = ctk.CTkProgressBar(prog, mode="indeterminate")
    bar.pack(pady=10, padx=20, fill="x")
    bar.start()

    def show_result(text):
        prog.destroy()
        d = ctk.CTkToplevel(app)
        d.title(c.UI_RESULT_TITLE)
        d.geometry("400x300")
        d.transient(app)
        ctk.CTkLabel(d, text=c.UI_VERIFICATION_RESULT_HEADER, font=c.FONT_BOLD).pack(pady=10)
        t = ctk.CTkTextbox(d, wrap="word", font=c.FONT_NORMAL)
        t.pack(fill="both", expand=True, padx=10, pady=5)
        t.insert("1.0", text)
        ctk.CTkButton(d, text=c.UI_BUTTON_CLOSE, command=d.destroy, font=c.FONT_NORMAL).pack(pady=10)
        d.grab_set()

    def show_result_missing(missing_list):
        prog.destroy()
        d = ctk.CTkToplevel(app)
        d.title(c.UI_MISSING_DEPS_TITLE)
        d.geometry("500x400")
        d.transient(app)
        ctk.CTkLabel(d, text=c.UI_MISSING_DEPS_MSG, text_color="red", font=c.FONT_BOLD).pack(pady=10)
        t = ctk.CTkTextbox(d, font=("Courier", 11))
        t.pack(fill="both", expand=True, padx=10, pady=5)
        t.insert("1.0", "\n".join(missing_list))

        def install():
            full_cmd = f"pkexec {install_cmd} {' '.join(missing_list)}"
            if messagebox.askyesno(c.UI_INFO_TITLE, c.UI_INSTALL_PROMPT.format(full_cmd=full_cmd)):
                term = next((t for t in ["gnome-terminal", "konsole", "xfce4-terminal", "mate-terminal", "lxterminal", "tilix", "xterm"] if shutil.which(t)), None)
                if term:
                    bash_cmd = f"{full_cmd}; echo; read -p '{c.UI_TERMINAL_PROMPT_CLOSE}'"
                    subprocess.Popen([term, "-e", f'bash -c "{bash_cmd}"'])
                else:
                    messagebox.showerror(c.UI_ERROR_TITLE, c.UI_NO_COMPATIBLE_TERMINAL)
                d.destroy()
        ctk.CTkButton(d, text=c.UI_BUTTON_INSTALL_ROOT, fg_color="orange", command=install, font=c.FONT_BOLD).pack(pady=10)
        d.grab_set()

    def run_check():
        app.after(0, lambda: lbl_prog.configure(text=f"{c.UI_VERIFYING_TITLE} {len(pkg_list)} packages..."))
        missing = [pkg for pkg in pkg_list if subprocess.call(check_cmd + [pkg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0]

        # Manejar casos de paquetes 't64' en sistemas APT
        if detected_manager_name == "APT":
            t64_alternatives = {
                "libasound2": "libasound2t64",
                "libcurl4": "libcurl4t64",
                "libqt5core5a": "libqt5core5t64",
                "libqt5gui5": "libqt5gui5t64",
                "libqt5network5": "libqt5network5t64",
                "libqt5widgets5": "libqt5widgets5t64",
                "libssl3": "libssl3t64"
            }

            packages_to_remove = []
            for pkg in missing:
                if pkg in t64_alternatives:
                    alt_pkg = t64_alternatives[pkg]
                    if subprocess.call(check_cmd + [alt_pkg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                        packages_to_remove.append(pkg)

            if packages_to_remove:
                missing = [p for p in missing if p not in packages_to_remove]

        if missing:
            app.after(0, lambda: show_result_missing(missing))
        else:
            app.after(0, lambda: show_result(c.UI_DEPENDENCIES_OK))

    threading.Thread(target=run_check).start()

def check_requirements_dialog(app):
    prog = ctk.CTkToplevel(app)
    prog.title(c.UI_ANALYZING_TITLE)
    prog.geometry("300x120")
    ctk.CTkLabel(prog, text=c.UI_ANALYZING_HW_MSG, font=c.FONT_NORMAL).pack(pady=20)
    bar = ctk.CTkProgressBar(prog, mode="indeterminate")
    bar.pack(pady=10, padx=20, fill="x")
    bar.start()

    def run_analysis():
        arch = platform.machine()
        cpu_flags = []
        cpu_model = c.UI_HW_NOT_DETECTED
        ram_total = c.UI_HW_NOT_DETECTED

        try:
            with open("/proc/cpuinfo", "r") as f:
                content = f.read()
                m_flags = re.search(r"flags\s*:\s*(.*)", content)
                if m_flags: cpu_flags = m_flags.group(1).split()

                m_model = re.search(r"model name\s*:\s*(.*)", content)
                if m_model: cpu_model = m_model.group(1).strip()
        except: pass

        try:
            with open("/proc/meminfo", "r") as f:
                m_mem = re.search(r"MemTotal:\s*(\d+)\s*kB", f.read())
                if m_mem:
                    ram_gb = round(int(m_mem.group(1)) / (1024 * 1024), 2)
                    ram_total = f"{ram_gb} GB"
        except: pass

        has_sse = all(flag in cpu_flags for flag in ["ssse3", "sse4_1", "sse4_2", "popcnt"])
        gl_ver, gl_es_3, gl_es_2, gl_es_31 = c.UI_SHADER_STATUS_UNKNOWN, False, False, False

        def get_gl_info(cmd_prefix=[]):
            nonlocal gl_ver, gl_es_3, gl_es_2, gl_es_31
            try:
                cmd = cmd_prefix + ["sh", "-c", "glxinfo | grep 'OpenGL ES profile version'"]
                output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
                gl_ver = output.strip()
                gl_es_3 = any(v in gl_ver for v in ["3.0", "3.1", "3.2", "3.3"])
                gl_es_31 = "3.1" in gl_ver or "3.2" in gl_ver
                gl_es_2 = "2.0" in gl_ver
                return True
            except:
                return False

        # Intentar normal, luego flatpak-spawn
        if not get_gl_info():
            if app.running_in_flatpak:
                get_gl_info(cmd_prefix=["flatpak-spawn", "--host"])

        if gl_ver == c.UI_SHADER_STATUS_UNKNOWN:
            gl_ver = c.UI_HW_NOT_DETECTED

        compat_ver = c.UI_INCOMPATIBLE_TEXT
        if arch == "x86_64" and has_sse:
            if gl_es_31: compat_ver = "1.13.0 - 1.21.130+"
            elif gl_es_3: compat_ver = "1.13.0 - 1.21.124"
            elif gl_es_2: compat_ver = "1.13.0 - 1.20.20"

        res_text = (f"--- {c.UI_HW_CPU_INFO} ---\n" +
                    f"{c.UI_HW_MODEL}: {cpu_model}\n" +
                    c.UI_HW_ARCH.format(arch=arch) +
                    c.UI_HW_CPU_EXT.format(status='✅' if has_sse else '⚠️') +
                    f"\n--- {c.UI_HW_RAM_INFO} ---\n" +
                    f"{c.UI_HW_RAM_TOTAL}: {ram_total}\n" +
                    f"\n--- {c.UI_HW_GPU_INFO} ---\n" +
                    c.UI_HW_OPENGL_ES.format(gl_ver=gl_ver) +
                    f"\n----------------------------\n" +
                    f"{c.UI_HARDWARE_ANALYSIS_RECOMMENDATION.format(compat_ver=compat_ver)}")
        app.after(0, lambda: show_dialog(res_text))

    def show_dialog(text):
        prog.destroy()
        dial = ctk.CTkToplevel(app)
        dial.title(c.UI_HARDWARE_ANALYSIS_TITLE)
        dial.geometry("550x400")
        dial.transient(app)
        ctk.CTkLabel(dial, text=c.UI_HARDWARE_ANALYSIS_HEADER, font=c.FONT_BOLD).pack(pady=10)
        txt_res = ctk.CTkTextbox(dial, font=("Courier", 12), wrap="none")
        txt_res.pack(fill="both", expand=True, padx=20, pady=10)
        txt_res.insert("1.0", text)
        txt_res.configure(state="disabled")
        ctk.CTkButton(dial, text=c.UI_BUTTON_CLOSE, command=dial.destroy, font=c.FONT_NORMAL).pack(pady=10)
        dial.grab_set()

    threading.Thread(target=run_analysis).start()
