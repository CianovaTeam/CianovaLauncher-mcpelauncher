import json
import os
from src import constants as c
from src.utils.resource_path import resource_path

def load_language(lang_code):
    """
    Carga el archivo de idioma JSON y actualiza las constantes en src.constants.
    """
    # Determinar la ruta del archivo usando resource_path para compatibilidad con PyInstaller
    lang_file = resource_path(os.path.join("src", "langs", f"{lang_code}.json"))

    if not os.path.exists(lang_file):
        print(f"Advertencia: Archivo de idioma no encontrado: {lang_file}. Usando valores por defecto.")
        return False

    try:
        with open(lang_file, "r", encoding="utf-8") as f:
            translations = json.load(f)

        # Definir variables globales que pueden usarse en las traducciones
        global_vars = {
            "APP_NAME": getattr(c, "APP_NAME", "CianovaLauncher"),
            "VERSION_LAUNCHER": getattr(c, "VERSION_LAUNCHER", "1.0.0"),
            "DEVELOPERS": getattr(c, "DEVELOPERS", "@PlaGaDev"),
            "UPDATE_NAME": getattr(c, "UPDATE_NAME", "New Update")
        }

        # Función para procesar reemplazos recursivamente (para diccionarios como UI_BIN_MODES)
        def process_value(val):
            if isinstance(val, str):
                for var_name, var_val in global_vars.items():
                    placeholder = "{" + var_name + "}"
                    if placeholder in val:
                        val = val.replace(placeholder, str(var_val))
                return val
            elif isinstance(val, dict):
                return {k: process_value(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [process_value(i) for i in val]
            return val

        # Actualizar constantes en el módulo src.constants
        for key, value in translations.items():
            processed_value = process_value(value)
            setattr(c, key, processed_value)

        return True
    except Exception as e:
        print(f"Error cargando idioma {lang_code}: {e}")
        return False

def get_available_languages():
    """
    Devuelve un diccionario de códigos de idioma y nombres amigables.
    """
    return {
        "en": "English",
        "es": "Español",
        "fr": "Français",
        "it": "Italiano",
        "pt": "Português",
        "ca": "Català",
        "de": "Deutsch"
    }
