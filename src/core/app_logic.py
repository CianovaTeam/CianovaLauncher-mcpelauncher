import os
import sys
import platform
import shutil
import subprocess
import shlex
import threading
import time
import re
from PySide6.QtCore import QTimer, Qt, QThread, Signal
from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtGui import QPixmap

from src.gui import custom_dialogs as messagebox
from src import constants as c
from src.utils.image_manager import ImageManager
from src.utils.logger import logger


# ═══════════════════════════════════════════
#  Core functions that stay in app_logic
# ═══════════════════════════════════════════

def launch_from_args(app, version):
    from .version_ops import get_installed_versions
    versions = get_installed_versions(app)
    if version in versions:
        app.play_tab.set(version)
        launch_game(app)
    else:
        messagebox.showerror(app, c.UI_ERROR_TITLE,
                             c.UI_VERSION_NOT_INSTALLED_ERROR.format(version=version))


def disable_shaders(app):
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
        messagebox.showinfo(app, c.UI_SUCCESS_TITLE, c.UI_SHADERS_DISABLED_MSG)
    except Exception as e:
        messagebox.showerror(app, c.UI_ERROR_TITLE, str(e))


def open_data_folder(app):
    if app.active_path:
        subprocess.Popen(["xdg-open", app.active_path])


def export_screenshots_dialog(app):
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
            app, c.UI_INFO_TITLE,
            c.UI_OPEN_COMOJANG_FOLDER_PROMPT.format(msg=c.UI_SCREENSHOTS_NOT_FOUND_MSG)
        ):
            if os.path.exists(com_mojang):
                subprocess.Popen(["xdg-open", com_mojang])
            else:
                messagebox.showerror(app, c.UI_ERROR_TITLE,
                                     "Folder com.mojang not found.")


def detect_installation(app):
    from .profiles import ensure_profile_system
    imode = app.config.get(c.CONFIG_KEY_INSTALL_MODE, c.MODE_INSTALL_LOCAL)
    fid = app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.DEFAULT_FLATPAK_ID)
    std_shared = os.path.join(app.home, c.LOCAL_SHARE_DIR)
    app.is_flatpak = False

    if app.running_in_flatpak and imode in [c.MODE_INSTALL_OWN, c.MODE_INSTALL_SHARED]:
        if os.path.exists(os.path.join(app.our_data_path, c.VERSIONS_DIR)):
            imode, app.active_path = c.MODE_INSTALL_OWN, app.our_data_path
        elif os.path.exists(os.path.join(std_shared, c.VERSIONS_DIR)):
            imode, app.active_path = c.MODE_INSTALL_SHARED, std_shared
        else:
            imode, app.active_path = c.MODE_INSTALL_OWN, app.our_data_path
        app.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, imode)
    else:
        if imode == c.MODE_INSTALL_OWN:
            app.active_path = app.our_data_path if app.running_in_flatpak else app.compiled_path
        elif imode == c.MODE_INSTALL_SHARED:
            app.active_path = std_shared
        elif imode == c.MODE_INSTALL_LOCAL:
            app.active_path = app.compiled_path
        elif imode == c.MODE_INSTALL_FLATPAK:
            app.is_flatpak = True
            app.active_path = os.path.join(
                app.home, f"{c.FLATPAK_DATA_DIR}/{fid}/{c.MCPELAUNCHER_DATA_SUBDIR}"
            )

    if app.active_path:
        ensure_profile_system(app)

    status_text = f"● Mode: {imode}"
    if imode == c.MODE_INSTALL_OWN:
        status_text = c.UI_STATUS_LOCAL_OWN
    elif imode == c.MODE_INSTALL_SHARED:
        status_text = c.UI_STATUS_LOCAL_SHARED
    elif imode == c.MODE_INSTALL_LOCAL:
        status_text = c.UI_STATUS_LOCAL
    elif imode == c.MODE_INSTALL_FLATPAK:
        status_text = c.UI_STATUS_FLATPAK_CUSTOM.format(flatpak_id=fid)

    app.play_tab.lbl_status.setText(status_text)
    app.update_floating_labels()
    app.play_tab.update_profile_indicator()

    refresh_version_list(app)
    check_shader_status(app)

    try:
        disp = c.UI_INSTALL_MODES.get(imode, "Unknown")
        app.play_tab.combo_mode.setCurrentText(disp)
        app.tools_tab.lbl_tools_status.setText(status_text)
        app.update_floating_labels()
    except Exception:
        pass


