# ==========================================
#  Valores por defecto de la interfaz (fallback)
#  Las traducciones se cargan desde los JSON en langs/
#  vía c.t("UI_*") — estos son el español por defecto
# ==========================================
from .values import (
    MODE_INSTALL_LOCAL, MODE_INSTALL_OWN, MODE_INSTALL_SHARED, MODE_INSTALL_FLATPAK,
    MODE_BIN_SYSTEM, MODE_BIN_LOCAL, MODE_BIN_CUSTOM, MODE_BIN_FLATPAK,
    STYLE_LIST, STYLE_GRID, STYLE_COLUMNS,
)

UI_SETUP_WIZARD_TITLE = "Asistente de Configuración Inicial"
UI_SETUP_WELCOME_TITLE = "Bienvenidos a CianovaLauncher v3.0"
UI_SETUP_WELCOME_SUB = "Gracias por elegir esta herramienta para gestionar tu experiencia en Minecraft Bedrock."
UI_SETUP_LANG_TITLE = "Selecciona tu Idioma"
UI_SETUP_APPEARANCE_TITLE = "Personaliza tu Estilo"
UI_SETUP_LEGAL_TITLE = "Aviso Legal y Términos"
UI_SETUP_LEGAL_CHECK = "He leído y acepto la licencia y los términos de uso"
UI_SETUP_MIGRATION_TITLE = "¿Deseas migrar tus datos?"
UI_SETUP_MIGRATION_SUB = "Si utilizabas MCPETool u otro launcher diferente, puedes traer tus mundos y versiones de forma sencilla."
UI_SETUP_FINISH_TITLE = "Primeros Pasos y Agradecimientos"
UI_SETUP_FINISH_SUB = """¡Muchas gracias por elegir CianovaLauncher v3.0!

Este proyecto ha sido desarrollado con dedicación para ofrecerte la mejor experiencia en Linux. Aquí tienes un pequeño resumen de lo que puedes hacer:

🎮 **Pestaña Jugar:** Aquí lanzas tus versiones y gestionas tus **Perfiles Independientes**. Cada perfil guarda sus propios mundos y configuraciones.
🛠️ **Herramientas:** Instala APKs, descarga desde Google Play, gestiona tus **Texturas, Resource Packs y Behavior Packs** o migra datos de otros launchers.
⚙️ **Ajustes:** Personaliza el launcher a tu gusto. Puedes cambiar el **Fondo de pantalla**, añadir una **Marca de agua**, ajustar la transparencia y optimizar el rendimiento con Nvidia y Zink.

¡Esperamos que disfrutes de tu aventura en Minecraft!"""
UI_BUTTON_NEXT = "Siguiente"
UI_BUTTON_BACK = "Anterior"
UI_BUTTON_FINISH = "Empezar ahora"
UI_BUTTON_SKIP = "Omitir"
UI_SETUP_THEME_PREVIEW = "Vista previa del estilo:"
UI_SETUP_STEP = "Paso {current} de {total}"
UI_SETUP_RESTART_NOTE = "* El modo claro/oscuro puede requerir reiniciar para aplicarse totalmente."
UI_BUTTON_OPEN_MIGRATION = "Abrir Herramienta de Migración"
UI_SETUP_CHANGELOG_TITLE = "Historial de Cambios"
UI_SETUP_INSTALL_TITLE = "Instalación Inicial"
UI_SETUP_INSTALL_SUB = "Puedes descargar Minecraft ahora o hacerlo más tarde desde la pestaña Herramientas."

# --- Diálogos de Versión ---
UI_WELCOME_NEW_VERSION_TITLE = "¡Bienvenido a la versión {ver}!"
UI_DOWNGRADE_WARNING_TITLE = "Advertencia de Versión"
UI_DOWNGRADE_WARNING_MSG = "Parece que has usado una versión más reciente ({old}) anteriormente. Se recomienda actualizar a la última versión para evitar conflictos en la configuración."


# --- Configuración Flatpak ---
UI_TITLE_VERSION = "{APP_NAME} - v{VERSION_LAUNCHER}"
UI_TAB_PLAY = " JUGAR "
UI_TAB_TOOLS = " HERRAMIENTAS "
UI_TAB_SETTINGS = " AJUSTES "
UI_TAB_ABOUT = " ACERCA DE "

# Pestaña Jugar
UI_LABEL_SEARCHING = "● Buscando..."
UI_LABEL_INSTALLATION = "Instalación:"
UI_LABEL_INSTALLED_VERSIONS = "Versiones Instaladas"
UI_CHECKBOX_CLOSE_ON_LAUNCH = "Cerrar al jugar"
UI_CHECKBOX_GAMEMODE = "Activar GameMode"
UI_CHECKBOX_DEBUG_LOG = "Ver Log (Terminal)"
UI_BUTTON_PLAY_NOW = "JUGAR AHORA"

