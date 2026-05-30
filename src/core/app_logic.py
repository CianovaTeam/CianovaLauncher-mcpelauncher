import os
import sys
import platform
import shutil
import subprocess
import shlex
import threading
import time
import re
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QLabel

from src.gui import custom_dialogs as messagebox
from src import constants as c
from src.utils.image_manager import ImageManager
from src.utils.logger import logger

from .worker import LogicWorker
from .install_ops import (
    detect_installation,
    change_mode_ui,
    switch_profile,
    check_shader_status,
    update_shader_status_label,
    refresh_version_list,
    select_version,
)


# ── Core functions ──

def launch_from_args(app, version):
    """Launch a specific version passed via CLI arguments."""
    from .version_ops import get_installed_versions
    versions = get_installed_versions(app)
    if version in versions:
        app.play_tab.set(version)
        launch_game(app)
    else:
        messagebox.showerror(app, c.t("UI_ERROR_TITLE"),
                             c.t("UI_VERSION_NOT_INSTALLED_ERROR", version=version))


def disable_shaders(app):
    """Disable shaders by resetting graphics_mode in options.txt."""
    if not app.active_path:
        return
    p = os.path.join(app.active_path, c.MINECRAFT_PE_DIR_ALT, c.OPTIONS_FILE)
    try:
        with open(p, "r") as f:
            content = f.read()
        new = content.replace("graphics_mode:2", "graphics_mode:0").replace(
            "graphics_mode:1", "graphics_mode:0"
        )
        with open(p, "w") as f:
            f.write(new)
        check_shader_status(app)
        messagebox.showinfo(app, c.t("UI_SUCCESS_TITLE"), c.t("UI_SHADERS_DISABLED_MSG"))
    except Exception as e:
        messagebox.showerror(app, c.t("UI_ERROR_TITLE"), str(e))


def open_data_folder(app):
    """Open the active Minecraft data folder in the file manager."""
    if app.active_path:
        subprocess.Popen(["xdg-open", app.active_path])


def export_screenshots_dialog(app):
    """Open the screenshots folder or prompt to open the com.mojang folder."""
    if not app.active_path:
        return
    p1 = os.path.join(app.active_path, c.SCREENSHOTS_DIR)
    p2 = os.path.join(app.active_path, c.SCREENSHOTS_DIR_ALT)
    p = p1 if os.path.exists(p1) else p2

    if os.path.exists(p):
        subprocess.Popen(["xdg-open", p])
    else:
        com_mojang = os.path.dirname(p1)
        if messagebox.askyesno(
            app, c.t("UI_INFO_TITLE"),
            c.t("UI_OPEN_COMOJANG_FOLDER_PROMPT", msg=c.t("UI_SCREENSHOTS_NOT_FOUND_MSG"))
        ):
            if os.path.exists(com_mojang):
                subprocess.Popen(["xdg-open", com_mojang])
            else:
                messagebox.showerror(app, c.t("UI_ERROR_TITLE"),
                                     "Folder com.mojang not found.")


def is_running_in_flatpak():
    """Return whether the launcher is running inside a Flatpak sandbox."""
    return os.path.exists(c.FLATPAK_INFO_FILE)


def get_flatpak_app_id():
    """Return the Flatpak application ID from the Flatpak info file."""
    if not is_running_in_flatpak():
        return None
    try:
        with open(c.FLATPAK_INFO_FILE, "r") as f:
            for line in f:
                if line.startswith("app="):
                    return line.split("=")[1].strip()
    except Exception:
        pass
    return None


def setup_flatpak_environment(app):
    """Configure default binary paths and mode for Flatpak environments."""
    if not app.running_in_flatpak:
        return
    if app.config.get(c.CONFIG_KEY_MODE) is None:
        app.config[c.CONFIG_KEY_MODE] = c.MODE_BIN_SYSTEM
    paths = app.config.get(c.CONFIG_KEY_BINARY_PATHS, {})
    changed = False
    m = {
        c.CONFIG_KEY_CLIENT: "/app/bin/mcpelauncher-client",
        c.CONFIG_KEY_EXTRACT: "/app/bin/mcpelauncher-extract",
    }
    for k, v in m.items():
        if not paths.get(k) or (
            paths.get(k).startswith("/app/bin/") and not os.path.exists(paths.get(k))
        ):
            if os.path.exists(v):
                paths[k], changed = v, True
    if changed:
        app.config[c.CONFIG_KEY_BINARY_PATHS] = paths
        app.config_manager.save_config()


