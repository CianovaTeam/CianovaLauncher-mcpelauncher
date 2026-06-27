import os
import sys
import platform
import shutil
import subprocess
import shlex
import threading
import time
import re
from datetime import datetime
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
        new = re.sub(r"^graphics_mode\s*:\s*[12]$", "graphics_mode:0", content, flags=re.MULTILINE)
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
    except (OSError, UnicodeDecodeError) as e:
        logger.warning("Failed to read flatpak app file: %s", e)
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
        c.CONFIG_KEY_SIGNIN_UI: "/app/bin/playdl-signin-ui-qt",
        c.CONFIG_KEY_GPLAYDL: "/app/bin/gplaydl",
        c.CONFIG_KEY_GPLAYVER: "/app/bin/gplayver",
        c.CONFIG_KEY_MSA_DAEMON: "/app/bin/msa-daemon",
        c.CONFIG_KEY_WEBVIEW: "/app/bin/mcpelauncher-webview",
        c.CONFIG_KEY_ERROR: "/app/bin/mcpelauncher-error",
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


# ── DRM Mod management ──

def check_drm_mod_installed(app):
    """Check if the DRM mod .so exists in the mods directory (nested structure)."""
    return _find_drm_mod_dir(app) is not None


def _find_drm_mod_dir(app):
    """Find the deepest directory containing libmcpelauncher-updates.so.

    Returns the full path to the directory (e.g. .../mods/mcpelauncher-updates/1.26.32.2/x86_64/)
    or None if the mod is not installed.
    """
    if not app.active_path:
        return None
    mods_base = os.path.join(app.active_path, c.MODS_DIR, "mcpelauncher-updates")
    if not os.path.isdir(mods_base):
        return None
    for root, dirs, files in os.walk(mods_base):
        if "libmcpelauncher-updates.so" in files:
            return root
    return None


def get_latest_version_needs_drm(app):
    """Return the name of the latest installed version that needs the DRM mod,
    or None if no such version is installed.

    DRM is needed for Minecraft 1.21.30+ (Pairip Core DRM was introduced then).
    We compare version names as tuples to determine the threshold.
    """
    if not app.active_path:
        return None
    from .version_ops import get_installed_versions, resolve_version
    versions = get_installed_versions(app)
    if not versions:
        return None

    threshold = (1, 21, 30)

    def _version_tuple(v):
        vpath = os.path.join(app.active_path, c.VERSIONS_DIR, v)
        ver_str = resolve_version(vpath)
        if not ver_str:
            return None
        parts = ver_str.split(".")
        try:
            return tuple(int(p) for p in parts[:3])
        except ValueError:
            return None

    for v in sorted(versions, reverse=True):
        vt = _version_tuple(v)
        if vt and vt >= threshold:
            return v
    return None


