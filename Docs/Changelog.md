# 📝 Changelog - CianovaLauncher

# [3.2] - 2026-08-03 — UI Update

### ⚙️ Rendimiento y compatibilidad
- Nuevos ajustes por desmarcado simples para controlar el renderizado de Minecraft, cada uno con su botón de ayuda (`?`):
  - **Forzar OpenGL** (`MESA_LOADER_DRIVER_OVERRIDE`) para evitar fallos con ciertos drivers gráficos.
  - **Forzar OpenGL ES 3.2** (`MESA_GLES_VERSION_OVERRIDE=3.2`) para versiones de Mesa que lo requieran.
  - **Desactivar Vsync** (`MESA_NO_ERROR=1`) para mejorar los FPS.
  - **Forzar GPU Discreta** (`DRI_PRIME=1`) para usar la tarjeta gráfica dedicada en lugar de la integrada.
- Estos ajustes se combinan automáticamente con los existentes de **Gamemode**, **NVIDIA Prime** y **Zink**.

### 🎨 Interfaz y apariencia
- Modo claro completo en el **Configurador de Juego** y el **Asistente de Migración**, con colores y bordes coherentes con el resto de la aplicación en ambos temas.
- Iconos de **perfil** rediseñados: cada perfil se distingue ahora por una silueta de persona en su color característico en lugar de un bloque genérico.
- El resumen final del **Asistente de Configuración** separa ahora sus secciones verticalmente para una lectura más clara de cada apartado.
- Corregido el borde de los **desplegables (combobox)** para que ya no muestren una línea oscura arriba y abajo.

### 🧰 Pestaña Herramientas rediseñada
- Las herramientas pasan a **tarjetas** con icono vectorial propio, título, breve descripción y cursor de clic, en lugar de botones de texto plano.
- Nuevo orden por uso: **Instalación**, **Contenido**, **Configuración** y **Sistema**.
- Iconos vectoriales dibujados en tiempo de ejecución (descarga, migración, lista, cubo, camiseta, cámara, sliders, chispa, carpeta, lupa, escudo, enchufe) con el color de acento del tema.
- **Badges de estado** integrados en las tarjetas: verde/amarillo/rojo para el estado de los Shaders, del Mod DRM y del rango de versiones compatibles.
- Nuevo selector de **Diseño de Herramientas** en Ajustes > Apariencia: **Dos Columnas** o **Tarjetas (Cuadrícula)**.
- Las tarjetas tienen ahora **fondo sólido** reconocible (independiente de la opacidad de sección) y un **efecto hover** que ilumina la tarjeta con el **color de acento** y resalta su borde en ambos temas (oscuro y claro).
- Corregido el **hover de las tarjetas** de Herramientas: ahora la regla QSS con especificidad suficiente (`#ToolsTab QFrame#ToolCard:hover`) hace que el fondo de acento y el borde se apliquen realmente al pasar el ratón.
- Mejorado el **contraste del texto secundario** (descripciones de tarjetas) en **modo claro**: color más oscuro (`#404040`) para una lectura cómoda sobre el fondo claro.

### ▶️ Pestaña Play — indicadores y tarjetas
- Los indicadores de la cabecera (**Estado**, **Estado del juego**, **Perfil**, **Instalación**, **Versiones Instaladas** y el **Modo** de ToolsTab) pasan a ser **píldoras** con fondo y borde teñidos del color de acento, coherentes en ambos temas.
- La cabecera usa un **FlowLayout**: al estrechar la ventana horizontalmente, las píldoras saltan a la línea siguiente en lugar de cortarse o desbordarse.
- Los indicadores de **Perfil**, **Instalación** y el selector de **Modo** quedan alineados a la **derecha** de la cabecera (con un spacer expansivo), mientras Estado y Estado del juego permanecen a la izquierda; el FlowLayout mantiene el wrap en ventanas estrechas.
- Nuevo **tamaño por defecto** de las tarjetas de versión: **200×200** con icono **96 px** y título **16 px** (antes 180×145, icono 32, título 13), para que luzcan grandes y resaltantes de serie; los deslizadores de Ajustes reflejan los nuevos valores.

