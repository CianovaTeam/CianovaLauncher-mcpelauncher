# 📝 Changelog - CianovaLauncher

# [3.0] - 2026-05-12 - The Qt6 Evolution
- **MAJOR UPDATE:** Migración completa de la interfaz de **CustomTkinter a PySide6 (Qt6)**. Esto mejora drásticamente la fluidez, el soporte para pantallas de alta resolución y la estabilidad general de la aplicación.
- **NEW:** Sistema de descarga de versiones desde Google Play integrado. Ahora puedes buscar y descargar versiones oficiales directamente desde el launcher (requiere login previo).
- **NEW:** Discord Rich Presence opcional. Muestra en Discord qué versión de Minecraft Bedrock estás jugando con contador de tiempo. Se activa desde Ajustes > Compatibilidad o en el Play Tab.
- **NEW:** Gestor Avanzado de Versiones: Ahora puedes asignar iconos personalizados a cada versión instalada, ajustar su posición/zoom y crear accesos directos individuales (`.desktop`) en tu menú de inicio.
- **NEW:** Motor de Personalización Extendido: Añadido soporte para fondos de pantalla personalizados con opacidad dinámica, marcas de agua (stickers) y ajuste de transparencia en los paneles.
- **NEW:** Se añadieron 12 temas de colores profesionales (Midnight, Cherry, Ocean, etc.) y la posibilidad de elegir entre vista de Lista o Cuadrícula para el selector de versiones.
- **NEW:** Reorganización completa del código del launcher. El archivo principal se dividió en 7 módulos más pequeños para que sea más fácil de mantener y añadir nuevas funciones.
- **FIX:** Reestructuración total de la carga de versiones mediante señales asíncronas (QThread), eliminando el bloqueo permanente en "Searching..." y optimizando el rendimiento.
- **FIX:** Ahora las versiones se muestran en orden inverso (las más nuevas primero) y el filtro predeterminado es "Estables" para acelerar la carga inicial.
- **FIX:** Se corrigió la ruta donde se guardan los archivos de sesión de Google para que funcione correctamente dentro de Flatpak.
- **FIX:** Se restauró la detección de sesión de Google mediante el binario gplayver por si falla la lectura de archivos.
- **FIX:** Se corrigió el nombre del archivo de configuración de dispositivo que se generaba como "cianova-device.conf" en lugar de "device.conf".
- **FIX:** Se corrigió la detección de runtimes Flatpak para que funcione estando dentro del sandbox.
- **FIX:** Los mensajes de error de descarga de Google Play ahora se pueden traducir a diferentes idiomas.
- **FIX:** En equipos muy restrictivos, si el launcher no puede abrir el juego con el método normal, ahora lo intenta reemplazando el proceso directamente (execve).
- **FIX:** Se solucionó un problema donde al hacer clic en las tarjetas de versión se podían producir artefactos visuales al mover la ventana.
- **FIX:** Se mejoró la suavidad del movimiento de los overlays (fondo y sticker) al redimensionar la ventana.
- **SUPPORT:** Mejora en las opciones de compatibilidad para Nvidia y Zink, incluyendo una gestión más limpia de argumentos de entorno y variables personalizadas.
- **SUPPORT:** Se añadieron los permisos necesarios para que Discord Rich Presence funcione dentro de Flatpak.

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
