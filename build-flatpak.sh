#!/bin/bash
# Script de construcción del paquete Flatpak de CianovaLauncher
# Uso: ./build-flatpak.sh

set -e  # Salir si hay errores

echo "========================================="
echo "  CianovaLauncher - Build Flatpak"
echo "========================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Sin color

# Verificar que estamos en el directorio correcto
if [ ! -f "src/main.py" ]; then
    echo -e "${RED}Error: No se encuentra el script de inicio main.py${NC}"
    echo "Ejecuta este script desde el directorio del proyecto."
    exit 1
fi

# Verificar dependencias
echo -e "${YELLOW}[1/6]${NC} Verificando dependencias..."

if ! command -v flatpak &> /dev/null; then
    echo -e "${RED}Error: flatpak no está instalado.${NC}"
    echo "Instala flatpak: sudo apt install flatpak (Debian/Ubuntu)"
    exit 1
fi

if ! command -v flatpak-builder &> /dev/null; then
    echo -e "${RED}Error: flatpak-builder no está instalado.${NC}"
    echo "Instala flatpak-builder: sudo apt install flatpak-builder"
    exit 1
fi

echo -e "${GREEN}✓ Dependencias OK${NC}"

# Agregar repositorio Flathub si no existe
echo -e "${YELLOW}[2/6]${NC} Configurando Flathub..."
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
echo -e "${GREEN}✓ Flathub configurado${NC}"

# Instalar runtime y SDK necesarios
echo -e "${YELLOW}[3/6]${NC} Instalando runtime KDE y dependencias..."
echo "Esto puede tomar varios minutos la primera vez..."

flatpak install -y flathub org.kde.Platform//6.10 || echo "Runtime ya instalado"
flatpak install -y flathub org.kde.Sdk//6.10 || echo "SDK ya instalado"
flatpak install -y flathub io.qt.qtwebengine.BaseApp//6.10 || echo "BaseApp ya instalado"

echo -e "${GREEN}✓ Runtime instalado${NC}"

if [ ! -d "dist/CianovaLauncherMCPE" ]; then
    echo -e "${RED}No se encuentra el proyecto compilado. Ejecuta build.sh primero.${NC}"
    exit 1
fi

echo -e "${YELLOW}[4/6]${NC} Preparando el build para Flatpak..."

# Preparar launcher-build/ (estructura que espera org.cianova.Launcher.yml)
rm -rf launcher-build
mkdir -p launcher-build/bin
cp -r dist/CianovaLauncherMCPE/* launcher-build/

if [ -f "bin/mcpelauncher-client" ]; then
    echo -e "${GREEN}✓ Binarios de mcpelauncher encontrados en bin/${NC}"
    cp -r bin/* launcher-build/bin/
else
    echo -e "${YELLOW}⚠ No se encontraron binarios en bin/${NC}"
    echo "El Flatpak se construirá SIN binarios mcpelauncher empaquetados."
    echo "El launcher necesitará usar modo Flatpak Personalizado o Personalizado."
    echo ""
    read -p "¿Deseas continuar de todos modos? (s/N): " confirm
    if [[ ! $confirm =~ ^[Ss]$ ]]; then
        echo "Build cancelado."
        exit 1
    fi
fi

echo -e "${GREEN}✓ Build preparado${NC}"

# Construir el Flatpak
echo -e "${YELLOW}[5/5]${NC} Construyendo paquete Flatpak (org.cianova.Launcher.yml)..."
echo "Esto puede tomar varios minutos..."

# Limpiar build anterior si existe
rm -rf .flatpak-builder build-dir

# Construir
flatpak-builder --user --install --force-clean build-dir org.cianova.Launcher.yml

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}  ✓ Build completado exitosamente${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo "Para ejecutar el launcher:"
    echo -e "  ${YELLOW}flatpak run org.cianova.Launcher${NC}"
    echo ""
    echo "Para crear un bundle distribuible (.flatpak):"
    echo -e "  ${YELLOW}flatpak build-bundle ~/.local/share/flatpak/repo CianovaLauncher.flatpak org.cianova.Launcher${NC}"
    echo ""
else
    echo -e "${RED}Error durante la construcción${NC}"
    exit 1
fi
