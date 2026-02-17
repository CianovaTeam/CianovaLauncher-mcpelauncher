import json
import os
from src import constants as c

def load_language(lang_code):
    """
    Carga el archivo de idioma JSON y actualiza las constantes en src.constants.
    """
    # Determinar la ruta del archivo
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lang_file = os.path.join(base_dir, "langs", f"{lang_code}.json")

    if not os.path.exists(lang_file):
        print(f"Advertencia: Archivo de idioma no encontrado: {lang_file}. Usando valores por defecto.")
        return False

    try:
        with open(lang_file, "r", encoding="utf-8") as f:
            translations = json.load(f)

        # Actualizar constantes en el módulo src.constants
        for key, value in translations.items():
            if hasattr(c, key):
                setattr(c, key, value)
            else:
                # Opcional: Permitir nuevas claves que no estén en constants.py
                setattr(c, key, value)

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
        "es": "Español"
    }
