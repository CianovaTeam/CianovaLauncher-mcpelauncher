import json
import os
import platform
import shutil
import subprocess
import zipfile
import shlex
import threading
from src.gui import custom_dialogs as messagebox
from PySide6.QtCore import QTimer, Qt, QThread, Signal, QProcess
from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtGui import QPixmap
import tempfile
import time
import re
import glob
import urllib.request
import urllib.parse
import urllib.error
import sys as _sys

# Debug logger gated by CIANOVA_DEBUG=1 (set by run.sh).
_CIANOVA_DEBUG = os.environ.get("CIANOVA_DEBUG", "") not in ("", "0", "false", "False")
def dbg(msg, *args):
    if not _CIANOVA_DEBUG:
        return
    try:
        formatted = msg % args if args else msg
    except Exception:
        formatted = f"{msg} {args}"
    print(f"[cianova] {formatted}", flush=True, file=_sys.stderr)

from src.gui.progress_dialog import ProgressDialog
from src import constants as c
from src.utils.dialogs import ask_directory_native
from src.utils.image_manager import ImageManager

def get_installed_versions(app):
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
    except: return []

def launch_from_args(app, version):
    versions = get_installed_versions(app)
    if version in versions:
        app.play_tab.set(version)
        launch_game(app)
    else:
        messagebox.showerror(app, c.UI_ERROR_TITLE, c.UI_VERSION_NOT_INSTALLED_ERROR.format(version=version))

def process_apk(app, apk_path, ver_name, target_root=None, is_target_flatpak=None, flatpak_id=None):
    current_root = target_root if target_root else app.active_path
    if not current_root:
        messagebox.showerror(app, c.UI_ERROR_TITLE, c.UI_NO_TARGET_PATH_ERROR)
        return

    target_dir = os.path.join(current_root, c.VERSIONS_DIR, ver_name)
    use_flatpak_logic = is_target_flatpak if is_target_flatpak is not None else app.is_flatpak

    from src.gui.progress_dialog import ProgressDialog
    progress_dialog = ProgressDialog(app, c.UI_EXTRACTING_APK_TITLE, c.UI_EXTRACTING_APK_MSG)
    progress_dialog.show()

    def run_extraction():
        try:
            if os.path.exists(target_dir): shutil.rmtree(target_dir)
            os.makedirs(target_dir, exist_ok=True)

            cmd = []
            custom_extract = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_EXTRACT)
            if custom_extract and os.path.exists(custom_extract):
                cmd = [custom_extract, apk_path, target_dir]
            elif use_flatpak_logic:
                app_id = flatpak_id if flatpak_id else app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.MCPELAUNCHER_FLATPAK_ID)
                base_cmd = ["flatpak", "run", "--command=mcpelauncher-extract", app_id, apk_path, target_dir]
                if app.running_in_flatpak:
                    fs = shutil.which("flatpak-spawn")
                    cmd = [fs, "--host"] + base_cmd if fs else ["mcpelauncher-extract", apk_path, target_dir]
                else: cmd = base_cmd
            else: cmd = ["mcpelauncher-extract", apk_path, target_dir]

            process = subprocess.run(cmd, capture_output=True, text=True)

            def finish():
                progress_dialog.accept()
                if process.returncode == 0:
                    messagebox.showinfo(app, c.UI_SUCCESS_TITLE, c.UI_EXTRACTION_SUCCESS_MSG.format(ver_name=ver_name))
                    if current_root == app.active_path: refresh_version_list(app)
                else:
                    messagebox.showerror(app, c.UI_ERROR_TITLE, c.UI_EXTRACTION_ERROR_MSG.format(err_msg=process.stderr))
            QTimer.singleShot(0, finish)
        except Exception as e:
            QTimer.singleShot(0, lambda: [progress_dialog.accept(), messagebox.showerror(app, c.UI_ERROR_TITLE, str(e))])

    threading.Thread(target=run_extraction).start()

def delete_version_dialog(app):
    version = app.play_tab.get()
    if not version: return

    # Simplified dialog for PySide6
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel
    dialog = QDialog(app)
    dialog.setWindowTitle(c.UI_MANAGE_VERSION_TITLE)
    l = QVBoxLayout(dialog)
    l.addWidget(QLabel(c.UI_MANAGE_VERSION_PROMPT.format(version=version)))

    def do_move():
        try:
            backup_dir = os.path.join(app.home, c.BACKUP_DIR)
            os.makedirs(backup_dir, exist_ok=True)
            shutil.move(os.path.join(app.active_path, c.VERSIONS_DIR, version), backup_dir)
            refresh_version_list(app)
            messagebox.showinfo(app, c.UI_SUCCESS_TITLE, c.UI_VERSION_MOVED_MSG)
            dialog.accept()
        except Exception as e: messagebox.showerror(app, c.UI_ERROR_TITLE, str(e))

    def do_delete():
        if messagebox.askyesno(dialog, c.UI_CONFIRM_DELETE_TITLE, c.UI_CONFIRM_PERMANENT_DELETE.format(version=version)):
            try:
                shutil.rmtree(os.path.join(app.active_path, c.VERSIONS_DIR, version))
                refresh_version_list(app)
                messagebox.showinfo(app, c.UI_SUCCESS_TITLE, c.UI_VERSION_DELETED_MSG)
                dialog.accept()
            except Exception as e: messagebox.showerror(app, c.UI_ERROR_TITLE, str(e))

    btn_move = QPushButton(c.UI_MOVE_TO_BACKUP)
    btn_move.clicked.connect(do_move)
    l.addWidget(btn_move)

    btn_del = QPushButton(c.UI_DELETE_PERMANENTLY)
    btn_del.clicked.connect(do_delete)
    l.addWidget(btn_del)

    dialog.exec()

def disable_shaders(app):
    if not app.active_path: return
    p = os.path.join(app.active_path, c.MINECRAFT_PE_DIR_ALT, c.OPTIONS_FILE)
    try:
        with open(p, "r") as f: content = f.read()
        new = content.replace("graphics_mode:2", "graphics_mode:0").replace("graphics_mode:1", "graphics_mode:0")
        with open(p, "w") as f: f.write(new)
        check_shader_status(app)
        messagebox.showinfo(app, c.UI_SUCCESS_TITLE, c.UI_SHADERS_DISABLED_MSG)
    except Exception as e: messagebox.showerror(app, c.UI_ERROR_TITLE, str(e))

def open_data_folder(app):
    if app.active_path: subprocess.Popen(["xdg-open", app.active_path])

def ensure_profile_system(app):
    if not app.active_path: return
    pdir = os.path.join(app.active_path, c.PROFILES_DIR)
    gdir = os.path.join(app.active_path, "games")
    def_path = os.path.join(pdir, c.UI_PROFILE_DEFAULT)
    if not os.path.exists(app.active_path): os.makedirs(app.active_path, exist_ok=True)
    if not os.path.exists(pdir):
        try:
            os.makedirs(def_path, exist_ok=True)
            if os.path.exists(gdir) and not os.path.islink(gdir):
                shutil.move(gdir, def_path)
                messagebox.showinfo(app, c.UI_INFO_TITLE, c.UI_PROFILE_MIGRATION_NOTICE)
            os.makedirs(os.path.join(def_path, "games"), exist_ok=True)
            if c.CONFIG_KEY_PROFILES not in app.config: app.config[c.CONFIG_KEY_PROFILES] = [c.UI_PROFILE_DEFAULT]
            if c.CONFIG_KEY_CURRENT_PROFILE not in app.config: app.config[c.CONFIG_KEY_CURRENT_PROFILE] = c.UI_PROFILE_DEFAULT
            app.config_manager.save_config()
            apply_profile_symlink(app, app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.UI_PROFILE_DEFAULT))
        except Exception as e: print(f"Profile migration error: {e}")
    else: apply_profile_symlink(app, app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.UI_PROFILE_DEFAULT))