### ⚠️ Avisos de versiones en Google Play
- El aviso de compatibilidad de una versión marcada aparece ahora **al seleccionarla** en el desplegable de Google Play, no solo al pulsar el botón de descarga.

### ✨ General
- CianovaLauncher se identifica ahora como **versión 3.2** con el lanzamiento "UI Update".
- Límite de logs: los registros rotan a 5 MB por archivo y se conservan como máximo 30 archivos, eliminando los más antiguos automáticamente.
- Los logs se escriben y leen en la misma ubicación (aware de Flatpak), por lo que la pestaña **Logs** encuentra siempre la sesión activa.

### 🚨 Avisos de hotfix
- Nuevo sistema de **hotfix**: una re-publicación de la misma versión (p. ej. `3.1.0` re-publicada con un fix urgente) ahora avisa a los usuarios aunque el número de versión no cambie.
- El `version.json` acepta un campo `hotfix` con `id`, `title`, `body` y `force`; el launcher lo detecta y muestra un diálogo de **Actualización crítica**.
- Los hotfix **obligatorios** (`force: true`) no se pueden ignorar; los no obligatorios ofrecen "Ignorar" y no vuelven a aparecer para ese `id`.
- El workflow de Release pide ahora **¿Es un hotfix?**, **Razón del hotfix** y **Aviso obligatorio** y publica el `version.json` en la raíz de `gh-pages` vía API (sin clonar el repositorio Flatpak de 500 MB).

### 🗂️ Pestaña Logs
- El log activo se lee de forma incremental sin recargar todo el contenido, evitando parpadeos y saltos de scroll forzados.
- Nuevo indicador de sesión: un punto **verde** con el texto "Sesión actual" para el log en vivo y un punto **gris** con "Sesión DD/MM/AAAA - HH:MM:SS" para los anteriores, tanto en la pestaña como en el desplegable.

### ⚙️ Ajustes reorganizados
- La sección "Rendimiento" pasa a llamarse **Extras** y ahora comienza con la opción de **Activar Argumentos/Variables Personalizadas** (movida desde Lanzamiento).
- La opción **Al lanzar el juego** (LaunchAction) se mueve a **General**.
- En modo de binarios **Personalizado** se añade un selector de **carpeta de binarios** con resolución automática: escanea la carpeta (y su subcarpeta `bin`) y asigna cada binario reconocido a su campo correspondiente.
- El texto de versión de binarios ("Precompiled binaries from mcpelauncher github" o el `info.txt`) se muestra ahora dentro de la sección Lanzamiento.
- El pie de Ajustes muestra "Project CianovaLauncher - v3.2" como enlace oculto que abre el changelog.
- Corregido: el campo "ID de App Flatpak" ya no se muestra cuando el modo de binarios es Sistema, Local o Personalizado.

### ▶️ Pestaña Play
- Las tarjetas de versión actualizan su color de tema automáticamente al cambiar entre modo claro/oscuro sin necesidad de hacer clic.
- El indicador de estado del juego ahora tiene un **fondo verde** cuando hay una sesión activa para que sea más visible.
- Se añade una insignia global "● Sesión activa" que se muestra sobre las pestañas mientras el juego está corriendo, incluso si no estás en la pestaña Play.

# [3.1] - 2026-06-28 — Refinements & New Features