# Mapeo de Modos de Instalación (Display)
UI_INSTALL_MODES = {
    MODE_INSTALL_LOCAL: "Local",
    MODE_INSTALL_OWN: "Local (Propio)",
    MODE_INSTALL_SHARED: "Local (Compartido)",
    MODE_INSTALL_FLATPAK: "Flatpak (Personalizado)"
}

# Pestaña Herramientas
UI_SECTION_MANAGEMENT = "Gestión"
UI_BUTTON_INSTALL_APK = "Instalar Versión"
UI_BUTTON_MOVE_DELETE_VERSION = "Gestor de Versiones"
UI_BUTTON_VERSION_MANAGER = "Gestor de Versiones"
UI_BUTTON_MIGRATE_DATA = "Migración de Datos"
UI_SECTION_ADDONS = "Complementos"
UI_BUTTON_ADDON_MANAGER = "Gestor de recursos"
UI_SECTION_CUSTOMIZATION = "Personalización"
UI_BUTTON_SKIN_PACK_CREATOR = "Creador de Skin Packs"
UI_BUTTON_GAME_CONFIG = "Configurador de Juego"
UI_LABEL_SHADERS_STATUS = "Shaders: ..."
UI_BUTTON_DISABLE_SHADERS = "Disable Shaders"
UI_SECTION_FILES = "Archivos"
UI_BUTTON_OPEN_DATA_FOLDER = "Abrir Carpeta de Datos"
UI_SECTION_SYSTEM = "Sistema"
UI_BUTTON_VERIFY_DEPS = "Verificar Dependencias"
UI_BUTTON_VERIFY_HW = "Verificar Requisitos (Hardware)"
UI_SECTION_SHORTCUT = "Menú de Inicio"
UI_BUTTON_MANAGE_SHORTCUT = "Gestor de Versiones"
UI_SECTION_EXPORT = "Exportación"
UI_BUTTON_EXPORT_WORLDS = "Exportar Mundos"
UI_BUTTON_OPEN_SCREENSHOTS = "Abrir Capturas"

# Pestaña Ajustes
UI_SECTION_BINARIES = "Rutas de Binarios"

# Mapeo de Modos de Binarios (Display)
UI_BIN_MODES = {
    MODE_BIN_SYSTEM: "Sistema (Instalado)",
    MODE_BIN_LOCAL: "Local (Junto al script)",
    MODE_BIN_CUSTOM: "Personalizado",
    MODE_BIN_FLATPAK: "Flatpak (Personalizado)"
}

UI_DEFAULT_MODE = MODE_BIN_SYSTEM
UI_LABEL_FLATPAK_ID = "ID de App Flatpak:"
UI_BUTTON_SAVE_SETTINGS = "Guardar Configuración"
UI_SECTION_APPEARANCE = "Apariencia"
UI_LABEL_COLOR_THEME = "Tema de Color:"
UI_LABEL_APPEARANCE_MODE = "Modo de Apariencia:"
UI_LABEL_LANGUAGE = "Idioma:"
UI_LABEL_VERSION_LIST_STYLE = "Estilo de Lista:"
UI_LABEL_TOOLS_LAYOUT = "Diseño de Herramientas:"
UI_LABEL_ICON_SIZE = "Tamaño de Icono:"
UI_LABEL_TITLE_SIZE = "Tamaño de Título:"
UI_LABEL_CARD_WIDTH = "Anchura de Tarjeta:"
UI_LABEL_CARD_HEIGHT = "Altura de Tarjeta:"

UI_SECTION_BACKGROUND = "Fondo Personalizado"
UI_LABEL_BG_PATH = "Imagen de Fondo:"
UI_LABEL_BG_X = "Posición X:"
UI_LABEL_BG_Y = "Posición Y:"
UI_LABEL_BG_OPACITY = "Opacidad:"
UI_LABEL_BG_ZOOM = "Zoom:"
UI_LABEL_POS_X = "Pos X:"
UI_LABEL_POS_Y = "Pos Y:"
UI_LABEL_COMPATIBLE_RANGE = "Versiones Compatibles:"
UI_BUTTON_RESET_ICON = "Restablecer Icono"

UI_SECTION_STICKER = "Sticker / Watermark"
UI_LABEL_STICKER_MODE = "Modo:"
UI_LABEL_STICKER_CONTENT = "Contenido (Texto/Ruta):"
UI_LABEL_STICKER_CORNER = "Esquina:"
UI_LABEL_STICKER_X = "Distancia X:"
UI_LABEL_STICKER_Y = "Distancia Y:"
UI_LABEL_STICKER_ZOOM = "Zoom Sticker:"
UI_LABEL_STICKER_OPACITY = "Opacidad:"

UI_LABEL_SECTION_OPACITY = "Section Opacity:"

UI_STICKER_MODES = {
    "none": "Desactivado",
    "image": "Imagen (PNG/WebP)",
    "text": "Texto Personalizado"
}