def apply_profile_symlink(app, profile):
    if not app.active_path: return
    link = os.path.join(app.active_path, "games")
    target_rel = os.path.join(c.PROFILES_DIR, profile, "games")
    target_abs = os.path.join(app.active_path, target_rel)

    os.makedirs(target_abs, exist_ok=True)
    try:
        # Resolve existing link/folder
        if os.path.islink(link):
            os.unlink(link)
        elif os.path.exists(link):
            if os.path.isdir(link):
                os.rename(link, link + "_bak_" + str(int(time.time())))
            else:
                os.remove(link)

        # Create symlink (using relative path for portability within the data folder)
        os.symlink(target_rel, link)
    except Exception as e:
        print(f"Symlink error: {e}")
        # Fallback: Move folder if symlinks fail (usually on FAT32/exFAT or restricted environments)
        try:
            if os.path.exists(link) and not os.path.islink(link):
                # If 'games' is a real folder, move it to a backup if not already done
                os.rename(link, link + "_bak_" + str(int(time.time())))

            # Sync by moving/copying (Simplified: we just warn and allow manual intervention
            # for now to avoid huge IO on launch, but we ensure the path exists)
            if not os.path.exists(link):
                os.makedirs(link, exist_ok=True)

            messagebox.showwarning(app, c.UI_SYMLINK_NOT_SUPPORTED_TITLE, c.UI_SYMLINK_NOT_SUPPORTED_MSG)
        except: pass

def get_profiles(app): return app.config.get(c.CONFIG_KEY_PROFILES, [c.UI_PROFILE_DEFAULT])

def create_profile_pyside(app, name):
    if name:
        name = "".join(x for x in name if x.isalnum() or x in " -_").strip()
        if name:
            profiles = get_profiles(app)
            if name not in profiles:
                profiles.append(name)
                app.config_manager.set(c.CONFIG_KEY_PROFILES, profiles)
                os.makedirs(os.path.join(app.active_path, c.PROFILES_DIR, name, "games"), exist_ok=True)
                switch_profile(app, name)
            return name
    return None

def delete_profile(app, name):
    if name == c.UI_PROFILE_DEFAULT or name == app.config.get(c.CONFIG_KEY_CURRENT_PROFILE): return False
    if messagebox.askyesno(app, c.UI_CONFIRM_DELETE_TITLE, c.UI_CONFIRM_DELETE_PROFILE.format(name=name)):
        try:
            p = get_profiles(app)
            if name in p:
                p.remove(name)
                app.config_manager.set(c.CONFIG_KEY_PROFILES, p)
                path = os.path.join(app.active_path, c.PROFILES_DIR, name)
                if os.path.exists(path): shutil.rmtree(path)
                return True
        except Exception as e: messagebox.showerror(app, c.UI_ERROR_TITLE, str(e))
    return False

def rename_profile(app, old, new):
    if old == c.UI_PROFILE_DEFAULT or not new: return False
    new = "".join(x for x in new if x.isalnum() or x in " -_").strip()
    p = get_profiles(app)
    if not new or new in p: return False
    try:
        os.rename(os.path.join(app.active_path, c.PROFILES_DIR, old), os.path.join(app.active_path, c.PROFILES_DIR, new))
        p[p.index(old)] = new
        app.config_manager.set(c.CONFIG_KEY_PROFILES, p)
        if app.config.get(c.CONFIG_KEY_CURRENT_PROFILE) == old:
            app.config_manager.set(c.CONFIG_KEY_CURRENT_PROFILE, new)
            apply_profile_symlink(app, new)
        return True
    except Exception as e: messagebox.showerror(app, c.UI_ERROR_TITLE, str(e))
    return False

def switch_profile(app, name):
    if app.active_path:
        apply_profile_symlink(app, name)
        app.config_manager.set(c.CONFIG_KEY_CURRENT_PROFILE, name)
        detect_installation(app)

def detect_installation(app):
    imode = app.config.get(c.CONFIG_KEY_INSTALL_MODE, c.MODE_INSTALL_LOCAL)
    fid = app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.DEFAULT_FLATPAK_ID)
    std_shared = os.path.join(app.home, c.LOCAL_SHARE_DIR)
    app.is_flatpak = False

    if app.running_in_flatpak and imode in [c.MODE_INSTALL_OWN, c.MODE_INSTALL_SHARED]:
        if os.path.exists(os.path.join(app.our_data_path, c.VERSIONS_DIR)):
            imode, app.active_path = c.MODE_INSTALL_OWN, app.our_data_path
        elif os.path.exists(os.path.join(std_shared, c.VERSIONS_DIR)):
            imode, app.active_path = c.MODE_INSTALL_SHARED, std_shared
        else: imode, app.active_path = c.MODE_INSTALL_OWN, app.our_data_path
        app.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, imode)
    else:
        if imode == c.MODE_INSTALL_OWN: app.active_path = app.our_data_path if app.running_in_flatpak else app.compiled_path
        elif imode == c.MODE_INSTALL_SHARED: app.active_path = std_shared
        elif imode == c.MODE_INSTALL_LOCAL: app.active_path = app.compiled_path
        elif imode == c.MODE_INSTALL_FLATPAK:
            app.is_flatpak = True
            app.active_path = os.path.join(app.home, f"{c.FLATPAK_DATA_DIR}/{fid}/{c.MCPELAUNCHER_DATA_SUBDIR}")

    if app.active_path: ensure_profile_system(app)

    # UI Updates (Signals/Calls)
    status_text = f"● Mode: {imode}"
    if imode == c.MODE_INSTALL_OWN: status_text = c.UI_STATUS_LOCAL_OWN
    elif imode == c.MODE_INSTALL_SHARED: status_text = c.UI_STATUS_LOCAL_SHARED
    elif imode == c.MODE_INSTALL_LOCAL: status_text = c.UI_STATUS_LOCAL
    elif imode == c.MODE_INSTALL_FLATPAK: status_text = c.UI_STATUS_FLATPAK_CUSTOM.format(flatpak_id=fid)

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
    except: pass

def change_mode_ui(app, disp):
    key = next((k for k, v in c.UI_INSTALL_MODES.items() if v == disp), c.MODE_INSTALL_LOCAL)
    app.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, key)
    if key == c.MODE_INSTALL_FLATPAK:
        from PySide6.QtWidgets import QInputDialog
        id, ok = QInputDialog.getText(app, c.UI_CONFIG_FLATPAK_CUSTOM_TITLE, c.UI_FLATPAK_ID_LABEL, text=app.config.get(c.CONFIG_KEY_FLATPAK_ID, ""))
        if ok and id:
            app.config_manager.set(c.CONFIG_KEY_FLATPAK_ID, id)
            detect_installation(app)
    else: detect_installation(app)

def is_running_in_flatpak(): return os.path.exists(c.FLATPAK_INFO_FILE)

def get_flatpak_app_id():
    if not is_running_in_flatpak(): return None
    try:
        with open(c.FLATPAK_INFO_FILE, "r") as f:
            for line in f:
                if line.startswith("app="): return line.split("=")[1].strip()
    except: pass
    return None

def setup_flatpak_environment(app):
    if not app.running_in_flatpak: return
    if app.config.get(c.CONFIG_KEY_MODE) is None: app.config[c.CONFIG_KEY_MODE] = c.MODE_BIN_SYSTEM
    paths = app.config.get(c.CONFIG_KEY_BINARY_PATHS, {})
    changed = False
    m = {c.CONFIG_KEY_CLIENT: "/app/bin/mcpelauncher-client", c.CONFIG_KEY_EXTRACT: "/app/bin/mcpelauncher-extract"}
    for k, v in m.items():
        if not paths.get(k) or (paths.get(k).startswith("/app/bin/") and not os.path.exists(paths.get(k))):
            if os.path.exists(v): paths[k], changed = v, True
    if changed:
        app.config[c.CONFIG_KEY_BINARY_PATHS] = paths
        app.config_manager.save_config()

