import json
import os
from src import constants as c

class ConfigManager:
    def __init__(self, config_file=c.CONFIG_FILE_NAME, old_config_file=None):
        self.config_file = config_file
        self.old_config_file = old_config_file

        # Asegurar que el directorio existe
        config_dir = os.path.dirname(self.config_file)
        if config_dir and not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir, exist_ok=True)
            except Exception as e:
                print(f"Error creando directorio de config: {e}")

        self.default_config = {
            c.CONFIG_KEY_BINARY_PATHS: {c.CONFIG_KEY_CLIENT: "", c.CONFIG_KEY_EXTRACT: "", c.CONFIG_KEY_ERROR: "", c.CONFIG_KEY_WEBVIEW: ""},
            c.CONFIG_KEY_MODE: c.UI_DEFAULT_MODE,
            c.CONFIG_KEY_INSTALL_MODE: c.MODE_INSTALL_LOCAL,
            c.CONFIG_KEY_LANGUAGE: "en",
            c.CONFIG_KEY_FLATPAK_ID: c.DEFAULT_FLATPAK_ID,
            "data_path": os.path.join(c.HOME_DIR, c.LOCAL_SHARE_DIR),
            c.CONFIG_KEY_CLOSE_ON_LAUNCH: True,
            c.CONFIG_KEY_LAST_VERSION: "",
            c.CONFIG_KEY_WINDOW_SIZE: "700x550",
            "accepted_terms": False,
            c.CONFIG_KEY_APPEARANCE: "Dark",
            c.CONFIG_KEY_COLOR_THEME: "blue",
            c.CONFIG_KEY_INITIAL_SETUP_COMPLETE: False,
            c.CONFIG_KEY_NVIDIA_PRIME: False,
            c.CONFIG_KEY_ZINK_MODE: False,
            c.CONFIG_KEY_CUSTOM_ENV_ENABLED: False,
            c.CONFIG_KEY_CUSTOM_ENV_VARS: "",
            c.CONFIG_KEY_VERSION_LIST_STYLE: c.STYLE_LIST,
            c.CONFIG_KEY_VERSION_ICON_SIZE: 32,
            c.CONFIG_KEY_VERSION_TITLE_SIZE: 13,
        }
        self.config = self.load_config()

    def restore_defaults(self):
        self.config = self.default_config.copy()
        self.save_config()

    def _deep_merge(self, defaults, loaded):
        """Mezcla profundamente dos diccionarios para asegurar que las claves anidadas existan"""
        result = defaults.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def load_config(self):
        """Carga configuración con migración automática desde archivo antiguo"""
        # Intentar cargar desde nuevo archivo
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    loaded_config = json.load(f)
                    return self._deep_merge(self.default_config, loaded_config)
            except Exception as e:
                print(f"Error cargando config: {e}")

        # Si no existe, intentar migrar desde archivo antiguo
        if self.old_config_file and os.path.exists(self.old_config_file):
            try:
                print(f"Migrando configuración desde {self.old_config_file}...")
                with open(self.old_config_file, "r") as f:
                    old_config = json.load(f)

                # Aplicar valores antiguos sobre defaults usando deep merge
                migrated_config = self._deep_merge(self.default_config, old_config)

                # Actualizar valores obsoletos y migrar a nuevas claves internas
                old_to_new_mode = {
                    "Sistema (Instalado)": c.MODE_BIN_SYSTEM,
                    "Local (Junto al script)": c.MODE_BIN_LOCAL,
                    "Personalizado": c.MODE_BIN_CUSTOM,
                    "Flatpak (Personalizado)": c.MODE_BIN_FLATPAK,
                    "Automático": c.MODE_BIN_SYSTEM
                }
                mode = migrated_config.get(c.CONFIG_KEY_MODE)
                if mode in old_to_new_mode:
                    migrated_config[c.CONFIG_KEY_MODE] = old_to_new_mode[mode]

                old_to_new_install = {
                    "Local": c.MODE_INSTALL_LOCAL,
                    "Local (Propio)": c.MODE_INSTALL_OWN,
                    "Local (Compartido)": c.MODE_INSTALL_SHARED,
                    "Flatpak (Personalizado)": c.MODE_INSTALL_FLATPAK
                }
                install_mode = migrated_config.get(c.CONFIG_KEY_INSTALL_MODE)
                if install_mode in old_to_new_install:
                    migrated_config[c.CONFIG_KEY_INSTALL_MODE] = old_to_new_install[install_mode]

                if (
                    migrated_config.get(c.CONFIG_KEY_FLATPAK_ID)
                    == c.MCPELAUNCHER_FLATPAK_ID
                ):
                    migrated_config[c.CONFIG_KEY_FLATPAK_ID] = c.DEFAULT_FLATPAK_ID

                # Guardar en nuevo archivo
                self.config = migrated_config
                self.save_config()
                print(f"Migración completada. Config guardado en: {self.config_file}")

                # Eliminar archivo antiguo si existe
                try:
                    os.remove(self.old_config_file)
                    print(f"Archivo antiguo eliminado: {self.old_config_file}")
                except Exception as e:
                    print(f"No se pudo eliminar el archivo antiguo: {e}")

                return migrated_config
            except Exception as e:
                print(f"Error migrando config: {e}")

        return self.default_config.copy()

    def save_config(self):
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error guardando config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()
