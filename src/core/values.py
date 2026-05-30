"""Constantes de valor compartidas entre constants.py y ui_strings.py.
Separadas para evitar importación circular: values.py no importa ningún 
módulo del proyecto, por lo que es seguro importarlo desde ambos lados.

Mantener sincronizado con las definiciones oficiales en constants.py.
"""

# ── Mode values ─────────────────────────────
MODE_BIN_SYSTEM = "system"
MODE_BIN_LOCAL = "local_script"
MODE_BIN_CUSTOM = "custom"
MODE_BIN_FLATPAK = "flatpak"

MODE_INSTALL_LOCAL = "local"
MODE_INSTALL_OWN = "local_own"
MODE_INSTALL_SHARED = "local_shared"
MODE_INSTALL_FLATPAK = "flatpak_custom"

# ── Style values ────────────────────────────
STYLE_LIST = "list"
STYLE_GRID = "grid"
STYLE_COLUMNS = "columns"
