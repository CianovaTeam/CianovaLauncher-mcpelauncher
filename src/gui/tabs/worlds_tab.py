"""
Worlds Management Tab for Cianova Launcher.
Displays and manages Minecraft Bedrock worlds (com.mojang/minecraftWorlds/),
including version metadata parsing, thumbnail previews, export to .mcworld,
importing, opening world directories, and safe deletion.
"""

import os
import io
import struct
import shutil
import zipfile
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QScrollArea, QFileDialog,
                             QSizePolicy, QApplication)
from PySide6.QtCore import Qt, QRect, QSize, QTimer, QThread, Signal
from PySide6.QtGui import (QPainter, QColor, QFont, QPen, QIcon, QPixmap,
                           QImage, QDesktopServices, QFontMetrics)
from src import constants as c
from src.core.ui_utils import FlowLayout, clear_layout, CreeperWatermarkWidget
from src.utils.resource_path import resource_path
from src.utils.image_manager import ImageManager
from src.utils.colors import adjust_color, hex_to_rgba
from src.utils.logger import logger
from src.utils.process_utils import open_folder
from src.utils.safe_archive import safe_extractall
from src.gui import custom_dialogs as messagebox
from src.utils.dialogs import ask_open_filename_native, ask_save_filename_native


class BedrockNBTReader:
    """Lightweight pure-Python Little-Endian Bedrock NBT parser for level.dat."""
    TAG_END = 0
    TAG_BYTE = 1
    TAG_SHORT = 2
    TAG_INT = 3
    TAG_LONG = 4
    TAG_FLOAT = 5
    TAG_DOUBLE = 6
    TAG_BYTE_ARRAY = 7
    TAG_STRING = 8
    TAG_LIST = 9
    TAG_COMPOUND = 10
    TAG_INT_ARRAY = 11
    _MAX_COLLECTION_ITEMS = 1_000_000

    def __init__(self, data: bytes):
        if len(data) >= 8:
            ver, length = struct.unpack("<II", data[:8])
            self.stream = io.BytesIO(data[8:])
        else:
            self.stream = io.BytesIO(data)

    def read_tag(self, tag_type):
        try:
            if tag_type == self.TAG_BYTE:
                return struct.unpack("<b", self.stream.read(1))[0]
            elif tag_type == self.TAG_SHORT:
                return struct.unpack("<h", self.stream.read(2))[0]
            elif tag_type == self.TAG_INT:
                return struct.unpack("<i", self.stream.read(4))[0]
            elif tag_type == self.TAG_LONG:
                return struct.unpack("<q", self.stream.read(8))[0]
            elif tag_type == self.TAG_FLOAT:
                return struct.unpack("<f", self.stream.read(4))[0]
            elif tag_type == self.TAG_DOUBLE:
                return struct.unpack("<d", self.stream.read(8))[0]
            elif tag_type == self.TAG_BYTE_ARRAY:
                length = struct.unpack("<i", self.stream.read(4))[0]
                if length < 0 or length > self._MAX_COLLECTION_ITEMS:
                    return None
                return self.stream.read(length)
            elif tag_type == self.TAG_STRING:
                str_len = struct.unpack("<H", self.stream.read(2))[0]
                return self.stream.read(str_len).decode("utf-8", errors="replace")
            elif tag_type == self.TAG_LIST:
                elem_type = struct.unpack("<b", self.stream.read(1))[0]
                list_len = struct.unpack("<i", self.stream.read(4))[0]
                if list_len < 0 or list_len > self._MAX_COLLECTION_ITEMS:
                    return None
                return [self.read_tag(elem_type) for _ in range(list_len)]
            elif tag_type == self.TAG_COMPOUND:
                result = {}
                while True:
                    b = self.stream.read(1)
                    if not b:
                        break
                    next_type = struct.unpack("<b", b)[0]
                    if next_type == self.TAG_END:
                        break
                    name_len = struct.unpack("<H", self.stream.read(2))[0]
                    name = self.stream.read(name_len).decode("utf-8", errors="replace")
                    result[name] = self.read_tag(next_type)
                return result
            elif tag_type == self.TAG_INT_ARRAY:
                length = struct.unpack("<i", self.stream.read(4))[0]
                if length < 0 or length > self._MAX_COLLECTION_ITEMS:
                    return None
                return [struct.unpack("<i", self.stream.read(4))[0] for _ in range(length)]
        except Exception:
            return None
        return None

    def parse(self) -> dict:
        try:
            b = self.stream.read(1)
            if not b:
                return {}
            root_type = struct.unpack("<b", b)[0]
            if root_type == self.TAG_COMPOUND:
                name_len = struct.unpack("<H", self.stream.read(2))[0]
                _ = self.stream.read(name_len)
                return self.read_tag(self.TAG_COMPOUND) or {}
        except Exception as e:
            logger.debug(f"NBT parse error: {e}")
        return {}


