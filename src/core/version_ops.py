import json
import os
import sys
import shutil
import subprocess
import shlex
import threading
from PySide6.QtCore import QTimer
from src import constants as c
from src.gui import custom_dialogs as messagebox
from src.utils.logger import logger


def get_installed_versions(app):
    """Return a sorted list of installed version folder names."""
    if not app.active_path:
        from src.core.install_ops import detect_installation
        detect_installation(app)
    if not app.active_path:
        return []
    versions_dir = os.path.join(app.active_path, c.VERSIONS_DIR)
    if not os.path.exists(versions_dir):
        logger.debug(f"Versions folder not found in: {app.active_path}")
        return []
    try:
        vers = sorted(
            [d for d in os.listdir(versions_dir) if os.path.isdir(os.path.join(versions_dir, d))],
            reverse=True,
        )
        logger.debug(f"Installed versions found: {len(vers)}")
        return vers
    except Exception as e:
        logger.error(f"Error listing versions: {e}")
        return []


def resolve_version(path):
    """Extract the version string from version_name.txt or manifest.json."""
    try:
        vt = os.path.join(path, "version_name.txt")
        if os.path.exists(vt):
            with open(vt, "r") as f:
                return f.read().strip()
        m = os.path.join(path, "assets/packs/vanilla/manifest.json")
        if os.path.exists(m):
            with open(m, "r") as f:
                d = json.load(f)
                v = d.get("header", {}).get("version", [])
                if v:
                    return ".".join(map(str, v))
    except Exception:
        pass
    return None


def process_apk(app, apk_path, ver_name, target_root=None, is_target_flatpak=None, flatpak_id=None):
    """Extract an APK into a named version directory using the configured extractor."""
    current_root = target_root if target_root else app.active_path
    if not current_root:
        messagebox.showerror(app, c.t("UI_ERROR_TITLE"), c.t("UI_NO_TARGET_PATH_ERROR"))
        return

    target_dir = os.path.join(current_root, c.VERSIONS_DIR, ver_name)
    use_flatpak_logic = is_target_flatpak if is_target_flatpak is not None else app.is_flatpak

    from src.gui.progress_dialog import ProgressDialog
    progress_dialog = ProgressDialog(app, c.t("UI_EXTRACTING_APK_TITLE"), c.t("UI_EXTRACTING_APK_MSG"))
    progress_dialog.show()

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
                    fs = shutil.which("flatpak-spawn")
                    cmd = [fs, "--host"] + base_cmd if fs else ["mcpelauncher-extract", apk_path, target_dir]
                else:
                    cmd = base_cmd
            else:
                cmd = ["mcpelauncher-extract", apk_path, target_dir]

            process = subprocess.run(cmd, capture_output=True, text=True)

            def finish():
                progress_dialog.accept()
                if process.returncode == 0:
                    messagebox.showinfo(app, c.t("UI_SUCCESS_TITLE"), c.t("UI_EXTRACTION_SUCCESS_MSG", ver_name=ver_name))
                    if current_root == app.active_path:
                        from src.core.install_ops import refresh_version_list
                        refresh_version_list(app)
                else:
                    messagebox.showerror(app, c.t("UI_ERROR_TITLE"), c.t("UI_EXTRACTION_ERROR_MSG", err_msg=process.stderr))
            QTimer.singleShot(0, finish)
        except Exception as e:
            QTimer.singleShot(0, lambda: [progress_dialog.accept(), messagebox.showerror(app, c.t("UI_ERROR_TITLE"), str(e))])

    threading.Thread(target=run_extraction).start()


def delete_version_dialog(app):
    """Show a dialog to move or permanently delete the selected version."""
    version = app.play_tab.get()
    if not version:
        return

    from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel
    dialog = QDialog(app)
    dialog.setWindowTitle(c.t("UI_MANAGE_VERSION_TITLE"))
    l = QVBoxLayout(dialog)
    l.addWidget(QLabel(c.t("UI_MANAGE_VERSION_PROMPT", version=version)))

    def do_move():
        try:
            backup_dir = os.path.join(app.home, c.BACKUP_DIR)
            os.makedirs(backup_dir, exist_ok=True)
            shutil.move(os.path.join(app.active_path, c.VERSIONS_DIR, version), backup_dir)
            from src.core.install_ops import refresh_version_list
            refresh_version_list(app)
            messagebox.showinfo(app, c.t("UI_SUCCESS_TITLE"), c.t("UI_VERSION_MOVED_MSG"))
            dialog.accept()
        except Exception as e:
            messagebox.showerror(app, c.t("UI_ERROR_TITLE"), str(e))

    def do_delete():
        if messagebox.askyesno(dialog, c.t("UI_CONFIRM_DELETE_TITLE"), c.t("UI_CONFIRM_PERMANENT_DELETE", version=version)):
            try:
                shutil.rmtree(os.path.join(app.active_path, c.VERSIONS_DIR, version))
                from src.core.install_ops import refresh_version_list
                refresh_version_list(app)
                messagebox.showinfo(app, c.t("UI_SUCCESS_TITLE"), c.t("UI_VERSION_DELETED_MSG"))
                dialog.accept()
            except Exception as e:
                messagebox.showerror(app, c.t("UI_ERROR_TITLE"), str(e))

    btn_move = QPushButton(c.t("UI_MOVE_TO_BACKUP"))
    btn_move.clicked.connect(do_move)
    l.addWidget(btn_move)

    btn_del = QPushButton(c.t("UI_DELETE_PERMANENTLY"))
    btn_del.clicked.connect(do_delete)
    l.addWidget(btn_del)

    dialog.exec()