def _fetch_json(url, app):
    """Fetch a JSON document from a URL using urllib."""
    import json, urllib.request, urllib.error

    req = urllib.request.Request(url, headers={"User-Agent": "CianovaLauncher/3.1"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Error de red: {e.reason}")
    return json.loads(data)


def _fetch_moddb(app):
    """Fetch the mod database from mcpelauncher-moddb."""
    url = "https://github.com/minecraft-linux/mcpelauncher-moddb/raw/main/moddb.json"
    return _fetch_json(url, app)


def _download_zip(url, dest_path, app):
    """Download a ZIP file and extract it to dest_path."""
    import zipfile
    import io
    import urllib.request, urllib.error
    from src.gui.progress_dialog import ProgressDialog

    dialog = ProgressDialog(app, c.t("UI_DOWNLOADING_TITLE"),
                            f"{c.t('UI_DOWNLOADING_MSG')}\n{url}")
    dialog.show()

    req = urllib.request.Request(url, headers={"User-Agent": "CianovaLauncher/3.1"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Error de red: {e.reason}")
    finally:
        dialog.close()

    if not data:
        raise RuntimeError(c.t("UI_DOWNLOAD_EMPTY"))

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(dest_path)


def _resolve_version_code(app, version_name):
    """Read the version code from a game version's manifest."""
    vpath = os.path.join(app.active_path, c.VERSIONS_DIR, version_name)
    from .version_ops import resolve_version
    ver_str = resolve_version(vpath)
    if not ver_str:
        return None
    return ver_str


def install_drm_mod(app):
    """One-click: descarga el mod DRM desde los repos oficiales y lo instala."""
    import platform as _platform

    if not app.active_path:
        messagebox.showerror(app, c.t("UI_ERROR_TITLE"), c.t("UI_DRM_NO_MODS_FOLDER"))
        return

    # Detectar arquitectura
    machine = _platform.machine()
    if machine in ("x86_64", "amd64"):
        arch = "x86_64"
    elif machine in ("aarch64", "arm64"):
        arch = "arm64-v8a"
    elif machine in ("i386", "i686", "x86"):
        arch = "x86"
    elif machine.startswith("arm"):
        arch = "armeabi-v7a"
    else:
        messagebox.showerror(app, c.t("UI_ERROR_TITLE"),
                             f"Arquitectura no soportada: {machine}")
        return

    # Buscar la versión instalada más reciente para hacer match con moddb
    from .version_ops import get_installed_versions
    installed_versions = get_installed_versions(app)
    latest_installed = installed_versions[0] if installed_versions else None
    if latest_installed:
        logger.info(f"Buscando mod DRM para la versión {latest_installed} (arch={arch})")

    try:
        # 1. Fetch moddb
        logger.info("Obteniendo lista de mods desde mcpelauncher-moddb...")
        moddb = _fetch_moddb(app)

        # 2. Find mcpelauncher-updates entry
        updates = None
        for entry in moddb:
            if entry.get("name") == "mcpelauncher-updates":
                updates = entry
                break

        if not updates:
            raise RuntimeError("mcpelauncher-updates no encontrado en el mod database")

        # 3. Find the matching version entry
        download_url = None
        mod_version = None
        for ver_entry in updates.get("versions", []):
            for extra in ver_entry.get("extraVersions", []):
                if arch in extra.get("codes", {}):
                    if latest_installed and extra.get("version_name", "").startswith(latest_installed):
                        download_url = ver_entry.get("assets", {}).get(arch)
                        mod_version = ver_entry.get("version")
                        break
            if download_url:
                break

        # 4. Fallback: tomar la última versión del mod (sin matchear contra una versión instalada)
        if not download_url and updates.get("versions"):
            fallback_ver = updates["versions"][0]
            download_url = fallback_ver.get("assets", {}).get(arch)
            mod_version = fallback_ver.get("version")
            if download_url:
                logger.info(f"No se encontró match, usando última versión del mod: {mod_version}")

        if not download_url:
            raise RuntimeError(
                f"No se encontró URL de descarga para la arquitectura {arch} "
                f"en mcpelauncher-moddb"
            )

        logger.info(f"Descargando mod desde: {download_url}")

        # 4. Download and extract
        mod_ver = mod_version or "latest"
        dest_dir = os.path.join(app.active_path, c.MODS_DIR, "mcpelauncher-updates", mod_ver, arch)
        os.makedirs(dest_dir, exist_ok=True)

        # Si el mod ya está instalado, preguntar si reinstalar
        if os.path.isfile(os.path.join(dest_dir, "libmcpelauncher-updates.so")):
            if not messagebox.askyesno(app, c.t("UI_CONFIRM_TITLE"),
                                       f"El mod mcpelauncher-updates {mod_ver} ya está instalado.\n¿Reinstalar?"):
                return

        _download_zip(download_url, dest_dir, app)

        # Verificar que se extrajo correctamente
        so_path = os.path.join(dest_dir, "libmcpelauncher-updates.so")
        if not os.path.isfile(so_path):
            raise RuntimeError(f"El ZIP descargado no contenía libmcpelauncher-updates.so")

        os.chmod(so_path, 0o755)
        # Dar permisos a los parches también
        patches_dir = os.path.join(dest_dir, "patches")
        if os.path.isdir(patches_dir):
            for root, dirs, files in os.walk(patches_dir):
                for f in files:
                    if f.endswith(".so"):
                        os.chmod(os.path.join(root, f), 0o755)

        _ensure_drm_token(app)

        messagebox.showinfo(app, c.t("UI_SUCCESS_TITLE"),
                           f"Mod DRM instalado correctamente:\n{so_path}")
        logger.info(f"Mod DRM instalado en {so_path}")

    except Exception as e:
        logger.error(f"Error instalando mod DRM: {e}")
        messagebox.showerror(app, c.t("UI_ERROR_TITLE"),
                            c.t("UI_DRM_INSTALL_ERROR_MSG", error=str(e)))


def open_mods_folder(app):
    """Open the mods directory in the file manager."""
    if not app.active_path:
        messagebox.showerror(app, c.t("UI_ERROR_TITLE"), c.t("UI_DRM_NO_MODS_FOLDER"))
        return
    mods_dir = os.path.join(app.active_path, c.MODS_DIR)
    if not os.path.isdir(mods_dir):
        os.makedirs(mods_dir, exist_ok=True)
    subprocess.Popen(["xdg-open", mods_dir])


# ── Game launcher ──

def _ensure_drm_token(app):
    """Create the DRM bypass token file if it doesn't exist.

    The mod mcpelauncher-updates checks for
    /data/data/com.mojang.minecraftpe/mcpelauncher-updates-oss.pass (redirected
    to ~/.local/share/mcpelauncher/) on startup.  If the content matches the
    hardcoded placeholder token, the mod skips the entire Google Play validation
    flow (credential helper request + HTTP callback hijacking), which avoids a
    Signal 11 crash in std::mutex::lock() inside the mod's libHttpClient hook.
    """
    token_path = os.path.join(app.active_path, "mcpelauncher-updates-oss.pass")
    if os.path.isfile(token_path):
        return
    token_content = "PLACE_HOLDERDFDFEFEFS"
    try:
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, "w") as f:
            f.write(token_content)
        logger.info(f"Created DRM bypass token: {token_path}")
    except OSError as e:
        logger.warning(f"Failed to create DRM token: {e}")


def _ensure_credential_helper(app):
    """Create a fake mcpelauncher-ui-qt script for the DRM mod's credential flow.

    When mcpelauncher-updates requests Google credentials, the client forks and
    execs ``mcpelauncher-ui-qt --request-google-credentials --mod <path>``.
    This script intercepts that call, reads the already‑stored ``playdl.conf``
    and prints ``CRED=email:token`` on stderr, which is the format
    ``requestGoogleCredentials`` in the core expects.
    """
    mode = app.config.get(c.CONFIG_KEY_MODE, c.t("UI_DEFAULT_MODE"))
    cl = ""
    if mode == c.MODE_BIN_CUSTOM:
        cl = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_CLIENT, "")
    elif mode == c.MODE_BIN_SYSTEM:
        cl = shutil.which("mcpelauncher-client") or ""
    elif mode == c.MODE_BIN_FLATPAK:
        if not app.running_in_flatpak:
            return
        cl = (app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_CLIENT, "")
              or "/app/bin/mcpelauncher-client")
    if not cl or not os.path.isfile(cl):
        return
    target = os.path.join(os.path.dirname(cl), "mcpelauncher-ui-qt")
    if os.path.isfile(target):
        return
    script = """#!/usr/bin/env bash
# Generated by CianovaLauncher
# vim: set ft=sh:
set -euo pipefail
MOD_PATH=""
while [[ $# -gt 0 ]]; do
    case "$1" in --mod) MOD_PATH="$2"; shift 2 ;; *) shift ;; esac
done
if [ -n "$MOD_PATH" ]; then
    d="${MOD_PATH}"; for _ in 1 2 3 4 5; do d="$(dirname "$d")"; done
    DATA_DIR="$d"
else
    DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/mcpelauncher"
fi
CONF="$DATA_DIR/playdl.conf"
if [ ! -f "$CONF" ]; then exit 1; fi
EMAIL=""; TOKEN=""
while IFS=" = " read -r KEY VAL; do
    [ "$KEY" = "user_email" ] && EMAIL="$VAL"
    [ "$KEY" = "user_token" ] && TOKEN="$VAL"
done < "$CONF"
if [ -z "$EMAIL" ] || [ -z "$TOKEN" ]; then exit 1; fi
echo "CRED=$EMAIL:$TOKEN" >&2
exit 0
"""
    try:
        with open(target, "w") as f:
            f.write(script)
        os.chmod(target, 0o755)
        logger.info(f"Created credential helper: {target}")
    except OSError as e:
        logger.warning(f"Failed to create credential helper: {e}")


def _ensure_mc_libraries(app):
    """Ensure libsqliteX.so is available at the path findDataFile expects.

    mcpelauncher-client busca lib/<arch>/libsqliteX.so via PathHelper::findDataFile().
    No está en el APK; se distribuye aparte (libs_mc/). Copiamos al data home si falta.
    """
    import platform as _platform
    machine = _platform.machine()
    arch_map = {
        "x86_64": "x86_64", "amd64": "x86_64",
        "aarch64": "arm64-v8a", "arm64": "arm64-v8a",
        "i386": "x86", "i686": "x86", "x86": "x86",
    }
    arch = arch_map.get(machine, "x86_64")
    dest_dir = os.path.join(app.active_path, "lib", arch)
    dest_path = os.path.join(dest_dir, "libsqliteX.so")
    needed = ["libsqliteX.so", "libmcpelauncher_mod.so"]

    if all(os.path.isfile(os.path.join(dest_dir, lib)) for lib in needed):
        return  # ya están todos

    # Buscar el .so en distintas fuentes
    candidates = []
    # 1) Junto al binario mcpelauncher-client: <client_dir>/../libs_mc/lib/<arch>/
    mode = app.config.get(c.CONFIG_KEY_MODE, c.t("UI_DEFAULT_MODE"))
    if mode == c.MODE_BIN_CUSTOM:
        cl = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_CLIENT, "")
        if cl:
            candidates.append(os.path.join(os.path.dirname(cl), "..", "libs_mc", "lib", arch))
    elif mode == c.MODE_BIN_SYSTEM:
        cl = shutil.which("mcpelauncher-client")
        if cl:
            candidates.append(os.path.join(os.path.dirname(cl), "..", "libs_mc", "lib", arch))
    # 2) Bundled en CianovaLauncher mismo (libs_mc/ en la raíz del proyecto)
    launcher_dir = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
    candidates.append(os.path.join(launcher_dir, "libs_mc", "lib", arch))
    # 3) En el directorio flatpak
    candidates.append(os.path.join("/app", "libs_mc", "lib", arch))

    for lib_name in needed:
        dest = os.path.join(dest_dir, lib_name)
        if os.path.isfile(dest):
            continue
        for src_dir in candidates:
            src = os.path.normpath(os.path.join(src_dir, lib_name))
            if os.path.isfile(src):
                try:
                    os.makedirs(dest_dir, exist_ok=True)
                    shutil.copy2(src, dest)
                    os.chmod(dest, 0o644)
                    logger.info(f"Copied {lib_name} from {src} to {dest}")
                    break
                except OSError as e:
                    logger.warning(f"Failed to copy {lib_name}: {e}")
        else:
            logger.warning(f"{lib_name} not found in any expected location")


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

    # Add DRM mod directory if installed (mod is loaded via -m flag by mcpelauncher-client)
    mod_dir = _find_drm_mod_dir(app)
    if mod_dir:
        logger.info(f"DRM mod found at {mod_dir}, adding -m flag")
        cmd.extend(["-m", mod_dir])

    # Ensure libsqliteX.so is available (needed by Minecraft >= 1.21.130)
    _ensure_mc_libraries(app)
    # Ensure DRM bypass token exists (avoids Signal 11 crash in mod)
    _ensure_drm_token(app)
    # Ensure the credential helper script exists for the DRM mod
    _ensure_credential_helper(app)

    env = os.environ.copy()
    if app.running_in_flatpak:
        # Clear LD_LIBRARY_PATH so child processes (mcpelauncher-client,
        # mcpelauncher-webview) resolve ALL libraries — including Qt6 —
        # exclusively from the KDE runtime via ld.so.cache. The PyInstaller
        # bundle at /app/lib/cianova/_internal bundles an older Qt6 that
        # conflicts with the runtime's 6.10.3 private ABI symbols.
        env.pop("LD_LIBRARY_PATH", None)
        # Ensure QML import paths are set for mcpelauncher-webview (inherits
        # env via QProcess from mcpelauncher-client). The QtWebEngine QML
        # module lives at /app/lib/qml/QtWebEngine/ from the base extension.
        env.setdefault("QML_IMPORT_PATH", "/app/lib/qml:/usr/lib/qml")
        env.setdefault("QML2_IMPORT_PATH", "/app/lib/qml:/usr/lib/qml")
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
            game_fh = logger.open_game_output("a")
            if game_fh:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                game_fh.write(f"\n{'='*20} MCPELAUNCHER LOG ({ts}) {'='*20}\n")
                game_fh.write(f"Command: {' '.join(cmd)}\n")
                for k, v in extra_env.items():
                    game_fh.write(f"  {k}={v}\n")
                game_fh.write("-" * 50 + "\n")
                game_fh.flush()
            try:
                app._game_process = subprocess.Popen(
                    cmd, env=env, cwd=app.active_path,
                    stdout=game_fh, stderr=subprocess.STDOUT
                )
            except (OSError, PermissionError) as e:
                if game_fh:
                    game_fh.write(f"[launcher] Popen failed: {e}, falling back to execve\n")
                    game_fh.close()
                app._game_process = None
                logger.warning(f"subprocess.Popen failed ({e}), trying os.execve...")
                os.execve(cmd[0], cmd, env)

        action = app.config.get(c.CONFIG_KEY_LAUNCH_ACTION, c.LAUNCH_ACTION_CLOSE)
        if action == c.LAUNCH_ACTION_CLOSE:
            logger.info("Closing launcher as requested on launch.")
            app.close()
        elif action == c.LAUNCH_ACTION_HIDE:
            logger.info("Hiding launcher to system tray on launch.")
            app.hide_to_tray()
        elif action == c.LAUNCH_ACTION_NONE:
            logger.info("Launching without closing launcher.")
            if hasattr(app, 'on_game_launched'):
                app.on_game_launched()
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