### 🔧 Gestor de Recursos (Addons + Mods)
- Los `.zip` con múltiples manifests ahora se detectan y los RP+BP se instalan por separado.
- Validación de ZIP con `testzip()` antes de extraer para evitar instalaciones corruptas.
- Añadido soporte para `.mctemplate` en escaneo y filtro de archivos.
- Escaneo recursivo de subdirectorios en `mods/` para encontrar `.so`.
- Nombres duplicados en `.mcaddon` se resuelven con sufijo (`_1`, `_2`) automáticamente.
- Exportación de mundos con sanitización más permisiva para nombres de archivo.
- Corregido el filtro de pestañas: la pestaña RP ya no muestra mods por error.

### 📦 Mod DRM desde compilación propia de Leimsoto
- El mod DRM (mcpelauncher-updates) ahora se descarga directamente desde [github.com/Leimsoto/mcpelauncher-updates](https://github.com/Leimsoto/mcpelauncher-updates/releases) en lugar del repositorio oficial ModDB.
- Arquitecturas mapeadas: `x86_64` y `arm64-v8a` con release tagging `v1.0.0`.
- Fallback de librerías: `libmcpelauncher-updates.so` resuelve como `libmcpelauncher_mod.so` en `_ensure_mc_libraries`.
- El launcher busca librerías dentro del mod instalado como fuente adicional.
- Mensajes y créditos actualizados para reflejar la fuente MIT de Leimsoto.
- Al lanzar una versión instalada desde Google Play, si falta el mod DRM el launcher pregunta si instalarlo antes de continuar. Si está desactivado, muestra advertencia.
- La gestión del mod DRM se movió completamente al Gestor de Recursos, eliminando la sección duplicada en Herramientas.

### 🏷️ Control de carga de mods
- Cada mod tiene checkbox "Cargar al inicio" que persiste entre sesiones.
- El estado se guarda con escritura atómica (`tmp` + `os.replace`) para evitar corrupción.
- Directorios `patches/` se filtran automáticamente del listado de mods a cargar.
- Los directorios de mod ahora se pasan explícitamente al comando de lanzamiento con flags `-m`.

### 📋 Metadatos de instalación
- Ahora se registra si una versión se instaló desde Google Play o desde un APK local.

### 🚀 Comportamiento de Inicio
- Nuevo sistema LaunchAction con tres modos: `close` (cerrar launcher), `hide` (minimizar a bandeja del sistema), `none` (indicador de estado en la UI).
- Monitor de juego con QTimer cada 2s para detectar cuándo termina el proceso.
- Migración automática: si tenías `close_on_launch: true`, se convierte a `launch_action: "close"`.

### 💾 Persistencia de Configuración
- Los checkboxes de Nvidia/Zink/Gamemode/LaunchAction y el campo de variables de entorno ahora persisten inmediatamente al cambiar.
- Gamemode y LaunchAction sincronizados entre pestañas Play y Settings.

### 🎮 Discord Rich Presence
- Envío síncrono de estado además de la cola para actualización inmediata.
- Añadidas rutas IPC para Discord Canary y PTB Flatpak.
- Limpieza mejorada: `stop()` llama a `clear()` antes de `close()`.

### 📋 Diálogo de Instalación
- La pestaña APK Local es ahora la predeterminada (Google Play en segundo lugar).

### ⚙️ Ajustes reorganizados
- Los ajustes ahora se organizan en 4 categorías con pestañas superiores: General, Lanzamiento, Apariencia e Integraciones.
- Navegación por QStackedWidget para evitar el scroll infinito.
- La categoría seleccionada se resalta con el color de acento.

### 🖥️ Detector de Hardware mejorado
- Soporte para arquitecturas ARM (lectura de `Features` además de `flags`).
- Timeout en `glxinfo` para evitar congelamientos.
- Parseo robusto de OpenGL ES con regex.
- Soporte x86 (32-bit) con requisito SSSE3.
- Soporte ARM NEON con detección y clasificación.
- GL desconocido ya no marca como Incompatible — asume ES 3.0.
- Rangos de versión actualizados.
- El indicador CPU muestra SSE/SSSE3/NEON según la arquitectura.

### 🐛 Correcciones
- ProgressDialog: ahora muestra mensajes largos sin cortarlos, con método para actualizar texto en vivo.
- Guardado de configuración de mods ahora atómico (tmp + `os.replace`) para evitar archivos corruptos.
# [3.0] - 2026-05-12 — The Qt6 Evolution

### 🔄 Framework: CustomTkinter → PySide6 (Qt6)
- Migración completa de toda la interfaz (19 archivos UI) de CustomTkinter a PySide6/Qt6.
- Las ventanas principales (`QMainWindow`), pestañas (`QWidget`) y diálogos (`QDialog`) ahora usan widgets Qt nativos.
- Los mensajes del sistema (`custom_dialogs.py`) reemplazaron los Tkinter messagebox por diálogos Qt temáticos.
- El sistema de imágenes migró de `CTkImage` a `QPixmap`/`QIcon` con caché centralizada.
- Los selectores de archivo migraron de `filedialog` a `QFileDialog`.
- El modelo de hilos migró a `QThread`/`QTimer`/`QProcess` para operaciones asíncronas.
- El sistema de estilos reemplazó los atributos de CustomTkinter por QSS (Qt Style Sheets) con selectores por ID.
- El tema oscuro usa `#242424` de fondo base con paneles `#3a3a3a` y acentos dinámicos.
- Dependencia eliminada: `customtkinter` → reemplazada por `PySide6`.
- Flatpak: actualizado de `org.kde.Platform//5.15` a `//6.10` (Qt6).

### ✨ Nuevas Funcionalidades

#### Google Play Integration
- Sistema completo de descarga desde Google Play: login vía `playdl-signin-ui-qt`, exploración de versiones con filtros Beta/Estables, descarga APK mediante `gplaydl`.
- Diálogo de instalación con dos pestañas: "Google Play" y "APK Local".
- Gestión de sesión: token guardado en `playdl.conf` con permisos `0o600`, detección de sesión alternativa vía `gplayver`.
- Mapeo de errores de Google Play traducibles a 7 idiomas.

#### Discord Rich Presence
- Integración completa vía `pypresence`: muestra "Explorando el launcher" en reposo y "Jugando {versión}" en juego con contador de tiempo.
- Activable desde el Play Tab y desde Ajustes.
- Client ID personalizable desde Ajustes (además del por defecto `1505628404362248213`).
- Permisos Flatpak para comunicación con Discord.

#### Gestor Avanzado de Versiones
- Nuevo diálogo para gestionar versiones instaladas: asignar iconos personalizados, ajustar posición/zoom, crear accesos directos `.desktop`, renombrar y eliminar carpetas, abrir directorios de datos y capturas.

#### Asistente de Migración (MigrationWizard)
- Reemplazado el antiguo `MigrationDialog` por un asistente de 5 pasos con tarjetas interactivas: Origen → Perfil → Contenido → Método → Resumen.
- +22 cadenas de texto traducidas a 7 idiomas.

#### Setup Wizard (Primer Inicio)
- Nuevo asistente de 7 pasos: Idioma → Términos → Migración → Estilo → Instalación → Changelog → Resumen.
- Flags CLI: `--first-wizard`, `--factory-reset`.

#### Changelog Dialog
- Nuevo diálogo que muestra el changelog en Markdown con cabecera de icono.

#### Update Checker
- Sistema de detección remota de actualizaciones. Consulta `version.json` en GitHub Pages al iniciar (máx. 1 vez/día) y muestra aviso si hay versión más reciente.
- Botón "Check Update (test)" en `--test-mode`.
- `version.json` soporta campo `prerelease`.
- Desplegado en `gh-pages`, compatible con GitHub Actions.

#### Gestor de Mods MCPELauncher
- Nueva pestaña "Mods MCPELauncher" en el Gestor de recursos.
- Escanea `mods/` en busca de `.so`; muestra tamaño, toggle activar/desactivar (`.so` ↔ `.so.disabled`) y eliminar.
- Importación de mods: file picker acepta `.so` (copia directa) y `.zip` (extrae los `.so` automáticamente).

#### Sistema de Advertencias de Compatibilidad
- Consulta remota de `version-warnings.json` en GitHub Pages.
- Muestra aviso en primer plano al instalar versiones con bugs conocidos, tanto en Google Play como en APK Local.
- El archivo JSON se actualiza remotamente sin necesidad de actualizar el launcher.

### 🎨 UI/UX y Personalización

#### Motor de Personalización
- Fondos de pantalla personalizados con control de opacidad.
- Sistema de marcas de agua (stickers) con opacidad y orden Z configurables.
- Transparencia dinámica por sección.
- Control de tamaño de iconos y títulos en las tarjetas de versión.
- Vista de lista o cuadrícula para el selector de versiones.

#### Temas de Color
- 12 temas profesionales: midnight, cherry, cyan, gray, ocean, orange, purple, red, yellow, más variantes claro/oscuro.
- Temas almacenados como JSON en `src/themes/`.
- Estilo QSS dinámico generado por `apply_theme_settings()` (~300 líneas).

#### Mejoras Visuales
- Tarjetas de versión con fondo sólido y etiquetas refinadas.
- Scrollbars consistentes en todas las secciones.
- Barra de pestañas centrada correctamente.
- Flecha de QComboBox renderizada correctamente (corregido el fallo del pseudo-triángulo CSS que se mostraba como "—").
- Layouts con limpieza optimizada de widgets sin fugas de memoria.

### 🧠 Arquitectura y Código

#### Reorganización del Código
- `constants.py` dividido en: `values.py` (modos/estilos), `config_keys.py` (claves de configuración), `ui_strings.py` (cadenas UI, +600 líneas).
- Nuevos módulos: `install_ops.py` (operaciones de instalación), `worker.py` (QThread genérico), `utils/colors.py` (utilidades de color).
- `app_logic.py` reducido de ~591 a ~338 líneas como fachada.
- Total: 45 archivos Python, ~9,660 líneas.

#### Optimizaciones de Rendimiento
- Carga de versiones asíncrona mediante QThread (elimina el bloqueo "Searching...").
- QSS global con selectores por ID elimina los congelamientos al cambiar de pestaña.
- Debounce de 100ms para reposicionamiento de overlays al redimensionar.
- Caché centralizada de imágenes (`ImageManager`) para minimizar E/S de disco.
- Las versiones se muestran en orden inverso (nuevas primero) con filtro "Estables" por defecto.
- Renderizado por lotes en lugar de actualizaciones individuales.

### ⚙️ Sistema de Compilación y Empaquetado

#### PyInstaller
- Spec actualizado: colección PySide6, import oculto `pypresence`, datos: `icon.png`, `src/langs`, `src/themes`, `Docs`.

#### Flatpak
- Runtime Qt6 (`org.kde.Platform//6.10` + `io.qt.qtwebengine.BaseApp//6.10`).
- Permisos: Discord IPC, red, sistema de archivos para migración.
- Variables de entorno: `QT_QPA_PLATFORMTHEME=kde`, `QT_STYLE_OVERRIDE=kvantum`.

#### CLI
- `--test-mode`, `--first-wizard`, `--factory-reset`, `--force-flatpak-ui`, `--force-nvidia-ui`.

### 🌐 Traducciones (i18n)
- 7 idiomas: español, inglés, francés, alemán, italiano, portugués, catalán.
- `LEGAL_TEXT` movido de archivos de idioma a constantes.py.
- Errores de Google Play traducibles en todos los idiomas.
- Sistema de traducción mediante monkey-patching de `constants` vía `language_manager.py`.

### 🐛 Correcciones
- **UI freezes eliminados:** Cambio de pestañas y carga de versiones ya no bloquean la interfaz.
- **"Searching..." corregido:** La lista de versiones ya no se queda cargando infinitamente.
- **Detección de runtimes Flatpak:** Ahora funciona desde dentro del sandbox.
- **execve fallback:** En equipos restrictivos, si falla el lanzamiento normal, reemplaza el proceso.
- **Señales de checkbox:** Actualizadas con `Qt.Checked.value` para compatibilidad PySide6 reciente.
- **Sincronización de ajustes:** GameMode y Cerrar-al-iniciar ahora sincronizados entre pestañas.
- **Alpha de Qt:** Corregido rango de 0.0-1.0 (Tkinter) a 0-255 (Qt).
- **Clave "Blur" residual:** Eliminada de configuración (feature roto).
- **Importaciones faltantes:** `json`, `platform`, `shlex` restauradas tras la migración.

### 🚀 Soporte y Compatibilidad
- **Nvidia Prime/Zink:** Gestión limpia de variables de entorno con opciones separadas.
- **GameMode:** Soporte completo con sincronización entre tabs.
- **Variables de entorno personalizadas:** Configurables desde Ajustes.
- **Verificador de dependencias:** Compatible con Flatpak.
- **Verificador de hardware:** Ahora funciona dentro de Flatpak.
- **Selector de modo de gráficos:** En el Configurador de Juego.

### 🗑️ Archivos Eliminados
- `src/gui/migration_dialog.py` (317 líneas, reemplazado por `migration_wizard.py`).
- Tkinter font tuples en `constants.py`.
- Blur config keys (feature roto).

### 📦 Archivos Nuevos (v3.0)
| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `src/core/google_integration.py` | 602 | Google Play login/download |
| `src/core/discord_rpc.py` | 193 | Discord Rich Presence |
| `src/core/config_keys.py` | 91 | Claves de configuración |
| `src/core/values.py` | 22 | Constantes de modo/estilo |
| `src/core/ui_strings.py` | 609 | Cadenas de interfaz |
| `src/core/install_ops.py` | 304 | Operaciones de instalación |
| `src/core/worker.py` | 22 | QThread worker genérico |
| `src/utils/colors.py` | 21 | Utilidades de color |
| `src/gui/setup_wizard.py` | ~450 | Asistente de primer inicio |
| `src/gui/migration_wizard.py` | 828 | Asistente de migración |
| `src/gui/changelog_dialog.py` | ~100 | Diálogo de changelog |
| `src/gui/version_manager_dialog.py` | 364 | Gestor avanzado de versiones |

# [2.2] - 2026-03-01 - Management Update
- **NEW:** Soporte multiperfil disponible para aislar tus mundos, recursos y configuraciones de Minecraft en diferentes perfiles mediante enlaces simbólicos (Symlink).
- **NEW:** Se cambiarón los dialogos genericos de Tkinter por unos más temáticos con la interfaz usando el mismo CustomTkinter.
- **NEW:** Gestor de recursos disponible para gestionar tus recursos de Minecraft de manera eficiente. Puedes importar, eliminar, activar/desactivar tus ResourcesPack (RP), BehaviorPacks (BP) y tus mundos donde tambien puedes exportarlos facilmente.
- **SOPORTE:** Tiene soporte para leer archivos en diferentes formatos (.mcpack, .mcaddon, .mcworld, .mcworldtemplate). Resuelve la ubicación del tipo de addon y en el caso de que no pueda, se puede ajustar manualmente. Ademas tambien muestra el nombre del addon real si esta dentro de archivos `.lang`.
- **FIX:** Se optimizó el sistema de renderizado a uno por lotes y caché para un desplazamiento fluido.
- **FIX:** El botón "Fix Shaders" se corrigió a "Desactivar Shaders" siendo el terminó más correcto. Además que se agrego la opción de modificar el modo de graficos desde el *Configurador de juego* disponible en herramientas.
- **FIX:** Ahora el resolvedor de las claves internas tendra en cuenta `cianovalauncher-config.json` a la hora de actualizar los datos.

# [v2.1.1] - 2026-02-25
- **FIX:** Se corrigio un error que provocaba que los usuarios de config anterior no podian cargar correctamente la ruta de binarios de Flatpak correctamente.
- **CODE FIX:** Se cambio para que el launcher pueda cambiarse la descripción de la versión desde constant.py.

# [v2.1] - 2026-02-17 - UserUI Update
- **NEW:** Se puede personalizar la IU con diferentes tonos de colores, modo claro/oscuro, tamaño de iconos y texto.
- **NEW HELLO:** Ahora esta la posibilidad de cambiar el idioma (Actualmente esta Ingles y Español).
- **SUPPORT:** Ahora esta separado las opciones de Nvidia y Zink, ademas de la posibilidad de colocar argumentos de entorno. ¡Ahora incluye gamemode!
- **FIX:** Se ajusto de mejor manera la IU para el instalador de APKs y se mejoro ligeramente el rendimiento para toda la IU en general.
- **FIX:** Ahora la IU y secciones no dependen de *strings* para la logica.
- **FIX:** Ahora permite ver los requisitos de hardware dentro de Flatpak tambien para darte un rango de versiones compatibles.

# [v2.0e] - 2026-01-15
- **SUPPORT:** Hay una nueva opción en ajustes para los usuarios de Nvidia con tarjeta dedicada que intentara usar Zink para darle uso (Tal como dice el boton es experimental).

# [v2.0d] - 2026-01-13
- **BUG FIX:** Ahora el launcher se asegura de tener por defecto "Local (Propio)" cuando esta dentro de Flatpak y tiene una verificación al ejecutar que tratara de evitar que se ejecute accidentalmente de nuevo el launcher en lugar del mcpelauncher.

# [v2.0c] - 2026-01-07
- **SUPPORT:** Si no encuentra flatpak-spawn usara el cmd local para hacer un subproceso entonces se reemplazara el proceso para ejecutar el juego con exec.

# [v2.0b] - 2026-01-05
- **BUG FIX:** flatpak-spawn.

# [v2.0a] - 2026-01-05
- **CHANGES:** Mejor distribución del codigo fuente, ahora esta todo el codigo fuente en la carpeta `src`.
- **BUG FIXES:** Solución de bugs que impedian usar correctamente el launcher.
- **MAJOR UPDATES:** Ahora se puede utilizar los selectores nativos del sistema en lugar de los por defecto en Tkinter.
- **libsqliteX.so:** ya puede encontrar el lib necesario dependiendo de la arquitectura correctamente.

# [v2.0] - 2026-01-02
- **Nombre nuevo:** Ahora pasara de MCPETool a la naturaleza de un launcher llamado **CianovaLauncher**.
- **Nuevas herramientas:** Migración, Acceso directo en el menú de inicio.
- Añadidos en Sección Ajustes y Acerca de.
- Independencia para usar binarios personalizados.
- Icono nuevo para el launcher.
- Detectar Flatpak (Custom).

# [v1.1.0] - 2025-12-03
- **Interfaz Rediseñada:** Nuevo look minimalista con bordes redondeados y mejor espaciado.
- **Selector de Versiones Visual:** Reemplazado el sistema de "puntos" por tarjetas interactivas. Detección inteligente de la versión real dentro de la carpeta `current`.
- **Verificador de Dependencias:** Nueva herramienta para comprobar si tu instalación de Flatpak tiene los runtimes necesarios.
- **Instalador Inteligente:** Detecta la arquitectura del APK antes de instalar y muestra advertencias.
- **Icono del Programa:** Se ha integrado el icono oficial.

# [v1.0.0] - Versión Inicial
- Lanzamiento inicial de la herramienta GUI.
- Funciones básicas: Lanzar juego, instalar APK, exportar mundos.