UI_STICKER_CORNERS = {
    "top-left": "Superior Izquierda",
    "top-right": "Superior Derecha",
    "bottom-left": "Inferior Izquierda",
    "bottom-right": "Inferior Derecha"
}

UI_LIST_STYLES = {
    STYLE_LIST: "Lista",
    STYLE_GRID: "Cuadrícula"
}

UI_TOOLS_LAYOUTS = {
    STYLE_LIST: "Una Columna",
    STYLE_COLUMNS: "Dos Columnas",
    STYLE_GRID: "Tarjetas (Cuadrícula)"
}

UI_APPEARANCE_MODES = {
    "Light": "Claro",
    "Dark": "Oscuro",
    "System": "Sistema"
}

UI_COLOR_THEMES = ["blue", "green", "dark-blue", "purple", "orange", "red", "gray", "cyan", "yellow", "midnight", "cherry", "ocean"]

UI_THEME_NAMES = {
    "blue": "Blue",
    "green": "Green",
    "dark-blue": "Dark Blue",
    "purple": "Purple",
    "orange": "Orange",
    "red": "Red",
    "gray": "Gray",
    "cyan": "Cyan",
    "yellow": "Yellow",
    "midnight": "Midnight",
    "cherry": "Cherry",
    "ocean": "Ocean"
}

UI_RESTART_REQUIRED_MSG = "* El cambio de color requiere reiniciar la aplicación."
UI_APPEARANCE_HINT = "Esto solo cambia ligeramente la IU, no la cambia radicalmente."
UI_CONFIRM_TITLE = "Confirmar"
UI_RESTORE_DEFAULTS_CONFIRM = "¿Estás seguro de que quieres restaurar todos los ajustes a sus valores por defecto? La aplicación se cerrará."
UI_RESTORE_DEFAULTS_SUCCESS_TITLE = "Ajustes restaurados"
UI_RESTORE_DEFAULTS_SUCCESS_MSG = "Los ajustes se han restaurado. La aplicación se cerrará ahora."
UI_BUTTON_RESTORE_DEFAULTS = "Restaurar valores"
UI_LABEL_CLIENT_GAME = "Cliente (game):"
UI_LABEL_EXTRACTOR_APK = "Extractor APK:"
UI_LABEL_SIGNIN_UI = "Google Login UI:"
UI_LABEL_GPLAYDL = "Google Play Downloader:"
UI_LABEL_GPLAYVER = "Google Play Version Check:"
UI_LABEL_WEBVIEW_OPTIONAL = "Webview (Opcional):"
UI_LABEL_ERROR_HANDLER_OPTIONAL = "Error Handler (Opcional):"
UI_LABEL_MSA_DAEMON = "MSA Daemon:"
UI_SECTION_COMPATIBILITY = "Compatibilidad"
UI_LOG_VIEWER_LABEL = "Logs:"
UI_BUTTON_EXPORT_LOG = "Exportar"
UI_EXPORT_LOG_TITLE = "Guardar Log"

# NVIDIA Compatibility
UI_NVIDIA_COMPAT_MODE_CHECKBOX = "Activar modo de compatibilidad para Nvidia (experimental, solo para Flatpak)"
UI_NVIDIA_COMPAT_MODE_TOOLTIP = "Activa esta opción si experimentas crasheos o problemas gráficos con una tarjeta Nvidia. Forza el uso de la GPU dedicada con una capa de compatibilidad (Zink)."
UI_NVIDIA_PRIME_CHECKBOX = "Usar Nvidia Prime (__NV_PRIME_RENDER_OFFLOAD=1)"
UI_NVIDIA_PRIME_TOOLTIP = "Fuerza el uso de la GPU Nvidia en sistemas híbridos (Prime Offloading). Establece __NV_PRIME_RENDER_OFFLOAD, __GLX_VENDOR_LIBRARY_NAME y DRI_PRIME."
UI_ZINK_CHECKBOX = "Usar Driver Zink (MESA_LOADER_DRIVER_OVERRIDE=zink)"
UI_ZINK_TOOLTIP = "Utiliza la capa de compatibilidad Zink para ejecutar OpenGL sobre Vulkan. Recomendado si tienes errores gráficos ('signal 6' o parpadeos) con los drivers nativos de Nvidia en Flatpak."
UI_GAMEMODE_CHECKBOX = "Usar GameMode (gamemoderun)"
UI_GAMEMODE_TOOLTIP = "Optimiza el rendimiento del sistema usando Feral GameMode. Requiere que 'gamemode' esté instalado en el sistema."
UI_CUSTOM_ARGS_CHECKBOX = "Activar Argumentos/Variables Personalizadas"
UI_CUSTOM_ARGS_TOOLTIP = "Permite pasar variables de entorno (KEY=VAL) o argumentos adicionales. Desactiva Nvidia Prime y Zink automáticos."
UI_CUSTOM_ARGS_LABEL = "Argumentos/Variables:"

