# 📘 MANUAL DE USO - CianovaLauncher v3.1

**Versión:** 3.1
**Desarrollador:** @PlaGaPlusDev, @Leimsoto y @DarkAnubis0100

---

## 🌟 1. Introducción
**CianovaLauncher** es una interfaz gráfica para gestionar Minecraft: Bedrock Edition en Linux. Trabaja con los binarios del proyecto **MCPELauncher-manifest** para instalar, lanzar y personalizar el juego.

Migrado a **PySide6 (Qt6)** desde la versión 3.0, ofrece una interfaz fluida con soporte HiDPI, temas, fondos personalizados y traducción a 7 idiomas.

> 🌐 Página web: [cianovateam.github.io/CianovaLauncher-mcpelauncher](https://cianovateam.github.io/CianovaLauncher-mcpelauncher/)

---

## 🚀 2. Instalación

### Flatpak (Recomendado)

**Express:**
```bash
curl -fsSL https://raw.githubusercontent.com/CianovaTeam/CianovaLauncher-mcpelauncher/gh-pages/install.sh | bash
```

**Repositorio (actualizaciones automáticas):**
```bash
flatpak remote-add --user --if-not-exists CianovaLauncher https://cianovateam.github.io/CianovaLauncher-mcpelauncher/CianovaLauncher.flatpakrepo
flatpak install --user CianovaLauncher org.cianova.Launcher
```

**Bundle:**
```bash
flatpak install --user CianovaLauncher.flatpak
```

**Runtums necesarios:**
```bash
flatpak install org.kde.Platform//6.10 io.qt.qtwebengine.BaseApp//6.10
```

### Versión portátil
Descarga `CianovaLauncher-vX.Y.tar.gz` de **Releases**, extrae y coloca los binarios de MCPELauncher en `bin/`. Ejecuta:
```bash
./CianovaLauncher.sh
```

### Desde código fuente
```bash
pip install PySide6 Pillow
./run.sh
```

---

## 🎮 3. Pestaña JUGAR

### Selector de Versiones
Muestra las versiones instaladas como tarjetas o lista (configurable en Ajustes). Las más recientes aparecen primero. Usa el menú desplegable para filtrar entre todas, solo estables o solo betas.

Cada tarjeta muestra el nombre, versión, y tiene un menú contextual (clic derecho o botón 🗑️) para:
- **Renombrar** la carpeta de la versión.
- **Cambiar icono** (imagen personalizada).
- **Crear acceso directo** en el menú de inicio.
- **Abrir carpeta de datos** o **capturas**.
- **Mover a respaldo** o **eliminar permanentemente**.

### Perfiles
Los perfiles aíslan mundos, ajustes y servidores. Al crear el primer perfil los datos existentes se migran al perfil `default`. Puedes crear, renombrar y eliminar perfiles desde el gestor (icono ⚙️ junto al selector).

### Mods MCPELauncher
Los mods `.so` se escanean desde `mods/`. Cada mod puede:
- **Activarse/desactivarse** (renombra a `.so.disabled`).
- **Marcarse para cargar al inicio** con el checkbox "Cargar al inicio". El estado persiste entre sesiones.

### Mod DRM (mcpelauncher-updates)
Necesario para versiones ≥ 1.21.30 instaladas desde Google Play. Si falta al lanzar, el launcher pregunta si instalarlo. Si está desactivado, muestra una advertencia. Puedes gestionarlo desde el Gestor de Recursos > pestaña Mods.

### Comportamiento al iniciar el juego
Tres modos (configurables desde Ajustes > Lanzamiento y desde el Play Tab):
- **Cerrar:** el launcher se cierra al abrir el juego.
- **Ocultar:** minimiza a la bandeja del sistema; la ventana reaparece al salir del juego.
- **Ninguno:** muestra "▶ En juego" en la interfaz.

---

## 🛠️ 4. Pestaña HERRAMIENTAS

### Instalación
**Google Play:** inicia sesión, selecciona versión (con filtro Estables/Betas), descarga e instala automáticamente.
**APK Local:** selecciona un `.apk`; el launcher verifica compatibilidad de arquitectura antes de instalar.

### Gestor de Recursos (Addons)
4 pestañas:

**Mundos:** importa/exporta mundos en `.mcworld`. Soporta `.mctemplate` y `.mcworldtemplate`.

**Resource Packs (RP):** importa `.mcpack`, activa/desactiva packs.

**Behavior Packs (BP):** similar a RP, con detección automática del tipo.

**Mods MCPELauncher:** gestiona mods `.so`:
- Activar/desactivar y eliminar.
- Checkbox "Cargar al inicio" por mod.
- **Mods disponibles:** presiona "↻ Actualizar lista de mods" para ver los modos del repositorio oficial [mcpelauncher-moddb](https://github.com/minecraft-linux/mcpelauncher-moddb) (zoom, fullbright, legacy, etc.) e instalarlos con un clic.
- Estado del mod DRM con botón de instalar o activar.

Cada pestaña tiene un botón "📂 Abrir carpeta".

### Otras herramientas
- **Configurador de Juego:** editor visual de ajustes básicos (FOV, vsync, distancia de renderizado, audio, controles, etc.).
- **Disable Shaders:** restablece los ajustes de video a modo compatible.
- **Creador de Skin Packs:** crea packs `.mcpack` desde imágenes PNG.
- **Migración de Datos:** asistente de 5 pasos para migrar desde otros launchers.
- **Verificador de Requisitos:** analiza CPU, GPU, OpenGL ES y RAM; muestra un rango de versiones recomendado.
- **Verificador de Dependencias:** comprueba librerías del sistema según tu gestor de paquetes.

---

## ⚙️ 5. Pestaña AJUSTES

Organizados en 4 categorías con pestañas en la parte superior.

### General
- **Perfiles:** selector y gestor de perfiles.
- **Acciones:** botones para guardar configuración y restaurar valores por defecto.

### Lanzamiento
- **Binarios:** selector de modo (Sistema, Local, Flatpak, Personalizado), ID de Flatpak, y rutas individuales para: cliente (`game`), extractor APK, interfaz de login de Google (`signin-ui`), `gplaydl`, `gplayver`, webview, error handler y `msa-daemon`.
- **Compatibilidad:**
  - **GameMode:** activa `gamemoderun` al lanzar el juego.
  - **Nvidia Prime:** fuerza el uso de la GPU Nvidia en sistemas híbridos.
  - **Zink:** ejecuta OpenGL sobre Vulkan (útil para Nvidia en Flatpak).
  - **LaunchAction:** elige entre Cerrar, Ocultar o Ninguno al iniciar el juego.
  - **Variables de entorno personalizadas:** define variables y argumentos adicionales.

### Apariencia
- **Tema de color:** 12 combinaciones (azul, verde, rojo, naranja, morado, amarillo, azul oscuro, gris, cian, medianoche, cereza, océano).
- **Modo visual:** claro, oscuro o seguir al sistema.
- **Estilo de lista:** lista o cuadrícula para las versiones.
- **Diseño de herramientas:** una columna, dos columnas o cuadrícula.
- **Tamaño de icono y título** en las tarjetas de versión.
- **Escalado de interfaz (DPI).**
- **Opacidad de sección:** controla la transparencia de los paneles.
- **Fondo de pantalla:** imagen con control de posición, zoom y opacidad.
- **Marca de agua (sticker):** texto o imagen en las esquinas, con opacidad y posición ajustables.

### Integraciones
- **Discord Rich Presence:** muestra "Explorando el launcher" en reposo y "Jugando {versión}" en juego con contador de tiempo. Incluye campo para Client ID personalizado.

---

## 🔄 6. Setup Wizard (Primer Inicio)
Al ejecutar el launcher por primera vez (o con `--first-wizard`), un asistente de 7 pasos guía al usuario:
1. **Idioma**
2. **Términos legales**
3. **Migración** (opcional)
4. **Estilo** (tema y modo claro/oscuro)
5. **Instalación** (descargar Minecraft ahora o después)
6. **Changelog** (novedades de la versión)
7. **Resumen** (primeros pasos)

---

## 🔔 7. Update Checker
Consulta `version.json` en GitHub Pages al iniciar (máx. 1 vez al día). Si hay una versión más reciente, muestra un aviso con enlace.

---

## 🌐 8. Traducciones
7 idiomas: español, inglés, francés, alemán, italiano, portugués y catalán.

---

## ⚠️ 9. Solución de Problemas
- **¿La lista de versiones no carga?** Verifica la conexión o cambia el filtro.
- **¿El juego parpadea o se cierra?** Activa **Modo Zink** en Ajustes > Lanzamiento.
- **¿No inicia la sesión de Google?** Revisa la ruta del binario `signin-ui` en Ajustes > **Lanzamiento** > Binarios.
- **¿Error de DRM al lanzar?** Asegúrate de que el mod DRM esté instalado y activo en Gestor de Recursos > Mods.
- **¿El launcher no abre?** Prueba con `--factory-reset` para restaurar la configuración.

---

*Hecho con ❤️ por y para la comunidad de Linux.*
