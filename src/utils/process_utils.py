"""Shared helpers for subprocess handling and the Flatpak sandbox.

Centralizes patterns that were previously duplicated across the codebase:
detecting the Flatpak sandbox, prefixing host commands with
``flatpak-spawn --host``, opening paths in the file manager and querying
``glxinfo``.
"""
import os
import shutil
import subprocess

from src import constants as c


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
        from src.utils.logger import logger
        logger.warning("Failed to read flatpak app file: %s", e)
    return None


def host_prefix():
    """Return ``["flatpak-spawn", "--host"]`` to run a command on the host.

    Returns ``None`` when ``flatpak-spawn`` is not available, letting callers
    decide on a fallback command.
    """
    fs = shutil.which("flatpak-spawn")
    return [fs, "--host"] if fs else None


def host_command(cmd):
    """Wrap ``cmd`` with the host prefix when ``flatpak-spawn`` is available.

    When ``flatpak-spawn`` is missing the command is returned unchanged.
    """
    prefix = host_prefix()
    return (prefix + list(cmd)) if prefix else list(cmd)


def open_path(path):
    """Open a file or folder in the desktop file manager with multi-tier fallbacks.

    Uses DBus org.freedesktop.FileManager1, native file managers (nautilus, dolphin, etc.),
    gio, and xdg-open to avoid sandbox/portal 'Invalid fd passed' bugs.
    """
    if not path:
        return None
    path_str = os.path.abspath(str(path))
    if not os.path.exists(path_str):
        try:
            if not os.path.splitext(path_str)[1]:
                os.makedirs(path_str, exist_ok=True)
            else:
                parent_dir = os.path.dirname(path_str)
                if parent_dir and os.path.exists(parent_dir):
                    path_str = parent_dir
        except Exception:
            pass

    is_dir = os.path.isdir(path_str)
    prefix = host_prefix() if is_running_in_flatpak() else []
    if prefix is None:
        prefix = []

    # 1. Try DBus org.freedesktop.FileManager1 (Official standard, bypasses portal issues)
    try:
        from PySide6.QtDBus import QDBusInterface, QDBusConnection
        from PySide6.QtCore import QUrl
        bus = QDBusConnection.sessionBus()
        if bus.isConnected():
            iface = QDBusInterface(
                "org.freedesktop.FileManager1",
                "/org/freedesktop/FileManager1",
                "org.freedesktop.FileManager1",
                bus
            )
            if iface.isValid():
                url_str = QUrl.fromLocalFile(path_str).toString()
                method = "ShowFolders" if is_dir else "ShowItems"
                reply = iface.call(method, [url_str], "")
                if reply.type() == reply.MessageType.ReplyMessage:
                    return True
    except Exception:
        pass

    # 2. Try native Linux desktop file managers directly
    for fm in ("nautilus", "dolphin", "nemo", "thunar", "pcmanfm", "caja"):
        if shutil.which(fm):
            try:
                cmd = prefix + [fm]
                if not is_dir and fm in ("nautilus", "dolphin", "nemo"):
                    cmd.append("--select")
                cmd.append(path_str)
                return subprocess.Popen(cmd)
            except Exception:
                pass

    # 3. Try gio open
    if shutil.which("gio"):
        try:
            cmd = prefix + ["gio", "open", path_str]
            return subprocess.Popen(cmd)
        except Exception:
            pass

    # 4. Try xdg-open
    if shutil.which("xdg-open"):
        try:
            cmd = prefix + ["xdg-open", path_str]
            return subprocess.Popen(cmd)
        except Exception:
            pass

    # 5. Fallback to QDesktopServices with proper QUrl
    try:
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        return QDesktopServices.openUrl(QUrl.fromLocalFile(path_str))
    except Exception:
        pass

    return None


def open_folder(path):
    """Open the containing folder or directory in the desktop file manager."""
    if not path:
        return None
    p = os.path.abspath(str(path))
    if os.path.isfile(p):
        p = os.path.dirname(p)
    return open_path(p)


def query_glxinfo(field, running_in_flatpak=False, timeout=None, host_timeout=None):
    """Return the ``glxinfo`` line matching ``field``, or ``"Unknown"``.

    Runs ``glxinfo | grep '<field>'`` locally and, when that fails inside a
    Flatpak sandbox, retries the query on the host through ``flatpak-spawn``.
    """
    grep_cmd = f"glxinfo | grep '{field}'"
    try:
        return subprocess.check_output(
            ["sh", "-c", grep_cmd], text=True,
            stderr=subprocess.DEVNULL, timeout=timeout,
        ).strip()
    except Exception:
        if running_in_flatpak:
            prefix = host_prefix()
            if prefix:
                try:
                    return subprocess.check_output(
                        prefix + ["sh", "-c", grep_cmd], text=True,
                        stderr=subprocess.DEVNULL, timeout=host_timeout,
                    ).strip()
                except Exception as e:
                    from src.utils.logger import logger
                    logger.debug(f"glxinfo via flatpak-spawn failed: {e}")
    return "Unknown"
