import subprocess
import shutil
from PySide6.QtWidgets import QFileDialog
from src import constants as c

def ask_open_filename_native(parent, title=None, filetypes=None):
    """
    Intenta usar Zenity para un diálogo de archivo nativo, con fallback a PySide6.
    """
    if title is None: title = c.t("UI_OPEN_FILE_TITLE")
    # Convert filetypes to QFileDialog format
    # Tkinter format: [("Name", "*.ext")]
    # PySide6 format: "Name (*.ext);;Other (*.other)"
    qt_file_filter = ""
    if filetypes:
        qt_file_filter = ";;".join([f"{name} ({pattern})" for name, pattern in filetypes])
    else:
        qt_file_filter = f"{c.t("UI_ALL_FILES_TYPE")} (*)"

    if shutil.which("zenity"):
        try:
            cmd = [
                "zenity",
                "--file-selection",
                f"--title={title}",
            ]
            if filetypes:
                for name, pattern in filetypes:
                    cmd.append(f"--file-filter={name}|{pattern}")

            selected_file = subprocess.check_output(cmd, text=True)
            return selected_file.strip()
        except subprocess.CalledProcessError:
            return ""
        except Exception as e:
            print(f"Error al usar Zenity, usando fallback: {e}")

    # Fallback a PySide6
    filename, _ = QFileDialog.getOpenFileName(parent, title, "", qt_file_filter)
    return filename

def ask_directory_native(parent, title=None):
    """
    Intenta usar Zenity para un diálogo de directorio nativo, con fallback a PySide6.
    """
    if title is None: title = c.t("UI_SELECT_FOLDER_TITLE")

    if shutil.which("zenity"):
        try:
            cmd = [
                "zenity",
                "--file-selection",
                "--directory",
                f"--title={title}",
            ]
            selected_dir = subprocess.check_output(cmd, text=True)
            return selected_dir.strip()
        except subprocess.CalledProcessError:
            return ""
        except Exception as e:
            print(f"Error al usar Zenity, usando fallback: {e}")

    # Fallback a PySide6
    return QFileDialog.getExistingDirectory(parent, title)

def ask_open_filenames_native(parent, title=None, filetypes=None):
    """
    Intenta usar Zenity para un diálogo de selección de múltiples archivos.
    """
    if title is None: title = c.t("UI_OPEN_FILES_TITLE")
    qt_file_filter = ""
    if filetypes:
        qt_file_filter = ";;".join([f"{name} ({pattern})" for name, pattern in filetypes])
    else:
        qt_file_filter = f"{c.t("UI_ALL_FILES_TYPE")} (*)"

    if shutil.which("zenity"):
        try:
            cmd = [
                "zenity",
                "--file-selection",
                "--multiple",
                f"--title={title}",
            ]
            if filetypes:
                for name, pattern in filetypes:
                    cmd.append(f"--file-filter={name}|{pattern}")

            selected_files = subprocess.check_output(cmd, text=True)
            # Zenity devuelve los archivos separados por un separador, por defecto '|' o '\n'
            # Usualmente usa '|' si no se especifica --separator
            if "|" in selected_files:
                return selected_files.strip().split("|")
            return selected_files.strip().splitlines()
        except subprocess.CalledProcessError:
            return []
        except Exception as e:
            print(f"Error al usar Zenity, usando fallback: {e}")

    # Fallback a PySide6
    filenames, _ = QFileDialog.getOpenFileNames(parent, title, "", qt_file_filter)
    return filenames