# --- Discord Rich Presence ---
UI_DISCORD_RPC_CHECKBOX = "Activar Discord Rich Presence"
UI_DISCORD_RPC_TOOLTIP = "Muestra en Discord qué versión de Minecraft Bedrock estás jugando con un contador de tiempo. Requiere la librería 'pypresence' instalada y Discord abierto."
UI_CHECKBOX_DISCORD_RPC = "Mostrar en Discord"
UI_DISCORD_RPC_CLIENT_ID_LABEL = "Discord Client ID:"
UI_DISCORD_RPC_MISSING_DEPS = "Discord RPC no disponible: instala 'pypresence' (pip install pypresence)"
UI_DISCORD_RPC_MISSING_CLIENT_ID = "Configura un Discord Client ID en Ajustes > Compatibilidad para activar Rich Presence."

# Diálogos y Mensajes
UI_INFO_TITLE = "Info"
UI_ERROR_TITLE = "Error"
UI_TITLE_LEGAL = "Términos y Condiciones"
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
UI_MAIN_LAUNCHER_LABEL = "Lanzador Principal"
UI_FLATPAK_SHORTCUT_INFO_TITLE = "Información"
UI_FLATPAK_SHORTCUT_INFO_MSG = "El acceso directo principal de la aplicación Flatpak se crea automáticamente al instalar.\n\nPuedes gestionarlo desde tu tienda de aplicaciones (ej. Discover, GNOME Software)."
UI_SHORTCUT_COMMENT = "Lanzador de Minecraft PE para Linux"
UI_BUTTON_ADD = "Añadir"
UI_BUTTON_DELETE = "Borrar"
UI_CLOSING_FOR_GAME = "Se cerrará el launcher para iniciar el juego..."
UI_CONFIG_ERROR_TITLE = "Error de Configuración"
UI_SELF_LAUNCH_ERROR_MSG = "Se ha detectado un error crítico: El lanzador está intentando ejecutarse a sí mismo en lugar del juego.\n\nPor favor, revisa la configuración de los binarios en la pestaña 'Ajustes' y asegúrate de que la ruta al 'mcpelauncher-client' es correcta."
UI_CRITICAL_LAUNCH_ERROR_TITLE = "Error Crítico de Lanzamiento"
UI_EXECVE_ERROR_MSG = "No se pudo iniciar el juego (execve falló).\nError: {e}"
UI_VERIFYING_TITLE = "Verificando..."
UI_STARTING_MSG = "Iniciando..."
UI_RESULT_TITLE = "Resultado"
UI_VERIFICATION_RESULT_HEADER = "Resultado de Verificación"
UI_ANALYZING_TITLE = "Analizando..."
UI_ANALYZING_HW_MSG = "Analizando Hardware..."
UI_HW_ARCH = "Arquitectura: {arch}\n"
UI_HW_CPU_EXT = "Extensiones CPU: {status}\n"
UI_HW_MODEL = "Modelo"
UI_HW_RAM_TOTAL = "Total"
UI_HW_CPU_INFO = "INFORMACIÓN DE CPU"
UI_HW_RAM_INFO = "INFORMACIÓN DE RAM"
UI_HW_GPU_INFO = "INFORMACIÓN DE GPU"
UI_HW_OPENGL_ES = "OpenGL ES: {gl_ver}\n\n"
UI_SYMLINK_NOT_SUPPORTED_TITLE = "Compatibilidad de Disco"
UI_SYMLINK_NOT_SUPPORTED_MSG = "Los enlaces simbólicos no están soportados en este sistema de archivos (exFAT/NTFS).\n\nEl sistema multiperfil ha sido desactivado por seguridad para evitar pérdida de datos. Se usará el perfil por defecto."
UI_LABEL_UI_SCALE = "Escalado de Interfaz (DPI):"
UI_RESTART_SCALE_MSG = "* El cambio de escalado requiere reiniciar el launcher para aplicarse."
UI_PROMPT_DESKTOP_SHORTCUT = "¿Deseas agregar también un acceso directo al escritorio?"
UI_VERIFYING_PACKAGES_LABEL = "{title} {count} paquetes..."
UI_INCOMPATIBLE_TEXT = "Incompatible"
UI_VERSION_TEXT = "Versión: "
UI_SHADER_STATUS_LABEL = "Estado Shaders: {status}"
UI_GAME_CONFIG_TITLE = "Configurador de Juego"
UI_TAB_VISUAL = "Interfaz Visual"
UI_TAB_EDITOR = "Editor Manual"
UI_BUTTON_SAVE_FILE = "Guardar Archivo"
UI_SAVE_FILE_SUCCESS = "Archivo guardado correctamente."
UI_ERROR_READING_FILE = "No se pudo leer el archivo: {e}"
UI_ERROR_SAVING_FILE = "No se pudo guardar el archivo: {e}"
UI_FILE_NOT_FOUND_WARN = "El archivo options.txt no existe en esta instalación."

