# ==========================================
# MAPA DE DEPENDENCIAS DEL SISTEMA
# ==========================================
DEPENDENCY_MAP = {
    "APT": [
        "libcurl4", "libssl3", "libx11-6", "libxext6", "libxi6",
        "libxrandr2", "libxcursor1", "libxfixes3", "libxrender1",
        "libasound2", "libpulse0", "libsystemd0", "libgl1", "libegl1",
        "libqt6core6", "libqt6gui6", "libqt6widgets6", "libqt6network6",
        "libqt6webengine6", "libqt6qml6", "libqt6quick6",
        "libqt6quickcontrols2-6", "libqt6svg6",
        "zenity", "unzip"
    ],
    "DNF": [
        "libcurl", "openssl-libs", "libX11", "libXext", "libXi",
        "libXrandr", "libXcursor", "libXfixes", "libXrender", "alsa-lib",
        "pulseaudio-libs", "systemd-libs", "mesa-libGL", "mesa-libEGL",
        "qt6-qtbase", "qt6-qtwebengine", "qt6-qtdeclarative", "qt6-qtsvg",
        "zenity", "unzip"
    ],
    "PACMAN": [
        "curl", "openssl", "libx11", "libxext", "libxi", "libxrandr",
        "libxcursor", "libxfixes", "libxrender", "alsa-lib", "pulseaudio",
        "systemd-libs", "mesa", "qt6-base", "qt6-webengine",
        "qt6-declarative", "qt6-svg", "zenity", "unzip"
    ]
}


# ==========================================
# CONSTANTES GLOBALES Y CONFIGURACIÓN
# ==========================================
import os

# --- Información de la Aplicación ---
APP_NAME = "CianovaLauncher"
VERSION_LAUNCHER = "3.0"
BINARY_VERSION_INFO = "v1.7.4-official"  # Default for Flatpak or if not found
BINARY_VERSION_FALLBACK = "PreCompiled Binaries from mcpelauncher Github"
DEVELOPERS = "@PlaGaDev"
UPDATE_NAME = "The Qt6 Evolution"
CHANGELOG = f"{UPDATE_NAME}: {APP_NAME} {VERSION_LAUNCHER}"
CREDITOS = f"Dev: {DEVELOPERS}\nProyecto: {APP_NAME}"
import re
from src.utils.resource_path import resource_path


def _load_legal_text():
    paths = [
        resource_path("Docs/LICENCE & TERMINOS y CONDICIONES.md"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)),
                     "Docs/LICENCE & TERMINOS y CONDICIONES.md"),
    ]
    for path in paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
                text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
                text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
                return text.strip()
            except Exception:
                pass
    return "(Legal text not available)"

LEGAL_TEXT = _load_legal_text()

# --- Setup Wizard Strings ---
FLATPAK_REQUIRED_RUNTIMES = [
    "org.kde.Platform//6.9",
    "io.qt.qtwebengine.BaseApp//6.9",
    "org.freedesktop.Platform.GL.default",
    "org.freedesktop.Platform.VAAPI.Intel"
]

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
PROFILES_DIR = "profiles"
DISABLED_PACKS_DIR = "disabled_packs"
MODS_DIR = "mods"
WORLDS_DIR = "games/com.mojang/minecraftWorlds"
SCREENSHOTS_DIR = "games/com.mojang/Screenshots"
SCREENSHOTS_DIR_ALT = "games/com.mojang/screenshots"
MINECRAFT_PE_DIR_ALT = "games/com.mojang/minecraftpe"
OPTIONS_FILE = "options.txt"
BACKUP_DIR = "MCPELauncher-OLD"
APPLICATIONS_DIR = ".local/share/applications"
DESKTOP_SHORTCUT_NAME = "cianova-launcher.desktop"


# Client ID — crear app en https://discord.com/developers/applications y pegar el ID.
DISCORD_DEFAULT_CLIENT_ID = "1505628404362248213"

# (MODE_* y STYLE_* se importan desde values.py al final del archivo)


# --- Colores de la Interfaz ---
COLOR_PRIMARY_GREEN = "#2cc96b"
COLOR_PRIMARY_GREEN_HOVER = "#229e54"
COLOR_BLUE_BUTTON = "#1f6aa5"
COLOR_RED_BUTTON = "#ef4444"
COLOR_RED_BUTTON_HOVER = "#dc2626"
COLOR_PURPLE_BUTTON = "#a855f7"
COLOR_PURPLE_BUTTON_HOVER = "#9333ea"
COLOR_YELLOW_BUTTON = "#fca311"
COLOR_YELLOW_BUTTON_HOVER = "#d68c0e"
COLOR_GRAY_BUTTON = "#64748b"
COLOR_GRAY_BUTTON_HOVER = "#475569"
COLOR_GREEN_BUTTON = "#22c55e"
COLOR_GREEN_BUTTON_HOVER = "#16a34a"
COLOR_ORANGE_BUTTON = "#f97316"
COLOR_ORANGE_BUTTON_HOVER = "#ea580c"
COLOR_SELECTED_GREEN = "#15803d"

CORNER_RADIUS = 12
BTN_HEIGHT = 32
SECTION_PADDING = 10
ELEMENT_SPACING = 5

# --- Textos de la Interfaz (UI Strings) ---
# General
THEME_COLOR_MAP = {
    "blue": "#1f6aa5",      # Classic Blue
    "green": "#2cc96b",     # Vibrant Green
    "red": "#ef4444",       # Bright Red
    "orange": "#f97316",    # Bright Orange
    "purple": "#a855f7",    # Bright Purple
    "yellow": "#eab308",    # Bright Yellow
    "dark-blue": "#1e40af", # Deeper Royal Blue
    "gray": "#64748b",      # Slate Gray
    "cyan": "#06b6d4",      # Cyan
    "midnight": "#334155",  # Slate Blue-Grey (Visible Midnight)
    "cherry": "#991b1b",    # Deep Cherry Red
    "ocean": "#0e7490"      # Deep Teal/Ocean
}
VERSION_MANIFEST_URL = "https://raw.githubusercontent.com/minecraft-linux/mcpelauncher-versiondb/master/versions.{arch}.json.min"

# ── Update checker ──
UPDATE_CHECK_URL = "https://plagaplusdev.github.io/CianovaLauncher-mcpelauncher/version.json"
UPDATE_CHECK_INTERVAL = 86400  # 24h between automatic checks
VERSION_WARNINGS_URL = "https://plagaplusdev.github.io/CianovaLauncher-mcpelauncher/version-warnings.json"


# ═══════════════════════════════════════════
#  Re-export from sub-modules
#  (Keep constants as the single namespace)
# ═══════════════════════════════════════════

from .core.values import *
from .core.config_keys import *
from .core.ui_strings import *

# ── Translation lookup (fallback; overridden by language_manager at startup) ──
def _t_fallback(key, **kwargs):
    val = globals().get(key, f"!{key}!")
    if isinstance(val, str):
        try:
            # Expand {VAR_NAME} with own globals (e.g. {VERSION_LAUNCHER})
            val = val.format(**{k: v for k, v in globals().items() if k.isupper()})
        except (KeyError, ValueError):
            pass
        if kwargs:
            try:
                val = val.format(**kwargs)
            except KeyError:
                pass
    return val

t = _t_fallback
