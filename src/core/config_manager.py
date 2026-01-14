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
            c.CONFIG_KEY_INSTALL_MODE: c.UI_MODE_VALUES_NORMAL[0], # "Local" por defecto
            c.CONFIG_KEY_FLATPAK_ID: c.DEFAULT_FLATPAK_ID,
            "data_path": os.path.join(c.HOME_DIR, c.LOCAL_SHARE_DIR),
            c.CONFIG_KEY_CLOSE_ON_LAUNCH: True,
            c.CONFIG_KEY_LAST_VERSION: "",
            c.CONFIG_KEY_WINDOW_SIZE: "700x550",
            "accepted_terms": False,
            c.CONFIG_KEY_APPEARANCE: "Dark",
            c.CONFIG_KEY_COLOR_THEME: "blue",
            c.CONFIG_KEY_INITIAL_SETUP_COMPLETE: False,
        }
        self.config = self.load_config()

    def restore_defaults(self):
        self.config = self.default_config.copy()
        self.save_config()

    def load_config(self):
        """Carga configuración con migración automática desde archivo antiguo"""
        # Intentar cargar desde nuevo archivo
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    return {**self.default_config, **json.load(f)}
            except Exception as e:
                print(f"Error cargando config: {e}")

        # Si no existe, intentar migrar desde archivo antiguo
        if self.old_config_file and os.path.exists(self.old_config_file):
            try:
                print(f"Migrando configuración desde {self.old_config_file}...")
                with open(self.old_config_file, "r") as f:
                    old_config = json.load(f)

                # Aplicar valores antiguos sobre defaults
                migrated_config = {**self.default_config, **old_config}

                # Actualizar valores obsoletos
                if migrated_config.get(c.CONFIG_KEY_MODE) == "Automático":
                    migrated_config[c.CONFIG_KEY_MODE] = c.UI_DEFAULT_MODE
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
