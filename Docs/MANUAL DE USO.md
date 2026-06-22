# 📘 MANUAL DE USO - CianovaLauncher v3.0

**Versión:** 3.0 (Edición PySide6)
**Desarrollador:** @PlaGaDev

---

## 🌟 1. Introducción
**CianovaLauncher** es una interfaz gráfica diseñada para facilitar la gestión de Minecraft: Bedrock Edition en sistemas Linux. Este proyecto nace con la intención de ofrecer una herramienta visual amigable que trabaje en conjunto con el proyecto **MCPELauncher-manifest**, centralizando funciones de instalación, ejecución y personalización en un solo lugar.

Originalmente desarrollado con *CustomTkinter*, esta versión 3.0 ha sido migrada a **PySide6 (Qt6)** para mejorar la estabilidad general, el manejo de procesos y ofrecer una interfaz más fluida y adaptable a diferentes pantallas. Este launcher no busca competir, sino sumar una opción más a la comunidad, respetando y valorando siempre el trabajo de otros desarrolladores del ecosistema.

> 🌐 Si quieres una vista rápida y visual antes de instalar, el proyecto tiene una **página web oficial** con resumen de características, métodos de descarga y preguntas frecuentes: [plagaplusdev.github.io/CianovaLauncher-mcpelauncher](https://plagaplusdev.github.io/CianovaLauncher-mcpelauncher/)

---

## 🚀 2. Primeros Pasos: Instalación

### Opción A: Instalación por Flatpak (Recomendado)
Flatpak ofrece un entorno aislado y seguro, ideal para asegurar que todas las librerías de Qt6 funcionen correctamente.

#### Método 1: Instalación Express (Un solo comando)
La forma más rápida si ya tienes Flatpak en tu sistema. Un script automatizado añade el repositorio de Cianova, instala los runtimes Qt6 necesarios y deja el launcher instalado y listo, sin pasos manuales.
 
```bash
curl -fsSL https://raw.githubusercontent.com/PlaGaPlusDev/CianovaLauncher-mcpelauncher/gh-pages/install.sh | bash
```
 
El script verifica que Flatpak esté disponible; si no lo está, te indica cómo instalarlo según tu distribución (Debian/Ubuntu, Fedora, Arch, openSUSE). Puedes [revisar su código en GitHub](https://github.com/PlaGaPlusDev/CianovaLauncher-mcpelauncher/blob/gh-pages/install.sh) antes de ejecutarlo.

#### Método 2: Repositorio Oficial (Recomendado para actualizaciones)
Al usar el repositorio, recibirás las actualizaciones automáticamente desde tu gestor de software.
1. **Añade el repositorio:**
   ```bash
   flatpak remote-add --user --if-not-exists CianovaLauncher https://plagaplusdev.github.io/CianovaLauncher-mcpelauncher/CianovaLauncher.flatpakrepo
   ```
2. **Instala el Launcher:**
   ```bash
   flatpak install --user CianovaLauncher org.cianova.Launcher
   ```

#### Método 3: Archivo Bundle (.flatpak)
Si has descargado el archivo `.flatpak` directamente desde **Releases**:
1. **Instala el archivo:**
   ```bash
   flatpak install --user CianovaLauncher.flatpak
   ```


### Importante (Runtimes): Si instalas por el metodo 2 y 3, asegúrate de tener los runtimes necesarios instalados:
   ```bash
   flatpak install org.kde.Platform//6.10 io.qt.qtwebengine.BaseApp//6.10
   ```

---

### Opción B: Versión Compilada (Ejecución Portátil)
Ideal para quienes no desean instalar paquetes en el sistema y prefieren mantener todo en una carpeta.
1. Descarga el archivo `CianovaLauncher-vX.Y.tar.gz` de la última **RELEASE** y extráelo.
2. **Preparación de Binarios:** Consigue los binarios del proyecto oficial **MCPELauncher-manifest** (puedes compilarlos o usar packs de confianza).
3. **Ubicación:** Crea una carpeta llamada `bin/` dentro de la raíz del launcher y coloca allí los ejecutables (`mcpelauncher-client`, `extractor`, etc.).
4. **Ejecución:** Haz doble clic en `CianovaLauncher.sh` o ejecútalo desde la terminal:
   ```bash
   ./CianovaLauncher.sh
   ```
   *Nota: En esta versión, las librerías necesarias suelen estar pre-incluidas localmente en la raíz.*

---

### Opción C: Ejecución desde el Código Fuente
Para usuarios avanzados o desarrolladores que deseen colaborar con el proyecto.
1. **Clonar y Entorno:** Clona el repositorio e instala las dependencias de Python:
   ```bash
   pip install PySide6 Pillow
   ```
2. **Ejecutar:** Inicia el launcher usando el script de desarrollo:
   ```bash
   ./run.sh
   ```
   *(Este script activa el entorno virtual si existe y ejecuta src/main.py)*

---

## ⚙️ Post-Instalación
Independientemente del método elegido, se recomienda:
- Usar el **Verificador de requisitos** para conocer tu rango de compatibilidad.
- Revisar el **Verificador de dependencias** (especialmente en versiones No-Flatpak) para asegurar que tu distribución (Ubuntu, Mint, Debian, Arch, etc.) tenga las librerías necesarias.
- Configurar y guardar las rutas de tus binarios en la pestaña **Ajustes**.

---
## 🎮 3. Pestaña Principal: JUGAR

### 👤 Gestión de Perfiles
Para ayudar a mantener tus datos organizados, CianovaLauncher permite crear perfiles independientes. Esto es útil para separar, por ejemplo, un mundo de supervivencia de uno con muchos packs de texturas.
- **¿Cómo funciona?** Cada perfil tiene su propia carpeta que se conecta automáticamente cuando lo seleccionas. Esto mantiene aislados tus mundos, servidores y el archivo de configuración `options.txt`.
- **Nota:** Al usar perfiles por primera vez, el launcher moverá tus datos actuales al perfil `default` de forma segura.

### 🗂️ Selector de Versiones
- **Vistas:** Puedes elegir entre ver tus versiones como una lista sencilla o como una cuadrícula de tarjetas en la pestaña de Ajustes.
- **Orden:** Por comodidad, las versiones instaladas más recientemente aparecerán al principio de la lista.
- **Detección:** El indicador flotante te ayudará a saber en todo momento si el launcher está leyendo los datos de tu carpeta local o de la instalación de Flatpak.

---

## 🛠️ 4. Pestaña: HERRAMIENTAS

Aquí encontrarás pequeñas utilidades para facilitar el mantenimiento del juego:

### 1. Instalación y Gestión
*   **Instalar Versión (Google Play):** Permite descargar APKs oficiales de forma directa. Para usarlo, primero utiliza el botón de login; una vez que tu sesión esté activa, podrás elegir la versión que desees bajar.
*   **Instalar APK Local:** Útil si ya tienes el archivo `.apk`. El launcher verificará si es compatible con la arquitectura de tu PC (x86_64) para evitar errores de instalación.
*   **Gestor Avanzado de Versiones (Icono 🗑️):** Desde aquí puedes renombrar carpetas, eliminar versiones que ya no uses o incluso subir un icono personalizado para que cada versión se vea única en el launcher.

### 2. Personalización y Archivos
*   **Gestor de recursos:** Una herramienta para importar archivos `.mcpack` o `.mcworld` y activar/desactivar complementos (Addons) sin necesidad de borrarlos.
*   **Configurador de Juego:** Un pequeño editor para cambiar ajustes básicos (como el campo de visión o la sincronización vertical) de forma visual antes de abrir el juego.
*   **Disable Shaders:** Si el juego no inicia por algún problema con los gráficos, este botón restablece los ajustes de video a un modo compatible.

---

## ⚙️ 5. Pestaña: AJUSTES

### ⚡ Compatibilidad y Rendimiento
*   **Nvidia Prime / Modo Zink:** Opciones diseñadas para mejorar la experiencia en equipos con tarjetas Nvidia, ayudando a evitar errores gráficos comunes en Linux (como el parpadeo o cierres inesperados).
*   **GameMode:** Si tienes instalado `gamemode` en tu sistema, el launcher puede activarlo automáticamente para dar prioridad al proceso del juego.

### 🎨 Personalización Visual
Gracias a la base en Qt6, puedes ajustar el launcher a tu gusto:
- **Temas:** Dispones de 12 combinaciones de colores.
- **Fondo:** Puedes poner una imagen de fondo y ajustar qué tan transparente quieres que se vea la interfaz sobre ella.
- **Marcas de agua:** Opción para añadir un pequeño texto o imagen de tu elección en las esquinas.

---

## ℹ️ 6. Ayuda y Sistema
*   **Verificador de Requisitos:** Te indica qué versiones de Minecraft podrían funcionar mejor según las capacidades de tu procesador y tarjeta gráfica.
*   **Verificador de Dependencias:** Te avisa si faltan librerías en tu sistema para que todo funcione correctamente.

---

## ⚠️ 7. Solución de Problemas
-   **¿La lista de versiones no carga?** Verifica tu conexión a internet o intenta cambiar el filtro (Estable/Beta).
-   **¿El juego parpadea o se cierra?** Prueba activando el **Modo Zink** en la pestaña de Ajustes.
-   **¿No inicia la sesión de Google?** Asegúrate de tener configurado el binario de login correctamente en los Ajustes.

---
*Hecho con ❤️ por y para la comunidad de Linux.*