def check_migration_needed(app):
    """Notify the user if legacy data from a previous Flatpak install is detected."""
    if not app.running_in_flatpak:
        return
    old = os.path.join(app.home, c.LOCAL_SHARE_DIR)
    if app.config.get(c.CONFIG_KEY_MIGRATION_NOTIFIED) or not os.path.exists(old):
        return
    if os.path.exists(os.path.join(old, c.VERSIONS_DIR)):
        messagebox.showinfo(app, c.t("UI_DATA_DETECTED_TITLE"), c.t("UI_MIGRATION_PROMPT_MSG"))
        app.config[c.CONFIG_KEY_MIGRATION_NOTIFIED] = True
        app.config_manager.save_config()


# ── Game launcher ──

def launch_game(app):
    """Launch the selected Minecraft version with the configured environment."""
    version = app.play_tab.get()
    if not version:
        messagebox.showwarning(app, c.t("UI_INFO_TITLE"),
                               c.t("UI_PLEASE_SELECT_VERSION_MSG"))
        return

    vpath = os.path.join(app.active_path, c.VERSIONS_DIR, version)
    mode = app.config.get(c.CONFIG_KEY_MODE, c.t("UI_DEFAULT_MODE"))
    fid = app.config.get(c.CONFIG_KEY_FLATPAK_ID,
                         c.MCPELAUNCHER_FLATPAK_ID)

    cmd = []
    gamemode_enabled = app.config.get(c.CONFIG_KEY_GAMEMODE_ENABLED, False)

    def apply_gamemode(cmd_list):
        if not gamemode_enabled:
            return cmd_list
        if shutil.which("gamemoderun"):
            return ["gamemoderun"] + cmd_list
        if app.running_in_flatpak:
            fs = shutil.which("flatpak-spawn")
            if fs:
                return [fs, "--host", "gamemoderun"] + cmd_list
        return cmd_list

    if mode == c.MODE_BIN_CUSTOM:
        cl = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_CLIENT)
        if not cl or not os.path.exists(cl):
            messagebox.showerror(app, c.t("UI_ERROR_TITLE"),
                                 c.t("UI_CLIENT_PATH_ERROR"))
            return
        cmd = apply_gamemode([cl, "-dg", vpath])
    elif mode == c.MODE_BIN_FLATPAK:
        base_cmd = ["flatpak", "run", fid, "-dg", vpath]
        if app.running_in_flatpak:
            fs = shutil.which("flatpak-spawn")
            if fs:
                cmd = [fs, "--host"]
                if gamemode_enabled:
                    cmd += ["gamemoderun"]
                cmd += base_cmd
            else:
                cl = (
                    app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_CLIENT)
                    or "/app/bin/mcpelauncher-client"
                )
                if os.path.exists(cl):
                    cmd = apply_gamemode([cl, "-dg", vpath])
                else:
                    messagebox.showerror(app, c.t("UI_ERROR_TITLE"),
                                         c.t("UI_CLIENT_PATH_ERROR"))
                    return
        else:
            cmd = apply_gamemode(base_cmd)
    elif mode == c.MODE_BIN_SYSTEM:
        cmd = apply_gamemode(["mcpelauncher-client", "-dg", vpath])

    if not cmd:
        return

    env = os.environ.copy()
    extra_env = {}
    if app.config.get(c.CONFIG_KEY_CUSTOM_ENV_ENABLED, False):
        custom_vars = app.config.get(c.CONFIG_KEY_CUSTOM_ENV_VARS, "")
        try:
            parts = shlex.split(custom_vars)
            for part in parts:
                if "=" in part:
                    k, v = part.split("=", 1)
                    extra_env[k] = v
                else:
                    cmd.append(part)
        except Exception as e:
            logger.error(f"Error parseando argumentos: {e}")
    else:
        if app.config.get(c.CONFIG_KEY_NVIDIA_PRIME):
            extra_env.update({
                "__NV_PRIME_RENDER_OFFLOAD": "1",
                "__GL_VENDOR_LIBRARY_NAME": "nvidia",
                "__VK_LAYER_NV_optimus": "NVIDIA_only",
                "DRI_PRIME": "1",
                "__GL_THREADED_OPTIMIZATIONS": "1",
                "__GL_GSYNC_ALLOWED": "1",
                "__GL_VRR_ALLOWED": "1",
            })
        if app.config.get(c.CONFIG_KEY_ZINK_MODE):
            extra_env["MESA_LOADER_DRIVER_OVERRIDE"] = "zink"

    is_flatpak_run = "flatpak" in cmd and "run" in cmd
    fs_path = shutil.which("flatpak-spawn")
    is_flatpak_spawn_host = (
        cmd and fs_path and cmd[0] == fs_path and "--host" in cmd
    )

    if extra_env:
        if is_flatpak_run:
            new_cmd = []
            for part in cmd:
                new_cmd.append(part)
                if part == "run":
                    for k, v in extra_env.items():
                        new_cmd.append(f"--env={k}={v}")
            cmd = new_cmd
        elif is_flatpak_spawn_host:
            idx = cmd.index("--host") + 1
            cmd = (
                cmd[:idx]
                + ["env"]
                + [f"{k}={v}" for k, v in extra_env.items()]
                + cmd[idx:]
            )
        else:
            env.update(extra_env)

    try:
        app.config[c.CONFIG_KEY_LAST_VERSION] = version
        app.config_manager.save_config()

        logger.info(f"Launching version: {version}")
        logger.info(f"Command: {' '.join(cmd)}")
        logger.debug(f"Environment variables added: {extra_env}")

        if hasattr(app, '_discord_rpc') and app._discord_rpc:
            app._discord_rpc.set_playing(version, time.time())

        debug_log = app.config.get(c.CONFIG_KEY_DEBUG_LOG, False)
        launched = False
        if debug_log and not app.running_in_flatpak:
            terms = ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"]
            term = next((t for t in terms if shutil.which(t)), None)
            if term:
                cmd_str = (
                    shlex.join(cmd)
                    if hasattr(shlex, 'join')
                    else " ".join(shlex.quote(x) for x in cmd)
                )
                bcmd = (
                    f"{cmd_str}; echo; read -p {shlex.quote(c.t("UI_TERMINAL_PROMPT_CLOSE"))}"
                )
                subprocess.Popen(
                    [term, "-e", f'bash -c {shlex.quote(bcmd)}'],
                    env=env, cwd=app.active_path,
                )
                launched = True

        if not launched:
            try:
                subprocess.Popen(cmd, env=env, cwd=app.active_path)
            except (OSError, PermissionError) as e:
                logger.warning(f"subprocess.Popen failed ({e}), trying os.execve...")
                os.execve(cmd[0], cmd, env)

        if app.config.get(c.CONFIG_KEY_CLOSE_ON_LAUNCH):
            logger.info("Closing launcher as requested on launch.")
            app.close()
    except Exception as e:
        logger.error(f"Launch error: {e}")
        messagebox.showerror(app, c.t("UI_ERROR_TITLE"), f"Launch error: {e}")


# ═══════════════════════════════════════════
#  Re-export from sub-modules (facade)
#  Keep app_logic as the public API module
# ═══════════════════════════════════════════

from .ui_utils import clear_layout
from .version_ops import (
    get_installed_versions,
    resolve_version,
    rename_version,
    create_version_shortcut,
    process_apk,
)
from .profiles import (
    get_profiles,
    create_profile_pyside,
    rename_profile,
    delete_profile,
    apply_profile_symlink,
    ensure_profile_system,
)
from .hardware import get_compatibility_range, check_requirements_dialog
from .dependencies import verify_dependencies, show_dep_results
from .google_integration import (
    launch_google_login,
    check_google_session,
    download_and_install_google,
)
