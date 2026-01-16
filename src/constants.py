# ==========================================
# MAPA DE DEPENDENCIAS DEL SISTEMA
# ==========================================
DEPENDENCY_MAP = {
    "APT": [
        "libcurl4", "libssl3", "libx11-6", "libxext6", "libxi6",
        "libxrandr2", "libxcursor1", "libxfixes3", "libxrender1",
        "libasound2", "libpulse0", "libsystemd0", "libgl1", "libegl1",
        "libqt5core5a", "libqt5gui5", "libqt5widgets5", "libqt5network5",
        "libqt5webengine5", "libqt5qml5", "libqt5quick5", "libqt5svg5",
        "zenity", "unzip"
    ],
    "DNF": [
        "libcurl", "openssl-libs", "libX11", "libXext", "libXi",
        "libXrandr", "libXcursor", "libXfixes", "libXrender", "alsa-lib",
        "pulseaudio-libs", "systemd-libs", "mesa-libGL", "mesa-libEGL",
        "qt5-qtbase", "qt5-qtwebengine", "qt5-qtdeclarative", "qt5-qtsvg",
        "qt5-qtquickcontrols2", "zenity", "unzip"
    ],
    "PACMAN": [
        "curl", "openssl", "libx11", "libxext", "libxi", "libxrandr",
        "libxcursor", "libxfixes", "libxrender", "alsa-lib", "pulseaudio",
        "systemd-libs", "mesa", "qt5-base", "qt5-webengine",
        "qt5-declarative", "qt5-svg", "qt5-quickcontrols2", "zenity", "unzip"
    ]
}


# ==========================================
# CONSTANTES GLOBALES Y CONFIGURACIÓN
# ==========================================
import os

# --- Información de la Aplicación ---
APP_NAME = "CianovaLauncherMCPE"
VERSION_LAUNCHER = "2.0e"
CHANGELOG = "Support for Nvidia: CianovaLauncher 2.0e"
CREDITOS = "Dev: @PlaGaDev & Antigravity\nProyecto: CianovaLauncherMCPE"
LEGAL_TEXT = """LICENCIA & TÉRMINOS Y CONDICIONES

Última Actualización: 26 de Diciembre de 2025

---

1. Naturaleza del Proyecto
CianovaLauncher es una herramienta de código abierto desarrollada con fines educativos y de utilidad para la comunidad de Minecraft Bedrock en Linux.

* Desarrollo Asistido por IA: Esta herramienta ha sido desarrollada con la asistencia de Google Antigravity, un agente de Inteligencia Artificial avanzado.
* Base Original: El script original `MCPELauncher Tools ver0.3.sh` es propiedad intelectual del usuario @PlaGaDev, quien lo ha cedido libremente para este proyecto.

2. Atribución y Dependencias
Este "launcher" solo funciona de forma independiente en su apartado visual pero cualquier opción de ejecución, extracción u otro proceso requiere la instalación previa y binarios compilados de:
* MCPELauncher-Manifest: Proyecto base en el que se fundamenta (Creditos a ChristopherHX y MCMrARM).

CianovaLauncher no busca reemplazar, competir ni apropiarse del crédito del proyecto mencionado anteriormente ni ningún otro launcher que cumpla su misma función. Su único propósito es facilitar la gestión de versiones y procesos para los usuarios de dicho manifest sin pretender ser el soporte oficial del proyecto.

El proyecto CCMC Launcher por CrowRei34, en el cual se basaba la versión anterior (v1.0, v1.1 y v1.2) de la herramienta MCPETool (Ahora llamada CianovaLauncher) se considera actualmente como obsoleto/legacy. CianovaLauncher busca ofrecer a los usuarios de la versión anterior una nueva forma para los usuarios que usan o usaban dicha estructura.

CianovaLauncher no proporcionará las APKs que se requieren para la ejecución, el usuario debe conseguirlas por sus propios medios.

3. Uso No Lucrativo
Este proyecto se distribuye bajo la licencia GNU GPL v3.0. Es de código abierto y se entrega con la intención de ser gratuito para siempre. Se agradece a la comunidad no monetizar esta herramienta para mantener el espíritu de colaboración.

4. Exención de Responsabilidad
El software se proporciona "tal cual", sin garantía de ningún tipo. Los desarrolladores (@PlaGaDev, GoogleAntigravity) no se hacen responsables de:
* Pérdida de datos (mundos, capturas, etc.).
* Baneos de cuentas por uso indebido.
* Fallos en el sistema derivados del uso de la herramienta.

Al utilizar CianovaLauncher, aceptas estos términos y condiciones.

---
Hecho con ❤️ y 🤖 para la comunidad Linux.
"""

