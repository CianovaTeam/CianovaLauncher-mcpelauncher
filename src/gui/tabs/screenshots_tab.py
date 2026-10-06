"""
Screenshots Gallery & Manager Tab for Cianova Launcher.
Displays genuine in-game Minecraft Bedrock screenshots (com.mojang/Screenshots/<xuid>/),
with full-resolution viewer, clipboard export, system file save, and a built-in gallery image editor.
"""

import os
import re
import json
import shutil
from datetime import datetime
from PIL import Image as PILImage, ImageEnhance, ImageOps
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QScrollArea, QDialog,
                             QFileDialog, QSlider, QSizePolicy,
                             QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QApplication)
from PySide6.QtCore import (Qt, QRectF, Property, QPropertyAnimation, QEasingCurve,
                            QTimer, QSize, QRect, QPoint, Signal, QThread)
from PySide6.QtGui import (QPainter, QColor, QFont, QPen, QIcon, QPixmap,
                           QImage, QTransform, QDesktopServices, QClipboard)
from src import constants as c
from src.core.ui_utils import FlowLayout, clear_layout, CreeperWatermarkWidget
from src.utils.resource_path import resource_path
from src.utils.image_manager import ImageManager
from src.utils.colors import adjust_color, blend_colors, hex_to_rgba
from src.utils.logger import logger
from src.utils.process_utils import open_folder
from src.gui import custom_dialogs as messagebox
from src.utils.dialogs import ask_save_filename_native


def _screenshot_base_dirs(active_path=None):
    """Return candidate screenshot directories without accessing Qt objects."""
    home = os.path.expanduser("~")
    base_dirs = [
        os.path.join(home, ".local", "share", "mcpelauncher", "games", "com.mojang", "Screenshots"),
        os.path.join(home, ".local", "share", "mcpelauncher", "games", "com.mojang", "screenshots"),
    ]
    if active_path:
        base_dirs.extend([
            os.path.join(active_path, "games", "com.mojang", "Screenshots"),
            os.path.join(active_path, "games", "com.mojang", "screenshots"),
            os.path.join(active_path, "screenshots"),
        ])
    return base_dirs