def check_migration_needed(app):
    if not app.running_in_flatpak: return
    old = os.path.join(app.home, c.LOCAL_SHARE_DIR)
    if app.config.get(c.CONFIG_KEY_MIGRATION_NOTIFIED) or not os.path.exists(old): return
    if os.path.exists(os.path.join(old, c.VERSIONS_DIR)):
        messagebox.showinfo(app, c.UI_DATA_DETECTED_TITLE, c.UI_MIGRATION_PROMPT_MSG)
        app.config[c.CONFIG_KEY_MIGRATION_NOTIFIED] = True
        app.config_manager.save_config()

def resolve_version(path):
    try:
        vt = os.path.join(path, "version_name.txt")
        if os.path.exists(vt):
            with open(vt, "r") as f: return f.read().strip()
        m = os.path.join(path, "assets/packs/vanilla/manifest.json")
        if os.path.exists(m):
            with open(m, "r") as f:
                d = json.load(f)
                v = d.get("header", {}).get("version", [])
                if v: return ".".join(map(str, v))
    except: pass
    return None

def clear_layout(layout):
    if layout is None: return
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            # Important: explicit parent reset can help GC
            widget.setParent(None)
            widget.deleteLater()
        else:
            sub_layout = item.layout()
            if sub_layout:
                clear_layout(sub_layout)

def refresh_version_list(app):
    layout = app.play_tab.version_list_layout
    clear_layout(layout)

    app.version_cards = {}
    if not app.active_path: return
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
        vers = sorted([d for d in os.listdir(vdir) if os.path.isdir(os.path.join(vdir, d))])
        if not vers:
            layout.addWidget(QLabel(c.UI_NO_VERSIONS_INSTALLED))
            return

        for v in vers:
            vpath = os.path.join(vdir, v)
            # Find custom icon
            v_pix = default_pix
            for ext in [".png", ".jpg", ".jpeg", ".webp"]:
                icon_p = os.path.join(vpath, "icon" + ext)
                if os.path.exists(icon_p):
                    zoom = zooms.get(v, 100) / 100.0
                    # Use a cache key for version icons to avoid re-loading/re-scaling
                    v_pix = ImageManager.get_image(icon_p, size=(int(isize * zoom), int(isize * zoom)))
                    if not v_pix: v_pix = default_pix
                    break

            card = QFrame(); card.setObjectName("VersionCard")
            if style == c.STYLE_GRID:
                card.setFixedSize(cwidth, cheight)
                cl = QVBoxLayout(card); cl.setAlignment(Qt.AlignCenter)

                # Container for icon to handle offsets
                icon_container = QFrame()
                icon_container.setFixedSize(isize + 10, isize + 10)
                icon_container.setStyleSheet("background: transparent; border: none;")
                icon_lbl = QLabel(icon_container); icon_lbl.setPixmap(v_pix)
                icon_lbl.setFixedSize(v_pix.size())
                icon_lbl.setStyleSheet("background: transparent;")

                off_x = xs.get(v, 0)
                off_y = ys.get(v, 0)
                # Center + offset
                icon_lbl.move((isize + 10 - v_pix.width()) // 2 + off_x,
                             (isize + 10 - v_pix.height()) // 2 + off_y)

                cl.addWidget(icon_container, 0, Qt.AlignCenter)

                name = v
                if v == "current":
                    rv = resolve_version(os.path.join(vdir, v))
                    if rv: name = f"current ({rv})"
                lbl = QLabel(name); lbl.setStyleSheet(f"font-size: {tsize}px; font-weight: bold; background: transparent;"); lbl.setAlignment(Qt.AlignCenter)
                cl.addWidget(lbl)
            else:
                cl = QHBoxLayout(card)
                # Container for icon to handle offsets
                icon_container = QFrame()
                icon_container.setFixedSize(isize + 10, isize + 10)
                icon_container.setStyleSheet("background: transparent; border: none;")
                icon_lbl = QLabel(icon_container); icon_lbl.setPixmap(v_pix)
                icon_lbl.setFixedSize(v_pix.size())
                icon_lbl.setStyleSheet("background: transparent;")

                off_x = xs.get(v, 0)
                off_y = ys.get(v, 0)
                icon_lbl.move((isize + 10 - v_pix.width()) // 2 + off_x,
                             (isize + 10 - v_pix.height()) // 2 + off_y)

                cl.addWidget(icon_container)

                name = v
                if v == "current":
                    rv = resolve_version(os.path.join(vdir, v))
                    if rv: name = f"current ({rv})"
                lbl = QLabel(name); lbl.setStyleSheet(f"font-size: {tsize}px; font-weight: bold; background: transparent;")
                cl.addWidget(lbl, 1)

            card.mousePressEvent = lambda e, ver=v: select_version(app, ver)
            app.version_cards[v] = card

            if style == c.STYLE_GRID:
                # We handle grid adding outside this loop or with a counter
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
        if last in vers: select_version(app, last)
        elif vers: select_version(app, vers[0])
    except: pass

def select_version(app, version):
    app.play_tab.set(version)
    theme_color = app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
    accent = c.THEME_COLOR_MAP.get(theme_color, "#1f6aa5")

    for v, card in app.version_cards.items():
        if v == version: card.setStyleSheet(f"#VersionCard {{ background-color: {accent}; border-radius: 8px; }}")
        else: card.setStyleSheet("#VersionCard { background-color: #333333; border-radius: 8px; }")

def check_shader_status(app):
    if not app.active_path: return
    op = os.path.join(app.active_path, c.MINECRAFT_PE_DIR_ALT, c.OPTIONS_FILE)
    status = "Unknown"
    if os.path.exists(op):
        try:
            with open(op, "r") as f:
                for line in f:
                    if "graphics_mode:" in line:
                        val = line.strip().split(":")[1]
                        if val == "0": status = "Simple"
                        elif val == "1": status = "Fancy"
                        elif val == "2": status = "Vibrant"
                        break
        except: pass
    if hasattr(app.tools_tab, "lbl_shader_status") and app.tools_tab.lbl_shader_status:
        app.tools_tab.lbl_shader_status.setText(f"Shaders: {status}")

def update_shader_status_label(app): check_shader_status(app)

def launch_game(app):
    version = app.play_tab.get()
    if not version:
        messagebox.showwarning(app, c.UI_INFO_TITLE, c.UI_PLEASE_SELECT_VERSION_MSG)
        return

    vpath = os.path.join(app.active_path, c.VERSIONS_DIR, version)
    mode = app.config.get(c.CONFIG_KEY_MODE, c.UI_DEFAULT_MODE)
    fid = app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.MCPELAUNCHER_FLATPAK_ID)

    cmd = []
    gamemode_enabled = app.config.get(c.CONFIG_KEY_GAMEMODE_ENABLED, False)

    def apply_gamemode(cmd_list):
        if not gamemode_enabled: return cmd_list
        if shutil.which("gamemoderun"): return ["gamemoderun"] + cmd_list
        if app.running_in_flatpak:
            fs = shutil.which("flatpak-spawn")
            if fs: return [fs, "--host", "gamemoderun"] + cmd_list
        return cmd_list

    if mode == c.MODE_BIN_CUSTOM:
        cl = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_CLIENT)
        if not cl or not os.path.exists(cl):
            messagebox.showerror(app, c.UI_ERROR_TITLE, c.UI_CLIENT_PATH_ERROR)
            return
        cmd = apply_gamemode([cl, "-dg", vpath])
    elif mode == c.MODE_BIN_FLATPAK:
        base_cmd = ["flatpak", "run", fid, "-dg", vpath]
        if app.running_in_flatpak:
            fs = shutil.which("flatpak-spawn")
            if fs:
                cmd = [fs, "--host"]
                if gamemode_enabled: cmd += ["gamemoderun"]
                cmd += base_cmd
            else:
                cl = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_CLIENT) or "/app/bin/mcpelauncher-client"
                if os.path.exists(cl): cmd = apply_gamemode([cl, "-dg", vpath])
                else: messagebox.showerror(app, c.UI_ERROR_TITLE, c.UI_CLIENT_PATH_ERROR); return
        else:
            cmd = apply_gamemode(base_cmd)
    elif mode == c.MODE_BIN_SYSTEM:
        cmd = apply_gamemode(["mcpelauncher-client", "-dg", vpath])

    if not cmd: return

    # Env & Launch
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
                else: cmd.append(part)
        except Exception as e: print(f"Error parseando argumentos: {e}")
    else:
        if app.config.get(c.CONFIG_KEY_NVIDIA_PRIME):
            extra_env.update({"__NV_PRIME_RENDER_OFFLOAD": "1", "__GL_VENDOR_LIBRARY_NAME": "nvidia",
                        "__VK_LAYER_NV_optimus": "NVIDIA_only", "DRI_PRIME": "1",
                        "__GL_THREADED_OPTIMIZATIONS": "1", "__GL_GSYNC_ALLOWED": "1", "__GL_VRR_ALLOWED": "1"})
        if app.config.get(c.CONFIG_KEY_ZINK_MODE): extra_env["MESA_LOADER_DRIVER_OVERRIDE"] = "zink"

    # In Flatpak, when using flatpak run, we should use --env to pass variables to the sandbox
    is_flatpak_run = "flatpak" in cmd and "run" in cmd
    fs_path = shutil.which("flatpak-spawn")
    is_flatpak_spawn_host = cmd and fs_path and cmd[0] == fs_path and "--host" in cmd

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
            # For host execution via flatpak-spawn, we use 'env' command to set variables
            idx = cmd.index("--host") + 1
            cmd = cmd[:idx] + ["env"] + [f"{k}={v}" for k, v in extra_env.items()] + cmd[idx:]
        else:
            # Local execution (sandbox or host)
            env.update(extra_env)

    try:
        app.config[c.CONFIG_KEY_LAST_VERSION] = version
        app.config_manager.save_config()

        debug_log = app.config.get(c.CONFIG_KEY_DEBUG_LOG, False)
        if debug_log and not app.running_in_flatpak:
            terms = ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"]
            term = next((t for t in terms if shutil.which(t)), None)
            if term:
                # Use shlex.join for safe command string building if available, else join with spaces
                cmd_str = shlex.join(cmd) if hasattr(shlex, 'join') else " ".join(shlex.quote(x) for x in cmd)
                bcmd = f"{cmd_str}; echo; read -p {shlex.quote(c.UI_TERMINAL_PROMPT_CLOSE)}"
                subprocess.Popen([term, "-e", f'bash -c {shlex.quote(bcmd)}'], env=env, cwd=app.active_path)
            else: subprocess.Popen(cmd, env=env, cwd=app.active_path)
        else:
            subprocess.Popen(cmd, env=env, cwd=app.active_path)

        if app.config.get(c.CONFIG_KEY_CLOSE_ON_LAUNCH): app.close()
    except Exception as e: messagebox.showerror(app, c.UI_ERROR_TITLE, f"Launch error: {e}")

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

