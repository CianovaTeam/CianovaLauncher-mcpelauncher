import os
import sys

def resource_path(relative_path):
    """Get absolute path to resource, works for dev, PyInstaller, and Flatpak."""
    if not relative_path:
        return ""

    if os.path.isabs(relative_path) and os.path.exists(relative_path):
        return relative_path

    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Calculate workspace root from the location of this file
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    clean_name = os.path.basename(relative_path)
    clean_rel = relative_path.lstrip("/\\")

    # Search candidates in logical priority order
    candidates = [
        os.path.join(base_path, "assets", "media", clean_name),
        os.path.join(base_path, "assets", "media", clean_rel),
        os.path.join(base_path, "assets", clean_name),
        os.path.join(base_path, "assets", clean_rel),
        os.path.join(base_path, clean_rel),
        os.path.join(base_path, clean_name),
        os.path.abspath(relative_path),
    ]

    for c in candidates:
        if os.path.exists(c):
            return c

    # Fallback for Flatpak
    flatpak_candidates = [
        os.path.join("/app/bin", "assets", "media", clean_name),
        os.path.join("/app/bin", "assets", clean_name),
        os.path.join("/app/bin", clean_rel),
    ]
    for fc in flatpak_candidates:
        if os.path.exists(fc):
            return fc

    # Default to assets/media path if not found yet
    return os.path.join(base_path, "assets", "media", clean_name)