def rename_version(app, old_name, new_name):
    """Rename a version folder and update related config entries."""
    vdir = os.path.join(app.active_path, c.VERSIONS_DIR)
    old_path = os.path.join(vdir, old_name)
    new_path = os.path.join(vdir, new_name)

    if os.path.exists(new_path):
        messagebox.showerror(app, c.t("UI_ERROR_TITLE"), "A version with that name already exists.")
        return False

    try:
        os.rename(old_path, new_path)
        zooms = app.config.get(c.CONFIG_KEY_VERSION_ICON_ZOOM, {})
        if old_name in zooms:
            zooms[new_name] = zooms.pop(old_name)
            app.config[c.CONFIG_KEY_VERSION_ICON_ZOOM] = zooms
            app.config_manager.save_config()

        if app.config.get(c.CONFIG_KEY_LAST_VERSION) == old_name:
            app.config[c.CONFIG_KEY_LAST_VERSION] = new_name
            app.config_manager.save_config()

        from src.core.install_ops import refresh_version_list
        refresh_version_list(app)
        return True
    except Exception as e:
        messagebox.showerror(app, c.t("UI_ERROR_TITLE"), str(e))
        return False


def create_version_shortcut(app, version):
    """Crea un acceso directo .desktop para una versión específica."""
    try:
        apps_dir = os.path.join(app.home, c.APPLICATIONS_DIR)
        os.makedirs(apps_dir, exist_ok=True)

        shortcut_path = os.path.join(apps_dir, f"cianova-{version}.desktop")
        vpath = os.path.join(app.active_path, c.VERSIONS_DIR, version)

        if app.running_in_flatpak:
            app_id = app.our_flatpak_id if app.our_flatpak_id else c.DEFAULT_FLATPAK_ID
            exec_cmd = f"flatpak run {app_id} --version {shlex.quote(version)}"
        else:
            exe_path = os.path.abspath(sys.argv[0])
            if exe_path.endswith(".py"):
                exec_cmd = f"python3 {shlex.quote(exe_path)} --version {shlex.quote(version)}"
            else:
                exec_cmd = f"{shlex.quote(exe_path)} --version {shlex.quote(version)}"

        from src.utils.resource_path import resource_path
        icon_path = resource_path("icon.png")
        for ext in [".png", ".jpg", ".jpeg", ".webp"]:
            v_icon = os.path.join(vpath, "icon" + ext)
            if os.path.exists(v_icon):
                icon_path = v_icon
                break

        content = f"""[Desktop Entry]
Type=Application
Name={c.APP_NAME} - {version}
Comment={c.t("UI_SHORTCUT_COMMENT")}
Exec={exec_cmd}
Icon={icon_path}
Terminal=false
Categories=Game;
Keywords=minecraft;mcpe;bedrock;
"""
        with open(shortcut_path, "w") as f:
            f.write(content)
        os.chmod(shortcut_path, 0o755)
        logger.info(f"Start menu shortcut created for version {version} at {shortcut_path}")

        if messagebox.askyesno(app, c.t("UI_CONFIRM_TITLE"), c.t("UI_PROMPT_DESKTOP_SHORTCUT")):
            desktop_dir = os.path.join(app.home, "Desktop")
            try:
                xdg_desktop = subprocess.check_output(["xdg-user-dir", "DESKTOP"], text=True).strip()
                if os.path.exists(xdg_desktop):
                    desktop_dir = xdg_desktop
            except Exception:
                pass

            if os.path.exists(desktop_dir):
                desktop_shortcut = os.path.join(desktop_dir, f"cianova-{version}.desktop")
                with open(desktop_shortcut, "w") as f:
                    f.write(content)
                os.chmod(desktop_shortcut, 0o755)
                logger.info(f"Desktop shortcut created at {desktop_shortcut}")

        messagebox.showinfo(app, c.t("UI_SUCCESS_TITLE"), c.t("UI_SHORTCUT_CREATED_MSG", name=version))
    except Exception as e:
        logger.error(f"Error creating shortcut: {e}")
        messagebox.showerror(app, c.t("UI_ERROR_TITLE"), c.t("UI_SHORTCUT_CREATION_ERROR_MSG", e=e))