def parse_world_info(world_path: str) -> dict:
    """Extract complete world metadata from a world directory."""
    folder_name = os.path.basename(world_path)
    info = {
        "folder_path": world_path,
        "folder_name": folder_name,
        "name": folder_name,
        "version_str": "",
        "gamemode_str": "Supervivencia",
        "difficulty_str": "Normal",
        "is_hardcore": False,
        "last_played_dt": None,
        "size_mb": 0.0,
        "icon_path": None,
    }

    # 1. Level Name Fallback from levelname.txt
    levelname_txt = os.path.join(world_path, "levelname.txt")
    if os.path.exists(levelname_txt):
        try:
            with open(levelname_txt, "r", encoding="utf-8", errors="replace") as f:
                txt_name = f.read().strip()
                if txt_name:
                    info["name"] = txt_name
        except Exception:
            pass

    # 2. Thumbnail
    icon_p = os.path.join(world_path, "world_icon.jpeg")
    if os.path.exists(icon_p):
        info["icon_path"] = icon_p
    else:
        icon_png = os.path.join(world_path, "world_icon.png")
        if os.path.exists(icon_png):
            info["icon_path"] = icon_png

    # 3. Calculate Folder Size & Mtime
    total_size = 0
    latest_mtime = 0
    try:
        for root, _, files in os.walk(world_path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    stat = os.stat(fp)
                    total_size += stat.st_size
                    if stat.st_mtime > latest_mtime:
                        latest_mtime = stat.st_mtime
                except OSError:
                    pass
    except OSError:
        pass

    info["size_mb"] = total_size / (1024.0 * 1024.0)
    if latest_mtime > 0:
        info["last_played_dt"] = datetime.fromtimestamp(latest_mtime)

    # 4. NBT parse from level.dat
    level_dat = os.path.join(world_path, "level.dat")
    if os.path.exists(level_dat):
        try:
            # level.dat is normally small.  A hard cap avoids spending large
            # amounts of RAM parsing a corrupt or malicious world file.
            if os.path.getsize(level_dat) > 32 * 1024 * 1024:
                raise ValueError("level.dat exceeds the 32 MiB parsing limit")
            with open(level_dat, "rb") as f:
                raw_bytes = f.read(32 * 1024 * 1024 + 1)
            reader = BedrockNBTReader(raw_bytes)
            nbt = reader.parse()

            if nbt.get("LevelName"):
                info["name"] = str(nbt["LevelName"])

            # GameType: 0=Survival, 1=Creative, 2=Adventure, 3=Spectator
            gt = nbt.get("GameType", 0)
            gt_map = {0: "Supervivencia", 1: "Creativo", 2: "Aventura", 3: "Espectador"}
            info["gamemode_str"] = gt_map.get(gt, "Supervivencia")

            # Difficulty: 0=Peaceful, 1=Easy, 2=Normal, 3=Hard
            diff = nbt.get("Difficulty", 2)
            diff_map = {0: "Pacífico", 1: "Fácil", 2: "Normal", 3: "Difícil"}
            info["difficulty_str"] = diff_map.get(diff, "Normal")

            info["is_hardcore"] = bool(nbt.get("IsHardcore", False))

            # Version formatting
            ver_arr = nbt.get("lastOpenedWithVersion") or nbt.get("MinimumCompatibleClientVersion")
            if isinstance(ver_arr, list) and len(ver_arr) >= 3:
                info["version_str"] = f"v{ver_arr[0]}.{ver_arr[1]}.{ver_arr[2]}"
            elif nbt.get("baseGameVersion") and str(nbt["baseGameVersion"]) != "*":
                info["version_str"] = f"v{nbt['baseGameVersion']}"

            # Last played time
            lp = nbt.get("LastPlayed")
            if lp and isinstance(lp, (int, float)) and lp > 0:
                info["last_played_dt"] = datetime.fromtimestamp(lp)
        except Exception as e:
            logger.debug(f"Error reading level.dat for {world_path}: {e}")

    return info


def get_worlds_dirs(app):
    """Return all valid world directories to scan."""
    dirs = []
    home = os.path.expanduser("~")
    p1 = os.path.join(home, ".local", "share", "mcpelauncher", "games", "com.mojang", "minecraftWorlds")
    dirs.append(p1)

    if app and getattr(app, "active_path", None):
        p2 = os.path.join(app.active_path, "games", "com.mojang", "minecraftWorlds")
        if p2 not in dirs:
            dirs.append(p2)
    return dirs


def _scan_world_directories(world_dirs) -> list:
    """Scan and return all parsed world dictionaries, newest first."""
    worlds = []
    seen_paths = set()

    for base_dir in world_dirs:
        if not os.path.isdir(base_dir):
            continue
        try:
            for entry in os.listdir(base_dir):
                world_path = os.path.join(base_dir, entry)
                if os.path.isdir(world_path) and world_path not in seen_paths:
                    # Filter out non-world helper dirs
                    if entry in ("Texture", "cache", "temp"):
                        continue
                    seen_paths.add(world_path)
                    w_info = parse_world_info(world_path)
                    worlds.append(w_info)
        except OSError as e:
            logger.warning(f"Error scanning worlds directory {base_dir}: {e}")

    # Sort newest last played first
    def sort_key(w):
        if w.get("last_played_dt"):
            return w["last_played_dt"].timestamp()
        return 0.0

    worlds.sort(key=sort_key, reverse=True)
    return worlds


def scan_all_worlds(app) -> list:
    """Compatibility wrapper for synchronous callers."""
    return _scan_world_directories(get_worlds_dirs(app))


class WorldScanWorker(QThread):
    """Scan world metadata off the Qt GUI thread."""

    finished = Signal(list)
    error = Signal(str)

    def __init__(self, world_dirs, parent=None):
        super().__init__(parent)
        self._world_dirs = tuple(world_dirs)

    def run(self):
        try:
            self.finished.emit(_scan_world_directories(self._world_dirs))
        except Exception as exc:
            logger.error("World scan failed: %s", exc)
            self.error.emit(str(exc))


class WorldFileWorker(QThread):
    """Run archive operations away from the Qt GUI thread."""

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, action, parent=None):
        super().__init__(parent)
        self._action = action

    def run(self):
        try:
            self.finished.emit(self._action())
        except Exception as exc:
            self.error.emit(str(exc))