def _collect_screenshot_files(active_path=None):
    """Discover screenshot paths and sort them by capture time."""
    files_found = []
    base_dirs = _screenshot_base_dirs(active_path)

    seen_paths = set()
    for b in base_dirs:
        if not os.path.isdir(b):
            continue
        for entry in os.listdir(b):
            sub_p = os.path.join(b, entry)
            if os.path.isdir(sub_p):
                # XUID directory (e.g. 2535465003278365)
                for f in os.listdir(sub_p):
                    if f.lower().endswith(('.jpeg', '.jpg', '.png')) and not f.startswith('.'):
                        full_p = os.path.join(sub_p, f)
                        if full_p not in seen_paths and os.path.isfile(full_p):
                            seen_paths.add(full_p)
                            files_found.append(full_p)
            elif entry.lower().endswith(('.jpeg', '.jpg', '.png')) and not entry.startswith('.'):
                if sub_p not in seen_paths and os.path.isfile(sub_p):
                    seen_paths.add(sub_p)
                    files_found.append(sub_p)

    def get_sort_key(path):
        json_meta = os.path.splitext(path)[0] + ".json"
        if os.path.exists(json_meta):
            try:
                with open(json_meta, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                    if "captureTime" in data:
                        return float(data["captureTime"])
            except Exception:
                pass
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0.0

    files_found.sort(key=get_sort_key, reverse=True)
    return files_found


def _scan_screenshot_entries(active_path=None):
    """Read metadata and scaled QImages without blocking the GUI thread."""
    entries = []
    for path in _collect_screenshot_files(active_path):
        json_meta = os.path.splitext(path)[0] + ".json"
        timestamp = None
        if os.path.exists(json_meta):
            try:
                with open(json_meta, "r", encoding="utf-8") as metadata_file:
                    timestamp = float(json.load(metadata_file).get("captureTime"))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                pass
        if timestamp is None:
            try:
                timestamp = os.path.getmtime(path)
            except OSError:
                timestamp = 0.0
        try:
            date_str = datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M")
        except (OSError, OverflowError, ValueError):
            date_str = "Desconocida"
        try:
            size_kb = os.path.getsize(path) / 1024.0
        except OSError:
            size_kb = 0.0

        # QImage is safe to create and transform in a worker; conversion to
        # QPixmap happens later in the main thread.
        thumbnail = QImage(path)
        if not thumbnail.isNull():
            thumbnail = thumbnail.scaled(220, 115, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        entries.append({
            "path": path,
            "date_str": date_str,
            "size_kb": size_kb,
            "thumbnail": thumbnail,
        })
    return entries


def get_screenshot_files(app):
    """Return screenshot paths; retained for callers outside the gallery."""
    active_path = getattr(app, "active_path", None) if app else None
    return _collect_screenshot_files(active_path)


class ScreenshotScanWorker(QThread):
    """Collect gallery metadata and thumbnails off the Qt GUI thread."""

    finished = Signal(list)
    error = Signal(str)

    def __init__(self, active_path=None, parent=None):
        super().__init__(parent)
        self._active_path = active_path

    def run(self):
        try:
            self.finished.emit(_scan_screenshot_entries(self._active_path))
        except Exception as exc:
            logger.error("Screenshot scan failed: %s", exc)
            self.error.emit(str(exc))


# =========================================================================
# Modals & Dialogs: Full Viewer & Image Editor
# =========================================================================

class ScreenshotImageViewerModal(QDialog):
    """High-res modal image viewer with zoom, copy to clipboard and export."""

    def __init__(self, image_path, parent=None, app=None):
        super().__init__(parent, Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.image_path = image_path
        self.app = app
        self.resize(880, 560)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 18, 18, 18)

        # Card container
        self.card = QFrame()
        self.card.setObjectName("ModalCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(12)

        # Top bar (Title & Close)
        row_top = QHBoxLayout()
        self.lbl_filename = QLabel(os.path.basename(image_path))
        self.lbl_filename.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        row_top.addWidget(self.lbl_filename, 1)

        self.btn_close = QPushButton("✕")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.clicked.connect(self.close)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                color: #ffffff;
                border: none;
                border-radius: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(244, 67, 54, 0.8);
            }
        """)
        row_top.addWidget(self.btn_close, 0)
        card_layout.addLayout(row_top)

        # Image preview area
        self.lbl_image = QLabel()
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setStyleSheet("background: #0d0e11; border-radius: 10px;")
        card_layout.addWidget(self.lbl_image, 1)

        # Bottom Action buttons
        row_actions = QHBoxLayout()
        row_actions.setSpacing(10)

        self.btn_copy = QPushButton(c.t("UI_SCREENSHOTS_BTN_COPY"))
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.setFixedHeight(34)
        self.btn_copy.clicked.connect(self._copy_to_clipboard)

        self.btn_export = QPushButton(c.t("UI_SCREENSHOTS_BTN_SAVE_AS"))
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setFixedHeight(34)
        self.btn_export.clicked.connect(self._export_image)

        row_actions.addWidget(self.btn_copy)
        row_actions.addWidget(self.btn_export)
        row_actions.addStretch(1)

        card_layout.addLayout(row_actions)
        self._layout.addWidget(self.card)

        self._load_image()
        self._apply_styling()

    def retranslate_ui(self):
        self.btn_copy.setText(c.t("UI_SCREENSHOTS_BTN_COPY"))
        self.btn_export.setText(c.t("UI_SCREENSHOTS_BTN_SAVE_AS"))

    def _load_image(self):
        if os.path.exists(self.image_path):
            pix = QPixmap(self.image_path)
            if not pix.isNull():
                scaled = pix.scaled(820, 420, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.lbl_image.setPixmap(scaled)

    def _copy_to_clipboard(self):
        if os.path.exists(self.image_path):
            img = QImage(self.image_path)
            if not img.isNull():
                QApplication.clipboard().setImage(img)
                self.btn_copy.setText(c.t("UI_SCREENSHOTS_BTN_COPIED"))
                QTimer.singleShot(1500, lambda: self.btn_copy.setText(c.t("UI_SCREENSHOTS_BTN_COPY")))

    def _export_image(self):
        if not os.path.exists(self.image_path):
            return
        default_path = os.path.expanduser(f"~/Imágenes/{os.path.basename(self.image_path)}")
        dest = ask_save_filename_native(
            self,
            title=c.t("UI_SCREENSHOTS_SAVE_TITLE"),
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg")],
            default_name=default_path
        )
        if dest:
            shutil.copy2(self.image_path, dest)
            self.btn_export.setText(c.t("UI_SCREENSHOTS_SAVED"))
            QTimer.singleShot(1500, lambda: self.btn_export.setText(c.t("UI_SCREENSHOTS_BTN_SAVE_AS")))

    def _apply_styling(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        self.card.setStyleSheet(f"""
            QFrame#ModalCard {{
                background-color: #141518;
                border: 1px solid {hex_to_rgba(accent, 0.6)};
                border-radius: 16px;
            }}
            QPushButton {{
                background: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 0 16px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {hex_to_rgba(accent, 0.35)};
                border-color: {accent};
            }}
        """)


class CropImageWidget(QWidget):
    """
    Gallery-style interactive crop canvas.
    Initially encompasses the entire image and allows dragging 8 handles (corners/edges)
    or moving the crop box directly, with rule-of-thirds grid and aspect ratio constraints.
    """
    cropSelectionChanged = Signal(bool)

    HANDLE_NONE = 0
    HANDLE_TL = 1
    HANDLE_TR = 2
    HANDLE_BL = 3
    HANDLE_BR = 4
    HANDLE_TOP = 5
    HANDLE_BOTTOM = 6
    HANDLE_LEFT = 7
    HANDLE_RIGHT = 8
    HANDLE_INSIDE = 9

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = None
        self.crop_rel = QRectF(0.0, 0.0, 1.0, 1.0)
        self.active_handle = self.HANDLE_NONE
        self.drag_start_pos = None
        self.drag_start_crop_rel = None
        self.aspect_ratio = None
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_pixmap(self, pix):
        self.pixmap = pix
        self.update()

    def reset_crop(self):
        self.crop_rel = QRectF(0.0, 0.0, 1.0, 1.0)
        self.aspect_ratio = None
        self.active_handle = self.HANDLE_NONE
        self.update()
        self.cropSelectionChanged.emit(False)

    def set_aspect_ratio(self, ratio):
        self.aspect_ratio = ratio
        if ratio is None or not self.pixmap or self.pixmap.isNull():
            self.cropSelectionChanged.emit(self.has_active_crop())
            self.update()
            return

        img_w, img_h = self.pixmap.width(), self.pixmap.height()
        if img_w <= 0 or img_h <= 0:
            return

        img_ratio = img_w / float(img_h)
        if ratio >= img_ratio:
            w_rel = 1.0
            h_rel = (img_w / ratio) / float(img_h)
        else:
            h_rel = 1.0
            w_rel = (img_h * ratio) / float(img_w)

        w_rel = max(0.05, min(1.0, w_rel))
        h_rel = max(0.05, min(1.0, h_rel))
        x_rel = (1.0 - w_rel) / 2.0
        y_rel = (1.0 - h_rel) / 2.0

        self.crop_rel = QRectF(x_rel, y_rel, w_rel, h_rel)
        self.cropSelectionChanged.emit(self.has_active_crop())
        self.update()

    def has_active_crop(self):
        if not self.crop_rel:
            return False
        return (
            self.crop_rel.left() > 0.005
            or self.crop_rel.top() > 0.005
            or self.crop_rel.right() < 0.995
            or self.crop_rel.bottom() < 0.995
        )

    def _get_image_draw_rect(self):
        if not self.pixmap or self.pixmap.isNull():
            return QRect()
        avail_sz = QSize(max(10, self.width() - 16), max(10, self.height() - 16))
        scaled_sz = self.pixmap.size().scaled(avail_sz, Qt.KeepAspectRatio)
        x = (self.width() - scaled_sz.width()) // 2
        y = (self.height() - scaled_sz.height()) // 2
        return QRect(x, y, scaled_sz.width(), scaled_sz.height())

    def _rel_to_abs_crop_rect(self):
        draw_rect = self._get_image_draw_rect()
        if draw_rect.isEmpty():
            return QRect()
        x = draw_rect.left() + int(self.crop_rel.left() * draw_rect.width())
        y = draw_rect.top() + int(self.crop_rel.top() * draw_rect.height())
        w = max(10, int(self.crop_rel.width() * draw_rect.width()))
        h = max(10, int(self.crop_rel.height() * draw_rect.height()))
        return QRect(x, y, w, h)

    def _hit_test(self, pos):
        crop_rect = self._rel_to_abs_crop_rect()
        if crop_rect.isEmpty():
            return self.HANDLE_NONE

        margin = 14
        x, y = pos.x(), pos.y()
        l, r = crop_rect.left(), crop_rect.right()
        t, b = crop_rect.top(), crop_rect.bottom()
        mx, my = crop_rect.center().x(), crop_rect.center().y()

        # Corners
        if abs(x - l) <= margin and abs(y - t) <= margin:
            return self.HANDLE_TL
        if abs(x - r) <= margin and abs(y - t) <= margin:
            return self.HANDLE_TR
        if abs(x - l) <= margin and abs(y - b) <= margin:
            return self.HANDLE_BL
        if abs(x - r) <= margin and abs(y - b) <= margin:
            return self.HANDLE_BR

        # Edges
        if abs(x - mx) <= margin * 2 and abs(y - t) <= margin:
            return self.HANDLE_TOP
        if abs(x - mx) <= margin * 2 and abs(y - b) <= margin:
            return self.HANDLE_BOTTOM
        if abs(y - my) <= margin * 2 and abs(x - l) <= margin:
            return self.HANDLE_LEFT
        if abs(y - my) <= margin * 2 and abs(x - r) <= margin:
            return self.HANDLE_RIGHT

        # Inside
        if crop_rect.contains(pos):
            return self.HANDLE_INSIDE

        return self.HANDLE_NONE

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.pixmap and not self.pixmap.isNull():
            handle = self._hit_test(event.pos())
            if handle != self.HANDLE_NONE:
                self.active_handle = handle
                self.drag_start_pos = event.pos()
                self.drag_start_crop_rel = QRectF(self.crop_rel)

    def mouseMoveEvent(self, event):
        if self.active_handle == self.HANDLE_NONE:
            handle = self._hit_test(event.pos())
            if handle in (self.HANDLE_TL, self.HANDLE_BR):
                self.setCursor(Qt.SizeFDiagCursor)
            elif handle in (self.HANDLE_TR, self.HANDLE_BL):
                self.setCursor(Qt.SizeBDiagCursor)
            elif handle in (self.HANDLE_TOP, self.HANDLE_BOTTOM):
                self.setCursor(Qt.SizeVerCursor)
            elif handle in (self.HANDLE_LEFT, self.HANDLE_RIGHT):
                self.setCursor(Qt.SizeHorCursor)
            elif handle == self.HANDLE_INSIDE:
                self.setCursor(Qt.SizeAllCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            return

        draw_rect = self._get_image_draw_rect()
        if draw_rect.isEmpty() or not self.drag_start_pos or not self.drag_start_crop_rel:
            return

        dx_rel = (event.pos().x() - self.drag_start_pos.x()) / float(draw_rect.width())
        dy_rel = (event.pos().y() - self.drag_start_pos.y()) / float(draw_rect.height())

        sr = self.drag_start_crop_rel
        min_dim = 0.05

        l = sr.left()
        r = sr.right()
        t = sr.top()
        b = sr.bottom()

        if self.active_handle == self.HANDLE_INSIDE:
            w = r - l
            h = b - t
            nl = min(max(0.0, l + dx_rel), 1.0 - w)
            nt = min(max(0.0, t + dy_rel), 1.0 - h)
            self.crop_rel = QRectF(nl, nt, w, h)
        else:
            if self.active_handle in (self.HANDLE_TL, self.HANDLE_LEFT, self.HANDLE_BL):
                l = min(max(0.0, l + dx_rel), r - min_dim)
            if self.active_handle in (self.HANDLE_TR, self.HANDLE_RIGHT, self.HANDLE_BR):
                r = min(max(l + min_dim, r + dx_rel), 1.0)
            if self.active_handle in (self.HANDLE_TL, self.HANDLE_TOP, self.HANDLE_TR):
                t = min(max(0.0, t + dy_rel), b - min_dim)
            if self.active_handle in (self.HANDLE_BL, self.HANDLE_BOTTOM, self.HANDLE_BR):
                b = min(max(t + min_dim, b + dy_rel), 1.0)

            self.crop_rel = QRectF(l, t, r - l, b - t)

        self.cropSelectionChanged.emit(self.has_active_crop())
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.active_handle != self.HANDLE_NONE:
            self.active_handle = self.HANDLE_NONE
            self.drag_start_pos = None
            self.drag_start_crop_rel = None
            self.cropSelectionChanged.emit(self.has_active_crop())
            self.update()

    def get_pixel_crop_bounds(self, orig_w, orig_h):
        if not self.has_active_crop():
            return None
        x1 = max(0, min(orig_w - 1, int(self.crop_rel.left() * orig_w)))
        y1 = max(0, min(orig_h - 1, int(self.crop_rel.top() * orig_h)))
        x2 = max(x1 + 1, min(orig_w, int(self.crop_rel.right() * orig_w)))
        y2 = max(y1 + 1, min(orig_h, int(self.crop_rel.bottom() * orig_h)))
        return (x1, y1, x2, y2)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), QColor("#0c0d10"))

        if not self.pixmap or self.pixmap.isNull():
            painter.end()
            return

        draw_rect = self._get_image_draw_rect()
        painter.drawPixmap(draw_rect, self.pixmap)

        crop_rect = self._rel_to_abs_crop_rect()
        if crop_rect.isEmpty():
            painter.end()
            return

        # 1. Dim outside overlay
        dim_color = QColor(0, 0, 0, 160)
        if crop_rect.top() > draw_rect.top():
            painter.fillRect(draw_rect.left(), draw_rect.top(), draw_rect.width(), crop_rect.top() - draw_rect.top(), dim_color)
        if draw_rect.bottom() > crop_rect.bottom():
            painter.fillRect(draw_rect.left(), crop_rect.bottom() + 1, draw_rect.width(), draw_rect.bottom() - crop_rect.bottom(), dim_color)
        if crop_rect.left() > draw_rect.left():
            painter.fillRect(draw_rect.left(), crop_rect.top(), crop_rect.left() - draw_rect.left(), crop_rect.height(), dim_color)
        if draw_rect.right() > crop_rect.right():
            painter.fillRect(crop_rect.right() + 1, crop_rect.top(), draw_rect.right() - crop_rect.right(), crop_rect.height(), dim_color)

        # 2. Rule of Thirds Grid lines
        pen_grid = QPen(QColor(255, 255, 255, 55), 1, Qt.SolidLine)
        painter.setPen(pen_grid)
        gw = crop_rect.width() / 3.0
        gh = crop_rect.height() / 3.0
        painter.drawLine(crop_rect.left() + int(gw), crop_rect.top(), crop_rect.left() + int(gw), crop_rect.bottom())
        painter.drawLine(crop_rect.left() + int(gw * 2), crop_rect.top(), crop_rect.left() + int(gw * 2), crop_rect.bottom())
        painter.drawLine(crop_rect.left(), crop_rect.top() + int(gh), crop_rect.right(), crop_rect.top() + int(gh))
        painter.drawLine(crop_rect.left(), crop_rect.top() + int(gh * 2), crop_rect.right(), crop_rect.top() + int(gh * 2))

        # 3. Main Crop Outline
        pen_border = QPen(QColor(255, 255, 255, 200), 1.5, Qt.SolidLine)
        painter.setPen(pen_border)
        painter.drawRect(crop_rect)

        # 4. Corner L-Brackets & Midpoint Handles
        bracket_len = 16
        bracket_thick = 3
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ffffff"))

        cl, cr = crop_rect.left(), crop_rect.right()
        ct, cb = crop_rect.top(), crop_rect.bottom()

        painter.fillRect(cl - 1, ct - 1, bracket_len, bracket_thick, QColor("#ffffff"))
        painter.fillRect(cl - 1, ct - 1, bracket_thick, bracket_len, QColor("#ffffff"))
        painter.fillRect(cr - bracket_len + 1, ct - 1, bracket_len, bracket_thick, QColor("#ffffff"))
        painter.fillRect(cr - bracket_thick + 1, ct - 1, bracket_thick, bracket_len, QColor("#ffffff"))
        painter.fillRect(cl - 1, cb - bracket_thick + 1, bracket_len, bracket_thick, QColor("#ffffff"))
        painter.fillRect(cl - 1, cb - bracket_len + 1, bracket_thick, bracket_len, QColor("#ffffff"))
        painter.fillRect(cr - bracket_len + 1, cb - bracket_thick + 1, bracket_len, bracket_thick, QColor("#ffffff"))
        painter.fillRect(cr - bracket_thick + 1, cb - bracket_len + 1, bracket_thick, bracket_len, QColor("#ffffff"))

        mx = (cl + cr) // 2
        my = (ct + cb) // 2
        painter.fillRect(mx - 8, ct - 1, 16, bracket_thick, QColor("#ffffff"))
        painter.fillRect(mx - 8, cb - bracket_thick + 1, 16, bracket_thick, QColor("#ffffff"))
        painter.fillRect(cl - 1, my - 8, bracket_thick, 16, QColor("#ffffff"))
        painter.fillRect(cr - bracket_thick + 1, my - 8, bracket_thick, 16, QColor("#ffffff"))

        painter.end()


class ScreenshotMiniEditorDialog(QDialog):
    """
    Studio-Grade Image Editor:
    Interactive 8-Handle Box Cropping, Aspect Ratios, Rotation, Live Brightness/Contrast Sliders,
    Natural Filter Chip Selection, and Direct Save Dialog.
    """

    def __init__(self, image_path, parent=None, app=None, on_saved=None):
        super().__init__(parent, Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.image_path = image_path
        self.app = app
        self.on_saved = on_saved

        # State
        self.rotation_angle = 0
        self.brightness_val = 0
        self.contrast_val = 0
        self.active_filter = "normal"
        self.crop_history = []

        try:
            self.base_pil_image = PILImage.open(self.image_path).convert("RGB")
            self.original_raw_image = self.base_pil_image.copy()
        except Exception as e:
            logger.error(f"Error loading image in editor {image_path}: {e}")
            self.base_pil_image = None
            self.original_raw_image = None

        self.resize(980, 640)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 18, 18, 18)

        self.card = QFrame()
        self.card.setObjectName("EditorCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        # 1. Header (Clean typography, no emojis)
        row_top = QHBoxLayout()
        self.lbl_title = QLabel(c.t("UI_SCREENSHOTS_EDITOR_TITLE", filename=os.path.basename(image_path)))
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        row_top.addWidget(self.lbl_title, 1)

        btn_close = QPushButton("✕")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setFixedSize(28, 28)
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 14px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background: rgba(239, 68, 68, 0.85); border-color: transparent; }
        """)
        row_top.addWidget(btn_close, 0)
        card_layout.addLayout(row_top)

        # 2. Main Workspace (Canvas + Tools Panel)
        row_work = QHBoxLayout()
        row_work.setSpacing(16)

        # Canvas
        self.preview_widget = CropImageWidget()
        self.preview_widget.cropSelectionChanged.connect(self._on_crop_selection_changed)
        row_work.addWidget(self.preview_widget, 1)

        # Controls Sidebar
        panel_ctrl = QFrame()
        panel_ctrl.setFixedWidth(280)
        panel_ctrl.setStyleSheet("background: rgba(255, 255, 255, 0.04); border-radius: 12px; padding: 6px;")
        col_ctrl = QVBoxLayout(panel_ctrl)
        col_ctrl.setContentsMargins(12, 12, 12, 12)
        col_ctrl.setSpacing(8)

        # --- Section 1: Recorte & Proporción ---
        lbl_crop = QLabel(c.t("UI_SCREENSHOTS_SECTION_CROP"))
        lbl_crop.setStyleSheet("font-size: 12px; font-weight: 700; color: #38bdf8;")
        col_ctrl.addWidget(lbl_crop)

        # Ratio Chips
        row_ratios = QHBoxLayout()
        row_ratios.setSpacing(6)
        self.btn_ratio_free = QPushButton(c.t("UI_SCREENSHOTS_RATIO_FREE"))
        self.btn_ratio_16_9 = QPushButton("16:9")
        self.btn_ratio_4_3 = QPushButton("4:3")
        self.btn_ratio_1_1 = QPushButton("1:1")
        self.ratio_buttons = [self.btn_ratio_free, self.btn_ratio_16_9, self.btn_ratio_4_3, self.btn_ratio_1_1]

        for btn in self.ratio_buttons:
            btn.setFixedHeight(26)
            btn.setCursor(Qt.PointingHandCursor)
            row_ratios.addWidget(btn)

        self.btn_ratio_free.clicked.connect(lambda: self._set_ratio(None, self.btn_ratio_free))
        self.btn_ratio_16_9.clicked.connect(lambda: self._set_ratio(16 / 9.0, self.btn_ratio_16_9))
        self.btn_ratio_4_3.clicked.connect(lambda: self._set_ratio(4 / 3.0, self.btn_ratio_4_3))
        self.btn_ratio_1_1.clicked.connect(lambda: self._set_ratio(1.0, self.btn_ratio_1_1))
        col_ctrl.addLayout(row_ratios)

        row_crop_acts = QHBoxLayout()
        self.btn_apply_crop = QPushButton(c.t("UI_SCREENSHOTS_APPLY_CROP"))
        self.btn_apply_crop.setFixedHeight(28)
        self.btn_apply_crop.setEnabled(False)
        self.btn_apply_crop.setCursor(Qt.PointingHandCursor)
        self.btn_apply_crop.clicked.connect(self._apply_crop)

        self.btn_undo_crop = QPushButton(c.t("UI_SCREENSHOTS_UNDO_CROP"))
        self.btn_undo_crop.setFixedHeight(28)
        self.btn_undo_crop.setEnabled(False)
        self.btn_undo_crop.setCursor(Qt.PointingHandCursor)
        self.btn_undo_crop.clicked.connect(self._undo_crop)

        row_crop_acts.addWidget(self.btn_apply_crop, 1)
        row_crop_acts.addWidget(self.btn_undo_crop, 0)
        col_ctrl.addLayout(row_crop_acts)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("background: rgba(255, 255, 255, 0.08); max-height: 1px;")
        col_ctrl.addWidget(sep1)

        # --- Section 2: Rotación ---
        lbl_rot = QLabel(c.t("UI_SCREENSHOTS_SECTION_ROTATION"))
        lbl_rot.setStyleSheet("font-size: 12px; font-weight: 700; color: #dedede;")
        col_ctrl.addWidget(lbl_rot)

        row_rot = QHBoxLayout()
        self.btn_rot_left = QPushButton(c.t("UI_SCREENSHOTS_ROTATE_LEFT"))
        self.btn_rot_left.setFixedHeight(28)
        self.btn_rot_left.setCursor(Qt.PointingHandCursor)
        self.btn_rot_left.clicked.connect(lambda: self._rotate(-90))

        self.btn_rot_right = QPushButton(c.t("UI_SCREENSHOTS_ROTATE_RIGHT"))
        self.btn_rot_right.setFixedHeight(28)
        self.btn_rot_right.setCursor(Qt.PointingHandCursor)
        self.btn_rot_right.clicked.connect(lambda: self._rotate(90))

        row_rot.addWidget(self.btn_rot_left)
        row_rot.addWidget(self.btn_rot_right)
        col_ctrl.addLayout(row_rot)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background: rgba(255, 255, 255, 0.08); max-height: 1px;")
        col_ctrl.addWidget(sep2)

        # --- Section 3: Ajustes de Color ---
        lbl_adj = QLabel(c.t("UI_SCREENSHOTS_COLOR_ADJ"))
        lbl_adj.setStyleSheet("font-size: 12px; font-weight: 700; color: #dedede;")
        col_ctrl.addWidget(lbl_adj)

        row_b_lbl = QHBoxLayout()
        self.lbl_bright_name = QLabel(c.t("UI_SCREENSHOTS_BRIGHTNESS"))
        self.lbl_bright_name.setStyleSheet("font-size: 11px; color: #9aa0a6;")
        self.lbl_bright_val = QLabel("0")
        self.lbl_bright_val.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffffff;")
        row_b_lbl.addWidget(self.lbl_bright_name)
        row_b_lbl.addStretch(1)
        row_b_lbl.addWidget(self.lbl_bright_val)
        col_ctrl.addLayout(row_b_lbl)

        self.slider_bright = QSlider(Qt.Horizontal)
        self.slider_bright.setRange(-50, 50)
        self.slider_bright.setValue(0)
        self.slider_bright.valueChanged.connect(self._on_brightness_change)
        col_ctrl.addWidget(self.slider_bright)

        row_c_lbl = QHBoxLayout()
        self.lbl_contrast_name = QLabel(c.t("UI_SCREENSHOTS_CONTRAST"))
        self.lbl_contrast_name.setStyleSheet("font-size: 11px; color: #9aa0a6;")
        self.lbl_contrast_val = QLabel("0")
        self.lbl_contrast_val.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffffff;")
        row_c_lbl.addWidget(self.lbl_contrast_name)
        row_c_lbl.addStretch(1)
        row_c_lbl.addWidget(self.lbl_contrast_val)
        col_ctrl.addLayout(row_c_lbl)

        self.slider_contrast = QSlider(Qt.Horizontal)
        self.slider_contrast.setRange(-50, 50)
        self.slider_contrast.setValue(0)
        self.slider_contrast.valueChanged.connect(self._on_contrast_change)
        col_ctrl.addWidget(self.slider_contrast)

        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.HLine)
        sep3.setStyleSheet("background: rgba(255, 255, 255, 0.08); max-height: 1px;")
        col_ctrl.addWidget(sep3)

        # --- Section 4: Filtros (Natural Segmented Selection) ---
        lbl_filters = QLabel(c.t("UI_SCREENSHOTS_FILTERS"))
        lbl_filters.setStyleSheet("font-size: 12px; font-weight: 700; color: #dedede;")
        col_ctrl.addWidget(lbl_filters)

        row_f1 = QHBoxLayout()
        row_f1.setSpacing(6)
        self.btn_f_norm = QPushButton(c.t("UI_SCREENSHOTS_FILTER_NORMAL"))
        self.btn_f_bw = QPushButton(c.t("UI_SCREENSHOTS_FILTER_BW"))
        self.btn_f_norm.setFixedHeight(28)
        self.btn_f_bw.setFixedHeight(28)
        self.btn_f_norm.clicked.connect(lambda: self._set_filter("normal"))
        self.btn_f_bw.clicked.connect(lambda: self._set_filter("bw"))
        row_f1.addWidget(self.btn_f_norm)
        row_f1.addWidget(self.btn_f_bw)
        col_ctrl.addLayout(row_f1)

        row_f2 = QHBoxLayout()
        row_f2.setSpacing(6)
        self.btn_f_warm = QPushButton(c.t("UI_SCREENSHOTS_FILTER_WARM"))
        self.btn_f_vivid = QPushButton(c.t("UI_SCREENSHOTS_FILTER_VIVID"))
        self.btn_f_warm.setFixedHeight(28)
        self.btn_f_vivid.setFixedHeight(28)
        self.btn_f_warm.clicked.connect(lambda: self._set_filter("warm"))
        self.btn_f_vivid.clicked.connect(lambda: self._set_filter("vivid"))
        row_f2.addWidget(self.btn_f_warm)
        row_f2.addWidget(self.btn_f_vivid)
        col_ctrl.addLayout(row_f2)

        self.filter_buttons = {
            "normal": self.btn_f_norm,
            "bw": self.btn_f_bw,
            "warm": self.btn_f_warm,
            "vivid": self.btn_f_vivid
        }

        col_ctrl.addStretch(1)

        # --- Section 5: Acciones Finales ---
        self.btn_reset_all = QPushButton(c.t("UI_SCREENSHOTS_RESET_ALL"))
        self.btn_reset_all.setFixedHeight(30)
        self.btn_reset_all.setCursor(Qt.PointingHandCursor)
        self.btn_reset_all.clicked.connect(self._reset_all)
        col_ctrl.addWidget(self.btn_reset_all)

        self.btn_save_copy = QPushButton(c.t("UI_SCREENSHOTS_SAVE_COPY"))
        self.btn_save_copy.setFixedHeight(36)
        self.btn_save_copy.setCursor(Qt.PointingHandCursor)
        self.btn_save_copy.clicked.connect(self._save_copy)
        col_ctrl.addWidget(self.btn_save_copy)

        row_work.addWidget(panel_ctrl, 0)
        card_layout.addLayout(row_work, 1)

        self._layout.addWidget(self.card)

        self._update_filter_styles()
        self._update_ratio_styles(self.btn_ratio_free)
        self._update_preview()
        self._apply_styling()

    def _set_ratio(self, ratio, active_btn):
        self.preview_widget.set_aspect_ratio(ratio)
        self._update_ratio_styles(active_btn)

    def _update_ratio_styles(self, active_btn):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        for btn in self.ratio_buttons:
            if btn is active_btn:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_to_rgba(accent, 0.40)};
                        color: #ffffff;
                        border: 1.5px solid {accent};
                        border-radius: 6px;
                        font-size: 11px;
                        font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {{
                        background-color: rgba(255, 255, 255, 0.05);
                        color: #a0a6b0;
                        border: 1px solid rgba(255, 255, 255, 0.10);
                        border-radius: 6px;
                        font-size: 11px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 0.10);
                        color: #ffffff;
                    }}
                """)

    def _on_crop_selection_changed(self, has_crop):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        self.btn_apply_crop.setEnabled(has_crop)
        if has_crop:
            self.btn_apply_crop.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent};
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 11px;
                }}
                QPushButton:hover {{ background-color: {adjust_color(accent, 1.15)}; }}
            """)
        else:
            self.btn_apply_crop.setStyleSheet("")

    def _apply_crop(self):
        if not self.base_pil_image:
            return
        proc_img = self._get_processed_pil_image()
        if not proc_img:
            return

        pixel_rect = self.preview_widget.get_pixel_crop_bounds(proc_img.width, proc_img.height)
        if pixel_rect:
            self.crop_history.append(self.base_pil_image.copy())
            self.btn_undo_crop.setEnabled(True)

            if self.rotation_angle != 0:
                self.base_pil_image = self.base_pil_image.rotate(-self.rotation_angle, expand=True)
                self.rotation_angle = 0

            self.base_pil_image = self.base_pil_image.crop(pixel_rect)
            self.preview_widget.reset_crop()
            self._update_preview()

    def _undo_crop(self):
        if self.crop_history:
            self.base_pil_image = self.crop_history.pop()
            self.btn_undo_crop.setEnabled(len(self.crop_history) > 0)
            self.preview_widget.reset_crop()
            self._update_preview()

    def _reset_all(self):
        if self.original_raw_image:
            self.base_pil_image = self.original_raw_image.copy()
            self.crop_history.clear()
            self.btn_undo_crop.setEnabled(False)
            self.rotation_angle = 0
            self.brightness_val = 0
            self.contrast_val = 0
            self.active_filter = "normal"
            self.slider_bright.setValue(0)
            self.slider_contrast.setValue(0)
            self.lbl_bright_val.setText("0")
            self.lbl_contrast_val.setText("0")
            self._update_filter_styles()
            self._update_ratio_styles(self.btn_ratio_free)
            self.preview_widget.reset_crop()
            self._update_preview()

    def _rotate(self, angle):
        self.rotation_angle = (self.rotation_angle + angle) % 360
        self.preview_widget.reset_crop()
        self._update_preview()

    def _on_brightness_change(self, val):
        self.brightness_val = val
        self.lbl_bright_val.setText(f"{'+' if val > 0 else ''}{val}")
        self._update_preview()

    def _on_contrast_change(self, val):
        self.contrast_val = val
        self.lbl_contrast_val.setText(f"{'+' if val > 0 else ''}{val}")
        self._update_preview()

    def _set_filter(self, name):
        self.active_filter = name
        self._update_filter_styles()
        self._update_preview()

    def _update_filter_styles(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        for key, btn in self.filter_buttons.items():
            if key == self.active_filter:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {accent};
                        color: #ffffff;
                        border: 1.5px solid {adjust_color(accent, 1.25)};
                        border-radius: 6px;
                        font-size: 11px;
                        font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {{
                        background-color: rgba(255, 255, 255, 0.06);
                        color: #c4c7c5;
                        border: 1px solid rgba(255, 255, 255, 0.10);
                        border-radius: 6px;
                        font-size: 11px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 0.12);
                        color: #ffffff;
                    }}
                """)

    def _get_processed_pil_image(self):
        if not self.base_pil_image:
            return None
        img = self.base_pil_image.copy()

        # 1. Rotate
        if self.rotation_angle != 0:
            img = img.rotate(-self.rotation_angle, expand=True)

        # 2. Brightness
        if self.brightness_val != 0:
            factor = 1.0 + (self.brightness_val / 50.0)
            img = ImageEnhance.Brightness(img).enhance(max(0.1, factor))

        # 3. Contrast
        if self.contrast_val != 0:
            factor = 1.0 + (self.contrast_val / 50.0)
            img = ImageEnhance.Contrast(img).enhance(max(0.1, factor))

        # 4. Filters
        if self.active_filter == "bw":
            img = ImageOps.grayscale(img).convert("RGB")
        elif self.active_filter == "warm":
            r, g, b = img.split()
            r = ImageEnhance.Brightness(r).enhance(1.15)
            b = ImageEnhance.Brightness(b).enhance(0.85)
            img = PILImage.merge("RGB", (r, g, b))
        elif self.active_filter == "vivid":
            img = ImageEnhance.Color(img).enhance(1.5)

        return img

    def _update_preview(self):
        pil_img = self._get_processed_pil_image()
        if pil_img:
            rgb_bytes = pil_img.tobytes("raw", "RGB")
            qimg = QImage(rgb_bytes, pil_img.width, pil_img.height, pil_img.width * 3, QImage.Format_RGB888)
            pix = QPixmap.fromImage(qimg)
            self.preview_widget.set_pixmap(pix)

    def _save_copy(self):
        """Open system file picker so the user can choose where to save the edited image."""
        img = self._get_processed_pil_image()
        if not img:
            return

        base, _ = os.path.splitext(os.path.basename(self.image_path))
        now_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        default_filename = f"{base}_edit_{now_str}.png"
        
        default_dir = os.path.expanduser(f"~/Imágenes/{default_filename}")
        if not os.path.exists(os.path.expanduser("~/Imágenes")):
            default_dir = os.path.expanduser(f"~/{default_filename}")

        dest_path = ask_save_filename_native(
            self,
            title=c.t("UI_SCREENSHOTS_SAVE_TITLE"),
            filetypes=[("Imágenes PNG", "*.png"), ("Imágenes JPEG", "*.jpg *.jpeg")],
            default_name=default_dir
        )
        if not dest_path:
            return

        try:
            img.save(dest_path)
            self.btn_save_copy.setText(c.t("UI_SCREENSHOTS_SAVED"))
            if callable(self.on_saved):
                self.on_saved()
            QTimer.singleShot(1200, self.close)
        except Exception as e:
            logger.error(f"Error saving edited screenshot {dest_path}: {e}")
            messagebox.showerror(self, "Error", f"No se pudo guardar la imagen: {e}")

    def retranslate_ui(self):
        self.lbl_title.setText(c.t("UI_SCREENSHOTS_EDITOR_TITLE", filename=os.path.basename(self.image_path)))
        self.btn_ratio_free.setText(c.t("UI_SCREENSHOTS_RATIO_FREE"))
        self.btn_apply_crop.setText(c.t("UI_SCREENSHOTS_APPLY_CROP"))
        self.btn_undo_crop.setText(c.t("UI_SCREENSHOTS_UNDO_CROP"))
        self.btn_rot_left.setText(c.t("UI_SCREENSHOTS_ROTATE_LEFT"))
        self.btn_rot_right.setText(c.t("UI_SCREENSHOTS_ROTATE_RIGHT"))
        self.lbl_bright_name.setText(c.t("UI_SCREENSHOTS_BRIGHTNESS"))
        self.lbl_contrast_name.setText(c.t("UI_SCREENSHOTS_CONTRAST"))
        self.btn_f_norm.setText(c.t("UI_SCREENSHOTS_FILTER_NORMAL"))
        self.btn_f_bw.setText(c.t("UI_SCREENSHOTS_FILTER_BW"))
        self.btn_f_warm.setText(c.t("UI_SCREENSHOTS_FILTER_WARM"))
        self.btn_f_vivid.setText(c.t("UI_SCREENSHOTS_FILTER_VIVID"))
        self.btn_reset_all.setText(c.t("UI_SCREENSHOTS_RESET_ALL"))
        self.btn_save_copy.setText(c.t("UI_SCREENSHOTS_SAVE_COPY"))

    def _apply_styling(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        self.card.setStyleSheet(f"""
            QFrame#EditorCard {{
                background-color: #141518;
                border: 1px solid {hex_to_rgba(accent, 0.6)};
                border-radius: 16px;
            }}
            QPushButton {{
                background: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {hex_to_rgba(accent, 0.28)};
                border-color: {accent};
            }}
            QPushButton:disabled {{
                background: rgba(255, 255, 255, 0.03);
                color: #4b5563;
                border-color: rgba(255, 255, 255, 0.05);
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: rgba(255, 255, 255, 0.15);
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: #ffffff;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
        """)
        self.btn_save_copy.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {adjust_color(accent, 1.15)};
            }}
        """)


# =========================================================================
# Screenshot Card Widget
# =========================================================================

class ScreenshotCardWidget(QFrame):
    """Card displaying thumbnail, metadata, and instant actions (View, Edit, Copy, Save, Delete)."""

    def __init__(self, file_path, app=None, parent_tab=None, scan_info=None):
        super().__init__()
        self.file_path = file_path
        self.app = app
        self.parent_tab = parent_tab
        self.scan_info = scan_info or {}
        self.setObjectName("ScreenshotCard")
        self.setFixedSize(240, 206)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(5)

        # 1. Thumbnail Container
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedHeight(120)
        self.lbl_thumb.setAlignment(Qt.AlignCenter)
        self.lbl_thumb.setCursor(Qt.PointingHandCursor)
        self.lbl_thumb.mousePressEvent = lambda e: self._open_viewer()
        self._layout.addWidget(self.lbl_thumb)

        # 2. Metadata / Date Label
        self.lbl_name = QLabel()
        self.lbl_name.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffffff;")
        self.lbl_name.setWordWrap(False)
        self._layout.addWidget(self.lbl_name)

        self.lbl_meta = QLabel()
        self.lbl_meta.setStyleSheet("font-size: 10px; color: #8c8c8c;")
        self._layout.addWidget(self.lbl_meta)

        # 3. Action Toolbar (Copy, Edit, Export, Delete)
        row_actions = QHBoxLayout()
        row_actions.setContentsMargins(0, 2, 0, 0)
        row_actions.setSpacing(6)

        self.btn_copy = QPushButton()
        self.btn_copy.setToolTip(c.t("UI_SCREENSHOTS_TOOLTIP_COPY"))
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.setFixedSize(28, 24)
        self.btn_copy.clicked.connect(self._copy_to_clipboard)

        self.btn_edit = QPushButton()
        self.btn_edit.setToolTip(c.t("UI_SCREENSHOTS_TOOLTIP_EDIT"))
        self.btn_edit.setCursor(Qt.PointingHandCursor)
        self.btn_edit.setFixedSize(28, 24)
        self.btn_edit.clicked.connect(self._open_editor)

        self.btn_export = QPushButton()
        self.btn_export.setToolTip(c.t("UI_SCREENSHOTS_TOOLTIP_EXPORT"))
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setFixedSize(28, 24)
        self.btn_export.clicked.connect(self._export_image)

        self.btn_delete = QPushButton()
        self.btn_delete.setToolTip(c.t("UI_SCREENSHOTS_TOOLTIP_DELETE"))
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setFixedSize(28, 24)
        self.btn_delete.clicked.connect(self._delete_image)

        row_actions.addWidget(self.btn_copy)
        row_actions.addWidget(self.btn_edit)
        row_actions.addWidget(self.btn_export)
        row_actions.addStretch(1)
        row_actions.addWidget(self.btn_delete)

        self._layout.addLayout(row_actions)

        self._load_data()
        self.update_theme_styles()

    def _load_data(self):
        filename = os.path.basename(self.file_path)

        # Elide long UUID filenames cleanly inside the card width
        fm = self.lbl_name.fontMetrics()
        elided_name = fm.elidedText(filename, Qt.ElideMiddle, 215)
        self.lbl_name.setText(elided_name)
        self.lbl_name.setToolTip(filename)

        date_str = self.scan_info.get("date_str", "")
        if not date_str:
            try:
                mtime = os.path.getmtime(self.file_path)
                dt = datetime.fromtimestamp(mtime)
                date_str = dt.strftime("%d/%m/%Y %H:%M")
            except OSError:
                date_str = "Desconocida"

        size_kb = self.scan_info.get("size_kb")
        if size_kb is None:
            try:
                size_kb = os.path.getsize(self.file_path) / 1024.0
            except OSError:
                size_kb = 0

        self.lbl_meta.setText(f"{date_str} • {size_kb:.0f} KB")

        thumbnail = self.scan_info.get("thumbnail")
        if thumbnail is not None and not thumbnail.isNull():
            self.lbl_thumb.setPixmap(QPixmap.fromImage(thumbnail))
        elif os.path.exists(self.file_path):
            pix = QPixmap(self.file_path)
            if not pix.isNull():
                self.lbl_thumb.setPixmap(pix.scaled(220, 115, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _open_viewer(self):
        modal = ScreenshotImageViewerModal(self.file_path, parent=self.window(), app=self.app)
        modal.exec_()

    def _open_editor(self):
        editor = ScreenshotMiniEditorDialog(
            self.file_path, parent=self.window(), app=self.app,
            on_saved=lambda: self.parent_tab.load_screenshots() if self.parent_tab else None
        )
        editor.exec_()

    def _copy_to_clipboard(self):
        if os.path.exists(self.file_path):
            img = QImage(self.file_path)
            if not img.isNull():
                QApplication.clipboard().setImage(img)
                icon_check = ImageManager.get_tinted_icon(resource_path("check_circle_icon.svg"), "#10b981", 14)
                if icon_check:
                    self.btn_copy.setIcon(icon_check)
                QTimer.singleShot(1400, self.update_theme_styles)

    def retranslate_ui(self):
        self.btn_copy.setToolTip(c.t("UI_SCREENSHOTS_TOOLTIP_COPY"))
        self.btn_edit.setToolTip(c.t("UI_SCREENSHOTS_TOOLTIP_EDIT"))
        self.btn_export.setToolTip(c.t("UI_SCREENSHOTS_TOOLTIP_EXPORT"))
        self.btn_delete.setToolTip(c.t("UI_SCREENSHOTS_TOOLTIP_DELETE"))

    def _export_image(self):
        if not os.path.exists(self.file_path):
            return
        default_path = os.path.expanduser(f"~/Imágenes/{os.path.basename(self.file_path)}")
        dest = ask_save_filename_native(
            self,
            title=c.t("UI_SCREENSHOTS_SAVE_TITLE"),
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg")],
            default_name=default_path
        )
        if dest:
            shutil.copy2(self.file_path, dest)
            icon_check = ImageManager.get_tinted_icon(resource_path("check_circle_icon.svg"), "#10b981", 14)
            if icon_check:
                self.btn_export.setIcon(icon_check)
            QTimer.singleShot(1400, self.update_theme_styles)

    def _delete_image(self):
        if messagebox.askyesno(self.parent_tab, c.t("UI_SCREENSHOTS_DELETE_TITLE"), c.t("UI_SCREENSHOTS_DELETE_CONFIRM")):
            try:
                os.remove(self.file_path)
                json_p = os.path.splitext(self.file_path)[0] + ".json"
                if os.path.exists(json_p):
                    os.remove(json_p)
                mc_p = os.path.splitext(self.file_path)[0] + ".mc"
                if os.path.exists(mc_p):
                    os.remove(mc_p)
                if self.parent_tab:
                    self.parent_tab.load_screenshots()
            except OSError as e:
                messagebox.showerror(self.parent_tab, "Error", f"No se pudo eliminar el archivo: {e}")

    def update_theme_styles(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        # Card base styling
        self.setStyleSheet(f"""
            QFrame#ScreenshotCard {{
                background-color: {"rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                border: 1px solid {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"};
                border-radius: 12px;
            }}
            QFrame#ScreenshotCard:hover {{
                background-color: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
                border: 1px solid {hex_to_rgba(accent, 0.7)};
            }}
        """)

        # Thumbnail background
        self.lbl_thumb.setStyleSheet(f"""
            background-color: {"#0d0e11" if is_dark else "#e5e7eb"};
            border-radius: 8px;
            border: 1px solid {"rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.05)"};
        """)

        # Text labels
        self.lbl_name.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {'#ffffff' if is_dark else '#18191c'}; background: transparent; border: none;")
        self.lbl_meta.setStyleSheet(f"font-size: 10px; color: {'#9aa0a6' if is_dark else '#6b7280'}; background: transparent; border: none;")

        # Icons color
        icon_color = "#ffffff" if is_dark else "#18191c"
        icon_copy = ImageManager.get_tinted_icon(resource_path("copy_clipboard_icon.svg"), icon_color, size=(14, 14))
        icon_edit = ImageManager.get_tinted_icon(resource_path("edit_pencil_icon.svg"), icon_color, size=(14, 14))
        icon_export = ImageManager.get_tinted_icon(resource_path("export_download_icon.svg"), icon_color, size=(14, 14))
        icon_trash = ImageManager.get_tinted_icon(resource_path("trash_delete_icon.svg"), "#ef4444", size=(14, 14))

        if icon_copy:
            self.btn_copy.setIcon(icon_copy)
        if icon_edit:
            self.btn_edit.setIcon(icon_edit)
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
        self.btn_copy.setStyleSheet(btn_card_style)
        self.btn_edit.setStyleSheet(btn_card_style)
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


# =========================================================================
# Main Screenshots Tab Widget
# =========================================================================

class ScreenshotsTab(QWidget):
    """Unified Screenshots Gallery & Manager View for Minecraft Bedrock."""

    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self._screenshot_scan_worker = None
        self._screenshot_scan_pending = False

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(28, 24, 28, 20)
        self._main_layout.setSpacing(14)

        # 1. Header (Brand Badge & Titles)
        row_brand = QHBoxLayout()
        row_brand.setSpacing(14)

        self.badge_camera = QLabel()
        self.badge_camera.setFixedSize(44, 44)
        self.badge_camera.setAlignment(Qt.AlignCenter)
        row_brand.addWidget(self.badge_camera, 0, Qt.AlignVCenter)

        col_brand_text = QVBoxLayout()
        col_brand_text.setContentsMargins(0, 0, 0, 0)
        col_brand_text.setSpacing(2)

        self.lbl_brand_title = QLabel(c.t("UI_SCREENSHOTS_HEADER_TITLE"))
        self.lbl_brand_sub = QLabel(c.t("UI_SCREENSHOTS_HEADER_SUBTITLE"))
        col_brand_text.addWidget(self.lbl_brand_title)
        col_brand_text.addWidget(self.lbl_brand_sub)
        row_brand.addLayout(col_brand_text, 1)

        self._main_layout.addLayout(row_brand)

        # 2. Toolbar (Count, Open Folder, Refresh)
        self.row_toolbar = QHBoxLayout()
        self.lbl_count = QLabel(c.t("UI_SCREENSHOTS_COUNT_LABEL", count=0, plural="s"))
        self.lbl_count.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        self.row_toolbar.addWidget(self.lbl_count)
        self.row_toolbar.addStretch(1)

        self.btn_open_folder = QPushButton(c.t("UI_SCREENSHOTS_BTN_OPEN_FOLDER"))
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_folder.setFixedHeight(32)
        self.btn_open_folder.clicked.connect(self._open_screenshots_folder)
        self.row_toolbar.addWidget(self.btn_open_folder)

        self.btn_refresh = QPushButton(c.t("UI_SCREENSHOTS_BTN_REFRESH"))
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setFixedHeight(32)
        self.btn_refresh.clicked.connect(self.load_screenshots)
        self.row_toolbar.addWidget(self.btn_refresh)

        self._main_layout.addLayout(self.row_toolbar)

        # 3. Empty State Card
        self.card_empty = QFrame()
        self.card_empty.setObjectName("EmptyStateCard")
        empty_layout = QVBoxLayout(self.card_empty)
        empty_layout.setContentsMargins(24, 32, 24, 32)
        empty_layout.setSpacing(10)
        empty_layout.setAlignment(Qt.AlignCenter)

        self.lbl_empty_title = QLabel(c.t("UI_SCREENSHOTS_EMPTY_TITLE"))
        self.lbl_empty_title.setAlignment(Qt.AlignCenter)
        self.lbl_empty_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        empty_layout.addWidget(self.lbl_empty_title)

        self.lbl_empty_desc = QLabel(c.t("UI_SCREENSHOTS_EMPTY_DESC"))
        self.lbl_empty_desc.setAlignment(Qt.AlignCenter)
        self.lbl_empty_desc.setWordWrap(True)
        self.lbl_empty_desc.setStyleSheet("font-size: 12px; color: #a0a6b0; max-width: 500px;")
        empty_layout.addWidget(self.lbl_empty_desc)

        self.btn_empty_open = QPushButton(c.t("UI_SCREENSHOTS_EMPTY_OPEN_BTN"))
        self.btn_empty_open.setCursor(Qt.PointingHandCursor)
        self.btn_empty_open.setFixedHeight(36)
        self.btn_empty_open.setFixedWidth(240)
        self.btn_empty_open.clicked.connect(self._open_screenshots_folder)
        empty_layout.addWidget(self.btn_empty_open, 0, Qt.AlignCenter)

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

    def _open_screenshots_folder(self):
        home = os.path.expanduser("~")
        p = os.path.join(home, ".local", "share", "mcpelauncher", "games", "com.mojang", "Screenshots")
        if os.path.isdir(p):
            open_folder(p)
            return
        elif self.app and getattr(self.app, "active_path", None):
            p2 = os.path.join(self.app.active_path, "games", "com.mojang", "Screenshots")
            if os.path.isdir(p2):
                open_folder(p2)
                return
        os.makedirs(p, exist_ok=True)
        open_folder(p)

    def load_screenshots(self):
        """Request a background gallery scan without blocking the UI."""
        if self._screenshot_scan_worker and self._screenshot_scan_worker.isRunning():
            self._screenshot_scan_pending = True
            return

        active_path = getattr(self.app, "active_path", None) if self.app else None
        worker = ScreenshotScanWorker(active_path)
        self._screenshot_scan_worker = worker
        worker.finished.connect(self._on_screenshots_loaded)
        worker.error.connect(self._on_screenshots_load_error)
        worker.start()

    def _on_screenshots_loaded(self, entries):
        clear_layout(self.grid_layout)
        count = len(entries)
        self.lbl_count.setText(
            c.t("UI_SCREENSHOTS_COUNT_LABEL", count=count, plural="s" if count != 1 else "")
        )

        if count == 0:
            self.card_empty.show()
            self.scroll_area.hide()
        else:
            self.card_empty.hide()
            self.scroll_area.show()
            for entry in entries:
                card = ScreenshotCardWidget(entry["path"], app=self.app, parent_tab=self, scan_info=entry)
                self.grid_layout.addWidget(card)

        self._screenshot_scan_worker = None
        if self._screenshot_scan_pending:
            self._screenshot_scan_pending = False
            self.load_screenshots()

    def _on_screenshots_load_error(self, error):
        logger.warning("Could not scan screenshots: %s", error)
        self._screenshot_scan_worker = None
        if self._screenshot_scan_pending:
            self._screenshot_scan_pending = False
            self.load_screenshots()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "watermark") and self.watermark:
            self.watermark.update_position()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_screenshots()
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

        # Camera Badge Icon (Clean matching sidebar style)
        self.badge_camera.setStyleSheet(f"""
            background-color: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
            border: 1px solid {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.08)"};
            border-radius: 12px;
        """)
        cam_icon_path = resource_path("camera_pixel.svg")
        if os.path.exists(cam_icon_path):
            if is_dark:
                icon = ImageManager.get_icon("camera_pixel.svg")
                pix = QPixmap(24, 24)
                pix.fill(Qt.transparent)
                p = QPainter(pix)
                p.setRenderHint(QPainter.Antialiasing)
                p.setRenderHint(QPainter.SmoothPixmapTransform)
                icon.paint(p, QRect(0, 0, 24, 24))
                p.end()
                self.badge_camera.setPixmap(pix)
            else:
                try:
                    with open(cam_icon_path, "r", encoding="utf-8") as f:
                        svg_content = f.read()
                    svg_light = svg_content.replace('fill="#ffffff"', 'fill="#18191c"').replace('fill="#1e1e24"', 'fill="#f3f4f6"')
                    from PySide6.QtSvg import QSvgRenderer
                    renderer = QSvgRenderer(svg_light.encode("utf-8"))
                    pix = QPixmap(24, 24)
                    pix.fill(Qt.transparent)
                    p = QPainter(pix)
                    renderer.render(p)
                    p.end()
                    self.badge_camera.setPixmap(pix)
                except Exception:
                    self.badge_camera.setPixmap(ImageManager.get_icon("camera_pixel.svg").pixmap(24, 24))

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

        self.btn_empty_open.setStyleSheet(f"""
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
        self.btn_open_folder.setStyleSheet(btn_style)
        self.btn_refresh.setStyleSheet(btn_style)

        # Update child cards
        if hasattr(self, "grid_layout"):
            for i in range(self.grid_layout.count()):
                item = self.grid_layout.itemAt(i)
                if item and item.widget() and hasattr(item.widget(), "update_theme_styles"):
                    item.widget().update_theme_styles()

    def retranslate_ui(self):
        self.lbl_brand_title.setText(c.t("UI_SCREENSHOTS_HEADER_TITLE"))
        self.lbl_brand_sub.setText(c.t("UI_SCREENSHOTS_HEADER_SUBTITLE"))
        self.btn_open_folder.setText(c.t("UI_SCREENSHOTS_BTN_OPEN_FOLDER"))
        self.btn_refresh.setText(c.t("UI_SCREENSHOTS_BTN_REFRESH"))
        self.lbl_empty_title.setText(c.t("UI_SCREENSHOTS_EMPTY_TITLE"))
        self.lbl_empty_desc.setText(c.t("UI_SCREENSHOTS_EMPTY_DESC"))
        self.btn_empty_open.setText(c.t("UI_SCREENSHOTS_EMPTY_OPEN_BTN"))

        screenshot_files = get_screenshot_files(self.app)
        count = len(screenshot_files)
        self.lbl_count.setText(
            c.t("UI_SCREENSHOTS_COUNT_LABEL", count=count, plural="s" if count != 1 else "")
        )

        if hasattr(self, "grid_layout"):
            for i in range(self.grid_layout.count()):
                item = self.grid_layout.itemAt(i)
                if item and item.widget() and hasattr(item.widget(), "retranslate_ui"):
                    item.widget().retranslate_ui()