# --- Rutas y Nombres de Archivos ---
HOME_DIR = os.path.expanduser("~")
FLATPAK_INFO_FILE = "/.flatpak-info"
DEFAULT_FLATPAK_ID = "org.cianova.Launcher"
MCPELAUNCHER_FLATPAK_ID = "com.mcpelauncher.MCPELauncher"

# Rutas de datos (sin modificar la estructura existente)
FLATPAK_DATA_DIR = ".var/app"
MCPELAUNCHER_DATA_SUBDIR = "data/mcpelauncher"
LOCAL_SHARE_DIR = ".local/share/mcpelauncher"

# Nombres de archivos de configuración
CONFIG_FILE_NAME = "cianovalauncher-config.json"
OLD_CONFIG_FILE_NAME = "config.json"

# Nombres de directorios
VERSIONS_DIR = "versions"
WORLDS_DIR = "games/com.mojang/minecraftWorlds"
SCREENSHOTS_DIR = "games/com.mojang/Screenshots"
SCREENSHOTS_DIR_ALT = "games/com.mojang/screenshots"
MINECRAFT_PE_DIR_ALT = "games/com.mojang/minecraftpe"
OPTIONS_FILE = "options.txt"
BACKUP_DIR = "MCPELauncher-OLD"
APPLICATIONS_DIR = ".local/share/applications"
DESKTOP_SHORTCUT_NAME = "cianova-launcher.desktop"


# --- Claves de Configuración ---
CONFIG_KEY_INSTALL_MODE = "install_mode"
CONFIG_KEY_MODE = "mode"
CONFIG_KEY_FLATPAK_ID = "flatpak_app_id"
CONFIG_KEY_BINARY_PATHS = "binary_paths"
CONFIG_KEY_CLIENT = "client"
CONFIG_KEY_EXTRACT = "extract"
CONFIG_KEY_WEBVIEW = "webview"
CONFIG_KEY_ERROR = "error"
CONFIG_KEY_WINDOW_SIZE = "window_size"
CONFIG_KEY_APPEARANCE = "appearance_mode"
CONFIG_KEY_COLOR_THEME = "color_theme"
CONFIG_KEY_CLOSE_ON_LAUNCH = "close_on_launch"
CONFIG_KEY_DEBUG_LOG = "debug_log"
CONFIG_KEY_LAST_VERSION = "last_version"
CONFIG_KEY_FIRST_RUN_FLATPAK = "first_run_flatpak"
CONFIG_KEY_MIGRATION_NOTIFIED = "migration_notified"
CONFIG_KEY_INITIAL_SETUP_COMPLETE = "initial_setup_complete"
CONFIG_KEY_NVIDIA_COMPAT_MODE = "nvidia_compat_mode"


# --- Colores de la Interfaz ---
COLOR_PRIMARY_GREEN = "#2cc96b"
COLOR_PRIMARY_GREEN_HOVER = "#229e54"
COLOR_BLUE_BUTTON = "#1f6aa5"
COLOR_RED_BUTTON = "#e63946"
COLOR_RED_BUTTON_HOVER = "#c92a35"
COLOR_PURPLE_BUTTON = "#8e44ad"
COLOR_PURPLE_BUTTON_HOVER = "#732d91"
COLOR_YELLOW_BUTTON = "#fca311"
COLOR_YELLOW_BUTTON_HOVER = "#d68c0e"
COLOR_GRAY_BUTTON = "#457b9d"
COLOR_GRAY_BUTTON_HOVER = "#36607c"
COLOR_GREEN_BUTTON = "#16a34a"
COLOR_GREEN_BUTTON_HOVER = "#15803d"
COLOR_ORANGE_BUTTON = "orange"
COLOR_ORANGE_BUTTON_HOVER = "darkorange"
COLOR_SELECTED_GREEN = "#1e8449"