# Labels Configuración de Juego
UI_GC_GRAPHICS = "Gráficos y Rendimiento"
UI_GC_VIEW_DISTANCE = "Distancia de Renderizado (Chunks)"
UI_GC_MAX_FPS = "Límite de FPS (0 = Ilimitado)"
UI_GC_VSYNC = "Sincronización Vertical (VSync)"
UI_GC_GAMMA = "Brillo (Gamma)"
UI_GC_FULLSCREEN = "Pantalla Completa"
UI_GC_FANCY_SKIES = "Cielos Detallados"
UI_GC_SMOOTH_LIGHTING = "Iluminación Suave"
UI_GC_GRAPHICS_MODE = "Modo de Gráficos"
UI_GC_GRAPHICS_MODE_MAP = ["Simple", "Fancy", "Vibrant Visual"]

UI_GC_GAMEPLAY = "Jugabilidad"
UI_GC_DIFFICULTY = "Dificultad"
UI_GC_DIFFICULTY_MAP = ["Pacífico", "Fácil", "Normal", "Difícil"]
UI_GC_PERSPECTIVE = "Cámara"
UI_GC_PERSPECTIVE_MAP = ["Primera Persona", "Tercera Persona (Detrás)", "Tercera Persona (Frente)"]
UI_GC_LANGUAGE = "Idioma del Juego (ej. es_MX)"

UI_GC_CONTROLS = "Controles"
UI_GC_SENSITIVITY = "Sensibilidad del Ratón"
UI_GC_INVERT_MOUSE = "Invertir Ratón"
UI_GC_AUTO_JUMP = "Salto Automático"
UI_GC_LEFT_HANDED = "Modo Zurdo"
UI_GC_SWAP_JUMP_SNEAK = "Intercambiar Saltar/Agacharse"

UI_GC_AUDIO = "Audio"
UI_GC_SOUND_VOLUME = "Efectos de Sonido"
UI_GC_MUSIC_VOLUME = "Música de Fondo"

UI_GC_PRIVACY = "Privacidad y Red"
UI_GC_SERVER_VISIBLE = "Partida LAN Visible"
UI_GC_XBOX_VISIBLE = "Estado Online (Xbox)"
UI_GC_AUTO_UPDATE = "Actualizaciones Automáticas"
UI_MIGRATION_MANAGER_TITLE = "Gestor de Migración de Datos"
UI_MIGRATION_TITLE = "Migración de Datos"
UI_SOURCE_LABEL = "Origen (Desde donde copiar):"
UI_SOURCE_MODES_DISPLAY = ["Local (.local)", "Flatpak (por ID)", "Personalizado"]
UI_DESTINATION_LABEL = "Destino (Ruta actual):"
UI_WHAT_TO_MIGRATE = "¿Qué deseas migrar?:"
UI_MIGRATE_VERSIONS = "📁 Versiones (versions/)"
UI_MIGRATE_WORLDS = "🌍 Mundos (games/com.mojang/minecraftWorlds/)"
UI_MIGRATE_RESOURCES = "🎨 Paquetes de Recursos (resource_packs/)"
UI_MIGRATE_VERSIONS_SIMPLE = "Versiones"
UI_MIGRATE_WORLDS_SIMPLE = "Mundos"
UI_MIGRATE_RESOURCES_SIMPLE = "Paquetes de Recursos"
UI_MIGRATE_ALL = "📦 Migrar TODO (carpeta completa mcpelauncher/)"
UI_MIGRATION_METHOD = "Método de Migración:"
UI_METHOD_COPY = "Copiar (Mantiene origen y duplica)"
UI_METHOD_MOVE = "Mover (Libera espacio en origen)"
UI_METHOD_LINK = "Enlazar (Symlink - Sincroniza carpetas)"
UI_BUTTON_START_MIGRATION = "🚀 INICIAR MIGRACIÓN"
UI_VALID_FOLDER_DETECTED = "✓ Carpeta válida detectada"
UI_INVALID_FOLDER_WARNING = "⚠ Carpeta no parece contener datos de mcpelauncher"
UI_FOLDER_NOT_EXISTS = "✗ Carpeta no existe"
UI_SELECT_SOURCE_FOLDER = "Seleccionar carpeta de origen"
UI_MIGRATION_CONFIRM_MSG = "¿Estás seguro de migrar datos?\n\nDe: {src}\nA: {dst}\nMétodo: {method}\nElementos: {items}"
UI_MIGRATING_TITLE = "Migrando..."
UI_MIGRATING_MSG = "Copiando archivos, por favor espera..."
UI_MIGRATION_SUCCESS_MSG = "Migración completada.\nElementos procesados: {count}\n\nRefresca para ver cambios."
UI_SKIN_PACK_CREATOR_TITLE = "Creador de Skin Packs"
UI_PACK_NAME_LABEL = "Nombre del Pack:"
UI_SKINS_ADDED_LABEL = "Skins Añadidas"
UI_BUTTON_ADD_SKINS_PNG = "Añadir Skins (PNG)"
UI_BUTTON_EXPORT_MCPACK = "Exportar .mcpack"
UI_ERROR_MISSING_NAME_OR_SKINS = "Falta nombre del pack o skins."
UI_PACK_SAVED_SUCCESS = "Pack guardado en {save_path}"
UI_INSTALL_NEW_VERSION_TITLE = "Instalar Nueva Versión"
UI_INSTALL_TAB_GOOGLE = "Google Play"
UI_INSTALL_TAB_LOCAL = "APK Local"
UI_BUTTON_LOGIN_GOOGLE = "Iniciar Sesión (Google)"
UI_LABEL_SELECT_VERSION = "Seleccionar Versión:"
UI_LABEL_SELECT_ARCH = "Arquitectura:"
UI_LABEL_FILTER_VERSIONS = "Filtrar:"
UI_FILTER_ALL = "Todas"
UI_FILTER_STABLE = "Estables"
UI_FILTER_BETA = "Betas"
UI_LABEL_DOWNLOAD_PROGRESS = "Descargando: {p}%"
UI_STATUS_GETTING_INFO = "Obteniendo información..."
UI_STATUS_DOWNLOADING = "Descargando..."
UI_STATUS_EXTRACTING = "Extrayendo..."
UI_STATUS_LOGIN_REQUIRED = "Inicia sesión para continuar"
UI_STATUS_SESSION_ACTIVE = "✓ Sesión Activa"
UI_STATUS_SESSION_INACTIVE = "✗ Sesión no Iniciada"
UI_STATUS_LOGIN_IN_PROGRESS = "⏳ Ventana de inicio de sesión abierta..."
UI_STATUS_LOGIN_WAITING = "⏳ Esperando token... ({s}s)"