def change_mode_ui(app, disp):
    key = next((k for k, v in c.UI_INSTALL_MODES.items() if v == disp),
               c.MODE_INSTALL_LOCAL)
    app.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, key)
    if key == c.MODE_INSTALL_FLATPAK:
        from PySide6.QtWidgets import QInputDialog
        id, ok = QInputDialog.getText(
            app, c.UI_CONFIG_FLATPAK_CUSTOM_TITLE, c.UI_FLATPAK_ID_LABEL,
            text=app.config.get(c.CONFIG_KEY_FLATPAK_ID, ""),
        )
        if ok and id:
            app.config_manager.set(c.CONFIG_KEY_FLATPAK_ID, id)
            detect_installation(app)
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
    except Exception:
        pass
    return None


def setup_flatpak_environment(app):
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
    if not app.running_in_flatpak:
        return
    old = os.path.join(app.home, c.LOCAL_SHARE_DIR)
    if app.config.get(c.CONFIG_KEY_MIGRATION_NOTIFIED) or not os.path.exists(old):
        return
    if os.path.exists(os.path.join(old, c.VERSIONS_DIR)):
        messagebox.showinfo(app, c.UI_DATA_DETECTED_TITLE, c.UI_MIGRATION_PROMPT_MSG)
        app.config[c.CONFIG_KEY_MIGRATION_NOTIFIED] = True
        app.config_manager.save_config()


def switch_profile(app, name):
    from .profiles import apply_profile_symlink
    if app.active_path:
        apply_profile_symlink(app, name)
        app.config_manager.set(c.CONFIG_KEY_CURRENT_PROFILE, name)
        detect_installation(app)


# ── Shader functions ──

def check_shader_status(app):
    if not app.active_path:
        return
    op = os.path.join(app.active_path, c.MINECRAFT_PE_DIR_ALT, c.OPTIONS_FILE)
    status = "Unknown"
    if os.path.exists(op):
        try:
            with open(op, "r") as f:
                for line in f:
                    if "graphics_mode:" in line:
                        val = line.strip().split(":")[1]
                        if val == "0":
                            status = "Simple"
                        elif val == "1":
                            status = "Fancy"
                        elif val == "2":
                            status = "Vibrant"
                        break
        except Exception:
            pass
    if hasattr(app.tools_tab, "lbl_shader_status") and app.tools_tab.lbl_shader_status:
        app.tools_tab.lbl_shader_status.setText(f"Shaders: {status}")


def update_shader_status_label(app):
    check_shader_status(app)


# ── Version list UI ──