# --- Textos de la Interfaz (UI Strings) ---
# General
UI_TITLE_VERSION = f"{APP_NAME} - v{VERSION_LAUNCHER}"
UI_TAB_PLAY = " JUGAR "
UI_TAB_TOOLS = " HERRAMIENTAS "
UI_TAB_SETTINGS = " AJUSTES "
UI_TAB_ABOUT = " ACERCA DE "

# Pestaña Jugar
UI_LABEL_SEARCHING = "● Buscando..."
UI_LABEL_INSTALLATION = "Instalación:"
UI_LABEL_INSTALLED_VERSIONS = "Versiones Instaladas"
UI_CHECKBOX_CLOSE_ON_LAUNCH = "Cerrar al jugar"
UI_CHECKBOX_DEBUG_LOG = "Ver Log (Terminal)"
UI_BUTTON_PLAY_NOW = "JUGAR AHORA"
UI_MODE_VALUES_FLATPAK = ["Local (Propio)", "Local (Compartido)", "Flatpak (Personalizado)"]
UI_MODE_VALUES_NORMAL = ["Local", "Flatpak (Personalizado)"]

# Pestaña Herramientas
UI_SECTION_MANAGEMENT = "Gestión"
UI_BUTTON_INSTALL_APK = "Instalar APK"
UI_BUTTON_MOVE_DELETE_VERSION = "Mover/Borrar Versión"
UI_BUTTON_MIGRATE_DATA = "Migración de Datos"
UI_SECTION_CUSTOMIZATION = "Personalización"
UI_BUTTON_SKIN_PACK_CREATOR = "Creador de Skin Packs"
UI_LABEL_SHADERS_STATUS = "Shaders: ..."
UI_BUTTON_FIX_SHADERS = "Fix Shaders"
UI_SECTION_FILES = "Archivos"
UI_BUTTON_OPEN_DATA_FOLDER = "Abrir Carpeta de Datos"
UI_SECTION_SYSTEM = "Sistema"
UI_BUTTON_VERIFY_DEPS = "Verificar Dependencias"
UI_BUTTON_VERIFY_HW = "Verificar Requisitos (Hardware)"
UI_SECTION_SHORTCUT = "Menú de Inicio"
UI_BUTTON_MANAGE_SHORTCUT = "Gestionar Acceso Directo"
UI_SECTION_EXPORT = "Exportación"
UI_BUTTON_EXPORT_WORLDS = "Exportar Mundos"
UI_BUTTON_OPEN_SCREENSHOTS = "Abrir Capturas"

# Pestaña Ajustes
UI_SECTION_BINARIES = "Rutas de Binarios"
UI_MODES_SETTINGS_NORMAL = ["Sistema (Instalado)", "Local (Junto al script)", "Personalizado", "Flatpak (Personalizado)"]
UI_MODES_SETTINGS_FLATPAK = ["Sistema (Instalado)", "Personalizado", "Flatpak (Personalizado)"]
UI_DEFAULT_MODE = "Sistema (Instalado)"
UI_LABEL_FLATPAK_ID = "ID de App Flatpak:"
UI_BUTTON_SAVE_SETTINGS = "Guardar Configuración"
UI_SECTION_APPEARANCE = "Apariencia"
UI_LABEL_COLOR_THEME = "Tema de Color:"
UI_COLOR_THEMES = ["blue", "green", "dark-blue"]
UI_RESTART_REQUIRED_MSG = "* El cambio de color requiere reiniciar la aplicación."

# NVIDIA Compatibility
UI_NVIDIA_COMPAT_MODE_CHECKBOX = "Activar modo de compatibilidad para Nvidia (experimental, solo para Flatpak)"
UI_NVIDIA_COMPAT_MODE_TOOLTIP = "Activa esta opción si experimentas crasheos o problemas gráficos con una tarjeta Nvidia. Forza el uso de la GPU dedicada con una capa de compatibilidad (Zink)."