# --- Google Play: Errores de descarga y sesión (mostrados en UI) ---
UI_GOOGLE_DELIVERY_STATUS_2 = ("Google Play did not deliver this specific version. Common causes:\n"
    "• The selected version is no longer in Google's active catalog\n"
    "  (Google removes old versions and only offers the current release plan).\n"
    "• The account does not own Minecraft Bedrock.\n\n"
    "Solutions:\n"
    "1. Check 'Latest version (auto)' and retry.\n"
    "2. Verify ownership at:\n"
    "   https://play.google.com/store/apps/details?id=com.mojang.minecraftpe\n"
    "3. Use the 'Local APK' tab to install an APK you already have.")
UI_GOOGLE_DELIVERY_STATUS_3 = ("The selected version is not available for this architecture.\n\n"
    "Try changing the architecture (x86_64 / x86) or choose another version.")
UI_GOOGLE_DELIVERY_STATUS_5 = "App not found on Google Play."
UI_GOOGLE_DELIVERY_STATUS_UNKNOWN = "Google Play rejected the download (delivery status={status})."
UI_GOOGLE_SESSION_EXPIRED = ("Your Google session has expired. Close this window, sign in again, "
    "and retry the download.")
UI_GOOGLE_DROIDGUARD_REQUIRED = ("Google requires DroidGuard for this account/device. "
    "Try with a different account or network.")
UI_GOOGLE_DOWNLOAD_ERROR = "Download error (code {code}).\n\ngplaydl output:\n{tail}"
UI_GOOGLE_TOKEN_EXCHANGE_FAILED = ("The Google token could not be exchanged.\n\n"
    "Possible causes:\n"
    "• The session expired before the exchange completed.\n"
    "• Google rejected the authentication (restricted account or no Play access).\n\n"
    "Sign in again without an encryption password and complete the quick flow.")
UI_GOOGLE_SIGNIN_NO_TOKEN = ("The sign-in process finished without delivering a token. "
    "Please try again and complete the flow in the Google window.")
UI_GOOGLE_SIGNIN_LAUNCH_FAILED = "Could not start '{bin_path}'. Check the path in Settings."
UI_GOOGLE_LOGIN_LAUNCH_ERROR = "Failed to launch sign-in: {error}"