# =========================================================================
# World Card Widget
# =========================================================================

class WorldCardWidget(QFrame):
    """Card displaying world banner, name, version tag, stats, and actions."""

    def __init__(self, world_info: dict, app=None, parent_tab=None):
        super().__init__()
        self.world_info = world_info
        self.app = app
        self.parent_tab = parent_tab
        self.setObjectName("WorldCard")
        self.setFixedSize(260, 230)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(5)

        # 1. Thumbnail Container with Version Badge
        self.thumb_container = QFrame()
        self.thumb_container.setFixedHeight(115)
        self.thumb_container.setStyleSheet("background-color: #0d0e11; border-radius: 8px;")
        self.thumbnail_label = QLabel(self.thumb_container)
        self.thumbnail_label.setGeometry(0, 0, 240, 115)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet("background: transparent; border: none;")
        thumb_layout = QVBoxLayout(self.thumb_container)
        thumb_layout.setContentsMargins(6, 6, 6, 6)

        # Top Badge Row over thumbnail (e.g. Version Chip)
        self.row_badge = QHBoxLayout()
        self.row_badge.setContentsMargins(0, 0, 0, 0)
        self.row_badge.addStretch(1)

        self.lbl_version_chip = QLabel(self.world_info.get("version_str") or "Bedrock")
        self.lbl_version_chip.setStyleSheet("""
            background: rgba(0, 0, 0, 0.70);
            color: #ffffff;
            font-size: 10px;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.18);
        """)
        self.row_badge.addWidget(self.lbl_version_chip)
        thumb_layout.addLayout(self.row_badge)
        thumb_layout.addStretch(1)

        self._layout.addWidget(self.thumb_container)

        # 2. World Name
        self.lbl_name = QLabel()
        self.lbl_name.setStyleSheet("font-size: 12px; font-weight: bold; color: #ffffff;")
        self._layout.addWidget(self.lbl_name)

        # 3. Mode & Difficulty Row
        self.lbl_mode_diff = QLabel()
        self.lbl_mode_diff.setStyleSheet("font-size: 10px; font-weight: 600; color: #38bdf8;")
        self._layout.addWidget(self.lbl_mode_diff)

        # 4. Date & Size Meta
        self.lbl_meta = QLabel()
        self.lbl_meta.setStyleSheet("font-size: 10px; color: #8c8c8c;")
        self._layout.addWidget(self.lbl_meta)

        # 5. Action Toolbar (Open Folder, Export .mcworld, Delete)
        row_actions = QHBoxLayout()
        row_actions.setContentsMargins(0, 2, 0, 0)
        row_actions.setSpacing(6)

        self.btn_open_folder = QPushButton()
        self.btn_open_folder.setToolTip(c.t("UI_WORLDS_TOOLTIP_FOLDER"))
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_folder.setFixedSize(28, 24)
        self.btn_open_folder.clicked.connect(self._open_world_folder)

        self.btn_export = QPushButton()
        self.btn_export.setToolTip(c.t("UI_WORLDS_TOOLTIP_EXPORT"))
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setFixedSize(28, 24)
        self.btn_export.clicked.connect(self._export_world)

        self.btn_delete = QPushButton()
        self.btn_delete.setToolTip(c.t("UI_WORLDS_TOOLTIP_DELETE"))
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setFixedSize(28, 24)
        self.btn_delete.clicked.connect(self._delete_world)

        row_actions.addWidget(self.btn_open_folder)
        row_actions.addWidget(self.btn_export)
        row_actions.addStretch(1)
        row_actions.addWidget(self.btn_delete)

        self._layout.addLayout(row_actions)

        self._load_data()
        self.update_theme_styles()

    def _load_data(self):
        name = self.world_info.get("name") or self.world_info.get("folder_name")
        fm = self.lbl_name.fontMetrics()
        self.lbl_name.setText(fm.elidedText(name, Qt.ElideMiddle, 235))
        self.lbl_name.setToolTip(name)

        mode = self.world_info.get("gamemode_str", "Supervivencia")
        diff = self.world_info.get("difficulty_str", "Normal")
        if self.world_info.get("is_hardcore"):
            mode = "Hardcore"
        self.lbl_mode_diff.setText(f"{mode} • {diff}")

        dt = self.world_info.get("last_played_dt")
        dt_str = dt.strftime("%d/%m/%Y %H:%M") if dt else "Desconocida"
        size_mb = self.world_info.get("size_mb", 0.0)
        self.lbl_meta.setText(f"{dt_str} • {size_mb:.1f} MB")

        # Load Thumbnail background
        icon_p = self.world_info.get("icon_path")
        if icon_p and os.path.exists(icon_p):
            pix = QPixmap(icon_p)
            if not pix.isNull():
                self._draw_thumbnail(pix)
        else:
            self._draw_default_banner()

    def _draw_thumbnail(self, pix):
        scaled = pix.scaled(240, 115, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        crop_x = max(0, (scaled.width() - 240) // 2)
        crop_y = max(0, (scaled.height() - 115) // 2)
        cropped = scaled.copy(crop_x, crop_y, 240, 115)

        # Apply rounded corners
        rounded = QPixmap(240, 115)
        rounded.fill(Qt.transparent)
        p = QPainter(rounded)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRoundedRect(0, 0, 240, 115, 8, 8)
        p.setClipPath(path)
        p.drawPixmap(0, 0, cropped)
        p.end()

        # Keep the rounded thumbnail in memory.  The former implementation
        # wrote one PNG per world to /tmp on every refresh and never removed it.
        self.thumbnail_label.setPixmap(rounded)
        self.thumbnail_label.show()
        self.thumbnail_label.lower()

    def _draw_default_banner(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        self.thumbnail_label.clear()
        self.thumbnail_label.hide()
        self.thumb_container.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a1c23, stop:1 {hex_to_rgba(accent, 0.4)});
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }}
        """)

    def _open_world_folder(self):
        path = self.world_info.get("folder_path")
        if path and os.path.isdir(path):
            open_folder(path)

    def _export_world(self):
        """Export world directory to a .mcworld archive."""
        world_dir = self.world_info.get("folder_path")
        if not world_dir or not os.path.isdir(world_dir):
            return

        name = self.world_info.get("name") or os.path.basename(world_dir)
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip() or "Mundo"
        default_export = os.path.expanduser(f"~/Descargas/{safe_name}.mcworld")
        if not os.path.exists(os.path.expanduser("~/Descargas")):
            default_export = os.path.expanduser(f"~/{safe_name}.mcworld")

        dest = ask_save_filename_native(
            self.parent_tab or self,
            title=c.t("UI_WORLDS_TOOLTIP_EXPORT"),
            filetypes=[("Mundo de Minecraft", "*.mcworld"), ("Archivo ZIP", "*.zip")],
            default_name=default_export
        )
        if not dest:
            return

        def export_world():
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(world_dir):
                    for file in files:
                        abs_p = os.path.join(root, file)
                        rel_p = os.path.relpath(abs_p, world_dir)
                        zipf.write(abs_p, rel_p)

            return dest

        self._export_worker = WorldFileWorker(export_world)

        def on_exported(_):
            icon_check = ImageManager.get_tinted_icon(resource_path("check_circle_icon.svg"), "#10b981", size=(14, 14))
            if icon_check:
                self.btn_export.setIcon(icon_check)
            QTimer.singleShot(1500, self.update_theme_styles)

        def on_export_error(error):
            logger.error("Error exporting world to %s: %s", dest, error)
            messagebox.showerror(self.parent_tab or self, c.t("UI_WORLDS_EXPORT_ERROR"), f"No se pudo exportar el mundo:\n{error}")

        self._export_worker.finished.connect(on_exported)
        self._export_worker.error.connect(on_export_error)
        self._export_worker.start()

    def _delete_world(self):
        name = self.world_info.get("name") or self.world_info.get("folder_name")
        if messagebox.askyesno(
            self.parent_tab or self,
            c.t("UI_WORLDS_DELETE_TITLE"),
            c.t("UI_WORLDS_DELETE_CONFIRM", name=name)
        ):
            path = self.world_info.get("folder_path")
            if not path or not os.path.isdir(path):
                return

            self._delete_worker = WorldFileWorker(lambda: shutil.rmtree(path))

            def on_deleted(_):
                if self.parent_tab:
                    self.parent_tab.load_worlds()

            def on_delete_error(error):
                logger.error("Error deleting world %s: %s", path, error)
                messagebox.showerror(self.parent_tab or self, "Error", f"No se pudo eliminar el mundo:\n{error}")

            self._delete_worker.finished.connect(on_deleted)
            self._delete_worker.error.connect(on_delete_error)
            self._delete_worker.start()

    def update_theme_styles(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        # Card base styling
        self.setStyleSheet(f"""
            QFrame#WorldCard {{
                background-color: {"rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                border: 1px solid {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"};
                border-radius: 12px;
            }}
            QFrame#WorldCard:hover {{
                background-color: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
                border: 1px solid {hex_to_rgba(accent, 0.7)};
            }}
        """)

        # Text labels
        self.lbl_name.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {'#ffffff' if is_dark else '#18191c'}; background: transparent; border: none;")
        self.lbl_mode_diff.setStyleSheet(f"font-size: 10px; font-weight: 600; color: {'#38bdf8' if is_dark else '#0284c7'}; background: transparent; border: none;")
        self.lbl_meta.setStyleSheet(f"font-size: 10px; color: {'#9aa0a6' if is_dark else '#6b7280'}; background: transparent; border: none;")

        # Icons color
        icon_color = "#ffffff" if is_dark else "#18191c"
        icon_folder = ImageManager.get_tinted_icon(resource_path("folder_browse_icon.svg"), icon_color, size=(14, 14))
        icon_export = ImageManager.get_tinted_icon(resource_path("export_download_icon.svg"), icon_color, size=(14, 14))
        icon_trash = ImageManager.get_tinted_icon(resource_path("trash_delete_icon.svg"), "#ef4444", size=(14, 14))

        if icon_folder:
            self.btn_open_folder.setIcon(icon_folder)
        if icon_export:
            self.btn_export.setIcon(icon_export)
        if icon_trash:
            self.btn_delete.setIcon(icon_trash)

        btn_card_style = f"""
            QPushButton {{
                background: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.05)"};
                border: 1px solid {"rgba(255, 255, 255, 0.10)" if is_dark else "rgba(0, 0, 0, 0.08)"};
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background: {hex_to_rgba(accent, 0.35)};
                border: 1px solid {accent};
            }}
            QToolTip {{
                background-color: {"#181a1f" if is_dark else "#ffffff"};
                color: {"#ffffff" if is_dark else "#18191c"};
                border: 1px solid {"rgba(255, 255, 255, 0.18)" if is_dark else "rgba(0, 0, 0, 0.16)"};
                border-radius: 6px;
                padding: 5px 9px;
                font-size: 11px;
                font-weight: 500;
            }}
        """
        self.btn_open_folder.setStyleSheet(btn_card_style)
        self.btn_export.setStyleSheet(btn_card_style)
        self.btn_delete.setStyleSheet(f"""
            QPushButton {{
                background: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.05)"};
                border: 1px solid {"rgba(255, 255, 255, 0.10)" if is_dark else "rgba(0, 0, 0, 0.08)"};
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background: rgba(239, 68, 68, 0.35);
                border: 1px solid #ef4444;
            }}
            QToolTip {{
                background-color: {"#181a1f" if is_dark else "#ffffff"};
                color: {"#ffffff" if is_dark else "#18191c"};
                border: 1px solid {"rgba(255, 255, 255, 0.18)" if is_dark else "rgba(0, 0, 0, 0.16)"};
                border-radius: 6px;
                padding: 5px 9px;
                font-size: 11px;
                font-weight: 500;
            }}
        """)

    def retranslate_ui(self):
        if hasattr(self, "btn_open_folder"):
            self.btn_open_folder.setToolTip(c.t("UI_WORLDS_TOOLTIP_FOLDER"))
        if hasattr(self, "btn_export"):
            self.btn_export.setToolTip(c.t("UI_WORLDS_TOOLTIP_EXPORT"))
        if hasattr(self, "btn_delete"):
            self.btn_delete.setToolTip(c.t("UI_WORLDS_TOOLTIP_DELETE"))


# =========================================================================
# Main Worlds Tab Widget
# =========================================================================

class WorldsTab(QWidget):
    """Studio-Grade Worlds Management View for Minecraft Bedrock."""

    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self._world_scan_worker = None
        self._world_scan_pending = False
        self._world_import_worker = None

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(28, 24, 28, 20)
        self._main_layout.setSpacing(14)

        # 1. Header (Brand Badge & Titles)
        row_brand = QHBoxLayout()
        row_brand.setSpacing(14)

        self.badge_world = QLabel()
        self.badge_world.setFixedSize(44, 44)
        self.badge_world.setAlignment(Qt.AlignCenter)
        row_brand.addWidget(self.badge_world, 0, Qt.AlignVCenter)

        col_brand_text = QVBoxLayout()
        col_brand_text.setContentsMargins(0, 0, 0, 0)
        col_brand_text.setSpacing(2)

        self.lbl_brand_title = QLabel(c.t("UI_WORLDS_HEADER_TITLE"))
        self.lbl_brand_sub = QLabel(c.t("UI_WORLDS_HEADER_SUB"))
        col_brand_text.addWidget(self.lbl_brand_title)
        col_brand_text.addWidget(self.lbl_brand_sub)
        row_brand.addLayout(col_brand_text, 1)

        self._main_layout.addLayout(row_brand)

        # 2. Toolbar (Count, Import .mcworld, Open Folder, Refresh)
        self.row_toolbar = QHBoxLayout()
        self._current_count = 0
        self.lbl_count = QLabel(c.t("UI_WORLDS_COUNT_LABEL", count=0, plural="s"))
        self.lbl_count.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        self.row_toolbar.addWidget(self.lbl_count)
        self.row_toolbar.addStretch(1)

        self.btn_import = QPushButton(c.t("UI_WORLDS_BTN_IMPORT"))
        self.btn_import.setCursor(Qt.PointingHandCursor)
        self.btn_import.setFixedHeight(32)
        self.btn_import.clicked.connect(self._import_world)
        self.row_toolbar.addWidget(self.btn_import)

        self.btn_open_folder = QPushButton(c.t("UI_WORLDS_BTN_OPEN_FOLDER"))
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_folder.setFixedHeight(32)
        self.btn_open_folder.clicked.connect(self._open_worlds_folder)
        self.row_toolbar.addWidget(self.btn_open_folder)

        self.btn_refresh = QPushButton(c.t("UI_WORLDS_BTN_REFRESH"))
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setFixedHeight(32)
        self.btn_refresh.clicked.connect(self.load_worlds)
        self.row_toolbar.addWidget(self.btn_refresh)

        self._main_layout.addLayout(self.row_toolbar)

        # 3. Empty State Card
        self.card_empty = QFrame()
        self.card_empty.setObjectName("EmptyStateCard")
        empty_layout = QVBoxLayout(self.card_empty)
        empty_layout.setContentsMargins(24, 32, 24, 32)
        empty_layout.setSpacing(10)
        empty_layout.setAlignment(Qt.AlignCenter)

        self.lbl_empty_title = QLabel(c.t("UI_WORLDS_EMPTY_TITLE"))
        self.lbl_empty_title.setAlignment(Qt.AlignCenter)
        self.lbl_empty_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        empty_layout.addWidget(self.lbl_empty_title)

        self.lbl_empty_desc = QLabel(c.t("UI_WORLDS_EMPTY_SUB"))
        self.lbl_empty_desc.setAlignment(Qt.AlignCenter)
        self.lbl_empty_desc.setWordWrap(True)
        self.lbl_empty_desc.setStyleSheet("font-size: 12px; color: #a0a6b0; max-width: 500px;")
        empty_layout.addWidget(self.lbl_empty_desc)

        row_empty_btns = QHBoxLayout()
        row_empty_btns.setSpacing(10)

        self.btn_empty_import = QPushButton(c.t("UI_WORLDS_BTN_IMPORT"))
        self.btn_empty_import.setCursor(Qt.PointingHandCursor)
        self.btn_empty_import.setFixedHeight(36)
        self.btn_empty_import.clicked.connect(self._import_world)

        self.btn_empty_open = QPushButton(c.t("UI_WORLDS_BTN_OPEN_WORLDS_FOLDER"))
        self.btn_empty_open.setCursor(Qt.PointingHandCursor)
        self.btn_empty_open.setFixedHeight(36)
        self.btn_empty_open.clicked.connect(self._open_worlds_folder)

        row_empty_btns.addWidget(self.btn_empty_import)
        row_empty_btns.addWidget(self.btn_empty_open)
        empty_layout.addLayout(row_empty_btns)

        self._main_layout.addWidget(self.card_empty)

        # 4. Scrollable Grid Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        self.grid_container = QWidget()
        self.grid_layout = FlowLayout(self.grid_container, margin=0, h_spacing=14, v_spacing=14)
        self.scroll_area.setWidget(self.grid_container)

        self._main_layout.addWidget(self.scroll_area, 1)

        # 5. Background Creeper Watermark (positioned bottom-right with soft opacity)
        self.watermark = CreeperWatermarkWidget(self)
        self.watermark.lower()

        self.update_theme_styles()

    def _open_worlds_folder(self):
        dirs = get_worlds_dirs(self.app)
        for d in dirs:
            if os.path.isdir(d):
                open_folder(d)
                return
        if dirs:
            os.makedirs(dirs[0], exist_ok=True)
            open_folder(dirs[0])

    def _import_world(self):
        """Import a .mcworld or .zip into the active minecraftWorlds folder."""
        file_path = ask_open_filename_native(
            self,
            title="Importar Mundo de Minecraft",
            filetypes=[("Mundos de Minecraft", "*.mcworld *.zip")],
            initial_dir=os.path.expanduser("~/Descargas")
        )
        if not file_path or not os.path.isfile(file_path):
            return

        dirs = get_worlds_dirs(self.app)
        dest_base = dirs[0] if dirs else os.path.expanduser("~/.local/share/mcpelauncher/games/com.mojang/minecraftWorlds")
        os.makedirs(dest_base, exist_ok=True)

        def import_world():
            # Generate unique folder name based on filename or timestamp
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            target_dir = os.path.join(dest_base, f"imported_{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(target_dir, exist_ok=True)

            with zipfile.ZipFile(file_path, "r") as zipf:
                safe_extractall(zipf, target_dir)

            # Check if there is a single inner directory and flatten if necessary
            entries = os.listdir(target_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(target_dir, entries[0])):
                inner = os.path.join(target_dir, entries[0])
                for item in os.listdir(inner):
                    shutil.move(os.path.join(inner, item), target_dir)
                os.rmdir(inner)

            return base_name

        self._world_import_worker = WorldFileWorker(import_world)

        def on_imported(base_name):
            messagebox.showinfo(self, c.t("UI_WORLDS_IMPORT_SUCCESS_TITLE"), c.t("UI_WORLDS_IMPORT_SUCCESS_MSG", base_name=base_name))
            self.load_worlds()

        def on_import_error(error):
            logger.error("Error importing world %s: %s", file_path, error)
            messagebox.showerror(self, c.t("UI_WORLDS_IMPORT_ERROR"), f"No se pudo importar el archivo:\n{error}")

        self._world_import_worker.finished.connect(on_imported)
        self._world_import_worker.error.connect(on_import_error)
        self._world_import_worker.start()

    def load_worlds(self):
        """Request a background scan and keep the current grid responsive."""
        if self._world_scan_worker and self._world_scan_worker.isRunning():
            self._world_scan_pending = True
            return

        worker = WorldScanWorker(get_worlds_dirs(self.app))
        self._world_scan_worker = worker
        worker.finished.connect(self._on_worlds_loaded)
        worker.error.connect(self._on_worlds_load_error)
        worker.start()

    def _on_worlds_loaded(self, worlds):
        clear_layout(self.grid_layout)
        count = len(worlds)
        self._current_count = count
        self.lbl_count.setText(c.t("UI_WORLDS_COUNT_LABEL", count=count, plural="s" if count != 1 else ""))

        if count == 0:
            self.card_empty.show()
            self.scroll_area.hide()
        else:
            self.card_empty.hide()
            self.scroll_area.show()
            for w in worlds:
                card = WorldCardWidget(w, app=self.app, parent_tab=self)
                self.grid_layout.addWidget(card)

        self._world_scan_worker = None
        if self._world_scan_pending:
            self._world_scan_pending = False
            self.load_worlds()

    def _on_worlds_load_error(self, error):
        logger.warning("Could not scan worlds: %s", error)
        self._world_scan_worker = None
        if self._world_scan_pending:
            self._world_scan_pending = False
            self.load_worlds()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "watermark") and self.watermark:
            self.watermark.update_position()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_worlds()
        if hasattr(self, "watermark") and self.watermark:
            self.watermark.update_position()

    def update_theme_styles(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        # Header titles
        self.lbl_brand_title.setStyleSheet(
            f"font-size: 16px; font-weight: 900; letter-spacing: 0.6px; color: {'#ffffff' if is_dark else '#111214'}; background: transparent; border: none;"
        )
        self.lbl_brand_sub.setStyleSheet(
            f"font-size: 13px; font-weight: {'normal' if is_dark else '500'}; color: {'#9aa0a6' if is_dark else '#2c2f36'}; background: transparent; border: none;"
        )

        # World Badge Icon
        self.badge_world.setStyleSheet(f"""
            background-color: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
            border: 1px solid {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.08)"};
            border-radius: 12px;
        """)
        icon_path = resource_path("world_pixel.svg")
        if os.path.exists(icon_path):
            if is_dark:
                icon = ImageManager.get_icon("world_pixel.svg")
                pix = QPixmap(24, 24)
                pix.fill(Qt.transparent)
                p = QPainter(pix)
                p.setRenderHint(QPainter.Antialiasing)
                p.setRenderHint(QPainter.SmoothPixmapTransform)
                icon.paint(p, QRect(0, 0, 24, 24))
                p.end()
                self.badge_world.setPixmap(pix)
            else:
                try:
                    with open(icon_path, "r", encoding="utf-8") as f:
                        svg_content = f.read()
                    svg_light = svg_content.replace('fill="#ffffff"', 'fill="#18191c"').replace('fill="#1e1e24"', 'fill="#f3f4f6"')
                    from PySide6.QtSvg import QSvgRenderer
                    renderer = QSvgRenderer(svg_light.encode("utf-8"))
                    pix = QPixmap(24, 24)
                    pix.fill(Qt.transparent)
                    p = QPainter(pix)
                    renderer.render(p)
                    p.end()
                    self.badge_world.setPixmap(pix)
                except Exception:
                    self.badge_world.setPixmap(ImageManager.get_icon("world_pixel.svg").pixmap(24, 24))

        # Empty State Card
        self.card_empty.setStyleSheet(f"""
            QFrame#EmptyStateCard {{
                background-color: {"rgba(255, 255, 255, 0.04)" if is_dark else "rgba(0, 0, 0, 0.03)"};
                border: 1.5px dashed {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.10)"};
                border-radius: 14px;
            }}
        """)
        self.lbl_empty_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {'#ffffff' if is_dark else '#18191c'}; background: transparent;")
        self.lbl_empty_desc.setStyleSheet(f"font-size: 12px; color: {'#a0a6b0' if is_dark else '#4b5563'}; background: transparent;")

        self.btn_empty_import.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {adjust_color(accent, 1.15)};
            }}
        """)
        self.btn_empty_open.setStyleSheet(f"""
            QPushButton {{
                background: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
                color: {'#ffffff' if is_dark else '#18191c'};
                border: 1px solid {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.10)"};
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background: {hex_to_rgba(accent, 0.30)};
                border: 1px solid {accent};
            }}
        """)

        # Toolbar Buttons
        self.lbl_count.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {'#ffffff' if is_dark else '#18191c'};")
        btn_style = f"""
            QPushButton {{
                background: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
                color: {'#ffffff' if is_dark else '#18191c'};
                border: 1px solid {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.10)"};
                border-radius: 8px;
                padding: 0 14px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {hex_to_rgba(accent, 0.30)};
                border: 1px solid {accent};
            }}
        """
        self.btn_import.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {adjust_color(accent, 1.15)};
            }}
        """)
        self.btn_open_folder.setStyleSheet(btn_style)
        self.btn_refresh.setStyleSheet(btn_style)

        # Update child cards
        if hasattr(self, "grid_layout"):
            for i in range(self.grid_layout.count()):
                item = self.grid_layout.itemAt(i)
                if item and item.widget() and hasattr(item.widget(), "update_theme_styles"):
                    item.widget().update_theme_styles()

    def retranslate_ui(self):
        if hasattr(self, "lbl_brand_title"):
            self.lbl_brand_title.setText(c.t("UI_WORLDS_HEADER_TITLE"))
        if hasattr(self, "lbl_brand_sub"):
            self.lbl_brand_sub.setText(c.t("UI_WORLDS_HEADER_SUB"))
        if hasattr(self, "btn_import"):
            self.btn_import.setText(c.t("UI_WORLDS_BTN_IMPORT"))
        if hasattr(self, "btn_open_folder"):
            self.btn_open_folder.setText(c.t("UI_WORLDS_BTN_OPEN_FOLDER"))
        if hasattr(self, "btn_refresh"):
            self.btn_refresh.setText(c.t("UI_WORLDS_BTN_REFRESH"))
        if hasattr(self, "lbl_empty_title"):
            self.lbl_empty_title.setText(c.t("UI_WORLDS_EMPTY_TITLE"))
        if hasattr(self, "lbl_empty_desc"):
            self.lbl_empty_desc.setText(c.t("UI_WORLDS_EMPTY_SUB"))
        if hasattr(self, "btn_empty_import"):
            self.btn_empty_import.setText(c.t("UI_WORLDS_BTN_IMPORT"))
        if hasattr(self, "btn_empty_open"):
            self.btn_empty_open.setText(c.t("UI_WORLDS_BTN_OPEN_WORLDS_FOLDER"))
        count = getattr(self, "_current_count", 0)
        if hasattr(self, "lbl_count"):
            self.lbl_count.setText(c.t("UI_WORLDS_COUNT_LABEL", count=count, plural="s" if count != 1 else ""))
        if hasattr(self, "grid_layout"):
            for i in range(self.grid_layout.count()):
                item = self.grid_layout.itemAt(i)
                if item and item.widget() and hasattr(item.widget(), "retranslate_ui"):
                    item.widget().retranslate_ui()