def verify_dependencies(app):
    if app.running_in_flatpak:
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel, QHBoxLayout
        d = QDialog(app); d.setWindowTitle(c.UI_FLATPAK_RUNTIME_INFO_TITLE)
        d.resize(650, 500)
        l = QVBoxLayout(d)
        l.addWidget(QLabel("<b>Flatpak Runtimes Requeridos:</b>"))

        t_req = QTextEdit()
        t_req.setPlainText("\n".join(c.FLATPAK_REQUIRED_RUNTIMES))
        l.addWidget(t_req)

        l.addWidget(QLabel("<b>Detección Actual:</b>"))
        t_det = QTextEdit(); t_det.setReadOnly(True)
        try:
            res = subprocess.check_output(["flatpak", "list", "--runtime"], text=True)
            t_det.setPlainText(res)
        except:
            t_det.setPlainText("Error al obtener lista de runtimes del host.")
        l.addWidget(t_det)

        btn_row = QHBoxLayout()
        b_save = QPushButton("Actualizar Lista")
        def update_list():
            new_list = t_req.toPlainText().strip().split('\n')
            c.FLATPAK_REQUIRED_RUNTIMES = [x.strip() for x in new_list if x.strip()]
            messagebox.showinfo(d, "Éxito", "Lista de runtimes actualizada (en memoria).")
        b_save.clicked.connect(update_list)
        btn_row.addWidget(b_save)

        b_close = QPushButton(c.UI_BUTTON_CLOSE); b_close.clicked.connect(d.accept)
        btn_row.addWidget(b_close)
        l.addLayout(btn_row)

        d.exec()
        return

    manager_map = {"APT": (["dpkg", "-s"], "apt install -y"), "DNF": (["rpm", "-q"], "dnf install -y"), "PACMAN": (["pacman", "-Q"], "pacman -S --noconfirm --needed")}
    detected = next((m for m in manager_map if shutil.which(m.lower())), None)
    if not detected: messagebox.showerror(app, c.UI_ERROR_TITLE, c.UI_PKG_MANAGER_NOT_SUPPORTED); return

    check_cmd, install_cmd = manager_map[detected]
    pkgs = sorted(list(set(c.DEPENDENCY_MAP[detected])))
    from src.gui.progress_dialog import ProgressDialog
    app._prog = ProgressDialog(app, c.UI_VERIFYING_TITLE, c.UI_STARTING_MSG)
    app._prog.show()

    def task(): return [p for p in pkgs if subprocess.call(check_cmd + [p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0]
    app._worker = LogicWorker(task)
    app._worker.finished.connect(lambda missing: [app._prog.accept(), show_dep_results(app, missing, install_cmd)])
    app._worker.error.connect(lambda e: [app._prog.accept(), messagebox.showerror(app, c.UI_ERROR_TITLE, e)])
    app._worker.start()

def show_dep_results(app, missing, icmd):
    if not missing: messagebox.showinfo(app, c.UI_RESULT_TITLE, c.UI_DEPENDENCIES_OK); return
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel
    d = QDialog(app); d.setWindowTitle(c.UI_MISSING_DEPS_TITLE); l = QVBoxLayout(d); l.addWidget(QLabel(c.UI_MISSING_DEPS_MSG))
    t = QTextEdit(); t.setPlainText("\n".join(missing)); l.addWidget(t)
    def install():
        cmd = f"pkexec {icmd} {' '.join(missing)}"
        if messagebox.askyesno(d, c.UI_INFO_TITLE, c.UI_INSTALL_PROMPT.format(full_cmd=cmd)):
            term = next((t for t in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"] if shutil.which(t)), None)
            if term: subprocess.Popen([term, "-e", f'bash -c "{cmd}; read -p OK"'])
            d.accept()
    b = QPushButton(c.UI_BUTTON_INSTALL_ROOT); b.clicked.connect(install); l.addWidget(b); d.exec()

def check_requirements_dialog(app):
    from src.gui.progress_dialog import ProgressDialog
    app._prog = ProgressDialog(app, c.UI_ANALYZING_TITLE, c.UI_ANALYZING_HW_MSG)
    app._prog.show()
    def task():
        arch = platform.machine(); cpu, ram = "Unknown", "Unknown"
        cpu_flags = []
        try:
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo") as f:
                    content = f.read()
                    m_model = re.search(r"model name\s*:\s*(.*)", content)
                    if m_model: cpu = m_model.group(1).strip()
                    m_flags = re.search(r"flags\s*:\s*(.*)", content)
                    if m_flags: cpu_flags = m_flags.group(1).split()
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo") as f:
                    m_mem = re.search(r"MemTotal:\s*(\d+)\s*kB", f.read())
                    if m_mem: ram = f"{int(m_mem.group(1))/1024/1024:.2f} GB"
        except: pass

        # OpenGL detection
        gl_ver = "Unknown"
        try:
            cmd = ["sh", "-c", "glxinfo | grep 'OpenGL ES profile version'"]
            output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
            gl_ver = output.strip()
        except:
            if app.running_in_flatpak:
                try:
                    cmd = ["flatpak-spawn", "--host", "sh", "-c", "glxinfo | grep 'OpenGL ES profile version'"]
                    output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
                    gl_ver = output.strip()
                except: pass

        has_sse = all(f in cpu_flags for f in ["ssse3", "sse4_1", "sse4_2", "popcnt"])
        compat_ver = c.UI_INCOMPATIBLE_TEXT
        if arch == "x86_64" and has_sse:
            if "3.1" in gl_ver or "3.2" in gl_ver: compat_ver = "1.13.0 - 1.21.130+"
            elif "3.0" in gl_ver: compat_ver = "1.13.0 - 1.21.124"
            elif "2.0" in gl_ver: compat_ver = "1.13.0 - 1.20.20"

        return (f"--- {c.UI_HW_CPU_INFO} ---\n" +
                f"{c.UI_HW_MODEL}: {cpu}\n" +
                c.UI_HW_ARCH.format(arch=arch) +
                c.UI_HW_CPU_EXT.format(status='✅' if has_sse else '⚠️') +
                f"\n--- {c.UI_HW_RAM_INFO} ---\n" +
                f"{c.UI_HW_RAM_TOTAL}: {ram}\n" +
                f"\n--- {c.UI_HW_GPU_INFO} ---\n" +
                c.UI_HW_OPENGL_ES.format(gl_ver=gl_ver) +
                f"\n----------------------------\n" +
                f"{c.UI_HARDWARE_ANALYSIS_RECOMMENDATION.format(compat_ver=compat_ver)}")
    app._worker = LogicWorker(task)
    app._worker.finished.connect(lambda res: [app._prog.accept(), show_hw_results(app, res)])
    app._worker.error.connect(lambda e: [app._prog.accept(), messagebox.showerror(app, c.UI_ERROR_TITLE, e)])
    app._worker.start()

def rename_version(app, old_name, new_name):
    vdir = os.path.join(app.active_path, c.VERSIONS_DIR)
    old_path = os.path.join(vdir, old_name)
    new_path = os.path.join(vdir, new_name)

    if os.path.exists(new_path):
        messagebox.showerror(app, c.UI_ERROR_TITLE, "A version with that name already exists.")
        return False

    try:
        os.rename(old_path, new_path)
        # Update zooms config if exists
        zooms = app.config.get(c.CONFIG_KEY_VERSION_ICON_ZOOM, {})
        if old_name in zooms:
            zooms[new_name] = zooms.pop(old_name)
            app.config[c.CONFIG_KEY_VERSION_ICON_ZOOM] = zooms
            app.config_manager.save_config()

        if app.config.get(c.CONFIG_KEY_LAST_VERSION) == old_name:
            app.config[c.CONFIG_KEY_LAST_VERSION] = new_name
            app.config_manager.save_config()

        refresh_version_list(app)
        return True
    except Exception as e:
        messagebox.showerror(app, c.UI_ERROR_TITLE, str(e))
        return False

def create_version_shortcut(app, version):
    """Crea un acceso directo .desktop para una versión específica."""
    try:
        # Use absolute path to home to ensure it's created in the correct location
        apps_dir = os.path.join(app.home, c.APPLICATIONS_DIR)
        os.makedirs(apps_dir, exist_ok=True)

        shortcut_path = os.path.join(apps_dir, f"cianova-{version}.desktop")
        vpath = os.path.join(app.active_path, c.VERSIONS_DIR, version)

        # Encontrar el icono si existe
        from src.utils.resource_path import resource_path
        icon_path = resource_path("icon.png") # Default icon
        for ext in [".png", ".jpg", ".jpeg", ".webp"]:
            v_icon = os.path.join(vpath, "icon" + ext)
            if os.path.exists(v_icon):
                icon_path = v_icon
                break

        # Determinar comando de ejecución
        mode = app.config.get(c.CONFIG_KEY_MODE, c.UI_DEFAULT_MODE)
        fid = app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.MCPELAUNCHER_FLATPAK_ID)

        # Comando base (el mismo que en launch_game pero como string para .desktop)
        if mode == c.MODE_BIN_CUSTOM:
            exe = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_CLIENT, "mcpelauncher-client")
            exec_cmd = f"{shlex.quote(exe)} -dg {shlex.quote(vpath)}"
        elif mode == c.MODE_BIN_FLATPAK:
            exec_cmd = f"flatpak run {shlex.quote(fid)} -dg {shlex.quote(vpath)}"
        else: # System
            exec_cmd = f"mcpelauncher-client -dg {shlex.quote(vpath)}"

        # Si estamos en flatpak y no es comando flatpak, necesitamos flatpak-spawn
        if is_running_in_flatpak() and mode != c.MODE_BIN_FLATPAK:
            exec_cmd = f"flatpak-spawn --host {exec_cmd}"

        content = f"""[Desktop Entry]
Type=Application
Name={c.APP_NAME} - {version}
Comment={c.UI_SHORTCUT_COMMENT}
Exec={exec_cmd}
Icon={icon_path}
Terminal=false
Categories=Game;
Keywords=minecraft;mcpe;bedrock;
"""
        with open(shortcut_path, "w") as f:
            f.write(content)

        os.chmod(shortcut_path, 0o755)
        messagebox.showinfo(app, c.UI_SUCCESS_TITLE, c.UI_SHORTCUT_CREATED_MSG.format(name=version))
    except Exception as e:
        messagebox.showerror(app, c.UI_ERROR_TITLE, c.UI_SHORTCUT_CREATION_ERROR_MSG.format(e=e))

def get_compatibility_range(app):
    arch = platform.machine()
    cpu_flags = []
    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo") as f:
                content = f.read()
                m_flags = re.search(r"flags\s*:\s*(.*)", content)
                if m_flags: cpu_flags = m_flags.group(1).split()
    except: pass

    gl_ver = "Unknown"
    try:
        cmd = ["sh", "-c", "glxinfo | grep 'OpenGL ES profile version'"]
        gl_ver = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except:
        if app.running_in_flatpak:
            try:
                cmd = ["flatpak-spawn", "--host", "sh", "-c", "glxinfo | grep 'OpenGL ES profile version'"]
                gl_ver = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
            except: pass

    has_sse = all(f in cpu_flags for f in ["ssse3", "sse4_1", "sse4_2", "popcnt"])
    if arch == "x86_64" and has_sse:
        if "3.1" in gl_ver or "3.2" in gl_ver: return "1.13.0 - 1.21.130+"
        if "3.0" in gl_ver: return "1.13.0 - 1.21.124"
        if "2.0" in gl_ver: return "1.13.0 - 1.20.20"
    return c.UI_INCOMPATIBLE_TEXT

def show_hw_results(app, txt):
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
    d = QDialog(app); d.setWindowTitle(c.UI_HARDWARE_ANALYSIS_TITLE); l = QVBoxLayout(d)
    t = QTextEdit(); t.setPlainText(txt); t.setReadOnly(True); l.addWidget(t)
    b = QPushButton(c.UI_BUTTON_CLOSE); b.clicked.connect(d.accept); l.addWidget(b); d.exec()

def export_screenshots_dialog(app):
    if not app.active_path: return
    p1 = os.path.join(app.active_path, c.SCREENSHOTS_DIR)
    p2 = os.path.join(app.active_path, c.SCREENSHOTS_DIR_ALT)
    p = p1 if os.path.exists(p1) else p2

    if os.path.exists(p):
        subprocess.Popen(["xdg-open", p])
    else:
        com_mojang = os.path.dirname(p1)
        if messagebox.askyesno(app, c.UI_INFO_TITLE, c.UI_OPEN_COMOJANG_FOLDER_PROMPT.format(msg=c.UI_SCREENSHOTS_NOT_FOUND_MSG)):
            if os.path.exists(com_mojang): subprocess.Popen(["xdg-open", com_mojang])
            else: messagebox.showerror(app, c.UI_ERROR_TITLE, "Folder com.mojang not found.")

def get_signin_workdir(app):
    """
    Directorio fijo donde signin-ui-qt y gplaydl escriben/leen playdl.conf.
    Garantiza que ambos binarios compartan la misma sesión y que
    check_google_session pueda encontrarla siempre.
    """
    d = os.path.join(app.home, ".local", "share", "mcpelauncher")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception as e:
        print(f"Could not create signin workdir: {e}")
    return d

def check_google_session(app):
    """
    Verifica si hay una sesión activa de Google Play.
    Busca playdl.conf / token_cache.conf en el workdir fijo y en rutas legacy
    por compatibilidad con sesiones creadas antes del fix.
    """
    workdir = get_signin_workdir(app)
    search_paths = [
        workdir,
        os.getcwd(),
        os.path.join(app.home, ".config", "mcpelauncher"),
        app.active_path if app.active_path else "",
    ]

    seen = set()
    for p in search_paths:
        if not p or p in seen:
            continue
        seen.add(p)
        for fname in ("playdl.conf", "token_cache.conf"):
            full = os.path.join(p, fname)
            try:
                if os.path.exists(full) and os.path.getsize(full) > 0:
                    return True
            except OSError:
                continue
    return False

GOOGLE_AUTH_URL = "https://android.clients.google.com/auth"

def _exchange_access_token(email, access_token):
    """
    Convierte el access_token (oauth_token de un solo uso) entregado por
    playdl-signin-ui-qt en un master Token reutilizable via /auth con
    ACCESS_TOKEN=1. Equivale a playapi::login_api::perform_with_access_token.
    Devuelve dict parseado de la respuesta (al menos 'Token') o None.
    """
    body = {
        "accountType": "HOSTED_OR_GOOGLE",
        "Token": access_token,
        "ACCESS_TOKEN": "1",
        "Email": email or "",
        "add_account": "1",
        "has_permission": "1",
        "service": "ac2dm",
        "source": "android",
        "app": "com.google.android.gsf",
        "device_country": "us",
        "lang": "en_US",
        "sdk_version": "36",
        "client_sig": "38918a453d07199354f8b19af05ec6562ced5788",
        "system_partition": "1",
        "droidguard_results": "null",
    }
    if not email:
        body.pop("Email", None)
        body.pop("add_account", None)

    data = urllib.parse.urlencode(body).encode("utf-8")
    req = urllib.request.Request(
        GOOGLE_AUTH_URL,
        data=data,
        headers={
            "User-Agent": "GoogleAuth/1.4 (desktop DSKTOP); gzip",
            "Content-Type": "application/x-www-form-urlencoded",
            "app": "com.google.android.gsf",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        try:
            text = e.read().decode("utf-8", errors="replace")
        except Exception:
            text = ""
        print(f"OAuth exchange HTTP {e.code}: {text[:300]}")
    except Exception as e:
        print(f"OAuth exchange request failed: {e}")
        return None

    parsed = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            parsed[k.strip()] = v.strip()

    if "Error" in parsed:
        print(f"OAuth exchange error: {parsed.get('Error')} (full: {parsed})")
        return None
    if "Token" not in parsed:
        print(f"OAuth exchange: no Token in response: {parsed}")
        return None
    return parsed

def _parse_signin_output(text):
    """
    Extrae user_email / user_id / user_token de la salida stdout del binario
    playdl-signin-ui-qt. El binario imprime líneas con formato 'clave = valor'.
    Devuelve dict con las claves encontradas (token, id, email).
    """
    fields = {}
    for line in text.splitlines():
        for key in ("user_token", "user_id", "user_email"):
            prefix = key + " = "
            if line.startswith(prefix):
                fields[key] = line[len(prefix):].strip()
    return fields

def _write_playdl_conf(workdir, fields):
    """
    Escribe playdl.conf en workdir con los campos obtenidos.
    Formato compatible con playapi::file_login_cache (clave = valor).
    Devuelve True si se escribió un token no vacío.
    """
    token = fields.get("user_token", "").strip()
    if not token:
        return False
    conf_path = os.path.join(workdir, "playdl.conf")
    lines = []
    for key in ("user_email", "user_id", "user_token"):
        val = fields.get(key, "").strip()
        if val:
            lines.append(f"{key} = {val}")
    try:
        with open(conf_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        os.chmod(conf_path, 0o600)
        return True
    except Exception as e:
        print(f"Error escribiendo playdl.conf: {e}")
        return False

def launch_google_login(app, on_finished=None):
    """
    Lanza playdl-signin-ui-qt como QProcess capturando stdout.
    - Fija cwd al workdir compartido.
    - Al terminar, parsea stdout (user_email/user_id/user_token) y escribe
      playdl.conf en el workdir para que gplaydl lo consuma.
    - Invoca on_finished(exit_code) si se proporciona.
    Devuelve el QProcess (None si falla el lanzamiento).
    """
    bin_path = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_SIGNIN_UI, "playdl-signin-ui-qt")
    workdir = get_signin_workdir(app)
    dbg("launch_google_login: bin=%s workdir=%s flatpak=%s", bin_path, workdir, app.running_in_flatpak)

    proc = QProcess(app)
    proc.setWorkingDirectory(workdir)
    # Stdout separate, stderr ignored (kept on its own channel)
    proc.setProcessChannelMode(QProcess.SeparateChannels)

    if app.running_in_flatpak:
        fs = shutil.which("flatpak-spawn")
        if fs:
            proc.setProgram(fs)
            proc.setArguments(["--host", bin_path])
        else:
            proc.setProgram(bin_path)
    else:
        proc.setProgram(bin_path)

    # Accumulator for stdout chunks
    state = {"stdout": b""}
    def _drain():
        try:
            data = bytes(proc.readAllStandardOutput())
            if data:
                state["stdout"] += data
        except Exception as e:
            print(f"Signin stdout read error: {e}")
    proc.readyReadStandardOutput.connect(_drain)

    def _on_done(code, _status):
        _drain()  # flush any remaining buffered output
        try:
            text = state["stdout"].decode("utf-8", errors="replace")
        except Exception:
            text = ""
        fields = _parse_signin_output(text)
        dbg("signin-ui finished code=%s stdout_len=%d fields=%s",
            code, len(text), {k: (len(v) if v else 0) for k, v in fields.items()})

        # Exchange single-use access_token for a long-lived master Token.
        access_token = fields.get("user_token", "").strip()
        email = fields.get("user_email", "").strip()
        wrote = False
        if access_token:
            dbg("exchanging access_token (len=%d) email=%s", len(access_token), email)
            exchanged = _exchange_access_token(email, access_token)
            dbg("exchange result: %s", "OK" if exchanged else "FAIL")
            if exchanged:
                master_fields = {
                    "user_email": exchanged.get("Email") or email,
                    "user_id": fields.get("user_id", ""),
                    "user_token": exchanged["Token"],
                }
                wrote = _write_playdl_conf(workdir, master_fields)
                dbg("playdl.conf written=%s path=%s", wrote, os.path.join(workdir, "playdl.conf"))
            else:
                try:
                    messagebox.showerror(
                        app, c.UI_ERROR_TITLE,
                        "El token de Google no pudo ser canjeado.\n\n"
                        "Posibles causas:\n"
                        "• La sesión expiró antes del intercambio.\n"
                        "• Google rechazó la autenticación (cuenta restringida o sin Play).\n\n"
                        "Vuelve a iniciar sesión sin contraseña de cifrado y completa el flujo rápido."
                    )
                except Exception:
                    pass

        if not wrote and code == 0 and not access_token:
            try:
                messagebox.showwarning(
                    app, c.UI_ERROR_TITLE,
                    "El proceso de inicio de sesión terminó sin entregar un token. "
                    "Vuelve a intentar y completa el flujo en la ventana de Google."
                )
            except Exception:
                pass

        if on_finished is not None:
            on_finished(code)

    proc.finished.connect(_on_done)

    def _on_error(err):
        try:
            messagebox.showerror(app, c.UI_ERROR_TITLE, f"Error al lanzar login: {err}")
        except Exception:
            print(f"Signin launch error: {err}")
    proc.errorOccurred.connect(_on_error)

    app._signin_proc = proc  # keep reference; QProcess parented to app
    proc.start()
    if not proc.waitForStarted(3000):
        messagebox.showerror(app, c.UI_ERROR_TITLE,
                             f"No se pudo iniciar '{bin_path}'. Verifica la ruta en Ajustes.")
        return None
    return proc

ABI_PROFILES = {
    "x86_64": ["x86_64", "x86"],
    "x86": ["x86"],
    "arm64-v8a": ["arm64-v8a", "armeabi-v7a"],
    "armeabi-v7a": ["armeabi-v7a"],
}

def _detect_country_locale():
    """Detecta country/locale del entorno. Cae a us/en_US si no se puede."""
    import locale as _l
    try:
        loc, _enc = _l.getdefaultlocale()
        if loc and "_" in loc:
            lang, region = loc.split("_", 1)
            region = region.split(".")[0].lower()
            return region, loc
    except Exception:
        pass
    return "us", "en_US"

def _write_device_conf(workdir, arch):
    """
    Genera un device.conf que sobrescribe los campos críticos del device_info
    interno de gplaydl. El default trae un typo ('armeabi-x7a'), solo x86 y
    country=us, locale=en_US → Google rechaza descargas de apps pagadas
    cuando la cuenta es de otra región. Aquí declaramos las ABIs reales y
    derivamos country/locale del entorno del usuario.
    """
    abis = ABI_PROFILES.get(arch, ["x86_64", "x86"])
    array_lines = ",\n".join(f'    "{a}"' for a in abis)
    country, locale_id = _detect_country_locale()
    body = (
        f"config.native_platforms = [\n{array_lines}\n]\n"
        "build.sdk_version = 36\n"
        f"country = {country}\n"
        f"locale = {locale_id}\n"
    )
    path = os.path.join(workdir, "cianova-device.conf")
    try:
        with open(path, "w") as f:
            f.write(body)
    except Exception as e:
        print(f"device.conf write error: {e}")
        return None
    return path

# gplaydl delivery error code → friendly Spanish message.
_DELIVERY_STATUS_MESSAGES = {
    "2": ("Google Play no entregó esta versión específica. Causas comunes:\n"
          "• La versión seleccionada ya no está en el catálogo activo de Google\n"
          "  (Google retira versiones antiguas y solo ofrece las del release plan).\n"
          "• La cuenta no tiene Minecraft Bedrock comprado.\n\n"
          "Soluciones:\n"
          "1. Marca la casilla 'Última versión (auto)' y reintenta.\n"
          "2. Verifica la compra en:\n"
          "   https://play.google.com/store/apps/details?id=com.mojang.minecraftpe\n"
          "3. Usa la pestaña 'APK Local' para instalar un APK que ya tengas."),
    "3": ("La versión seleccionada no está disponible para esta arquitectura.\n\n"
          "Intenta cambiar la arquitectura (x86_64 / x86) o elige otra versión."),
    "5": "App no encontrada en Google Play.",
}

def _map_gplaydl_error(returncode, tail_text):
    """
    Convierte la salida de gplaydl en un mensaje amigable. Detecta los
    errores estructurados emitidos por nuestros parches (status, no-cookie).
    """
    # status=N error path (added by our gplaydl patch)
    m = re.search(r"delivery status=(\d+)", tail_text)
    if m:
        msg = _DELIVERY_STATUS_MESSAGES.get(m.group(1))
        if msg:
            return msg
        return f"Google Play rechazó la descarga (delivery status={m.group(1)})."

    if "no downloadauthcookie" in tail_text:
        return _DELIVERY_STATUS_MESSAGES["2"]
    if "bad token" in tail_text or "BadAuthentication" in tail_text:
        return ("La sesión de Google expiró. Cierra esta ventana, vuelve a "
                "iniciar sesión y reintenta la descarga.")
    if "MissingDroidguard" in tail_text:
        return ("Google requiere DroidGuard para esta cuenta/dispositivo. "
                "Intenta con otra cuenta o desde otra red.")

    return ("Error en la descarga (código {code}).\n\n"
            "Salida de gplaydl:\n{tail}").format(
        code=returncode, tail=tail_text[-600:] or "(vacía)"
    )

def download_and_install_google(app, vcode, vname, arch, target_root, is_target_flatpak, flatpak_id,
                                progress_callback, status_callback, finished_callback):
    """
    Inicia el proceso de descarga con gplaydl y luego extrae usando el método actual.
    """
    dbg("download_and_install_google: vcode=%s vname=%s arch=%s target_root=%s flatpak=%s id=%s",
        vcode, vname, arch, target_root, is_target_flatpak, flatpak_id)
    def run_flow():
        temp_apk = os.path.join(tempfile.gettempdir(), f"minecraft_{vcode}.apk")
        dbg("run_flow: temp_apk=%s", temp_apk)
        try:
            # 1. Download
            QTimer.singleShot(0, lambda: status_callback(c.UI_STATUS_DOWNLOADING))

            bin_path = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_GPLAYDL, "gplaydl")
            signin_cwd = get_signin_workdir(app)

            # Read token + email from playdl.conf written by launch_google_login.
            # gplaydl's checkin.cpp asserts `user.email.length() > 0` after
            # fetch_service_auth_cookie, so we MUST pass -u together with -t.
            token = ""
            user_email = ""
            try:
                with open(os.path.join(signin_cwd, "playdl.conf"), "r") as f:
                    for line in f:
                        if line.startswith("user_token = "):
                            token = line[len("user_token = "):].strip()
                        elif line.startswith("user_email = "):
                            user_email = line[len("user_email = "):].strip()
            except FileNotFoundError:
                pass

            # Generate device.conf with correct ABIs for the selected arch.
            # The internal default in gplaydl has a typo ('armeabi-x7a') and
            # is missing x86_64, which causes Google to refuse delivery.
            dev_conf = _write_device_conf(signin_cwd, arch)

            # Auth flags: -sa saves auth (skips "store the token? [Y/n]" prompt),
            # -tos auto-accepts ToS, -t passes the token explicitly so gplaydl
            # doesn't fall back to interactive login. -d overrides device profile.
            cmd = [bin_path, "-sa", "-tos"]
            if user_email:
                cmd += ["-u", user_email]
            if token:
                cmd += ["-t", token]
            if dev_conf:
                cmd += ["-d", dev_conf]
            cmd += ["-a", "com.mojang.minecraftpe"]
            # vcode==0 / None / "latest" → omit -v so gplaydl uses Google's
            # currently-offered version (most reliable; older vcodes get
            # rejected with status=2 even on owning accounts).
            try:
                vcode_int = int(vcode)
            except (TypeError, ValueError):
                vcode_int = 0
            if vcode_int > 0:
                cmd += ["-v", str(vcode_int)]
            cmd += ["-o", temp_apk]

            if app.running_in_flatpak:
                fs = shutil.which("flatpak-spawn")
                if fs: cmd = [fs, "--host"] + cmd

            dbg("gplaydl cwd=%s", signin_cwd)
            dbg("gplaydl cmd=%s", " ".join(cmd))
            dbg("device.conf=%s exists=%s", dev_conf, os.path.exists(dev_conf) if dev_conf else False)
            dbg("playdl.conf exists=%s token_len=%d email=%s",
                os.path.exists(os.path.join(signin_cwd, "playdl.conf")), len(token), user_email)

            # Keep stderr separate so structured errors don't get drowned in
            # binary protobuf noise from stdout. stdin=DEVNULL avoids hangs.
            # errors='replace' is required: gplaydl prints raw protobuf bytes
            # and gzip-compressed payloads to stdout (debug build), which
            # contain invalid UTF-8 sequences (e.g. 0x8b gzip magic).
            process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       encoding="utf-8", errors="replace",
                                       bufsize=1, cwd=signin_cwd)
            dbg("gplaydl pid=%s", process.pid)

            stdout_tail = []
            stderr_tail = []

            # Drain stderr in a background thread (gplaydl prints structured
            # errors there; reading only stdout would block on a full stderr
            # pipe for large protobuf debug dumps).
            def drain_stderr():
                try:
                    for line in process.stderr:
                        stderr_tail.append(line)
                        if len(stderr_tail) > 40:
                            stderr_tail.pop(0)
                except Exception:
                    pass
            t_err = threading.Thread(target=drain_stderr, daemon=True)
            t_err.start()

            for line in process.stdout:
                stdout_tail.append(line)
                if len(stdout_tail) > 40:
                    stdout_tail.pop(0)
                # Parse progress: "Downloaded 45% [123/270 MiB]"
                match = re.search(r"Downloaded (\d+)%", line)
                if match:
                    p_val = int(match.group(1))
                    QTimer.singleShot(0, lambda p=p_val: progress_callback(p))

            process.wait()
            t_err.join(timeout=2)
            dbg("gplaydl exit=%s temp_apk_exists=%s",
                process.returncode, os.path.exists(temp_apk))
            if stderr_tail:
                dbg("gplaydl stderr tail:\n%s", "".join(stderr_tail).strip())
            if _CIANOVA_DEBUG and stdout_tail:
                dbg("gplaydl stdout last 5 lines:\n%s",
                    "".join(stdout_tail[-5:]).strip())

            if process.returncode != 0 or not os.path.exists(temp_apk):
                combined = "".join(stderr_tail) + "\n" + "".join(stdout_tail)
                err_msg = _map_gplaydl_error(process.returncode, combined)
                dbg("download FAILED → mapped msg:\n%s", err_msg)
                QTimer.singleShot(0, lambda m=err_msg: finished_callback(False, m))
                return

            # 2. Extract. Minecraft Bedrock is delivered as split APKs:
            # <name>.apk (main) + <name>.config.<id>.apk (per-ABI / locale /
            # density / install_pack). mcpelauncher-extract accepts multiple
            # input APKs (`<apk> [<apk>+] <destination>`) and merges them.
            QTimer.singleShot(0, lambda: status_callback(c.UI_STATUS_EXTRACTING))

            target_dir = os.path.join(target_root, c.VERSIONS_DIR, vname)
            if os.path.exists(target_dir): shutil.rmtree(target_dir)
            os.makedirs(target_dir, exist_ok=True)

            # Collect main + every split component sitting next to temp_apk.
            base_no_ext = temp_apk[:-len(".apk")] if temp_apk.endswith(".apk") else temp_apk
            apk_inputs = [temp_apk]
            for split_path in sorted(glob.glob(base_no_ext + ".*.apk")):
                if split_path != temp_apk:
                    apk_inputs.append(split_path)
            dbg("extract inputs (%d): %s",
                len(apk_inputs),
                ", ".join(f"{os.path.basename(p)}({os.path.getsize(p)//1024}K)"
                          for p in apk_inputs if os.path.exists(p)))

            use_flatpak_logic = is_target_flatpak
            extract_cmd = []
            custom_extract = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_EXTRACT)

            if custom_extract and os.path.exists(custom_extract):
                extract_cmd = [custom_extract, *apk_inputs, target_dir]
            elif use_flatpak_logic:
                app_id = flatpak_id if flatpak_id else app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.MCPELAUNCHER_FLATPAK_ID)
                base_cmd = ["flatpak", "run", "--command=mcpelauncher-extract", app_id, *apk_inputs, target_dir]
                if app.running_in_flatpak:
                    fs = shutil.which("flatpak-spawn")
                    extract_cmd = [fs, "--host"] + base_cmd if fs else ["mcpelauncher-extract", *apk_inputs, target_dir]
                else: extract_cmd = base_cmd
            else:
                extract_cmd = ["mcpelauncher-extract", *apk_inputs, target_dir]

            dbg("extract cmd=%s", " ".join(extract_cmd))
            extract_proc = subprocess.run(extract_cmd, capture_output=True, text=True)
            dbg("extract exit=%s stdout_tail=%r stderr_tail=%r",
                extract_proc.returncode,
                extract_proc.stdout[-300:] if extract_proc.stdout else "",
                extract_proc.stderr[-300:] if extract_proc.stderr else "")

            # Cleanup all temp APKs (main + splits)
            for p in apk_inputs:
                try:
                    if os.path.exists(p): os.remove(p)
                except OSError:
                    pass

            # When user picked "Latest (auto)", vname was a placeholder.
            # Read manifest from extracted dir and rename folder to real version.
            final_vname = vname
            if extract_proc.returncode == 0 and vname == "latest":
                real = resolve_version(target_dir)
                if real:
                    new_target = os.path.join(target_root, c.VERSIONS_DIR, real)
                    if not os.path.exists(new_target):
                        try:
                            os.rename(target_dir, new_target)
                            target_dir = new_target
                            final_vname = real
                        except OSError as e:
                            print(f"Rename latest→{real} failed: {e}")

            if extract_proc.returncode == 0:
                if target_root == app.active_path:
                    # Refresh UI in main thread
                    QTimer.singleShot(0, lambda: refresh_version_list(app))
                QTimer.singleShot(0, lambda fn=final_vname: finished_callback(True, c.UI_EXTRACTION_SUCCESS_MSG.format(ver_name=fn)))
            else:
                QTimer.singleShot(0, lambda err=extract_proc.stderr: finished_callback(False, c.UI_EXTRACTION_ERROR_MSG.format(err_msg=err)))

        except Exception as e:
            import traceback as _tb
            tb_text = _tb.format_exc()
            dbg("run_flow EXCEPTION:\n%s", tb_text)
            if os.path.exists(temp_apk):
                try: os.remove(temp_apk)
                except OSError: pass
            err_msg = f"{type(e).__name__}: {e}"
            QTimer.singleShot(0, lambda msg=err_msg: finished_callback(False, msg))

    threading.Thread(target=run_flow, daemon=True).start()