UI_VERSION_LATEST_LABEL = "★ Última versión (auto) — recomendado"
UI_APK_FILE_LABEL = "Archivo APK:"
UI_SELECT_APK_PLACEHOLDER = "Selecciona un APK..."
UI_VERSION_NAME_LABEL = "Nombre de la Versión:"
UI_VERSION_NAME_PLACEHOLDER = "Ej: 1.20.50"
UI_INSTALL_MODE_DEST_LABEL = "Modo de Instalación (Destino):"
UI_INSTALL_MODE_OWN = "Local (Flatpak Propio)"
UI_INSTALL_MODE_SHARED = "Local (.local/share)"
UI_INSTALL_MODE_LOCAL = "Local"
UI_INSTALL_MODE_FLATPAK_DESC = "Flatpak (Personalizado)"
UI_FLATPAK_CUSTOM_ID_LABEL = "Flatpak (ID Personalizado):"
UI_BUTTON_INSTALL_NOW = "INSTALAR AHORA"
UI_SELECT_APK_TITLE = "Seleccionar archivo APK"
UI_APK_FILES_TYPE = "Archivos APK"
UI_ERROR_SELECT_VALID_APK = "Selecciona un APK válido."
UI_ERROR_WRITE_VERSION_NAME = "Escribe un nombre para la versión."
UI_OPEN_FILE_TITLE = "Abrir archivo"
UI_ALL_FILES_TYPE = "Todos los archivos"
UI_SELECT_FOLDER_TITLE = "Seleccionar carpeta"
UI_OPEN_FILES_TITLE = "Abrir archivos"
UI_ARCH_NATIVE = "Compatible ({arch} Nativo)"
UI_ARCH_LEGACY = "Compatible (x86 Legacy)"
UI_ARCH_INCOMPATIBLE = "Incompatible (Solo ARM detectado)"
UI_ARCH_UNKNOWN = "Desconocido (No se detectaron librerías)"
UI_ARCH_POSSIBLY_INCOMPATIBLE = "Posiblemente Incompatible (Sistema: {arch})"
UI_VERSION_NOT_INSTALLED_ERROR = "La versión '{version}' no está instalada."
UI_NO_TARGET_PATH_ERROR = "No se ha definido una ruta de destino."
UI_EXTRACTING_APK_TITLE = "Extrayendo APK"
UI_EXTRACTING_APK_MSG = "Por favor espera, esto puede tardar unos minutos..."
UI_EXTRACTION_SUCCESS_MSG = "Versión {ver_name} instalada correctamente."
UI_EXTRACTION_ERROR_MSG = "El extractor falló:\n{err_msg}"
UI_CRITICAL_ERROR_MSG = "Fallo crítico: {e}"
UI_MANAGE_VERSION_TITLE = "Gestor Avanzado de Versiones"
UI_MANAGE_VERSION_PROMPT = "Gestionar versión: {version}"
UI_BUTTON_RENAME = "Renombrar"
UI_BUTTON_CHANGE_ICON = "Cambiar Icono"
UI_LABEL_ICON_ZOOM = "Zoom Icono:"
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

# --- Sistema de Perfiles ---
UI_LABEL_PROFILE = "Perfil:"
UI_PROFILE_DEFAULT = "default"
UI_BUTTON_MANAGE_PROFILES = "Gestionar Perfiles"
UI_PROFILES_MANAGER_TITLE = "Gestor de Perfiles"
UI_BUTTON_ADD_PROFILE = "Añadir Perfil"
UI_BUTTON_DELETE_PROFILE = "Eliminar Perfil"
UI_BUTTON_RENAME_PROFILE = "Renombrar"
UI_PROFILE_MIGRATION_NOTICE = "Sistema de perfiles activado. Tus datos se han movido al perfil 'default'."
UI_PROFILE_NAME_REQUIRED = "Escribe un nombre para el perfil:"
UI_CONFIRM_DELETE_PROFILE = "¿Estás seguro de que quieres eliminar el perfil '{name}'?"

# --- Gestor de Addons ---
UI_ADDON_MANAGER_TITLE = "Gestor de Addons y Recursos"
UI_SEARCH_PLACEHOLDER = "Buscar por nombre..."
UI_STATUS_ACTIVE = "Activo"
UI_STATUS_DISABLED = "Desactivado"
UI_BUTTON_ACTIVATE = "Activar"
UI_BUTTON_DEACTIVATE = "Desactivar"
UI_BUTTON_IMPORT_FILE = "Importar archivo"
UI_TAB_WORLDS = "Mundos"
UI_TAB_BP = "Behavior Packs (BP)"
UI_TAB_RP = "Resource Packs (RP)"
UI_TAB_MCPE_MODS = "Mods MCPELauncher"
UI_TYPE_RESOURCE = "Recursos"
UI_TYPE_BEHAVIOR = "Comportamiento"
UI_TYPE_WORLD = "Mundo"
UI_TYPE_SKIN = "Skins"
UI_TYPE_SKINPACK = "Skinpack"
UI_SCANNING_RESOURCES = "Escaneando recursos..."
UI_TOGGLING_STATUS = "Cambiando estado..."
UI_DELETING_RESOURCE = "Eliminando recurso..."
UI_WORLD_EXPORTED_SUCCESS = "Mundo exportado a: {path}"
UI_INSTALLING_PACK = "Instalando pack..."
UI_PACK_INSTALLED = "Pack instalado correctamente."
UI_INVALID_MANIFEST = "Manifest inválido o no encontrado."
UI_SELECT_PACK_TYPE = "Selecciona el tipo de pack:"
UI_BUTTON_EXPORT = "Exportar"
UI_YES = "Sí"
UI_NO = "No"
UI_CANCEL = "Cancelar"
UI_ERROR_SAME_FOLDER = "Error: La carpeta de origen y destino son la misma"
UI_ERROR_NOTHING_SELECTED = "Nada seleccionado para migrar"
UI_ERROR_FLATPAK_SPAWN_NOT_FOUND = "Error: 'flatpak-spawn' no encontrado. No se puede abrir un terminal externo."
UI_HW_NOT_DETECTED = "No detectado"
UI_LABEL_APP_ID = "App ID:"
UI_PLACEHOLDER_SOURCE_PATH = "Ruta de origen..."
UI_BUTTON_BROWSE_FOLDER = "Buscar Carpeta"
UI_ERROR_READING_APK = "Error leyendo APK: {e}"
UI_APK_COMPATIBLE_X86 = "La APK es compatible (x86) o (x86_64)"
UI_APK_INCOMPATIBLE_ARM = "Esta APK no es compatible (Esta es una APK ARM y necesita una x86)"
UI_APK_INVALID = "La APK esta incompleta o no es de Minecraft"
UI_SKIN_PACK_FILES_TYPE = "Archivos de Skin Pack"
UI_MCPACK_FILES_TYPE = "Archivos Minecraft Pack"
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
UI_TERMINAL_PROMPT_CLOSE = "Presiona Enter para cerrar..."
UI_DETECTED_LABEL = "Detectado: {version}"
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
- org.kde.Platform//6.10
- io.qt.qtwebengine.BaseApp

