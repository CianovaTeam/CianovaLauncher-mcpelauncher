import copy
import json
import os
import threading
from src import constants as c
from src.utils.logger import logger


class ConfigManager:
    """Manages application configuration with merging, migration, and debounced saving."""

    def __init__(self, config_file=c.CONFIG_FILE_NAME, old_config_file=None):
        """Initialize the manager, ensure the config directory exists, and load settings."""
        self.config_file = config_file
        self.old_config_file = old_config_file
        self._dirty = False
        self._debounce_timer = None
        self._debounce_ms = 400

        # Asegurar que el directorio existe
        config_dir = os.path.dirname(self.config_file)
        if config_dir and not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"Error creando directorio de config: {e}")

        self.default_config = {
            c.CONFIG_KEY_BINARY_PATHS: {
                c.CONFIG_KEY_CLIENT: "",
                c.CONFIG_KEY_EXTRACT: "",
                c.CONFIG_KEY_SIGNIN_UI: "",
                c.CONFIG_KEY_GPLAYDL: "",
                c.CONFIG_KEY_GPLAYVER: "",
                c.CONFIG_KEY_ERROR: "",
                c.CONFIG_KEY_WEBVIEW: "",
                c.CONFIG_KEY_MSA_DAEMON: ""
            },
            c.CONFIG_KEY_MODE: c.MODE_BIN_SYSTEM,
            c.CONFIG_KEY_INSTALL_MODE: c.MODE_INSTALL_LOCAL,
            c.CONFIG_KEY_LANGUAGE: "en",
            c.CONFIG_KEY_FLATPAK_ID: c.DEFAULT_FLATPAK_ID,
            "data_path": os.path.join(c.HOME_DIR, c.LOCAL_SHARE_DIR),
            c.CONFIG_KEY_CLOSE_ON_LAUNCH: True,
            c.CONFIG_KEY_LAUNCH_ACTION: c.LAUNCH_ACTION_CLOSE,
            c.CONFIG_KEY_LAST_VERSION: "",
            c.CONFIG_KEY_WINDOW_SIZE: "700x550",
            c.CONFIG_KEY_ACCEPTED_TERMS: False,
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
            c.CONFIG_KEY_PROFILES: ["default"],
            c.CONFIG_KEY_CURRENT_PROFILE: "default",
            c.CONFIG_KEY_SECTION_OPACITY: 100,
            c.CONFIG_KEY_VERSION: c.VERSION_LAUNCHER, # Initial version
            c.CONFIG_KEY_UI_SCALE: "1.0",
            c.CONFIG_KEY_VERSION_ICON_ZOOM: {},
            c.CONFIG_KEY_VERSION_ICON_X: {},
            c.CONFIG_KEY_VERSION_ICON_Y: {},
            c.CONFIG_KEY_DISCORD_RPC_ENABLED: False,
        }
        self.config = self.load_config()

    def restore_defaults(self):
        """Reset configuration to default values and persist them."""
        self.config = copy.deepcopy(self.default_config)
        self.save_config()

    def _deep_merge(self, defaults, loaded):
        """Mezcla profundamente dos diccionarios para asegurar que las claves anidadas existan"""
        result = copy.deepcopy(defaults)
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _migrate_config(self, config):
        """Migra valores de configuración antiguos o localizados a los nuevos formatos internos"""
        changed = False

        # 1. Migración de modos de ejecución/binarios
        old_to_new_mode = {
            "Sistema (Instalado)": c.MODE_BIN_SYSTEM,
            "Local (Junto al script)": c.MODE_BIN_LOCAL,
            "Personalizado": c.MODE_BIN_CUSTOM,
            "Flatpak (Personalizado)": c.MODE_BIN_FLATPAK,
            "Automático": c.MODE_BIN_SYSTEM,
            "System (Installed)": c.MODE_BIN_SYSTEM,
            "Local (Next to script)": c.MODE_BIN_LOCAL,
            "Custom": c.MODE_BIN_CUSTOM,
            "Flatpak (Custom)": c.MODE_BIN_FLATPAK
        }

        mode = config.get(c.CONFIG_KEY_MODE)
        if mode in old_to_new_mode:
            config[c.CONFIG_KEY_MODE] = old_to_new_mode[mode]
            changed = True

        # 2. Migración de modos de instalación
        old_to_new_install = {
            "Local": c.MODE_INSTALL_LOCAL,
            "Local (Propio)": c.MODE_INSTALL_OWN,
            "Local (Compartido)": c.MODE_INSTALL_SHARED,
            "Flatpak (Personalizado)": c.MODE_INSTALL_FLATPAK,
            "Local (Own Data)": c.MODE_INSTALL_OWN,
            "Local (Shared .local)": c.MODE_INSTALL_SHARED,
            "Flatpak (Custom)": c.MODE_INSTALL_FLATPAK
        }

        install_mode = config.get(c.CONFIG_KEY_INSTALL_MODE)
        if install_mode in old_to_new_install:
            config[c.CONFIG_KEY_INSTALL_MODE] = old_to_new_install[install_mode]
            changed = True

        # 3. Corregir ID de Flatpak antiguo si existe
        if config.get(c.CONFIG_KEY_FLATPAK_ID) == c.MCPELAUNCHER_FLATPAK_ID:
            config[c.CONFIG_KEY_FLATPAK_ID] = c.DEFAULT_FLATPAK_ID
            changed = True

        # 4. Migrar close_on_launch (bool) → launch_action (str)
        if c.CONFIG_KEY_LAUNCH_ACTION not in config:
            old_val = config.get(c.CONFIG_KEY_CLOSE_ON_LAUNCH, True)
            config[c.CONFIG_KEY_LAUNCH_ACTION] = c.LAUNCH_ACTION_CLOSE if old_val else c.LAUNCH_ACTION_NONE
            changed = True

        return changed

    def load_config(self):
        """Load configuration with automatic migration from an old file if present."""
        # Intentar cargar desde nuevo archivo
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    loaded_config = json.load(f)

                # Aplicar valores cargados sobre defaults usando deep merge
                config = self._deep_merge(self.default_config, loaded_config)

                # Aplicar migraciones por si acaso vienen de una v2.1 temprana con strings localizados
                if self._migrate_config(config):
                    logger.info("Configuración actualizada con nuevos estándares de claves internas.")
                    self.config = config
                    self.save_config()

                return config
            except Exception as e:
                logger.error(f"Error cargando config: {e}")

        # Si no existe, intentar migrar desde archivo antiguo
        if self.old_config_file and os.path.exists(self.old_config_file):
            try:
                logger.info(f"Migrando configuración desde {self.old_config_file}...")
                with open(self.old_config_file, "r") as f:
                    old_config = json.load(f)

                # Aplicar valores antiguos sobre defaults usando deep merge
                migrated_config = self._deep_merge(self.default_config, old_config)

                # Aplicar migraciones a claves internas
                self._migrate_config(migrated_config)

                # Guardar en nuevo archivo
                self.config = migrated_config
                self.save_config()
                logger.info(f"Migración completada. Config guardado en: {self.config_file}")

                # Eliminar archivo antiguo si existe
                try:
                    os.remove(self.old_config_file)
                    logger.info(f"Archivo antiguo eliminado: {self.old_config_file}")
                except Exception as e:
                    logger.error(f"No se pudo eliminar el archivo antiguo: {e}")

                return migrated_config
            except Exception as e:
                logger.error(f"Error migrando config: {e}")

        return self.default_config.copy()

    def save_config(self):
        """Persist the current configuration to disk as JSON."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logger.error(f"Error guardando config: {e}")

    def get(self, key, default=None):
        """Return the config value for *key*, or *default* if not found."""
        return self.config.get(key, default)

    def _mark_dirty(self):
        self._dirty = True
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self._debounce_timer = threading.Timer(self._debounce_ms / 1000.0, self._flush)
        self._debounce_timer.daemon = True
        self._debounce_timer.start()

    def flush(self):
        if self._debounce_timer:
            self._debounce_timer.cancel()
            self._debounce_timer = None
        self._flush()

    def _flush(self):
        if self._dirty:
            self._dirty = False
            self.save_config()

    def set(self, key, value):
        """Set a config value and schedule a debounced save."""
        self.config[key] = value
        self._mark_dirty()
