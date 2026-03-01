# 📝 Changelog - CianovaLauncher

# [2.2] - 2026-03-01 - Management Update
**NEW:** Soporte multiperfil disponible para aislar tus mundos, recursos y configuraciones de Minecraft en diferentes perfiles mediante enlaces simbólicos (Symlink).
**NEW:** Se cambiarón los dialogos genericos de Tkinter por unos más temáticos con la interfaz usando el mismo CustomTkinter.
**NEW:** Gestor de recursos disponible para gestionar tus recursos de Minecraft de manera eficiente. Puedes importar, eliminar, activar/desactivar tus ResourcesPack (RP), BehaviorPacks (BP) y tus mundos donde tambien puedes exportarlos facilmente.
  **SOPORTE:** Tiene soporte para leer archivos en diferentes formatos (.mcpack, .mcaddon, .mcworld, .mcworldtemplate). Resuelve la ubicación del tipo de addon y en el caso de que no pueda, se puede ajustar manualmente. Ademas tambien muestra el nombre del addon real si esta dentro de archivos `.lang`.
**FIX:** Se optimizó el sistema de renderizado a uno por lotes y caché para un desplazamiento fluido.
**FIX:** El botón "Fix Shaders" se corrigió a "Desactivar Shaders" siendo el terminó más correcto. Además que se agrego la opción de modificar el modo de graficos desde el *Configurador de juego* disponible en herramientas.
**FIX:** Ahora el resolvedor de las claves internas tendra en cuenta `cianovalauncher-config.json` a la hora de actualizar los datos

# [v2.1.1] - 2026-02-25
**FIX:** Se corrigio un error que provocaba que los usuarios de config anterior no podian cargar correctamente la ruta de binarios de Flatpak correctamente
**CODE FIX:** Se cambio para que el launcher pueda cambiarse la descripción de la versión desde constant.py

# [v2.1] - 2026-02-17 - UserUI Update
**NEW:** Se puede personalizar la IU con diferentes tonos de colores, modo claro/oscuro, tamaño de iconos y texto.
**NEW HELLO:** Ahora esta la posibilidad de cambiar el idioma (Actualmente esta Ingles y Español)
**SUPPORT:** Ahora esta separado las opciones de Nvidia y Zink, ademas de la posibilidad de colocar argumentos de entorno. ¡Ahora incluye gamemode!
**FIX:** Se ajusto de mejor manera la IU para el instalador de APKs y se mejoro ligeramente el rendimiento para toda la IU en general.
**FIX:** Ahora la IU y secciones no dependen de *strings* para la logica.
**FIX:** Ahora permite ver los requisitos de hardware dentro de Flatpak tambien para darte un rango de versiones compatibles.


# [v2.0e] - 2026-01-15
**SUPPORT** Hay una nueva opción en ajustes para los usuarios de Nvidia con tarjeta dedicada que intentara usar Zink para darle uso (Tal como dice el boton es experimental).

# [v2.0d] - 2026-01-13
**BUG FIX** Ahora el launcher se asegura de tener por defecto "Local (Propio)" cuando esta dentro de Flatpak y tiene una verificación al ejecutar que tratara de evitar que se ejecute accidentalmente de nuevo el launcher en lugar del mcpelauncher.

# [v2.0c] - 2026-01-07
**SUPPORT** Si no encuentra flatpak-spawn usara el cmd local para hacer un subproceso entonces se reemplazara el proceso para ejecutar el juego con exec.

# [v2.0b] - 2026-01-05
- **BUG FIX** flatpak-spawn

# [v2.0a] - 2026-01-05
### CHANGES:
- **Mejor distribución del codigo fuente** ahora esta todo el codigo fuente en la carpeta `src`
- **BUG FIXES** Solución de bugs que impedian usar correctamente el launcher
- **MAJOR UPDATES** Ahora se puede utilizar los selectores nativos del sistema en lugar de los por defecto en Tkinter
- **libsqliteX.so** ya puede encontrar el lib necesario dependiendo de la arquitectura correctamente.

# [v2.0] - 2026-01-02
### ✨Novedades:
- **Nombre nuevo:** Ahora pasara de MCPETool a la naturaleza de un launcher llamado **CianovaLauncher**
- **Nuevas herramientas:** Migración, Acceso directo en el menú de inicio
- Añadidos en Sección Ajustes y Acerca de
- Independencia para usar binarios personalizados
- Icono nuevo para el launcher
- Detectar Flatpak (Custom)

Para mas información de las herramientas consulte el ***Manual.***

### ⚙️ Mejoras Técnicas
- Mejoras en verificador de dependencias.
- Mejoras en la calidad de la GUI.
- Capacidad de guardar configuraciones.
## [v1.1.0] - 2025-12-03
### ✨ Novedades
*   **Interfaz Rediseñada:** Nuevo look minimalista con bordes redondeados y mejor espaciado.
*   **Selector de Versiones Visual:**
    *   Reemplazado el sistema de "puntos" por tarjetas interactivas.
    *   Detección inteligente de la versión real dentro de la carpeta `current`.
*   **Verificador de Dependencias:** Nueva herramienta para comprobar si tu instalación de Flatpak tiene los runtimes necesarios (`org.kde.Platform`, etc.).
*   **Instalador Inteligente:**
    *   Ahora detecta la arquitectura del APK antes de instalar.
    *   Muestra una advertencia en **ROJO** si el APK es incompatible con tu PC (ej. APK de ARM en PC x86).
*   **Icono del Programa:** Se ha integrado el icono oficial en la ventana y en el ejecutable compilado.

### 🔧 Mejoras Técnicas
*   **Portabilidad:** El ejecutable final ahora es totalmente autocontenido ("One-File"), incluyendo todos los recursos e iconos.
*   **Optimización:** El launcher se cierra automáticamente al iniciar el juego (opcional) para liberar RAM.
*   **Correcciones:**
    *   Arreglado bug donde la terminal se quedaba colgada al lanzar el juego.
    *   Mejorada la detección de rutas para instalaciones Flatpak vs Compiladas.

---

## [v1.0.0] - Versión Inicial
*   Lanzamiento inicial de la herramienta GUI.
*   Funciones básicas: Lanzar juego, instalar APK, exportar mundos.