Para Desarrolladores:
- org.kde.Sdk//6.10
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
UI_SECTION_FLATPAK_RUNTIMES = "Gestión de Runtimes (Flatpak)"
UI_BUTTON_UPDATE_RUNTIMES = "Actualizar Runtimes Requeridos"

# Migration Wizard UI Strings
UI_WIZARD_STEP_SOURCE_TITLE = "Selecciona el origen"
UI_WIZARD_SOURCE_LOCAL_DESC = "Para usuarios que vengan de CCMC Launcher, MCPETools o instalaciones con datos almacenados en local compartido"
UI_WIZARD_SOURCE_FLATPAK_DESC = "Para usuarios que vengan de un launcher Flatpak, incluido el Oficial o similares"
UI_WIZARD_SOURCE_CUSTOM_DESC = "Selecciona manualmente la carpeta de origen"
UI_WIZARD_SOURCE_CUSTOM_PLACEHOLDER = "Selecciona o escribe la ruta de la carpeta de origen..."

UI_WIZARD_STEP_PROFILE_TITLE = "Selecciona el perfil destino"
UI_WIZARD_PROFILE_DEFAULT_ONLY = "Solo existe el perfil Default. Los datos se guardarán ahí."

UI_WIZARD_STEP_CONTENT_TITLE = "¿Qué deseas migrar?"
UI_WIZARD_CONTENT_ALL_DESC = "Migra todas las versiones, mundos y recursos sin personalizar"
UI_WIZARD_CONTENT_CUSTOM = "Personalizado"
UI_WIZARD_CONTENT_CUSTOM_DESC = "Elige manualmente qué elementos migrar"

UI_WIZARD_STEP_METHOD_TITLE = "Elige el método de migración"
UI_WIZARD_METHOD_SUB = "Selecciona una opción para continuar:"
UI_WIZARD_METHOD_COPY_TITLE = "Copiar (Duplicar)"
UI_WIZARD_METHOD_COPY_DESC = "Copia los datos al nuevo destino sin modificar el origen. Ocupa el doble de espacio pero conserva todo intacto por si algo sale mal."
UI_WIZARD_METHOD_MOVE_TITLE = "Mover (Trasladar)"
UI_WIZARD_METHOD_MOVE_DESC = "Mueve los datos completamente al nuevo destino. Los archivos originales se eliminan. Recomendado si ya no usarás el launcher anterior."
UI_WIZARD_METHOD_LINK_TITLE = "Symlink (Sincronizar)"
UI_WIZARD_METHOD_LINK_DESC = "Crea un enlace simbólico entre origen y destino. Los datos permanecen en su ubicación original y se reflejan en el launcher. Ideal para conservar espacio en disco."

UI_WIZARD_STEP_SUMMARY_TITLE = "Resumen de migración"
UI_WIZARD_SUMMARY_LABEL_SOURCE = "Origen"
UI_WIZARD_SUMMARY_LABEL_DEST = "Destino"
UI_WIZARD_SUMMARY_LABEL_PROFILE = "Perfil"
UI_WIZARD_SUMMARY_LABEL_ITEMS = "Elementos"
UI_WIZARD_SUMMARY_LABEL_METHOD = "Método"
UI_BUTTON_MIGRATE = "🚀 Migrar"

# ── Update checker ──
UI_UPDATE_AVAILABLE = "Versión {version} disponible. Actualiza CianovaLauncher para obtener las novedades."

