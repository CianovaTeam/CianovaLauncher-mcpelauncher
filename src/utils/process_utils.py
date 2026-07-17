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
    """Open a file or folder in the desktop file manager via ``xdg-open``."""
    return subprocess.Popen(["xdg-open", path])


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