def refresh_version_list(app):
    from .ui_utils import clear_layout
    from .version_ops import resolve_version
    layout = app.play_tab.version_list_layout
    clear_layout(layout)

    app.version_cards = {}
    if not app.active_path:
        return
    vdir = os.path.join(app.active_path, c.VERSIONS_DIR)
    if not os.path.exists(vdir):
        layout.addWidget(QLabel(c.UI_NO_VERSIONS_FOLDER_MSG))
        return

    style = app.config.get(c.CONFIG_KEY_VERSION_LIST_STYLE, c.STYLE_LIST)
    isize = app.config.get(c.CONFIG_KEY_VERSION_ICON_SIZE, 32)
    tsize = app.config.get(c.CONFIG_KEY_VERSION_TITLE_SIZE, 13)
    cwidth = app.config.get(c.CONFIG_KEY_VERSION_CARD_WIDTH, 180)
    cheight = app.config.get(c.CONFIG_KEY_VERSION_CARD_HEIGHT, 145)
    default_pix = ImageManager.get_image("icon.png", size=(isize, isize))

    zooms = app.config.get(c.CONFIG_KEY_VERSION_ICON_ZOOM, {})
    xs = app.config.get(c.CONFIG_KEY_VERSION_ICON_X, {})
    ys = app.config.get(c.CONFIG_KEY_VERSION_ICON_Y, {})

    try:
        vers = sorted(
            [d for d in os.listdir(vdir) if os.path.isdir(os.path.join(vdir, d))]
        )
        if not vers:
            layout.addWidget(QLabel(c.UI_NO_VERSIONS_INSTALLED))
            return

        for v in vers:
            vpath = os.path.join(vdir, v)
            v_pix = default_pix
            for ext in [".png", ".jpg", ".jpeg", ".webp"]:
                icon_p = os.path.join(vpath, "icon" + ext)
                if os.path.exists(icon_p):
                    zoom = zooms.get(v, 100) / 100.0
                    v_pix = ImageManager.get_image(
                        icon_p, size=(int(isize * zoom), int(isize * zoom))
                    )
                    if not v_pix:
                        v_pix = default_pix
                    break

            card = QFrame()
            card.setObjectName("VersionCard")
            if style == c.STYLE_GRID:
                card.setFixedSize(cwidth, cheight)
                cl = QVBoxLayout(card)
                cl.setAlignment(Qt.AlignCenter)

                icon_container = QFrame()
                icon_container.setFixedSize(isize + 10, isize + 10)
                icon_container.setStyleSheet(
                    "background: transparent; border: none;"
                )
                icon_lbl = QLabel(icon_container)
                icon_lbl.setPixmap(v_pix)
                icon_lbl.setFixedSize(v_pix.size())
                icon_lbl.setStyleSheet("background: transparent;")

                off_x = xs.get(v, 0)
                off_y = ys.get(v, 0)
                icon_lbl.move(
                    (isize + 10 - v_pix.width()) // 2 + off_x,
                    (isize + 10 - v_pix.height()) // 2 + off_y,
                )

                cl.addWidget(icon_container, 0, Qt.AlignCenter)

                name = v
                if v == "current":
                    rv = resolve_version(os.path.join(vdir, v))
                    if rv:
                        name = f"current ({rv})"
                lbl = QLabel(name)
                lbl.setStyleSheet(
                    f"font-size: {tsize}px; font-weight: bold; background: transparent;"
                )
                lbl.setAlignment(Qt.AlignCenter)
                cl.addWidget(lbl)
            else:
                cl = QHBoxLayout(card)
                icon_container = QFrame()
                icon_container.setFixedSize(isize + 10, isize + 10)
                icon_container.setStyleSheet(
                    "background: transparent; border: none;"
                )
                icon_lbl = QLabel(icon_container)
                icon_lbl.setPixmap(v_pix)
                icon_lbl.setFixedSize(v_pix.size())
                icon_lbl.setStyleSheet("background: transparent;")

                off_x = xs.get(v, 0)
                off_y = ys.get(v, 0)
                icon_lbl.move(
                    (isize + 10 - v_pix.width()) // 2 + off_x,
                    (isize + 10 - v_pix.height()) // 2 + off_y,
                )

                cl.addWidget(icon_container)

                name = v
                if v == "current":
                    rv = resolve_version(os.path.join(vdir, v))
                    if rv:
                        name = f"current ({rv})"
                lbl = QLabel(name)
                lbl.setStyleSheet(
                    f"font-size: {tsize}px; font-weight: bold; background: transparent;"
                )
                cl.addWidget(lbl, 1)

            card.mousePressEvent = lambda e, ver=v: (select_version(app, ver), QFrame.mousePressEvent(card, e))
            app.version_cards[v] = card

            if style == c.STYLE_GRID:
                pass
            else:
                layout.addWidget(card)

        if style == c.STYLE_GRID:
            from PySide6.QtWidgets import QGridLayout
            grid = QGridLayout()
            layout.addLayout(grid)
            for i, v in enumerate(vers):
                grid.addWidget(app.version_cards[v], i // 3, i % 3)

        last = app.config.get(c.CONFIG_KEY_LAST_VERSION)
        if last in vers:
            select_version(app, last)
        elif vers:
            select_version(app, vers[0])
    except Exception:
        pass


def select_version(app, version):
    app.play_tab.set(version)
    theme_color = app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
    accent = c.THEME_COLOR_MAP.get(theme_color, "#1f6aa5")

    for v, card in app.version_cards.items():
        if v == version:
            card.setStyleSheet(
                f"#VersionCard {{ background-color: {accent}; border-radius: 8px; }}"
            )
        else:
            card.setStyleSheet(
                "#VersionCard { background-color: #333333; border-radius: 8px; }"
            )


# ── Game launcher ──

def launch_game(app):
    version = app.play_tab.get()
    if not version:
        messagebox.showwarning(app, c.UI_INFO_TITLE,
                               c.UI_PLEASE_SELECT_VERSION_MSG)
        return

    vpath = os.path.join(app.active_path, c.VERSIONS_DIR, version)
    mode = app.config.get(c.CONFIG_KEY_MODE, c.UI_DEFAULT_MODE)
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
            messagebox.showerror(app, c.UI_ERROR_TITLE,
                                 c.UI_CLIENT_PATH_ERROR)
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
                    messagebox.showerror(app, c.UI_ERROR_TITLE,
                                         c.UI_CLIENT_PATH_ERROR)
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
            print(f"Error parseando argumentos: {e}")
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
                    f"{cmd_str}; echo; read -p {shlex.quote(c.UI_TERMINAL_PROMPT_CLOSE)}"
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
        messagebox.showerror(app, c.UI_ERROR_TITLE, f"Launch error: {e}")


class LogicWorker(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, task, *args):
        super().__init__()
        self.task = task
        self.args = args

    def run(self):
        try:
            res = self.task(*self.args)
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))


# ═══════════════════════════════════════════
#  Re-export from sub-modules
#  (Keep app_logic as the public API facade)
# ═══════════════════════════════════════════

from .ui_utils import *             # clear_layout
from .profiles import *             # ensure_profile_system, apply_profile_symlink, ...
from .version_ops import *          # get_installed_versions, resolve_version, ...
from .hardware import *             # get_compatibility_range, check_requirements_dialog, ...
from .dependencies import *         # verify_dependencies, show_dep_results
from .google_integration import *   # launch_google_login, check_google_session, ...