# Diálogos y Mensajes
UI_INFO_TITLE = "Info"
UI_ERROR_TITLE = "Error"
UI_SUCCESS_TITLE = "Éxito"
UI_SAVE_SUCCESS_MSG = "Configuración guardada.\nSe aplicarán los cambios al detectar instalación."
UI_RESTART_REQUIRED_TITLE = "Reinicio Requerido"
UI_RESTART_MSG = "El cambio de color se aplicará completamente al reiniciar la aplicación."
UI_MANAGE_SHORTCUT_TITLE = "Gestionar Accesos Directos"
UI_SHORTCUT_ACTIVE_MSG = "✓ Activo en Menú de Inicio"
UI_SHORTCUT_INACTIVE_MSG = "✗ No instalado en Menú"
UI_CONFIRM_DELETE_SHORTCUT_MSG = "¿Deseas eliminar el acceso directo principal?"
UI_SHORTCUT_DELETED_MSG = "Acceso directo principal eliminado."
UI_SHORTCUT_CREATED_MSG = "Acceso directo '{name}' creado."
UI_CONFIRM_DELETE_TITLE = "Confirmar Eliminación"
UI_SHADER_STATUS_SIMPLE = "0 (Simple)"
UI_SHADER_STATUS_FANCY = "1 (Fancy)"
UI_SHADER_STATUS_VIBRANT = "2 (Vibrant - Activo)"
UI_SHADER_STATUS_UNKNOWN = "Desconocido"
UI_SHORTCUT_CREATION_ERROR_MSG = "No se pudo crear: {e}"
UI_BUTTON_DELETE_MAIN = "Eliminar Principal"
UI_BUTTON_CREATE_MAIN = "Crear Principal"
UI_SECTION_VERSION_SHORTCUTS = "Accesos Directos por Versión"
UI_NO_VERSIONS_INSTALLED = "No hay versiones instaladas"
UI_MANAGE_EXISTING_SHORTCUTS = "Gestionar existentes:"
UI_NO_SHORTCUTS_DETECTED = "(Ninguno detectado)"
UI_BUTTON_CLOSE = "Cerrar"
UI_ERROR_MIGRATION_TOOL = "No se pudo abrir la herramienta: {e}"
UI_VERSION_NOT_INSTALLED_ERROR = "La versión '{version}' no está instalada."
UI_NO_TARGET_PATH_ERROR = "No se ha definido una ruta de destino."
UI_EXTRACTING_APK_TITLE = "Extrayendo APK"
UI_EXTRACTING_APK_MSG = "Por favor espera, esto puede tardar unos minutos..."
UI_EXTRACTION_SUCCESS_MSG = "Versión {ver_name} instalada correctamente."
UI_EXTRACTION_ERROR_MSG = "El extractor falló:\n{err_msg}"
UI_CRITICAL_ERROR_MSG = "Fallo crítico: {e}"
UI_MANAGE_VERSION_TITLE = "Gestionar Versión"
UI_MANAGE_VERSION_PROMPT = "¿Qué deseas hacer con la versión '{version}'?"
UI_MOVE_TO_BACKUP = "Mover a Respaldo"
UI_DELETE_PERMANENTLY = "Eliminar"
UI_VERSION_MOVED_MSG = "Versión movida al respaldo."
UI_CONFIRM_PERMANENT_DELETE = "¿Estás seguro de eliminar PERMANENTELMENTE '{version}'?\nEsta acción no se puede deshacer."
UI_VERSION_DELETED_MSG = "Versión eliminada."
UI_SHADERS_DISABLED_MSG = "Shaders desactivados (Modo 0)."
UI_STATUS_LOCAL_OWN = "● Modo: Local (Datos Propios)"
UI_STATUS_LOCAL_SHARED = "● Modo: Local (Compartido .local)"
UI_STATUS_LOCAL = "● Modo: Local (.local)"
UI_STATUS_FLATPAK_CUSTOM = "● Modo: Flatpak ({flatpak_id})"
UI_STATUS_FLATPAK_NO_DATA = "● Flatpak: Datos no encontrados"
UI_STATUS_LOCAL_NO_VERSIONS = "● Local: Sin versiones"
UI_BUTTON_VERIFY_DEPS_FLATPAK = "Verificar Dependencias [Flatpak]"
UI_BUTTON_VERIFY_DEPS_LOCAL = "Verificar Dependencias [Local]"
UI_CONFIG_FLATPAK_CUSTOM_TITLE = "Configurar Flatpak Personalizado"
UI_FLATPAK_ID_LABEL = "ID de Aplicación Flatpak:"
UI_FLATPAK_ID_EXAMPLE = "Ejemplo: org.mcpelauncher.Other"
UI_FLATPAK_ID_REQUIRED_MSG = "Por favor ingresa un ID válido."
UI_BUTTON_USE_ID = "Usar ID"
UI_DATA_DETECTED_TITLE = "Datos Detectados"
UI_MIGRATION_PROMPT_MSG = "Se detectaron datos de una instalación anterior en .local.\nPuedes importarlos desde la pestaña 'Herramientas' > 'Migración de Datos'."
UI_NO_VERSIONS_FOLDER_MSG = "No se encontró la carpeta 'versions'"
UI_ERROR_LISTING_VERSIONS = "Error al listar versiones: {e}"
UI_PLEASE_SELECT_VERSION_MSG = "Por favor selecciona una versión."
UI_CLIENT_PATH_ERROR = "Ruta de Cliente no configurada o inválida."
UI_LOCAL_BINARY_NOT_FOUND = "No se encontró el binario local en: {local_bin}"
UI_SYSTEM_BINARY_NOT_FOUND = "No se encontró mcpelauncher-client en el sistema."
UI_NO_COMPATIBLE_TERMINAL = "No se encontró terminal compatible."
UI_LAUNCH_ERROR = "Fallo al lanzar: {e}"
UI_NO_WORLDS_FOUND = "No se encontraron mundos."
UI_EXPORT_WORLDS_TITLE = "Exportar Mundos"
UI_SELECT_WORLDS_LABEL = "Selecciona Mundos"
UI_SELECT_DEST_FOLDER_TITLE = "Selecciona carpeta de destino"
UI_WORLDS_EXPORTED_SUCCESS = "{count} mundos exportados a {dest_dir}"
UI_BUTTON_SELECT_ALL = "Seleccionar Todo"
UI_BUTTON_EXPORT_SELECTED = "Exportar Seleccionados"
UI_SCREENSHOTS_NOT_FOUND_MSG = "No se encontró la carpeta específica 'Screenshots'."
UI_OPEN_COMOJANG_FOLDER_PROMPT = "{msg}\n\n¿Quieres abrir la carpeta 'com.mojang' para buscarla manualmente?"
UI_CANNOT_OPEN_FOLDER_ERROR = "No se pudo abrir la carpeta: {e}"
UI_FLATPAK_RUNTIME_INFO_TITLE = "Requisitos de Runtime Flatpak"
UI_FLATPAK_RUNTIME_INFO_TEXT = """
El lanzador se ejecuta en Flatpak. Las dependencias son manejadas
por el entorno de ejecución (runtime).

Asegúrate de tener instalados los runtimes necesarios.

Para Usuarios:
- org.kde.Platform//5.15-24.08
- io.qt.qtwebengine.BaseApp//5.15-24.08

Para Desarrolladores:
- org.kde.Sdk//5.15-24.08
"""
UI_DEPENDENCY_CHECK_ERROR = "No se encontró '{list_file}'"
UI_PKG_MANAGER_NOT_SUPPORTED = "Gestor de paquetes no soportado."
UI_DEPENDENCY_LIST_READ_ERROR = "Error leyendo lista: {e}"
UI_MISSING_DEPS_TITLE = "Faltan Dependencias"
UI_MISSING_DEPS_MSG = "❌ Paquetes Faltantes"
UI_INSTALL_PROMPT = "Se intentará ejecutar:\n{full_cmd}\n\n¿Continuar?"
UI_BUTTON_INSTALL_ROOT = "Instalar (Root)"
UI_HARDWARE_ANALYSIS_TITLE = "Verificador de Requisitos"
UI_HARDWARE_ANALYSIS_HEADER = "Análisis de Hardware"
UI_HARDWARE_ANALYSIS_RECOMMENDATION = "VERSIÓN RECOMENDADA MCPE:\n{compat_ver}"
UI_DEPENDENCIES_OK = "✅ Requisitos instalados correctamente."
UI_DEPENDENCIES_FLATPAK_OK = "✅ Flatpak detectado correctamente.\nID: {flatpak_id}"
UI_FLATPAK_APP_NOT_FOUND = "La aplicación Flatpak '{flatpak_id}' no parece estar instalada."
UI_FLATPAK_VERIFICATION_ERROR = "Error verificando Flatpak:\n{e}"
