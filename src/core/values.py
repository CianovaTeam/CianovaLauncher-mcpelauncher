"""Shared value constants between constants.py and ui_strings.py.
Separated to avoid circular imports: values.py does not import any
project module, making it safe to import from both sides.

Keep synchronized with official definitions in constants.py.
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
