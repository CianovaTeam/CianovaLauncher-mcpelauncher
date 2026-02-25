# CianovaLauncher v2.1.1
## Nota está rama es para la versión Qt5

CianovaLauncher es una interfaz gráfica moderna diseñada para facilitar la gestión, instalación y personalización de Minecraft: Bedrock Edition en Linux. Esta herramienta trabaja en conjunto con la base del proyecto **MCPELauncher-manifest**, proporcionando una experiencia de usuario amigable y potente.

### 1. Ejecución
#### Instalación para Flatpak

**NOTA:** Antes de cualquier instalación por Flatpak recuerda instalarlo en el caso de que no lo tengas.
Link para configurar Flatpak la primera vez según tu distro: [FLATPAK SETUP](https://flathub.org/en/setup)
**NOTA 2** Si tu distro es muy estricto con permisos y no tiene `flatpak-spawn` va a hacer un subproceso local o reemplazar el proceso del launcher (Solo usara los binarios disponibles en el Flatpak. Si no es muy estricto tipo Ubuntu, Mint, Debian, Arch, ZorinOS funcionara completamente.)

##### Metodo 1 (Recomendado) - Actualizaciones

Descarga el archivo `CianovaLauncher.flatpakrepo` en **RELEASE** o **EXTRA** para instalar y recibir actualizaciones desde tu gestor de software. (Esto descarga automáticamente las ultimas actualizaciones y runtimes necesarios).

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


##### Metodo 2 - Bundle

 Descarga e instala `CianovaLauncher.flatpak` en **RELEASE** publicado en el GitHub oficial del launcher y ábrelo con algún **gestor de software** que tengas o usando el comando:

```bash
flatpak install --user CianovaLauncher.flatpak
```
*(NOTA: El nombre del archivo también puede incluir el numero de la versión).*

Eh instala los runtimes necesarios con:
```bash
flatpak install org.kde.Platform//5.15-24.08 io.qt.qtwebengine.BaseApp//5.15-24.08
```

#### Instalación no-Flatpak:

Descarga de la ultima **RELEASE** el archivo `CianovaLauncher-vX.Y.tar.gz` donde `X.Y.Z` es el numero de la versión y lo extraes en alguna carpeta que desees y también compila o descarga algún paquete de binarios del **MCPELAUNCHER-MANIFEST** del proyecto oficial; o algún algún pack Pre-compilado disponible de confianza llamado `BIN X.Y.Z (DATE) + <NOTES>.tar.gz` que vas a extraer y te dejara una carpeta llamada `bin` que la colocaras dentro de la carpeta raíz del launcher (Recomendado) o donde mejor te parezca.

Para iniciar el launcher, simplemente haz doble clic en el script `CianovaLauncher.sh` o ejecútalo desde la terminal:

```bash
./CianovaLauncher.sh
```

---
Luego ve a Ajustes y completa la configuración de binarios, requisitos y guarda la config.

**Para saber mas vaya a [MANUAL DE USO](MANUAL%DE%USO.md).**

---
## 2. Atribución y Dependencias
Este "launcher" solo funciona de forma independiente en su apartado visual pero cualquier opción de ejecución, extracción u otro proceso requiere la instalación previa y binarios compilados de:

*   **MCPELauncher-Manifest:** Proyecto base en el que se fundamenta (Creditos a **ChristopherHX** y **MCMrARM**).

**Para ver todos los términos y condiciones vaya a [LICENCE AND TERMS](LICENCE%&%TERMINOS%y%CONDICIONES.md)**

---
*Hecho con ❤️ y 🤖 para la comunidad Linux.*
