import json
import os
from src import constants as c
from src.utils.resource_path import resource_path
from src.utils.logger import logger

_translations = {}
_global_vars = {}


def _process_value(val, global_vars):
    if isinstance(val, str):
        for var_name, var_val in global_vars.items():
            placeholder = "{" + var_name + "}"
            if placeholder in val:
                val = val.replace(placeholder, str(var_val))
        return val
    elif isinstance(val, dict):
        return {k: _process_value(v, global_vars) for k, v in val.items()}
    elif isinstance(val, list):
        return [_process_value(i, global_vars) for i in val]
    return val


def load_language(lang_code):
    """Load translations for the given language code and register the lookup function."""
    lang_file = resource_path(os.path.join("src", "langs", f"{lang_code}.json"))

    if not os.path.exists(lang_file):
        logger.warning(f"Archivo de idioma no encontrado: {lang_file}. Usando valores por defecto.")
        return False

    try:
        with open(lang_file, "r", encoding="utf-8") as f:
            translations = json.load(f)
    except Exception as e:
        logger.error(f"Error cargando idioma {lang_code}: {e}")
        return False

    global_vars = {
        "APP_NAME": getattr(c, "APP_NAME", "CianovaLauncher"),
        "VERSION_LAUNCHER": getattr(c, "VERSION_LAUNCHER", "1.0.0"),
        "DEVELOPERS": getattr(c, "DEVELOPERS", "@PlaGaDev"),
        "UPDATE_NAME": getattr(c, "UPDATE_NAME", "New Update"),
    }

    _translations.clear()
    for key, value in translations.items():
        _translations[key] = _process_value(value, global_vars)

    _global_vars.clear()
    _global_vars.update(global_vars)

    c.t = lambda key, **kwargs: _translate(key, **kwargs)

    return True


def _translate(key, **kwargs):
    if key in _translations:
        val = _translations[key]
    else:
        val = getattr(c, key, f"!{key}!")
        if isinstance(val, str):
            val = _process_value(val, _global_vars)
    if kwargs and isinstance(val, str):
        try:
            val = val.format(**kwargs)
        except KeyError:
            pass
    return val


def get_available_languages():
    """Return a dict mapping language codes to language display names."""
    return {
        "en": "English",
        "es": "Español",
        "fr": "Français",
        "it": "Italiano",
        "pt": "Português",
        "ca": "Català",
        "de": "Deutsch",
    }
