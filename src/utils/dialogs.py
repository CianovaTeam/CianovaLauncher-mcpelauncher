import os
import subprocess
import shutil
from PySide6.QtWidgets import QFileDialog
from src import constants as c


class _ZenityCancelled(Exception):
    """Raised when the user cancels a zenity dialog."""


def _qt_file_filter(filetypes):
    if filetypes:
        return ";;".join([f"{name} ({pattern})" for name, pattern in filetypes])
    return f"{c.t('UI_ALL_FILES_TYPE')} (*)"


def _append_zenity_filters(cmd, filetypes):
    if filetypes:
        for name, pattern in filetypes:
            cmd.append(f"--file-filter={name}|{pattern}")


def _run_zenity(cmd):
    """Run a zenity file-selection command.

    Returns the stripped stdout (possibly empty). Raises ``_ZenityCancelled``
    when the user cancels, and returns ``None`` on any other error so the
    caller can fall back to the Qt dialog.
    """
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except subprocess.CalledProcessError:
        raise _ZenityCancelled
    except Exception as e:
        print(f"Zenity error, usando fallback: {e}")
        return None


def ask_open_filename_native(parent, title=None, filetypes=None, initial_dir=None):
    if title is None: title = c.t("UI_OPEN_FILE_TITLE")
    qt_filter = _qt_file_filter(filetypes)

    if shutil.which("zenity"):
        cmd = ["zenity", "--file-selection", f"--title={title}"]
        if initial_dir:
            dir_path = os.path.expanduser(initial_dir).rstrip('/')
            cmd.append(f"--filename={dir_path}/")
        _append_zenity_filters(cmd, filetypes)
        try:
            selected = _run_zenity(cmd)
        except _ZenityCancelled:
            return ""
        if selected:
            return selected

    start_dir = initial_dir or ""
    filename, _ = QFileDialog.getOpenFileName(parent, title, start_dir, qt_filter)
    if not filename:
        filename, _ = QFileDialog.getOpenFileName(parent, title, start_dir, qt_filter, options=QFileDialog.DontUseNativeDialog)
    return filename


def ask_save_filename_native(parent, title=None, filetypes=None, default_name=None):
    if title is None: title = c.t("UI_SAVE_FILE_TITLE")
    qt_filter = _qt_file_filter(filetypes)

    if shutil.which("zenity"):
        cmd = ["zenity", "--file-selection", "--save", "--confirm-overwrite", f"--title={title}"]
        if default_name:
            cmd.append(f"--filename={os.path.expanduser(default_name)}")
        _append_zenity_filters(cmd, filetypes)
        try:
            selected = _run_zenity(cmd)
        except _ZenityCancelled:
            return ""
        if selected:
            # If user didn't type an extension, append it from default_name or filetypes
            if "." not in os.path.basename(selected):
                if default_name and "." in os.path.basename(default_name):
                    ext = os.path.splitext(default_name)[1]
                    selected += ext
                elif filetypes and filetypes[0][1]:
                    first_pat = filetypes[0][1].split()[0]
                    if first_pat.startswith("*."):
                        selected += first_pat[1:]
            return selected

    start_name = default_name or ""
    path, _ = QFileDialog.getSaveFileName(parent, title, start_name, qt_filter)
    if not path:
        path, _ = QFileDialog.getSaveFileName(parent, title, start_name, qt_filter, options=QFileDialog.DontUseNativeDialog)
    return path


def ask_directory_native(parent, title=None):
    if title is None: title = c.t("UI_SELECT_FOLDER_TITLE")

    if shutil.which("zenity"):
        cmd = ["zenity", "--file-selection", "--directory", f"--title={title}"]
        try:
            selected = _run_zenity(cmd)
        except _ZenityCancelled:
            return ""
        if selected:
            return selected

    path = QFileDialog.getExistingDirectory(parent, title)
    if not path:
        path = QFileDialog.getExistingDirectory(parent, title, options=QFileDialog.DontUseNativeDialog)
    return path


def ask_open_filenames_native(parent, title=None, filetypes=None):
    if title is None: title = c.t("UI_OPEN_FILES_TITLE")
    qt_filter = _qt_file_filter(filetypes)

    if shutil.which("zenity"):
        cmd = ["zenity", "--file-selection", "--multiple", f"--title={title}"]
        _append_zenity_filters(cmd, filetypes)
        try:
            selected = _run_zenity(cmd)
        except _ZenityCancelled:
            return []
        if selected:
            if "|" in selected:
                return selected.split("|")
            return selected.splitlines()

    filenames, _ = QFileDialog.getOpenFileNames(parent, title, "", qt_filter)
    if not filenames:
        filenames, _ = QFileDialog.getOpenFileNames(parent, title, "", qt_filter, options=QFileDialog.DontUseNativeDialog)
    return filenames
