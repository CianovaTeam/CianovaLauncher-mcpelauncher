# <img src="icon.png" width="48" height="48"> CianovaLauncher v2.2
### Nota está rama es para la versión Qt5

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blue?style=for-the-badge)](https://github.com/TomSchimansky/CustomTkinter)
[![Flatpak](https://img.shields.io/badge/Platform-Flatpak-316dad?style=for-the-badge&logo=flatpak&logoColor=white)](https://flatpak.org/)
[![Linux](https://img.shields.io/badge/OS-Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)](https://www.kernel.org/)
[![License](https://img.shields.io/badge/License-GPL%20v3-red?style=for-the-badge)](LICENSE)

**CianovaLauncher** es una interfaz gráfica moderna diseñada para facilitar la gestión, instalación y personalización de **Minecraft: Bedrock Edition** en Linux. Esta herramienta trabaja en conjunto con la base del proyecto **MCPELauncher-manifest**, proporcionando una experiencia de usuario amigable y potente.

---

## ✨ Características de la v2.1 y v2.2
### 👤 Gestión Multiperfil Inteligente
Aísla completamente tus entornos de juego. Crea perfiles específicos para "Survival", "Creativo" o "Packs de Texturas" sin conflictos.
- **Migración Automática:** Si vienes de versiones anteriores, tus datos se mueven al perfil `default` sin perder nada.
- **Aislamiento Total:** Cada perfil tiene sus propios mundos, ajustes (`options.txt`) y servidores.

### 📦 Gestor de Complementos (Addons)
Una herramienta integral para administrar el contenido del juego:
- **Soporte de Formatos:** Importa `.mcpack`, `.mcaddon`, `.mcworld` y `.mcworldtemplate` con un clic.
- **Extracción de Metadatos:** Lee el `manifest.json` y archivos `.lang` para mostrar nombres reales e iconos, incluso si están cifrados o usan claves de traducción.
- **Control de Estado:** Activa o desactiva packs sin necesidad de borrarlos.

### 🚀 Rendimiento y Gráficos
- **Optimización Nvidia:** Soporte nativo para Nvidia Prime y capa de compatibilidad **Zink** para solucionar errores de drivers en Flatpak.
- **GameMode:** Prioriza el proceso de Minecraft sobre otras aplicaciones del sistema.
- **Verificador de Hardware:** Analiza tu CPU y GPU para recomendarte la mejor versión compatible.

## 1. Ejecución

### Requisitos Previos

**NOTA:** Antes de cualquier instalación por **Flatpak** recuerda instalarlo en el caso de que no lo tengas.
Link para configurar Flatpak la primera vez según tu distro: [FLATPAK SETUP](https://flathub.org/en/setup)
**NOTA 2:** Tu PC debe soportar instrucciones x86_64 y tener **OpenGLES 3.0** para las versiones modernas de Minecraft Bedrock.
**NOTA 3:** Si tu distro es muy estricto con permisos y no tiene `flatpak-spawn` va a hacer un subproceso local o reemplazar el proceso del launcher (Solo usara los binarios disponibles en el Flatpak. Si no es muy estricto tipo Ubuntu, Mint, Debian, Arch, ZorinOS funcionara completamente.)

### Instalación para Flatpak

#### Metodo 1 (Recomendado) - Actualizaciones

Descarga el archivo `CianovaLauncher.flatpakrepo` en **RELEASES** o **EXTRA** para instalar y recibir actualizaciones desde tu gestor de software. (Esto descarga automáticamente las ultimas actualizaciones y runtimes necesarios).

O añade manualmente con:
- Añade el repositorio
```bash
flatpak remote-add --user --if-not-exists CianovaLauncher https://plagaplusdev.github.io/CianovaLauncher-mcpelauncher/CianovaLauncher.flatpakrepo
```

- Asegurate de instalar los runtimes necesarios que puedes instalarlos manualmente con:

```bash
flatpak install org.kde.Platform//5.15-24.08 io.qt.qtwebengine.BaseApp//5.15-24.08
```

- Ahora instala el Launcher :
```bash
flatpak install --user CianovaLauncher org.cianova.Launcher
```


#### Metodo 2 - Bundle

Descarga e instala `CianovaLauncher.flatpak` en **RELEASE** publicado en el GitHub oficial del launcher y ábrelo con algún **gestor de software** que tengas o usando el comando:

```bash
flatpak install --user CianovaLauncher.flatpak
```
*(NOTA: El nombre del archivo también puede incluir el numero de la versión).*

Eh instala los runtimes necesarios con:
```bash
flatpak install org.kde.Platform//5.15-24.08 io.qt.qtwebengine.BaseApp//5.15-24.08
```

### Instalación no-Flatpak:

Descarga de la ultima **RELEASE** el archivo `CianovaLauncher-vX.Y.tar.gz` donde `X.Y.Z` es el numero de la versión y lo extraes en alguna carpeta que desees y también compila o descarga algún paquete de binarios del **MCPELAUNCHER-MANIFEST** del proyecto oficial; o algún algún pack Pre-compilado disponible de confianza llamado `BIN X.Y.Z (DATE) + <NOTES>.tar.gz` que vas a extraer y te dejara una carpeta llamada `bin` que la colocaras dentro de la carpeta raíz del launcher (Recomendado) o donde mejor te parezca.

**NOTA:** En el paquete portable ya se deja unos binarios Pre-compilados y sus librerias necesarias

Para iniciar el launcher, simplemente haz doble clic en el script `CianovaLauncher.sh` o ejecútalo desde la terminal:

```bash
./CianovaLauncher.sh
```

---
Luego ve a Ajustes y completa la configuración de binarios, requisitos y guarda la config.

**NOTA 2:** Dependiendo de tu distribucion y *PKG MANAGER* algunos nombres pueden no coincidir con el paquete disponible. Por lo tanto use la lista como referencia para saber cuales librerias le hacen falta.

**Para saber mas vaya a [MANUAL DE USO](MANUAL%DE%USO.md).**

---
## ⚖️ Términos y Condiciones (Resumen)

El uso de esta herramienta implica la aceptación de los siguientes puntos:
1. **Independencia:** Este launcher es una interfaz visual independiente y NO incluye el juego ni las APKs necesarias.
2. **Atribución:** Se reconoce el trabajo de **MCPELauncher-manifest** (Perteneciente de **ChristopherHX**, **MCMrARM** y todo su equipo de trabajo). como la base técnica esencial.
3. **No Lucrativo:** Esta herramienta es gratuita y de código abierto (GPL v3). Se agradece a la comunidad de mantenerlo asi para fomentar el espiritu colaborativo.
4. **Responsabilidad:** Los desarrolladores no se hacen responsables por pérdida de datos, baneos de cuentas o fallos en el sistema derivados del uso indebido.

> 📄 Consulta el documento completo en: [LICENCIA & TÉRMINOS Y CONDICIONES](Docs/LICENCE%20&%20TERMINOS%20y%20CONDICIONES.md)

---
<p align="center">
  <b>Hecho con ❤️ y 🤖 para la comunidad Linux.</b>
</p>
