#!/bin/bash
# Script de lanzamiento para CianovaLauncher en Flatpak
# Configurar variables de entorno

#General
export PATH="/app/bin:$PATH"
export LD_LIBRARY_PATH="/app/lib:$LD_LIBRARY_PATH"
export MCPELAUNCHER_DATA_DIR="/app/share/mcpelauncher"

# Qt6 WebEngine: QML module lives at /app/lib/qml/ from base extension
export QML_IMPORT_PATH="/app/lib/qml:/usr/lib/qml"
export QML2_IMPORT_PATH="/app/lib/qml:/usr/lib/qml"

# Qt6 plugins (xcb, wayland) for subprocesses like playdl-signin-ui-qt
export QT_PLUGIN_PATH="/app/lib/plugins:/usr/lib/plugins"

# Directorio de datos del usuario
DATA_DIR="${XDG_DATA_HOME:-$HOME/.var/app/org.cianova.Launcher/data}/mcpelauncher"
mkdir -p "$DATA_DIR"

exec /app/lib/cianova/CianovaLauncherMCPE "$@"
