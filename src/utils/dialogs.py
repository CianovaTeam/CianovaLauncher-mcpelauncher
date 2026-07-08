import subprocess
import shutil
from PySide6.QtWidgets import QFileDialog
from src import constants as c


def _qt_file_filter(filetypes):
    if filetypes:
        return ";;".join([f"{name} ({pattern})" for name, pattern in filetypes])
    return f"{c.t("UI_ALL_FILES_TYPE")} (*)"


def ask_open_filename_native(parent, title=None, filetypes=None):
    if title is None: title = c.t("UI_OPEN_FILE_TITLE")
    qt_filter = _qt_file_filter(filetypes)

    if shutil.which("zenity"):
        try:
            cmd = ["zenity", "--file-selection", f"--title={title}"]
            if filetypes:
                for name, pattern in filetypes:
                    cmd.append(f"--file-filter={name}|{pattern}")
            selected = subprocess.check_output(cmd, text=True).strip()
            if selected:
                return selected
        except subprocess.CalledProcessError:
            return ""
        except Exception as e:
            print(f"Zenity error, usando fallback: {e}")

    filename, _ = QFileDialog.getOpenFileName(parent, title, "", qt_filter)
    if not filename:
        filename, _ = QFileDialog.getOpenFileName(parent, title, "", qt_filter, QFileDialog.DontUseNativeDialog)
    return filename


def ask_save_filename_native(parent, title=None, filetypes=None, default_name=None):
    if title is None: title = c.t("UI_SAVE_FILE_TITLE")
    qt_filter = _qt_file_filter(filetypes)

    if shutil.which("zenity"):
        try:
            cmd = ["zenity", "--file-selection", "--save", f"--title={title}"]
            if default_name:
                cmd.append(f"--filename={default_name}")
            if filetypes:
                for name, pattern in filetypes:
                    cmd.append(f"--file-filter={name}|{pattern}")
            selected = subprocess.check_output(cmd, text=True).strip()
            if selected:
                return selected
        except subprocess.CalledProcessError:
            return ""
        except Exception as e:
            print(f"Zenity error, usando fallback: {e}")

    path, _ = QFileDialog.getSaveFileName(parent, title, "", qt_filter)
    if not path:
        path, _ = QFileDialog.getSaveFileName(parent, title, "", qt_filter, QFileDialog.DontUseNativeDialog)
    return path


def ask_directory_native(parent, title=None):
    if title is None: title = c.t("UI_SELECT_FOLDER_TITLE")

    if shutil.which("zenity"):
        try:
            cmd = ["zenity", "--file-selection", "--directory", f"--title={title}"]
            selected = subprocess.check_output(cmd, text=True).strip()
            if selected:
                return selected
        except subprocess.CalledProcessError:
            return ""
        except Exception as e:
            print(f"Zenity error, usando fallback: {e}")

    path = QFileDialog.getExistingDirectory(parent, title)
    if not path:
        path = QFileDialog.getExistingDirectory(parent, title, QFileDialog.DontUseNativeDialog)
    return path


def ask_open_filenames_native(parent, title=None, filetypes=None):
    if title is None: title = c.t("UI_OPEN_FILES_TITLE")
    qt_filter = _qt_file_filter(filetypes)

    if shutil.which("zenity"):
        try:
            cmd = ["zenity", "--file-selection", "--multiple", f"--title={title}"]
            if filetypes:
                for name, pattern in filetypes:
                    cmd.append(f"--file-filter={name}|{pattern}")
            selected = subprocess.check_output(cmd, text=True).strip()
            if selected:
                if "|" in selected:
                    return selected.split("|")
                return selected.splitlines()
        except subprocess.CalledProcessError:
            return []
        except Exception as e:
            print(f"Zenity error, usando fallback: {e}")

    filenames, _ = QFileDialog.getOpenFileNames(parent, title, "", qt_filter)
    if not filenames:
        filenames, _ = QFileDialog.getOpenFileNames(parent, title, "", qt_filter, QFileDialog.DontUseNativeDialog)
    return filenames
