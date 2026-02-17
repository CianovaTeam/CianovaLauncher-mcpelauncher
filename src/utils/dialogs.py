import subprocess
from tkinter import filedialog
import shutil
from src import constants as c

def ask_open_filename_native(parent, title=None, filetypes=None):
    """
    Intenta usar Zenity para un diálogo de archivo nativo, con fallback a Tkinter.
    Refactorizado para usar check_output y evitar cuelgues del sistema.
    """
    if title is None: title = c.UI_OPEN_FILE_TITLE
    if filetypes is None: filetypes = [(c.UI_ALL_FILES_TYPE, "*")]
    if hasattr(parent, 'force_flatpak_ui') and parent.force_flatpak_ui:
        return filedialog.askopenfilename(title=title, filetypes=filetypes)

    if shutil.which("zenity"):
        parent.grab_release()
        try:
            cmd = [
                "zenity",
                "--file-selection",
                f"--title={title}",
            ]
            for name, pattern in filetypes:
                cmd.append(f"--file-filter={name}|{pattern}")

            selected_file = subprocess.check_output(cmd, text=True)
            return selected_file.strip()
        except subprocess.CalledProcessError:
            return ""
        except Exception as e:
            print(f"Error al usar Zenity, usando fallback: {e}")
            # Retornar None puede ser una opción para indicar un error inesperado
            return None
        finally:
            parent.grab_set()

    # Fallback a Tkinter solo si Zenity no está instalado o falla catastróficamente
    return filedialog.askopenfilename(title=title, filetypes=filetypes)

def ask_directory_native(parent, title=None):
    """
    Intenta usar Zenity para un diálogo de directorio nativo, con fallback a Tkinter.
    Refactorizado para usar check_output y evitar cuelgues del sistema.
    """
    if title is None: title = c.UI_SELECT_FOLDER_TITLE
    if hasattr(parent, 'force_flatpak_ui') and parent.force_flatpak_ui:
        return filedialog.askdirectory(title=title)

    if shutil.which("zenity"):
        parent.grab_release()
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
            return None
        finally:
            parent.grab_set()

    # Fallback a Tkinter solo si Zenity no está instalado o falla catastróficamente
    return filedialog.askdirectory(title=title)

def ask_open_filenames_native(parent, title=None, filetypes=None):
    """
    Intenta usar Zenity para un diálogo de selección de múltiples archivos.
    """
    if title is None: title = c.UI_OPEN_FILES_TITLE
    if filetypes is None: filetypes = [(c.UI_ALL_FILES_TYPE, "*")]
    if hasattr(parent, 'force_flatpak_ui') and parent.force_flatpak_ui:
        return filedialog.askopenfilenames(title=title, filetypes=filetypes)

    if shutil.which("zenity"):
        parent.grab_release()
        try:
            cmd = [
                "zenity",
                "--file-selection",
                "--multiple",
                f"--title={title}",
            ]
            for name, pattern in filetypes:
                cmd.append(f"--file-filter={name}|{pattern}")

            selected_files = subprocess.check_output(cmd, text=True)
            # Zenity devuelve los archivos separados por un separador, por defecto '|' o '\n'
            return selected_files.strip().splitlines()
        except subprocess.CalledProcessError:
            return []  # Devolver lista vacía si el usuario cancela
        except Exception as e:
            print(f"Error al usar Zenity, usando fallback: {e}")
        finally:
            parent.grab_set()

    return filedialog.askopenfilenames(title=title, filetypes=filetypes)
