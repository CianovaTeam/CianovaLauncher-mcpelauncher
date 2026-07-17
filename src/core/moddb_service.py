import os
import json
import io
import zipfile
import urllib.request
import urllib.error
from PySide6.QtCore import QThread, Signal
from src import constants as c
from src.utils.logger import logger


MODDB_URL = "https://github.com/minecraft-linux/mcpelauncher-moddb/raw/main/moddb.json"
MODDB_CACHE_FILE = "moddb_cache.json"


def _moddb_cache_path(active_path):
    return os.path.join(active_path, c.MODS_DIR, MODDB_CACHE_FILE)


def fetch_moddb():
    """Fetch the full mod database from GitHub."""
    req = urllib.request.Request(MODDB_URL, headers={"User-Agent": "CianovaLauncher/3.1"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_cached_moddb(active_path):
    """Read cached moddb from disk."""
    if not active_path:
        return None
    path = _moddb_cache_path(active_path)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not read moddb cache at {path}: {e}")
    return None


def cache_moddb(active_path, data):
    """Write moddb cache to disk."""
    if not active_path:
        return
    path = _moddb_cache_path(active_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        logger.warning(f"Failed to cache moddb: {e}")


def get_mod_info(moddb, name):
    """Find a specific mod by name in moddb list."""
    if not isinstance(moddb, list):
        return None
    for entry in moddb:
        if entry.get("name") == name:
            return entry
    return None


def find_asset_for_arch(mod_entry, arch):
    """Find the best-matching download URL and version for a given arch.

    Returns (download_url, version_str) or (None, None).
    """
    versions = mod_entry.get("versions", [])
    for ver_entry in versions:
        assets = ver_entry.get("assets", {})
        if arch in assets:
            return assets[arch], ver_entry.get("version")
    if versions:
        fallback_assets = versions[0].get("assets", {})
        if fallback_assets:
            return list(fallback_assets.values())[0], versions[0].get("version")
    return None, None


def is_mod_installed(active_path, mod_name):
    """Check if a mod's directory exists in the mods folder."""
    if not active_path:
        return False
    return os.path.isdir(os.path.join(active_path, c.MODS_DIR, mod_name))


def get_installed_mod_dirs(active_path):
    """Return set of installed mod directory names under mods/."""
    if not active_path:
        return set()
    mods_dir = os.path.join(active_path, c.MODS_DIR)
    if not os.path.isdir(mods_dir):
        return set()
    return {d for d in os.listdir(mods_dir)
            if os.path.isdir(os.path.join(mods_dir, d))
            and d != "__pycache__"}


def detect_architecture():
    """Detect the system architecture and return the moddb asset key.

    Returns e.g. "x86_64", "arm64-v8a", "x86", "armeabi-v7a", or None.
    """
    import platform as _platform
    machine = _platform.machine()
    if machine in ("x86_64", "amd64"):
        return "x86_64"
    elif machine in ("aarch64", "arm64"):
        return "arm64-v8a"
    elif machine in ("i386", "i686", "x86"):
        return "x86"
    elif machine.startswith("arm"):
        return "armeabi-v7a"
    return None


# ── Background workers ──

class ModInstallWorker(QThread):
    """Background worker for downloading and installing any mod from a ZIP URL."""
    progress = Signal(str)
    error = Signal(str)
    finished = Signal(str)  # destination directory path

    def __init__(self, mod_name, download_url, dest_dir):
        super().__init__()
        self.mod_name = mod_name
        self.download_url = download_url
        self.dest_dir = dest_dir

    def run(self):
        try:
            self.progress.emit(f"Descargando {self.mod_name}...")
            req = urllib.request.Request(
                self.download_url, headers={"User-Agent": "CianovaLauncher/3.1"}
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()

            if not data:
                self.error.emit("El archivo descargado está vacío")
                return

            self.progress.emit("Extrayendo archivos...")
            os.makedirs(self.dest_dir, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                zf.extractall(self.dest_dir)

            for root, dirs, files in os.walk(self.dest_dir):
                for f in files:
                    if f.endswith(".so"):
                        os.chmod(os.path.join(root, f), 0o755)

            self.finished.emit(self.dest_dir)

        except urllib.error.HTTPError as e:
            self.error.emit(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            self.error.emit(f"Error de red: {e.reason}")
        except Exception as e:
            self.error.emit(str(e))


class ModDBFetchWorker(QThread):
    """Background worker that fetches and caches moddb.json."""
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, active_path):
        super().__init__()
        self.active_path = active_path

    def run(self):
        try:
            data = fetch_moddb()
            cache_moddb(self.active_path, data)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))
