#!/usr/bin/env bash
set -euo pipefail

# CianovaLauncher - Instalación automática para Flatpak (Método 1)
# Repositorio: https://github.com/plagaplusdev/CianovaLauncher-mcpelauncher

REPO_NAME="CianovaLauncher"
REPO_URL="https://plagaplusdev.github.io/CianovaLauncher-mcpelauncher/CianovaLauncher.flatpakrepo"
APP_ID="org.cianova.Launcher"
RUNTIMES=("org.kde.Platform//6.10" "io.qt.qtwebengine.BaseApp//6.10")

print_bold() { echo -e "\033[1m$1\033[0m"; }
print_ok()   { echo -e "  [\033[32mOK\033[0m] $1"; }
print_info() { echo -e "  [\033[34m..\033[0m] $1"; }
print_err()  { echo -e "  [\033[31mER\033[0m] $1" >&2; }
print_step() { echo; print_bold "==> $1"; }

cleanup() {
    if [ "${1:-}" = "error" ]; then
        print_err "La instalación ha fallado. Revisa los mensajes anteriores."
    fi
}
trap 'cleanup error' ERR

if ! command -v flatpak &>/dev/null; then
    print_err "Flatpak no está instalado."
    echo
    echo "  Instálalo según tu distribución:"
    echo "    Debian/Ubuntu/Mint:  sudo apt install flatpak"
    echo "    Fedora:              sudo dnf install flatpak"
    echo "    Arch/Manjaro:        sudo pacman -S flatpak"
    echo "    openSUSE:            sudo zypper install flatpak"
    echo
    echo "  Luego reinicia sesión o ejecuta: flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo"
    echo "  Más info: https://flathub.org/setup"
    exit 1
fi

print_step "Añadiendo repositorio Flathub (necesario para runtimes KDE)"
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
print_ok "Flathub añadido correctamente."

print_step "Añadiendo repositorio $REPO_NAME"
flatpak remote-add --user --if-not-exists "$REPO_NAME" "$REPO_URL"
print_ok "Repositorio añadido correctamente."

print_step "Instalando runtimes necesarios"
for rt in "${RUNTIMES[@]}"; do
    print_info "Instalando $rt ..."
    flatpak install --user --noninteractive --assumeyes flathub "$rt"
    print_ok "$rt instalado."
done

print_step "Instalando $APP_ID"
flatpak install --user --noninteractive --assumeyes "$REPO_NAME" "$APP_ID"
print_ok "CianovaLauncher instalado correctamente."

echo
print_bold "Instalación completada."
echo "  Ejecútalo desde tu menú de aplicaciones o con:"
echo "    flatpak run $APP_ID"
echo
