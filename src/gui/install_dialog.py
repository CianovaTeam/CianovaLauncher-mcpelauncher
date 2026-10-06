from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFrame, QRadioButton,
                             QTabWidget, QWidget, QComboBox, QProgressBar,
                             QStackedWidget, QSizePolicy, QScrollArea, QBoxLayout)
from PySide6.QtCore import (Qt, QThread, Signal, QProcess, QTimer, QRectF, QRect,
                           QPoint, Property, QPropertyAnimation, QEasingCurve, QSize)
from PySide6.QtGui import (QDragEnterEvent, QDropEvent, QPainter, QColor, QFont, QPen, QPixmap,
                           QConicalGradient, QImage, QLinearGradient, QIcon, QFontMetrics)
import os
import ssl
import zipfile
import re
import math
import urllib.request
import urllib.error
import json
import threading
import time
from src.gui import custom_dialogs as messagebox
from src.gui.custom_dialogs import _find_theme
from src.utils.dialogs import ask_open_filename_native
from src.utils.logger import logger
from src.utils.colors import hex_to_rgba, blend_colors, adjust_color
from src.utils.resource_path import resource_path
from src import constants as c
from src.utils.image_manager import ImageManager


def mask_google_email(email: str) -> str:
    """Mask email preserving only the first 2 letters before @ and the full domain."""
    if not email or "@" not in email:
        return "correo***@gmail.com"
    parts = email.split("@", 1)
    username, domain = parts[0], parts[1]
    if len(username) <= 2:
        masked_user = username + "***"
    else:
        masked_user = username[:2] + "***"
    return f"{masked_user}@{domain}"


class AdaptiveStackedWidget(QStackedWidget):
    """
    QStackedWidget that sizes its minimumSizeHint and sizeHint according
    to the active child page, preventing wide or tall inactive tabs from
    imposing excessive constraints on other tabs.
    """
    def minimumSizeHint(self):
        cw = self.currentWidget()
        if cw is not None:
            return cw.minimumSizeHint()
        return super().minimumSizeHint()

    def sizeHint(self):
        cw = self.currentWidget()
        if cw is not None:
            return cw.sizeHint()
        return super().sizeHint()


class Tactile3DActionButton(QPushButton):
    """
    Tactile 3D push-down action button with rotating theme-adaptive conical glowing aura,
    subtle hover expansion, smooth hover slowdown, and mechanical 3D click response.
    Mirrors the main PLAY button design from PlayTab.
    """
    def __init__(self, text="INSTALAR AHORA", app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self._text = text
        self._press_offset = 0.0
        self._button_scale = 1.0
        self._is_hovered = False
        self._is_pressed = False
        self._glow_angle = 0.0
        self._is_cancel_mode = False
        self._original_text = text
        self.setObjectName("ActionButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(48)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("background: transparent; border: none;")

        self._anim_offset = QPropertyAnimation(self, b"pressOffset", self)
        self._anim_offset.setEasingCurve(QEasingCurve.OutQuad)

        self._anim_scale = QPropertyAnimation(self, b"buttonScale", self)
        self._anim_scale.setEasingCurve(QEasingCurve.OutCubic)

        # Rotating glowing aura timer
        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._on_glow_tick)
        self._glow_timer.start(25)

    def set_cancel_mode(self, enabled: bool):
        self._is_cancel_mode = enabled
        if enabled:
            self._text = "CANCELAR"
            self.setEnabled(True)
        else:
            self._text = self._original_text
        self.update()

    def is_cancel_mode(self):
        return self._is_cancel_mode

    def getPressOffset(self):
        return self._press_offset

    def setPressOffset(self, val):
        self._press_offset = val
        self.update()

    pressOffset = Property(float, getPressOffset, setPressOffset)

    def getButtonScale(self):
        return self._button_scale

    def setButtonScale(self, val):
        self._button_scale = val
        self.update()

    buttonScale = Property(float, getButtonScale, setButtonScale)

    def setText(self, text):
        self._text = text
        if not self._is_cancel_mode:
            self._original_text = text
        self.update()

    def text(self):
        return self._text

    def _on_glow_tick(self):
        if not self.isEnabled():
            return
        speed = 0.7 if self._is_hovered else 2.6
        self._glow_angle = (self._glow_angle + speed) % 360.0
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "_glow_timer") and not self._glow_timer.isActive():
            self._glow_timer.start(25)

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, "_glow_timer") and self._glow_timer.isActive():
            self._glow_timer.stop()

    def enterEvent(self, event):
        if self.isEnabled():
            self._is_hovered = True
            self._animate_scale(1.015, 140)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self._is_pressed = False
        self._animate_scale(1.0, 140)
        if self._press_offset > 0:
            self._animate_offset(0.0, 80)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.isEnabled():
            self._is_pressed = True
            self._animate_scale(1.0, 45)
            self._animate_offset(5.0, 40)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.isEnabled():
            self._is_pressed = False
            target_scale = 1.015 if self._is_hovered else 1.0
            self._animate_scale(target_scale, 90)
            self._animate_offset(0.0, 90)
        super().mouseReleaseEvent(event)

    def _animate_scale(self, target, duration):
        self._anim_scale.stop()
        self._anim_scale.setDuration(duration)
        self._anim_scale.setStartValue(self._button_scale)
        self._anim_scale.setEndValue(target)
        self._anim_scale.start()

    def _animate_offset(self, target, duration):
        self._anim_offset.stop()
        self._anim_offset.setDuration(duration)
        self._anim_offset.setStartValue(self._press_offset)
        self._anim_offset.setEndValue(target)
        self._anim_offset.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = float(self.width())
        h = float(self.height())
        cx, cy = w / 2.0, h / 2.0

        painter.save()
        painter.translate(cx, cy)
        painter.scale(self._button_scale, self._button_scale)
        painter.translate(-cx, -cy)

        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        is_disabled = not self.isEnabled()

        if self._is_cancel_mode:
            accent = "#ef4444"

        c_accent = QColor(accent)
        base_h, base_s, base_v, _ = c_accent.getHsv()

        # 0. Rotating Glowing Conical Aura (when enabled)
        if not is_disabled:
            grad = QConicalGradient(cx, cy, self._glow_angle)
            if self._is_cancel_mode:
                theme_glow_stops = [
                    (0.00, QColor("#ef4444")),
                    (0.25, QColor("#f87171")),
                    (0.50, QColor("#dc2626")),
                    (0.75, QColor("#fca5a5")),
                    (1.00, QColor("#ef4444")),
                ]
            else:
                theme_glow_stops = [
                    (0.00, QColor.fromHsv((base_h + 18) % 360, min(255, base_s + 40), 255)),
                    (0.15, QColor.fromHsv(base_h, max(120, base_s - 30), 240)),
                    (0.30, QColor.fromHsv((base_h - 15) % 360, min(255, base_s + 50), 255)),
                    (0.45, QColor.fromHsv((base_h + 10) % 360, 255, 230)),
                    (0.60, QColor.fromHsv((base_h - 20) % 360, min(255, base_s + 40), 255)),
                    (0.75, QColor.fromHsv(base_h, max(140, base_s - 10), 255)),
                    (0.90, QColor.fromHsv((base_h + 22) % 360, min(255, base_s + 30), 245)),
                    (1.00, QColor.fromHsv((base_h + 18) % 360, min(255, base_s + 40), 255)),
                ]
            for pos, col in theme_glow_stops:
                grad.setColorAt(pos, col)

            base_body_rect = QRectF(10.0, 6.0, w - 20.0, h - 14.0)
            n_steps = 10
            max_expand = 5.5
            for i in range(n_steps):
                t = float(i) / (n_steps - 1)
                expand = 0.5 + t * (max_expand - 0.5)
                alpha = int(140.0 * math.pow(1.0 - t, 1.8))
                if alpha <= 0:
                    continue
                glow_pen = QPen(grad, 1.5)
                painter.setPen(glow_pen)
                painter.setBrush(Qt.NoBrush)
                painter.setOpacity(alpha / 255.0)
                glow_rect = base_body_rect.adjusted(-expand, -expand, expand, expand)
                rad = 8.0 + expand * 0.8
                painter.drawRoundedRect(glow_rect, rad, rad)

            painter.setOpacity(1.0)

        if is_disabled:
            top_color_hex = "#36363c" if is_dark else "#d1d5db"
            top_highlight_hex = "#44444c" if is_dark else "#e5e7eb"
            bevel_color_hex = "#242428" if is_dark else "#9ca3af"
            socket_color_hex = "#18181c" if is_dark else "#6b7280"
        elif self._is_cancel_mode:
            top_color_hex = "#dc2626" if not self._is_hovered else "#ef4444"
            top_highlight_hex = "#fca5a5"
            bevel_color_hex = "#991b1b"
            socket_color_hex = "#450a0a"
        else:
            top_color_hex = adjust_color(accent, 24 if self._is_hovered and not self._is_pressed else 12)
            top_highlight_hex = adjust_color(accent, 60)
            bevel_color_hex = adjust_color(accent, -45)
            socket_color_hex = blend_colors("#0a0a0a", accent, 0.22)

        offset = float(self._press_offset) if not is_disabled else 0.0

        # 1. Base socket / chassis underneath
        socket_radius = 8.0
        socket_rect = QRectF(10.0, 8.0, w - 20.0, h - 16.0)
        painter.setBrush(QColor(socket_color_hex))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(socket_rect, socket_radius, socket_radius)

        # 2. 3D Bevel Body
        btn_radius = 6.0
        bevel_rect = QRectF(12.0, 5.0 + offset, w - 24.0, h - 16.0 - offset)
        painter.setBrush(QColor(bevel_color_hex))
        painter.drawRoundedRect(bevel_rect, btn_radius, btn_radius)

        # 3. Top Face
        top_h = h - 22.0
        top_rect = QRectF(12.0, 5.0 + offset, w - 24.0, top_h)
        painter.setBrush(QColor(top_color_hex))
        painter.drawRoundedRect(top_rect, btn_radius, btn_radius)

        # Inset highlight line at top edge
        highlight_pen = QPen(QColor(top_highlight_hex), 1.2)
        painter.setPen(highlight_pen)
        painter.drawLine(
            int(top_rect.left() + 6),
            int(top_rect.top() + 1),
            int(top_rect.right() - 6),
            int(top_rect.top() + 1)
        )

        # 4. Text
        font = QFont("Helvetica", 12, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.6)
        painter.setFont(font)

        shadow_rect = QRectF(top_rect.x(), top_rect.y() + 1.2, top_rect.width(), top_rect.height())
        painter.setPen(QColor(0, 0, 0, 190))
        painter.drawText(shadow_rect, Qt.AlignCenter, self._text)

        painter.setPen(QColor("#ffffff") if not is_disabled else (QColor("#888888") if is_dark else QColor("#666666")))
        painter.drawText(top_rect, Qt.AlignCenter, self._text)

        painter.restore()
        painter.end()


class GooglePlayLoginButton(QPushButton):
    """
    3D tactile Google Play sign-in button with mechanical push-down animation,
    hover scaling, theme border, and crisp Google favicon.
    """
    def __init__(self, text=None, app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self._text = text if text is not None else c.t("UI_INSTALL_BTN_LOGIN")
        self._press_offset = 0.0
        self._button_scale = 1.0
        self._is_hovered = False
        self._is_pressed = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)
        self.setMinimumWidth(110)
        self.setStyleSheet("background: transparent; border: none;")

        self._icon = ImageManager.get_icon("google_favicon.svg")
        if self._icon.isNull():
            self._icon = ImageManager.get_icon("google_favicon.png")

        self._anim_press = QPropertyAnimation(self, b"pressOffset", self)
        self._anim_press.setDuration(90)
        self._anim_press.setEasingCurve(QEasingCurve.OutQuad)

        self._anim_scale = QPropertyAnimation(self, b"buttonScale", self)
        self._anim_scale.setDuration(120)
        self._anim_scale.setEasingCurve(QEasingCurve.OutCubic)

    def setText(self, text):
        self._text = text
        super().setText(text)
        self.updateGeometry()
        self.update()

    def sizeHint(self):
        font = self.font()
        font.setPointSize(9)
        font.setBold(True)
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self._text)
        return QSize(text_w + 18 + 8 + 36, 44)

    def minimumSizeHint(self):
        return self.sizeHint()

    @Property(float)
    def pressOffset(self):
        return self._press_offset

    @pressOffset.setter
    def pressOffset(self, val):
        self._press_offset = float(val)
        self.update()

    @Property(float)
    def buttonScale(self):
        return self._button_scale

    @buttonScale.setter
    def buttonScale(self, val):
        self._button_scale = float(val)
        self.update()

    def setText(self, text):
        self._text = text
        self.update()

    def text(self):
        return self._text

    def enterEvent(self, event):
        self._is_hovered = True
        self._anim_scale.stop()
        self._anim_scale.setStartValue(self._button_scale)
        self._anim_scale.setEndValue(1.02)
        self._anim_scale.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self._is_pressed = False
        self._anim_scale.stop()
        self._anim_scale.setStartValue(self._button_scale)
        self._anim_scale.setEndValue(1.0)
        self._anim_scale.start()
        if self._press_offset > 0:
            self._anim_press.stop()
            self._anim_press.setStartValue(self._press_offset)
            self._anim_press.setEndValue(0.0)
            self._anim_press.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_pressed = True
            self._anim_press.stop()
            self._anim_press.setStartValue(self._press_offset)
            self._anim_press.setEndValue(1.0)
            self._anim_press.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._is_pressed = False
        self._anim_press.stop()
        self._anim_press.setStartValue(self._press_offset)
        self._anim_press.setEndValue(0.0)
        self._anim_press.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        accent_color = QColor(accent)

        w = float(self.width())
        h = float(self.height())

        # Scale & Mechanical 3D push
        painter.translate(w / 2.0, h / 2.0)
        painter.scale(self._button_scale, self._button_scale)
        painter.translate(-w / 2.0, -h / 2.0)

        sink_px = self._press_offset * 2.0
        margin_x = 5.0
        margin_y = 3.0
        btn_rect = QRectF(margin_x, margin_y + sink_px, w - margin_x * 2, h - margin_y * 2 - sink_px)
        radius = btn_rect.height() / 2.0

        bg_alpha = 60 if is_dark else 40
        if self._is_hovered:
            bg_alpha = 90 if is_dark else 70
        btn_bg = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), bg_alpha)
        border_color = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 180 if is_dark else 150)

        painter.setBrush(btn_bg)
        painter.setPen(QPen(border_color, 1.5))
        painter.drawRoundedRect(btn_rect, radius, radius)

        # Text & Google Icon
        font = painter.font()
        font.setBold(True)
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff" if is_dark else "#111214"))

        icon_size = 18
        spacing = 8
        fm = painter.fontMetrics()
        text_w = fm.horizontalAdvance(self._text)
        total_w = text_w + spacing + icon_size
        start_x = max(10.0, (w - total_w) / 2.0)

        text_rect = QRect(int(start_x), int(margin_y + sink_px), text_w, int(h - margin_y * 2))
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self._text)

        if not self._icon.isNull():
            icon_x = int(start_x + text_w + spacing)
            icon_y = int((h - icon_size) / 2.0 + sink_px)
            self._icon.paint(painter, QRect(icon_x, icon_y, icon_size, icon_size))

        painter.end()

def _fetch_remote_json_with_cache(url: str, cache_filename: str, timeout: int = 6, max_retries: int = 2):
    """
    Fetches JSON from remote URL with resilient retries, mirror fallback (e.g. jsDelivr CDN),
    custom headers, and automatic fallback to local disk cache on network failures.
    """
    cache_dir = os.path.join(c.HOME_DIR, ".cache", "mcpelauncher", "manifests")
    cache_path = os.path.join(cache_dir, cache_filename)

    headers = {
        "User-Agent": f"CianovaLauncher/{c.VERSION_LAUNCHER} (X11; Linux; +https://github.com/PlaGaPlusDev/CianovaLauncher-mcpelauncher)",
        "Accept": "application/json, text/plain, */*",
        "Connection": "close"
    }

    # Generate mirror fallback URL if using raw.githubusercontent.com
    urls_to_try = [url]
    if "raw.githubusercontent.com/PlaGaPlusDev/mcpelauncher-versiondb/master/" in url:
        mirror_url = url.replace(
            "raw.githubusercontent.com/PlaGaPlusDev/mcpelauncher-versiondb/master/",
            "cdn.jsdelivr.net/gh/PlaGaPlusDev/mcpelauncher-versiondb@master/"
        )
        urls_to_try.append(mirror_url)

    last_error = None
    for target_url in urls_to_try:
        for attempt in range(1, max_retries + 1):
            try:
                req = urllib.request.Request(target_url, headers=headers)
                ctx = ssl.create_default_context()
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                    if response.status == 200:
                        raw_content = response.read().decode("utf-8")
                        data = json.loads(raw_content)
                        try:
                            os.makedirs(cache_dir, exist_ok=True)
                            with open(cache_path, "w", encoding="utf-8") as f:
                                f.write(raw_content)
                        except Exception as cache_err:
                            logger.warning(f"Failed writing cache to {cache_path}: {cache_err}")
                        return data
                    else:
                        raise urllib.error.HTTPError(target_url, response.status, f"HTTP {response.status}", response.headers, None)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
                last_error = e
                if isinstance(e, urllib.error.HTTPError) and e.code == 404:
                    break
                if attempt < max_retries:
                    time.sleep(0.4 * attempt)
            except Exception as e:
                last_error = e
                break

    if os.path.isfile(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Loaded cached manifest '{cache_filename}' due to network issue: {last_error}")
            return data
        except Exception as read_err:
            logger.warning(f"Could not load fallback cache '{cache_path}': {read_err}")

    if last_error:
        raise last_error
    raise RuntimeError(f"Failed to fetch {url}")


class VersionFetcher(QThread):
    """Thread that fetches available version data from a remote manifest URL."""
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, arch):
        """Initialize the fetcher with the target CPU architecture."""
        super().__init__()
        self.arch = arch

    def run(self):
        """Fetch version manifest data and emit finished or error signal."""
        try:
            url = c.VERSION_MANIFEST_URL.format(arch=self.arch)
            data = _fetch_remote_json_with_cache(
                url=url,
                cache_filename=f"versions.{self.arch}.json.min",
                timeout=6,
                max_retries=3
            )
            if isinstance(data, list):
                self.finished.emit(data)
            else:
                self.error.emit(c.t("UI_INSTALL_INVALID_MANIFEST"))
        except Exception as e:
            logger.error(f"Error loading versions: {e}")
            self.error.emit(str(e))


class VersionWarningsFetcher(QThread):
    """Thread that fetches version compatibility warnings from a remote JSON."""
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            data = _fetch_remote_json_with_cache(
                url=c.VERSION_WARNINGS_URL,
                cache_filename="version-warnings.json",
                timeout=5,
                max_retries=3
            )
            if isinstance(data, dict):
                self.finished.emit(data.get("warnings", []))
            elif isinstance(data, list):
                self.finished.emit(data)
            else:
                self.finished.emit([])
        except Exception as e:
            logger.warning(f"Failed to fetch version warnings: {e}")
            self.finished.emit([])

class SleekDropdownTrigger(QPushButton):
    """Sleek pill button displaying current value with accent arrow."""
    def __init__(self, text="", app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self._text = text
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(36)
        self.setMinimumWidth(116)
        self.setStyleSheet("background: transparent; border: none;")

    def setText(self, text):
        self._text = text
        self.update()

    def text(self):
        return self._text

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        accent_color = QColor(accent)

        w, h = float(self.width()), float(self.height())
        rect = QRectF(1, 1, w - 2, h - 2)

        if is_dark:
            bg_color = QColor(255, 255, 255, 18 if not self.underMouse() else 35)
            border_color = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 180 if self.underMouse() else 115)
        else:
            bg_color = QColor(0, 0, 0, 12 if not self.underMouse() else 24)
            border_color = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 160 if self.underMouse() else 95)

        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1.0))
        painter.drawRoundedRect(rect, 8, 8)

        font = painter.font()
        font.setBold(True)
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff" if is_dark else "#111214"))

        text_rect = QRect(12, 0, int(w - 32), int(h))
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self._text)

        painter.setPen(accent_color)
        painter.drawText(QRect(int(w - 20), 0, 14, int(h)), Qt.AlignVCenter | Qt.AlignCenter, "▼")
        painter.end()


class SleekDropdownPopup(QWidget):
    """Floating animated dropdown menu for architecture and filter selection."""
    optionSelected = Signal(str)

    def __init__(self, options, current_text="", app=None, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.app = app
        self._options = options
        self._current_text = current_text
        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(4)
        self.setMinimumWidth(130)

        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        for opt in options:
            btn = QPushButton(opt)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.PointingHandCursor)
            is_active = (opt == current_text)
            active_bg = blend_colors("#1c1c1c", accent, 0.16) if is_dark else blend_colors("#e9ecf0", accent, 0.12)
            hover_bg = blend_colors("#282828", accent, 0.25) if is_dark else blend_colors("#dfe3e8", accent, 0.20)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {active_bg if is_active else 'transparent'};
                    color: {'#ffffff' if is_dark else '#111214'};
                    border: none;
                    border-radius: 6px;
                    text-align: left;
                    padding-left: 10px;
                    font-size: 11px;
                    font-weight: {'bold' if is_active else 'normal'};
                }}
                QPushButton:hover {{
                    background: {hover_bg};
                    font-weight: bold;
                }}
            """)
            def make_handler(o=opt):
                return lambda: self._on_select(o)
            btn.clicked.connect(make_handler(opt))
            self._layout.addWidget(btn)

    def _on_select(self, opt):
        self._current_text = opt
        self.optionSelected.emit(opt)
        self.close()

    def show_below(self, target_widget):
        p = target_widget.mapToGlobal(QPoint(0, target_widget.height() + 4))
        self.adjustSize()
        self.move(p.x(), p.y() - 10)
        self._anim.stop()
        self._anim.setStartValue(QPoint(p.x(), p.y() - 10))
        self._anim.setEndValue(p)
        self.show()
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        if is_dark:
            bg_color = QColor(blend_colors("#0e0e0e", accent, 0.05))
        else:
            bg_color = QColor(blend_colors("#ffffff", accent, 0.02))
        painter.setBrush(bg_color)
        painter.setPen(QPen(QColor(accent), 1.2))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 10, 10)
        painter.end()


class SleekCardSelector(QFrame):
    """Wireframe card with icon badge, title label and sleek dropdown trigger button."""
    currentTextChanged = Signal(str)

    def __init__(self, title, icon_name, options, default_value="", app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self._options = options
        self._current_text = default_value or (options[0] if options else "")
        self.setObjectName("SleekCardSelector")
        self.setFixedHeight(64)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        # Icon badge
        self.badge_icon = QFrame()
        self.badge_icon.setFixedSize(38, 38)
        badge_layout = QVBoxLayout(self.badge_icon)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setAlignment(Qt.AlignCenter)

        self.lbl_icon = QLabel()
        self._raw_icon = ImageManager.get_icon(icon_name)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        badge_layout.addWidget(self.lbl_icon)
        layout.addWidget(self.badge_icon, 0, Qt.AlignVCenter)

        # Title
        self.lbl_title = QLabel(title)
        self.lbl_title.setWordWrap(True)
        layout.addWidget(self.lbl_title, 1, Qt.AlignVCenter)

        # Dropdown Trigger
        self.btn_trigger = SleekDropdownTrigger(self._current_text, app=self.app)
        self.btn_trigger.setMinimumWidth(75)
        self.btn_trigger.clicked.connect(self._open_dropdown)
        layout.addWidget(self.btn_trigger, 0, Qt.AlignVCenter)

        self.update_theme_styles()

    def update_theme_styles(self):
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        self.setStyleSheet(f"""
            QFrame#SleekCardSelector {{
                background-color: {"rgba(255, 255, 255, 0.055)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                border: 1px solid {hex_to_rgba(accent, 0.45) if is_dark else hex_to_rgba(accent, 0.35)};
                border-radius: 12px;
            }}
        """)
        self.badge_icon.setStyleSheet(f"""
            background-color: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
            border-radius: 8px;
            border: 1px solid {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.08)"};
        """)
        if not self._raw_icon.isNull():
            pix = self._raw_icon.pixmap(18, 18)
            if not is_dark:
                tinted = QPixmap(pix.size())
                tinted.fill(Qt.transparent)
                p_tint = QPainter(tinted)
                p_tint.drawPixmap(0, 0, pix)
                p_tint.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                p_tint.fillRect(tinted.rect(), QColor("#111214"))
                p_tint.end()
                self.lbl_icon.setPixmap(tinted)
            else:
                self.lbl_icon.setPixmap(pix)
        self.lbl_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {'#ffffff' if is_dark else '#18191c'}; background: transparent; border: none;")
        self.btn_trigger.update()

    def _open_dropdown(self):
        popup = SleekDropdownPopup(self._options, self._current_text, app=self.app, parent=self)
        popup.optionSelected.connect(self._on_option_selected)
        popup.show_below(self.btn_trigger)

    def _on_option_selected(self, opt):
        self._current_text = opt
        self.btn_trigger.setText(opt)
        self.currentTextChanged.emit(opt)

    def currentText(self):
        return self._current_text

    def setCurrentText(self, text):
        if text in self._options:
            self._current_text = text
            self.btn_trigger.setText(text)

    def addItems(self, items):
        self._options = list(items)
        if self._options:
            self._current_text = self._options[0]
            self.btn_trigger.setText(self._current_text)

    def setTitle(self, title):
        self.lbl_title.setText(title)


class VersionListItemButton(QPushButton):
    """Clean version option button with tiny minecraft grass logo and clean semantic name."""
    def __init__(self, display_text, version_data, is_beta=False, is_latest=False, is_selected=False, app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self.version_data = version_data
        self.display_text = display_text
        self.is_beta = is_beta
        self.is_latest = is_latest
        self.is_selected = is_selected
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(38)
        self.setStyleSheet("background: transparent; border: none;")
        self._icon = ImageManager.get_icon("minecraft_logo.png")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        accent_color = QColor(accent)

        w = float(self.width())
        h = float(self.height())
        rect = self.rect().adjusted(2, 2, -2, -2)

        if self.is_selected:
            painter.setBrush(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 70 if is_dark else 40))
            painter.setPen(QPen(accent_color, 1.2))
            painter.drawRoundedRect(rect, 8, 8)
        elif self.underMouse():
            painter.setBrush(QColor(255, 255, 255, 20) if is_dark else QColor(0, 0, 0, 15))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, 8, 8)

        # Draw tiny Minecraft Logo Icon
        icon_size = 20
        icon_x = 10
        icon_y = int((h - icon_size) / 2.0)
        if not self._icon.isNull():
            self._icon.paint(painter, icon_x, icon_y, icon_size, icon_size)

        # Draw Title
        painter.setPen(QColor("#ffffff" if is_dark else "#111214"))
        font = painter.font()
        font.setBold(self.is_selected or self.is_latest)
        font.setPointSize(10 if not self.is_latest else 9)
        painter.setFont(font)

        text_x = icon_x + icon_size + 10
        text_w = int(w - text_x - 70 if (self.is_beta or self.is_latest) else w - text_x - 12)
        painter.drawText(QRect(text_x, 0, text_w, int(h)), Qt.AlignVCenter | Qt.AlignLeft, self.display_text)

        # Optional Pill Tag (BETA / AUTO)
        if self.is_beta:
            tag_rect = QRectF(w - 62, (h - 20) / 2.0, 52, 20)
            painter.setBrush(QColor("#f59e0b" if is_dark else "#d97706"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(tag_rect, 4, 4)
            painter.setPen(QColor("#ffffff"))
            f_tag = QFont(font)
            f_tag.setPointSize(8)
            f_tag.setBold(True)
            painter.setFont(f_tag)
            painter.drawText(tag_rect, Qt.AlignCenter, "BETA")
        elif self.is_latest:
            tag_rect = QRectF(w - 92, (h - 20) / 2.0, 84, 20)
            painter.setBrush(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 180))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(tag_rect, 4, 4)
            painter.setPen(QColor("#ffffff"))
            f_tag = QFont(font)
            f_tag.setPointSize(8)
            f_tag.setBold(True)
            painter.setFont(f_tag)
            painter.drawText(tag_rect, Qt.AlignCenter, "RECOMENDADA")

        painter.end()


class SleekSearchableVersionPopup(QWidget):
    """Floating searchable version selector drawer with smooth real-time filter."""
    versionPicked = Signal(object, str)

    def __init__(self, version_items, selected_data=None, app=None, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.app = app
        self._all_items = version_items
        self._selected_data = selected_data
        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self.setFixedHeight(300)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 1. Search Box
        self.entry_search = QLineEdit()
        self.entry_search.setPlaceholderText(c.t("UI_INSTALL_SEARCH_PLACEHOLDER"))
        self.entry_search.setFixedHeight(34)
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        input_bg = blend_colors("#181818", accent, 0.08) if is_dark else blend_colors("#f8f9fa", accent, 0.03)
        self.entry_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {"#ffffff" if is_dark else "#111214"};
                border: 1px solid {"rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.15)"};
                border-radius: 8px;
                padding-left: 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {accent};
            }}
        """)
        self.entry_search.textChanged.connect(self._filter_list)
        main_layout.addWidget(self.entry_search)

        # 2. Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(3)
        self.scroll_area.setWidget(self.list_container)
        main_layout.addWidget(self.scroll_area, 1)

        self._populate_list("")

    def _populate_list(self, query=""):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        q = query.strip().lower()
        matched = 0
        for info in self._all_items:
            disp = info["display"]
            vname = str(info["data"][1]) if info["data"] else ""
            if q and (q not in disp.lower() and q not in vname.lower()):
                continue

            is_sel = (self._selected_data == info["data"])
            btn = VersionListItemButton(
                info["display"],
                info["data"],
                is_beta=info.get("is_beta", False),
                is_latest=info.get("is_latest", False),
                is_selected=is_sel,
                app=self.app
            )
            def make_handler(d=info["data"], disp_text=info["display"]):
                return lambda: self._on_item_clicked(d, disp_text)
            btn.clicked.connect(make_handler())
            self.list_layout.addWidget(btn)
            matched += 1

        if matched == 0:
            lbl_empty = QLabel(c.t("UI_INSTALL_NO_VERSIONS_FOUND"))
            lbl_empty.setAlignment(Qt.AlignCenter)
            lbl_empty.setStyleSheet("color: #8c8c8c; font-size: 12px; padding: 20px;")
            self.list_layout.addWidget(lbl_empty)

        self.list_layout.addStretch()

    def _filter_list(self, text):
        self._populate_list(text)

    def _on_item_clicked(self, data, disp_text):
        self.versionPicked.emit(data, disp_text)
        self.close()

    def show_below(self, target_widget):
        p = target_widget.mapToGlobal(QPoint(0, target_widget.height() + 4))
        self.setFixedWidth(target_widget.width())
        self.move(p.x(), p.y() - 10)
        self._anim.stop()
        self._anim.setStartValue(QPoint(p.x(), p.y() - 10))
        self._anim.setEndValue(p)
        self.show()
        self._anim.start()
        self.entry_search.setFocus()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        if is_dark:
            bg_color = QColor(blend_colors("#0e0e0e", accent, 0.05))
        else:
            bg_color = QColor(blend_colors("#ffffff", accent, 0.02))
        painter.setBrush(bg_color)
        painter.setPen(QPen(QColor(accent), 1.5))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 12, 12)
        painter.end()


class SleekProgressCard(QFrame):
    """
    Sleek modern card showing download & extraction progress with
    percentage, status text, and an animated themed gradient progress bar.
    """
    def __init__(self, app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self.setObjectName("SleekProgressCard")
        self.setFixedHeight(72)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        row_info = QHBoxLayout()
        row_info.setContentsMargins(0, 0, 0, 0)
        self.lbl_status = QLabel("Descargando...")
        self.lbl_pct = QLabel("0%")

        row_info.addWidget(self.lbl_status, 1, Qt.AlignLeft | Qt.AlignVCenter)
        row_info.addWidget(self.lbl_pct, 0, Qt.AlignRight | Qt.AlignVCenter)
        layout.addLayout(row_info)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.update_theme_styles()

    def setProgress(self, val: int):
        self.progress_bar.setValue(val)
        self.lbl_pct.setText(f"{val}%")

    def setStatus(self, text: str):
        self.lbl_status.setText(text)

    def update_theme_styles(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        self.setStyleSheet(f"""
            QFrame#SleekProgressCard {{
                background-color: {"rgba(255, 255, 255, 0.055)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                border: 1px solid {hex_to_rgba(accent, 0.45) if is_dark else hex_to_rgba(accent, 0.35)};
                border-radius: 12px;
            }}
        """)
        self.lbl_status.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {'#ffffff' if is_dark else '#18191c'}; background: transparent; border: none;")
        self.lbl_pct.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {accent}; background: transparent; border: none;")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {"rgba(0, 0, 0, 0.30)" if is_dark else "rgba(0, 0, 0, 0.08)"};
                border-radius: 4px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 {adjust_color(accent, 35)});
                border-radius: 4px;
            }}
        """)


class SleekInstanceNameDialog(QDialog):
    """Modern popup dialog to specify custom instance name or use default."""
    def __init__(self, default_name="latest", app=None, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.app = app
        self.default_name = default_name
        self.selected_name = default_name
        self.setFixedSize(440, 240)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("InstanceNameCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl_title = QLabel(c.t("UI_INSTALL_INSTANCE_NAME_TITLE"))
        layout.addWidget(lbl_title)

        lbl_sub = QLabel(c.t("UI_INSTALL_INSTANCE_NAME_SUB", default_name=default_name))
        lbl_sub.setWordWrap(True)
        layout.addWidget(lbl_sub)

        self.entry_name = QLineEdit()
        self.entry_name.setText(default_name)
        self.entry_name.setFixedHeight(38)
        layout.addWidget(self.entry_name)

        row_buttons = QHBoxLayout()
        row_buttons.setSpacing(10)

        self.btn_cancel = QPushButton(c.t("UI_CANCEL"))
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_default = QPushButton(c.t("UI_BUTTON_DEFAULT"))
        self.btn_default.setFixedHeight(36)
        self.btn_default.setCursor(Qt.PointingHandCursor)
        self.btn_default.clicked.connect(self._use_default)

        self.btn_confirm = QPushButton(c.t("UI_BUTTON_INSTALL_NOW") if c.t("UI_BUTTON_INSTALL_NOW") else "Instalar")
        self.btn_confirm.setFixedHeight(36)
        self.btn_confirm.setCursor(Qt.PointingHandCursor)
        self.btn_confirm.clicked.connect(self._use_custom)

        row_buttons.addWidget(self.btn_cancel)
        row_buttons.addWidget(self.btn_default)
        row_buttons.addWidget(self.btn_confirm)
        layout.addLayout(row_buttons)

        main_layout.addWidget(card)

        # Style based on theme
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        card.setStyleSheet(f"""
            QFrame#InstanceNameCard {{
                background-color: {"#16171a" if is_dark else "#f4f6f8"};
                border: 1.5px solid {hex_to_rgba(accent, 0.50)};
                border-radius: 14px;
            }}
        """)
        lbl_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {'#ffffff' if is_dark else '#111214'}; background: transparent; border: none;")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {'#8ea3b0' if is_dark else '#4b5563'}; background: transparent; border: none;")
        self.entry_name.setStyleSheet(f"""
            QLineEdit {{
                background-color: {"rgba(0, 0, 0, 0.35)" if is_dark else "rgba(0, 0, 0, 0.05)"};
                color: {'#ffffff' if is_dark else '#111214'};
                border: 1px solid {hex_to_rgba(accent, 0.40)};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 13px;
                font-weight: 500;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {accent};
            }}
        """)
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {'#8ea3b0' if is_dark else '#6b7280'};
                border: 1px solid {'rgba(255, 255, 255, 0.15)' if is_dark else 'rgba(0, 0, 0, 0.15)'};
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: rgba(239, 68, 68, 0.15);
                color: #ef4444;
                border: 1px solid #ef4444;
            }}
        """)
        self.btn_default.setStyleSheet(f"""
            QPushButton {{
                background: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
                color: {'#ffffff' if is_dark else '#111214'};
                border: 1px solid {'rgba(255, 255, 255, 0.18)' if is_dark else 'rgba(0, 0, 0, 0.12)'};
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: {"rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.12)"};
            }}
        """)
        self.btn_confirm.setStyleSheet(f"""
            QPushButton {{
                background: {accent};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background: {adjust_color(accent, 20)};
            }}
        """)

    def _use_default(self):
        self.selected_name = self.default_name
        self.accept()

    def _use_custom(self):
        entered = self.entry_name.text().strip()
        self.selected_name = entered if entered else self.default_name
        self.accept()


class SleekVersionSelectorCard(QFrame):
    """Full-width version selector card with star badge, clean title, and searchable dropdown."""
    currentIndexChanged = Signal(int)

    def __init__(self, app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self._items = []
        self._current_index = 0
        self.setObjectName("SleekVersionSelectorCard")
        self.setFixedHeight(72)
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 16, 12)
        layout.setSpacing(12)

        # Star Icon Badge
        self.badge_icon = QFrame()
        self.badge_icon.setFixedSize(38, 38)
        badge_layout = QVBoxLayout(self.badge_icon)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setAlignment(Qt.AlignCenter)

        self.lbl_icon = QLabel()
        self._raw_icon = ImageManager.get_icon("star_pixel.svg")
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        badge_layout.addWidget(self.lbl_icon)
        layout.addWidget(self.badge_icon, 0, Qt.AlignVCenter)

        # Text Column (Title on top, Selected Version + Icon on bottom)
        col_text = QVBoxLayout()
        col_text.setContentsMargins(0, 0, 0, 0)
        col_text.setSpacing(2)

        self.lbl_title = QLabel(c.t("UI_INSTALL_SELECT_VERSION"))
        col_text.addWidget(self.lbl_title)

        row_sel = QHBoxLayout()
        row_sel.setContentsMargins(0, 0, 0, 0)
        row_sel.setSpacing(6)

        self.lbl_mc_icon = QLabel()
        mc_pix = ImageManager.get_image("minecraft_logo.png", (16, 16))
        if mc_pix and not mc_pix.isNull():
            self.lbl_mc_icon.setPixmap(mc_pix)
        self.lbl_mc_icon.setStyleSheet("background: transparent; border: none;")
        row_sel.addWidget(self.lbl_mc_icon, 0, Qt.AlignVCenter)

        self.lbl_selected_version = QLabel(c.t("UI_INSTALL_LOADING_VERSIONS"))
        row_sel.addWidget(self.lbl_selected_version, 1, Qt.AlignVCenter)

        col_text.addLayout(row_sel)
        layout.addLayout(col_text, 1)

        # Arrow indicator
        self.lbl_arrow = QLabel("▼")
        layout.addWidget(self.lbl_arrow, 0, Qt.AlignVCenter)

        self.update_theme_styles()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.isEnabled() and self._items:
            self._open_popup()
        super().mousePressEvent(event)

    def _open_popup(self):
        curr_data = self.currentData()
        popup = SleekSearchableVersionPopup(self._items, selected_data=curr_data, app=self.app, parent=self)
        popup.versionPicked.connect(self._on_version_picked)
        popup.show_below(self)

    def _on_version_picked(self, data, display_text):
        for idx, it in enumerate(self._items):
            if it["data"] == data:
                self._current_index = idx
                self.lbl_selected_version.setText(display_text)
                self.currentIndexChanged.emit(idx)
                break

    def clear(self):
        self._items = []
        self._current_index = 0
        self.lbl_selected_version.setText(c.t("UI_INSTALL_LOADING_VERSIONS"))

    def addItem(self, display_text, data=None):
        is_latest = (data and data[1] == "latest")
        is_beta = "[BETA]" in display_text
        clean_text = display_text.replace(" [BETA]", "")
        self._items.append({
            "display": clean_text,
            "data": data,
            "is_beta": is_beta,
            "is_latest": is_latest
        })
        if len(self._items) == 1:
            self._current_index = 0
            self.lbl_selected_version.setText(clean_text)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self.update()

    def count(self):
        return len(self._items)

    def currentData(self):
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index]["data"]
        return None

    def currentText(self):
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index]["display"]
        return ""

    def currentIndex(self):
        return self._current_index

    def setCurrentIndex(self, idx):
        if 0 <= idx < len(self._items):
            self._current_index = idx
            self.lbl_selected_version.setText(self._items[idx]["display"])
            self.currentIndexChanged.emit(idx)

    def itemData(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]["data"]
        return None

    def update_theme_styles(self):
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        self.setStyleSheet(f"""
            QFrame#SleekVersionSelectorCard {{
                background-color: {"rgba(255, 255, 255, 0.055)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                border: 1px solid {hex_to_rgba(accent, 0.45) if is_dark else hex_to_rgba(accent, 0.35)};
                border-radius: 12px;
            }}
        """)
        self.badge_icon.setStyleSheet(f"""
            background-color: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
            border-radius: 8px;
            border: 1px solid {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.08)"};
        """)
        if not self._raw_icon.isNull():
            pix = self._raw_icon.pixmap(18, 18)
            if not is_dark:
                tinted = QPixmap(pix.size())
                tinted.fill(Qt.transparent)
                p_tint = QPainter(tinted)
                p_tint.drawPixmap(0, 0, pix)
                p_tint.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                p_tint.fillRect(tinted.rect(), QColor("#111214"))
                p_tint.end()
                self.lbl_icon.setPixmap(tinted)
            else:
                self.lbl_icon.setPixmap(pix)

        self.lbl_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {'#ffffff' if is_dark else '#18191c'}; background: transparent; border: none;")
        self.lbl_selected_version.setStyleSheet(f"font-size: 11px; color: {'#8ea3b0' if is_dark else '#3c4049'}; background: transparent; border: none;")
        self.lbl_arrow.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {accent}; background: transparent; border: none;")

    def retranslate_ui(self):
        if hasattr(self, "lbl_title"):
            self.lbl_title.setText(c.t("UI_INSTALL_SELECT_VERSION"))
        if not self._items:
            self.lbl_selected_version.setText(c.t("UI_INSTALL_LOADING_VERSIONS"))
        elif 0 <= self._current_index < len(self._items):
            it = self._items[self._current_index]
            if it.get("is_latest"):
                it["display"] = c.t("UI_INSTALL_LATEST_AUTO")
                self.lbl_selected_version.setText(it["display"])


class SteveWatermarkWidget(QWidget):
    """
    Subtle low-contrast watermark illustration of Steve with Diamond Ore,
    tinted and feathered into the background canvas with theme-adaptive accent blending.
    """
    def __init__(self, app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent; border: none;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(0)

        path = resource_path("steve_ore.png")
        self._pixmap = QPixmap(path) if os.path.exists(path) else None

    def paintEvent(self, event):
        if not self._pixmap or self._pixmap.isNull():
            return

        w, h = float(self.width()), float(self.height())
        if w < 30.0 or h < 30.0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h = float(self.width()), float(self.height())
        target_h = min(h + 10, 160.0)
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        cache_key = (int(target_h), accent, is_dark)

        if getattr(self, "_cached_key", None) != cache_key or getattr(self, "_cached_img", None) is None:
            scaled_pm = self._pixmap.scaledToHeight(int(target_h), Qt.SmoothTransformation)

            # Create blended and feathered image
            img = QImage(scaled_pm.size(), QImage.Format_ARGB32_Premultiplied)
            img.fill(Qt.transparent)
            p_img = QPainter(img)
            p_img.setRenderHint(QPainter.RenderHint.Antialiasing)
            p_img.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p_img.drawPixmap(0, 0, scaled_pm)

            # Soft accent color overlay tint
            p_img.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
            tint_color = QColor(accent)
            tint_color.setAlpha(65 if is_dark else 45)
            p_img.fillRect(img.rect(), tint_color)

            # Soft left-to-right and top-to-bottom feathering mask
            grad_x = QLinearGradient(0, 0, img.width(), 0)
            grad_x.setColorAt(0.00, QColor(0, 0, 0, 0))
            grad_x.setColorAt(0.18, QColor(0, 0, 0, 120))
            grad_x.setColorAt(0.45, QColor(0, 0, 0, 255))
            grad_x.setColorAt(0.85, QColor(0, 0, 0, 255))
            grad_x.setColorAt(1.00, QColor(0, 0, 0, 160))

            grad_y = QLinearGradient(0, 0, 0, img.height())
            grad_y.setColorAt(0.00, QColor(0, 0, 0, 0))
            grad_y.setColorAt(0.20, QColor(0, 0, 0, 140))
            grad_y.setColorAt(0.50, QColor(0, 0, 0, 255))
            grad_y.setColorAt(0.85, QColor(0, 0, 0, 255))
            grad_y.setColorAt(1.00, QColor(0, 0, 0, 180))

            p_img.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            p_img.fillRect(img.rect(), grad_x)
            p_img.fillRect(img.rect(), grad_y)
            p_img.end()

            self._cached_key = cache_key
            self._cached_img = img
        else:
            img = self._cached_img

        # Position on the right side
        target_x = max(0.0, w - float(img.width()) - 15.0)
        target_y = max(0.0, h - float(img.height()) - 5.0)

        # Draw with low contrast opacity (opaco y bajo ~ 0.22 in dark, 0.16 in light)
        painter.setOpacity(0.22 if is_dark else 0.16)
        painter.drawImage(int(target_x), int(target_y), img)
        painter.end()


class GooglePlayTab(QWidget):
    """Tab widget for searching and installing versions from Google Play."""

    def __init__(self, parent_dialog):
        super().__init__()
        self.dialog = parent_dialog
        self.app = parent_dialog.parent_app
        self.all_versions_data = []
        self.fetcher = None
        self.setup_ui()
        self.load_versions("x86_64")

    def setup_ui(self):
        """Build the UI layout for the Google Play tab."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(10)

        # 1. Login Capsule Frame (Thick, with rounded corners, Google G badge, branding text & tactile 3D button)
        self.card_google_login = QFrame()
        self.card_google_login.setObjectName("GoogleLoginCard")
        self.card_google_login.setMinimumHeight(74)
        
        self.login_card_layout = QHBoxLayout(self.card_google_login)
        self.login_card_layout.setContentsMargins(12, 8, 12, 8)
        self.login_card_layout.setSpacing(10)

        # White Rounded Icon Badge
        self.badge_google = QFrame()
        self.badge_google.setFixedSize(44, 44)
        self.badge_google.setStyleSheet("background-color: #ffffff; border-radius: 11px; border: 1px solid rgba(0, 0, 0, 0.08);")
        badge_layout = QVBoxLayout(self.badge_google)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setAlignment(Qt.AlignCenter)

        self.lbl_google_icon = QLabel()
        g_pix = ImageManager.get_image("google_favicon.svg", (26, 26)) or ImageManager.get_image("google_favicon.png", (26, 26))
        if g_pix and not g_pix.isNull():
            self.lbl_google_icon.setPixmap(g_pix)
        self.lbl_google_icon.setAlignment(Qt.AlignCenter)
        self.lbl_google_icon.setStyleSheet("background: transparent; border: none;")
        badge_layout.addWidget(self.lbl_google_icon)
        self.login_card_layout.addWidget(self.badge_google, 0, Qt.AlignVCenter)

        # Text Column (Title + Subtitle)
        col_google_text = QVBoxLayout()
        col_google_text.setContentsMargins(0, 0, 0, 0)
        col_google_text.setSpacing(2)

        self.lbl_google_title = QLabel(c.t("UI_INSTALL_GOOGLE_TITLE"))
        self.lbl_google_title.setWordWrap(True)
        col_google_text.addWidget(self.lbl_google_title)

        self.lbl_google_sub = QLabel(c.t("UI_INSTALL_GOOGLE_SUB"))
        self.lbl_google_sub.setWordWrap(True)
        col_google_text.addWidget(self.lbl_google_sub)

        self.login_card_layout.addLayout(col_google_text, 1)

        # 3D Tactile Login Button
        self.btn_login = GooglePlayLoginButton(text=c.t("UI_INSTALL_BTN_LOGIN"), app=self.app)
        self.btn_login.clicked.connect(self.do_login)
        self.login_card_layout.addWidget(self.btn_login, 0, Qt.AlignVCenter)

        layout.addWidget(self.card_google_login)

        # Row below login card: Mini status badge (left) + Remove account button (right)
        self.row_session_info = QHBoxLayout()
        self.row_session_info.setContentsMargins(4, 0, 4, 0)
        self.row_session_info.setSpacing(10)

        self.badge_session_status = QFrame()
        self.badge_session_status.setObjectName("BadgeSessionStatus")
        self.badge_session_status.setFixedHeight(28)
        badge_status_layout = QHBoxLayout(self.badge_session_status)
        badge_status_layout.setContentsMargins(10, 0, 12, 0)
        badge_status_layout.setSpacing(8)

        self.dot_session_status = QLabel()
        self.dot_session_status.setFixedSize(8, 8)
        self.dot_session_status.setStyleSheet("background-color: #ef4444; border-radius: 4px; border: none;")
        badge_status_layout.addWidget(self.dot_session_status, 0, Qt.AlignVCenter)

        self.lbl_session_status = QLabel(c.t("UI_INSTALL_NO_SESSION"))
        self.lbl_session_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #ef4444; background: transparent; border: none;")
        badge_status_layout.addWidget(self.lbl_session_status, 0, Qt.AlignVCenter)

        self.row_session_info.addWidget(self.badge_session_status, 0, Qt.AlignVCenter)
        self.row_session_info.addStretch(1)

        self.btn_remove_account = QPushButton(c.t("UI_INSTALL_BTN_REMOVE_ACCOUNT"))
        self.btn_remove_account.setCursor(Qt.PointingHandCursor)
        self.btn_remove_account.setFixedHeight(28)
        self.btn_remove_account.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.12);
                color: #ef4444;
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 14px;
                padding: 0 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.25);
                border: 1px solid #ef4444;
                color: #ff6b6b;
            }
            QPushButton:pressed {
                background-color: rgba(239, 68, 68, 0.40);
            }
        """)
        self.btn_remove_account.clicked.connect(self.do_remove_account)
        self.row_session_info.addWidget(self.btn_remove_account, 0, Qt.AlignVCenter)

        layout.addLayout(self.row_session_info)

        # 2. Side-by-side Row: Arquitectura Card (Left) & Filtrar Versiones Card (Right)
        self.selectors_layout = QHBoxLayout()
        self.selectors_layout.setContentsMargins(0, 0, 0, 0)
        self.selectors_layout.setSpacing(12)

        self.card_arch = SleekCardSelector(c.t("UI_COMPAT_ARCH_LABEL"), "cpu_pixel.svg", ["x86_64", "x86"], default_value="x86_64", app=self.app)
        self.card_arch.setFixedHeight(64)
        self.card_arch.currentTextChanged.connect(self.load_versions)
        self.combo_arch = self.card_arch
        self.selectors_layout.addWidget(self.card_arch, 1)

        self.card_filter = SleekCardSelector(
            c.t("UI_LABEL_FILTER_VERSIONS").rstrip(":"),
            "filter_pixel.svg",
            [c.t("UI_FILTER_STABLE"), c.t("UI_FILTER_ALL"), c.t("UI_FILTER_BETA")],
            default_value=c.t("UI_FILTER_STABLE"),
            app=self.app
        )
        self.card_filter.setFixedHeight(64)
        self.card_filter.currentTextChanged.connect(self.apply_filter)
        self.combo_filter = self.card_filter
        self.selectors_layout.addWidget(self.card_filter, 1)

        layout.addLayout(self.selectors_layout)

        # 3. Full-width Version Selector Card with Searchable Dropdown Popup
        self.card_version = SleekVersionSelectorCard(app=self.app)
        self.card_version.setFixedHeight(72)
        self.card_version.currentIndexChanged.connect(self._on_version_selected)
        self.combo_versions = self.card_version
        layout.addWidget(self.card_version)

        # Watermark illustration of Steve with Diamond Ore (on the right)
        self.watermark = SteveWatermarkWidget(app=self.app)
        layout.addWidget(self.watermark, 1)

        # Progress Section Card
        self.card_progress = SleekProgressCard(app=self.app)
        self.card_progress.hide()
        layout.addWidget(self.card_progress)

        # Subtle hint divider: "──────── Sign in to continue ────────"
        self.box_login_hint = QWidget()
        box_hint_layout = QHBoxLayout(self.box_login_hint)
        box_hint_layout.setContentsMargins(8, 2, 8, 2)
        box_hint_layout.setSpacing(12)

        self.line_left = QFrame()
        self.line_left.setFrameShape(QFrame.HLine)
        self.line_left.setFrameShadow(QFrame.Plain)
        self.line_left.setFixedHeight(1)

        self.lbl_login_hint = QLabel(c.t("UI_INSTALL_LOGIN_HINT"))
        self.lbl_login_hint.setAlignment(Qt.AlignCenter)

        self.line_right = QFrame()
        self.line_right.setFrameShape(QFrame.HLine)
        self.line_right.setFrameShadow(QFrame.Plain)
        self.line_right.setFixedHeight(1)

        box_hint_layout.addWidget(self.line_left, 1)
        box_hint_layout.addWidget(self.lbl_login_hint, 0, Qt.AlignCenter)
        box_hint_layout.addWidget(self.line_right, 1)
        layout.addWidget(self.box_login_hint)

        self.btn_download = Tactile3DActionButton(text=c.t("UI_BUTTON_INSTALL_NOW"), app=self.app)
        self.btn_download.clicked.connect(self.start_download_flow)
        layout.addWidget(self.btn_download)

        # Apply theme-aware styling
        self.update_theme_styles()

        # Call this LAST to ensure btn_download exists
        self.update_session_status()

    def minimumSizeHint(self):
        return QSize(260, 320)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        if hasattr(self, "selectors_layout"):
            if w < 480:
                self.selectors_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            else:
                self.selectors_layout.setDirection(QBoxLayout.Direction.LeftToRight)
        if hasattr(self, "login_card_layout") and hasattr(self, "badge_google"):
            if w < 440:
                self.login_card_layout.setDirection(QBoxLayout.Direction.TopToBottom)
                self.badge_google.hide()
            else:
                self.login_card_layout.setDirection(QBoxLayout.Direction.LeftToRight)
                self.badge_google.show()

    def do_remove_account(self):
        """Confirm and clear Google Play session from disk."""
        confirm = messagebox.askyesno(
            self,
            c.t("UI_INSTALL_REMOVE_ACCOUNT_TITLE"),
            c.t("UI_INSTALL_REMOVE_ACCOUNT_CONFIRM")
        )
        if confirm:
            if hasattr(self.app.logic, "remove_google_session"):
                self.app.logic.remove_google_session(self.app)
            self.update_session_status()

    def update_theme_styles(self):
        """Update Google Login Card and selector styling based on current theme."""
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        if hasattr(self, "card_google_login"):
            self.card_google_login.setStyleSheet(f"""
                QFrame#GoogleLoginCard {{
                    background-color: {hex_to_rgba(accent, 0.15) if is_dark else hex_to_rgba(accent, 0.08)};
                    border: 1.5px solid {hex_to_rgba(accent, 0.45) if is_dark else hex_to_rgba(accent, 0.30)};
                    border-radius: 14px;
                }}
            """)
        if hasattr(self, "lbl_google_title"):
            self.lbl_google_title.setStyleSheet(
                f"font-size: 13px; font-weight: bold; color: {'#ffffff' if is_dark else '#18191c'}; background: transparent; border: none;"
            )
        if hasattr(self, "lbl_google_sub"):
            self.lbl_google_sub.setStyleSheet(
                f"font-size: 11px; color: {'#8ea3b0' if is_dark else '#4b5563'}; background: transparent; border: none;"
            )
        if hasattr(self, "btn_login"):
            self.btn_login.update()
        if hasattr(self, "card_arch"):
            self.card_arch.update_theme_styles()
        if hasattr(self, "card_filter"):
            self.card_filter.update_theme_styles()
        if hasattr(self, "card_version"):
            self.card_version.update_theme_styles()
        if hasattr(self, "watermark"):
            self.watermark.update()
        if hasattr(self, "card_progress"):
            self.card_progress.update_theme_styles()
        if hasattr(self, "line_left"):
            line_color = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.12)"
            self.line_left.setStyleSheet(f"background-color: {line_color}; border: none;")
        if hasattr(self, "line_right"):
            line_color = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.12)"
            self.line_right.setStyleSheet(f"background-color: {line_color}; border: none;")
        if hasattr(self, "lbl_login_hint"):
            text_color = "rgba(255, 255, 255, 0.45)" if is_dark else "rgba(0, 0, 0, 0.50)"
            self.lbl_login_hint.setStyleSheet(f"font-size: 11px; font-weight: 500; color: {text_color}; background: transparent; border: none;")

        if hasattr(self, "btn_download"):
            self.btn_download.update()
        self.update_session_status()

    def do_login(self):
        """Launch the Google login flow and monitor for session token."""
        # Avoid double-launch
        if getattr(self, "_login_proc", None) and hasattr(self._login_proc, "state") and self._login_proc.state() == QProcess.Running:
            return

        def _on_finished(code):
            self.update_session_status()

        if hasattr(self.app, "logic") and hasattr(self.app.logic, "launch_google_login"):
            self._login_proc = self.app.logic.launch_google_login(self.app, on_finished=_on_finished)
        elif hasattr(self.app, "logic") and hasattr(self.app.logic, "start_google_login_flow"):
            self._login_proc = self.app.logic.start_google_login_flow(self.app)

        if not hasattr(self, "_login_poll_timer") or not self._login_poll_timer:
            self._login_poll_timer = QTimer(self)
            self._login_poll_timer.setInterval(1000)
            self._login_poll_timer.timeout.connect(self._check_login_status)
        self._login_poll_timer.start()

    def _check_login_status(self):
        """Periodic poll to check if the user completed authentication in the browser."""
        is_auth = False
        if hasattr(self.app, "logic") and hasattr(self.app.logic, "check_google_session"):
            is_auth = self.app.logic.check_google_session(self.app)
        elif hasattr(self.app, "logic") and hasattr(self.app.logic, "is_google_authenticated"):
            is_auth = self.app.logic.is_google_authenticated(self.app)

        if is_auth:
            if hasattr(self, "_login_poll_timer") and self._login_poll_timer.isActive():
                self._login_poll_timer.stop()
            self.update_session_status()

    def update_session_status(self):
        """Update session status pill and button state based on Google authentication."""
        try:
            is_authenticated = False
            raw_email = ""
            if hasattr(self.app, "logic"):
                if hasattr(self.app.logic, "check_google_session"):
                    is_authenticated = self.app.logic.check_google_session(self.app)
                elif hasattr(self.app.logic, "is_google_authenticated"):
                    is_authenticated = self.app.logic.is_google_authenticated(self.app)

                if is_authenticated:
                    if hasattr(self.app.logic, "get_google_session_email"):
                        raw_email = self.app.logic.get_google_session_email(self.app) or ""
                    elif hasattr(self.app.logic, "get_google_email"):
                        raw_email = self.app.logic.get_google_email(self.app) or ""

            is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

            if is_authenticated:
                masked = mask_google_email(raw_email)
                if hasattr(self, "btn_login"):
                    self.btn_login.setText(c.t("UI_INSTALL_BTN_SWITCH_ACCOUNT"))
                if hasattr(self, "lbl_session_status"):
                    self.lbl_session_status.setText(c.t("UI_INSTALL_LOGGED_IN", masked=masked))
                    self.lbl_session_status.setStyleSheet(
                        f"font-size: 11px; font-weight: bold; color: {'#2ed573' if is_dark else '#16a34a'}; background: transparent; border: none;"
                    )
                if hasattr(self, "dot_session_status"):
                    self.dot_session_status.setStyleSheet("background-color: #2ed573; border-radius: 4px; border: none;")
                if hasattr(self, "btn_remove_account"):
                    self.btn_remove_account.setVisible(True)
                if hasattr(self, "btn_download"):
                    if not self.btn_download.is_cancel_mode():
                        self.btn_download.setEnabled(True)
                if hasattr(self, "box_login_hint"):
                    self.box_login_hint.setVisible(False)
            else:
                if hasattr(self, "btn_login"):
                    self.btn_login.setText(c.t("UI_INSTALL_BTN_LOGIN"))
                if hasattr(self, "lbl_session_status"):
                    self.lbl_session_status.setText(c.t("UI_INSTALL_NO_SESSION"))
                    self.lbl_session_status.setStyleSheet(
                        f"font-size: 11px; font-weight: bold; color: {'#ef4444' if is_dark else '#dc2626'}; background: transparent; border: none;"
                    )
                if hasattr(self, "dot_session_status"):
                    self.dot_session_status.setStyleSheet("background-color: #ef4444; border-radius: 4px; border: none;")
                if hasattr(self, "btn_remove_account"):
                    self.btn_remove_account.setVisible(False)
                if hasattr(self, "btn_download"):
                    if not self.btn_download.is_cancel_mode():
                        self.btn_download.setEnabled(False)
                if hasattr(self, "box_login_hint"):
                    self.box_login_hint.setVisible(True)

            if hasattr(self, "btn_download"):
                self.btn_download.update()
        except Exception as e:
            logger.warning(f"Failed to update session status: {e}")

    def load_versions(self, arch):
        """Fetch available versions for the given architecture in a background thread."""
        # Stop any ongoing fetch
        if self.fetcher and self.fetcher.isRunning():
            self.fetcher.terminate()
            self.fetcher.wait()

        self.all_versions_data = []
        self.combo_versions.clear()
        self.combo_versions.addItem(c.t("UI_LABEL_SEARCHING"))
        self.combo_versions.setEnabled(False)

        self.fetcher = VersionFetcher(arch)
        self.fetcher.finished.connect(self.on_versions_loaded)
        self.fetcher.error.connect(self.on_versions_error)
        self.fetcher.start()

    def on_versions_loaded(self, data):
        """Handle successfully loaded version data and apply the current filter."""
        self.all_versions_data = data
        self.apply_filter()

    def on_versions_error(self, err):
        """Display an error message when version loading fails."""
        logger.error(f"Error loading versions: {err}")
        self.combo_versions.clear()
        self.combo_versions.addItem(c.t("UI_INSTALL_ERROR_LOAD_NET"))
        self.combo_versions.setEnabled(True)

    def _on_version_selected(self, index):
        """Warn the user as soon as a flagged version is picked from the combo,
        not only when the download button is pressed."""
        if index < 0:
            return
        version_data = self.combo_versions.itemData(index)
        if not version_data:
            return
        version_name = version_data[1]
        if version_name == "latest":
            return
        warning = self.dialog.get_warning_for_version(version_name)
        if not warning:
            return
        messagebox.showwarning(
            self,
            c.t("UI_INSTALL_COMPAT_WARN_TITLE"),
            c.t("UI_INSTALL_COMPAT_WARN_MSG", version=version_name, warning=warning)
        )

    def apply_filter(self, _text=None):
        """Filter the version list by stable/beta/all and populate the combo box."""
        self.combo_versions.clear()
        self.combo_versions.setEnabled(True)
        
        if not self.all_versions_data:
            return

        filter_type = self.combo_filter.currentText()

        # "Latest (auto)" — vcode=0 → app_logic omits -v so Google picks
        # whichever version is currently being offered. Most reliable path:
        self.combo_versions.addItem(c.t("UI_INSTALL_LATEST_AUTO"), (0, "latest"))

        # data is list of lists [[vcode, vname, isbeta], ...]
        # Reversed to show newest first
        for ver in reversed(self.all_versions_data):
            is_beta = len(ver) > 2 and bool(ver[2])

            if filter_type == c.t("UI_FILTER_STABLE") and is_beta:
                continue
            if filter_type == c.t("UI_FILTER_BETA") and not is_beta:
                continue

            # Clean semantic version without noisy internal code numbers
            display = f"Minecraft Bedrock v{ver[1]}"
            if is_beta:
                display += " [BETA]"
            self.combo_versions.addItem(display, (ver[0], ver[1])) # Store both code and name


    def start_download_flow(self):
        """Begin downloading and installing the selected Google Play version."""
        if self.btn_download.is_cancel_mode():
            self.card_progress.setStatus(c.t("UI_INSTALL_CANCELING_DOWNLOAD"))
            if hasattr(self.app, "logic") and hasattr(self.app.logic, "cancel_google_install"):
                self.app.logic.cancel_google_install(self.app)
            return

        version_data = self.combo_versions.currentData()
        if not version_data:
            logger.warning("start_download_flow: no version selected")
            return

        version_code, version_name = version_data
        arch = self.combo_arch.currentText()

        warning = self.dialog.get_warning_for_version(version_name)
        if warning:
            messagebox.showwarning(
                self,
                c.t("UI_INSTALL_COMPAT_WARN_TITLE"),
                c.t("UI_INSTALL_COMPAT_WARN_MSG", version=version_name, warning=warning)
            )

        # Instance name selection popup dialog
        name_dialog = SleekInstanceNameDialog(default_name=version_name, app=self.app, parent=self)
        if name_dialog.exec() != QDialog.Accepted:
            return
        instance_name = name_dialog.selected_name

        # Determine target mode/path
        mode_key = self.dialog.target_mode_val
        is_target_flatpak = (mode_key == c.MODE_INSTALL_FLATPAK)
        target_root = self.dialog.get_target_root()
        flatpak_id = self.dialog.entry_flatpak_id.text().strip() if is_target_flatpak else None

        logger.info(f"start_download_flow: vcode={version_code} vname={version_name} instance={instance_name} "
              f"arch={arch} mode={mode_key} target_root={target_root} flatpak_id={flatpak_id}")

        self.btn_download.set_cancel_mode(True)
        self.card_progress.setProgress(0)
        self.card_progress.setStatus(c.t("UI_STATUS_DOWNLOADING"))
        self.card_progress.show()

        # This will call logic to start gplaydl and then extraction
        self.app.logic.download_and_install_google(
            self.app, version_code, version_name, arch,
            target_root, is_target_flatpak, flatpak_id,
            progress_callback=self.update_progress,
            status_callback=self.card_progress.setStatus,
            finished_callback=self.on_finished,
            instance_name=instance_name
        )

    def update_progress(self, value):
        """Update the progress card to the given percentage value."""
        self.card_progress.setProgress(value)

    def on_finished(self, success, message):
        """Handle completion of the download and install process."""
        self.btn_download.set_cancel_mode(False)
        self.card_progress.hide()
        self.update_session_status()
        if success:
            messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), message)
            self.dialog.accept()
        else:
            if not getattr(self.app, "_install_cancelled", False):
                messagebox.showerror(self, c.t("UI_ERROR_TITLE"), message)

    def retranslate_ui(self):
        if hasattr(self, "lbl_google_title"):
            self.lbl_google_title.setText(c.t("UI_INSTALL_GOOGLE_TITLE"))
        if hasattr(self, "lbl_google_sub"):
            self.lbl_google_sub.setText(c.t("UI_INSTALL_GOOGLE_SUB"))
        if hasattr(self, "btn_remove_account"):
            self.btn_remove_account.setText(c.t("UI_INSTALL_BTN_REMOVE_ACCOUNT"))
        if hasattr(self, "card_arch"):
            self.card_arch.setTitle(c.t("UI_COMPAT_ARCH_LABEL"))
        if hasattr(self, "card_filter"):
            self.card_filter.setTitle(c.t("UI_LABEL_FILTER_VERSIONS").rstrip(":"))
        if hasattr(self, "card_version") and hasattr(self.card_version, "retranslate_ui"):
            self.card_version.retranslate_ui()
        if hasattr(self, "lbl_login_hint"):
            self.lbl_login_hint.setText(c.t("UI_INSTALL_LOGIN_HINT"))
        if hasattr(self, "btn_download") and not self.btn_download.is_cancel_mode():
            self.btn_download.setText(c.t("UI_BUTTON_INSTALL_NOW"))
        self.update_session_status()


class SleekApkDropzoneCard(QFrame):
    """
    Sleek theme-aware APK selection card matching the Google Login Card layout,
    with an APK vector icon badge, header text, and an inner dashed dropzone with
    upload icon, drop hint, and 'Examinar' file browser button.
    """
    apkSelected = Signal(str)

    def __init__(self, app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self.setObjectName("SleekApkCard")
        self._selected_apk = ""
        self._is_drag_over = False
        self.setAcceptDrops(True)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(16, 14, 16, 14)
        self._main_layout.setSpacing(12)

        # 1. Header row (Icon Badge + Title / Subtitle)
        row_header = QHBoxLayout()
        row_header.setContentsMargins(0, 0, 0, 0)
        row_header.setSpacing(14)

        self.badge_icon = QLabel()
        self.badge_icon.setFixedSize(44, 44)
        self.badge_icon.setAlignment(Qt.AlignCenter)

        col_title = QVBoxLayout()
        col_title.setContentsMargins(0, 0, 0, 0)
        col_title.setSpacing(3)

        self.lbl_title = QLabel(c.t("UI_INSTALL_APK_TITLE"))
        self.lbl_title.setWordWrap(True)
        self.lbl_sub = QLabel(c.t("UI_INSTALL_APK_SUB"))
        self.lbl_sub.setWordWrap(True)
        col_title.addWidget(self.lbl_title)
        col_title.addWidget(self.lbl_sub)

        row_header.addWidget(self.badge_icon, 0, Qt.AlignVCenter)
        row_header.addLayout(col_title, 1)
        self._main_layout.addLayout(row_header)

        # 2. Inner Dashed Dropzone
        self.dropzone = QFrame()
        self.dropzone.setObjectName("ApkDashedDropzone")
        self.dropzone.setMinimumHeight(74)

        dropzone_layout = QHBoxLayout(self.dropzone)
        dropzone_layout.setContentsMargins(14, 8, 14, 8)
        dropzone_layout.setSpacing(0)

        # Left slot (Balanced spacer or Mini Clear Button on left)
        self.box_left = QWidget()
        self.box_left_layout = QHBoxLayout(self.box_left)
        self.box_left_layout.setContentsMargins(0, 0, 6, 0)
        self.box_left_layout.setSpacing(0)

        self.btn_clear = QPushButton(c.t("UI_INSTALL_APK_BTN_CLEAR"))
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setFixedHeight(34)
        self.btn_clear.setFixedWidth(86)
        self.btn_clear.setToolTip(c.t("UI_INSTALL_APK_CLEAR_TIP"))
        self.btn_clear.clicked.connect(self.clearApk)
        self.btn_clear.hide()
        self.box_left_layout.addWidget(self.btn_clear, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.box_left.hide()

        dropzone_layout.addWidget(self.box_left, 0, Qt.AlignVCenter)

        # Middle slot: Upload icon directly next to the centered text
        row_center = QHBoxLayout()
        row_center.setContentsMargins(0, 0, 6, 0)
        row_center.setSpacing(10)

        self.lbl_upload_icon = QLabel()
        self.lbl_upload_icon.setFixedSize(36, 36)
        self.lbl_upload_icon.setAlignment(Qt.AlignCenter)
        row_center.addWidget(self.lbl_upload_icon, 0, Qt.AlignVCenter)

        col_drop_text = QVBoxLayout()
        col_drop_text.setContentsMargins(0, 0, 0, 0)
        col_drop_text.setSpacing(2)

        self.lbl_drop_main = QLabel(c.t("UI_INSTALL_APK_DROP_MAIN"))
        self.lbl_drop_main.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_drop_main.setWordWrap(True)
        self.lbl_drop_sub = QLabel(c.t("UI_INSTALL_APK_DROP_SUB"))
        self.lbl_drop_sub.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_drop_sub.setWordWrap(True)
        col_drop_text.addWidget(self.lbl_drop_main)
        col_drop_text.addWidget(self.lbl_drop_sub)
        row_center.addLayout(col_drop_text, 1)

        dropzone_layout.addLayout(row_center, 1)

        # Right slot: Botón Examinar con tamaño elástico
        self.btn_browse = QPushButton(c.t("UI_INSTALL_BTN_BROWSE"))
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.setFixedHeight(34)
        self.btn_browse.setMinimumWidth(86)
        self.btn_browse.setMaximumWidth(110)
        self.btn_browse.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.btn_browse.clicked.connect(self._on_browse_clicked)
        dropzone_layout.addWidget(self.btn_browse, 0, Qt.AlignRight | Qt.AlignVCenter)

        self._main_layout.addWidget(self.dropzone)

        self.update_theme_styles()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".apk"):
                    event.acceptProposedAction()
                    self._is_drag_over = True
                    self.update_theme_styles()
                    return

    def dragLeaveEvent(self, event):
        self._is_drag_over = False
        self.update_theme_styles()

    def dropEvent(self, event: QDropEvent):
        self._is_drag_over = False
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".apk"):
                self.setApkPath(path)
                return
        self.update_theme_styles()

    def _on_browse_clicked(self):
        path = ask_open_filename_native(self, title=c.t("UI_SELECT_APK_TITLE"), filetypes=[(c.t("UI_APK_FILES_TYPE"), "*.apk")])
        if path:
            self.setApkPath(path)

    def clearApk(self):
        self._selected_apk = ""
        self.lbl_drop_main.setText(c.t("UI_INSTALL_APK_DROP_MAIN"))
        self.lbl_drop_sub.setText(c.t("UI_INSTALL_APK_DROP_SUB"))
        if hasattr(self, "btn_clear"):
            self.btn_clear.hide()
        if hasattr(self, "box_left"):
            self.box_left.hide()
        self.update_theme_styles()
        self.apkSelected.emit("")

    def setApkPath(self, path):
        if not path:
            self.clearApk()
            return
        self._selected_apk = path
        base = os.path.basename(path)
        self.lbl_drop_main.setText(base)
        self.lbl_drop_sub.setText(path)
        if hasattr(self, "btn_clear"):
            self.btn_clear.show()
        if hasattr(self, "box_left"):
            self.box_left.show()
        self.update_theme_styles()
        self.apkSelected.emit(path)

    def getApkPath(self):
        return self._selected_apk

    def update_theme_styles(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        # Card container styling (matching Google Play selector cards)
        self.setStyleSheet(f"""
            QFrame#SleekApkCard {{
                background-color: {"rgba(255, 255, 255, 0.055)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                border: 1px solid {hex_to_rgba(accent, 0.45) if is_dark else hex_to_rgba(accent, 0.35)};
                border-radius: 14px;
            }}
        """)

        # Badge APK icon (matching Google Play icon badges)
        self.badge_icon.setStyleSheet(f"""
            background-color: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
            border: 1px solid {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.08)"};
            border-radius: 10px;
        """)
        # Tint icon
        apk_icon_path = resource_path("apk_file_icon.svg")
        if os.path.exists(apk_icon_path):
            pix = QIcon(apk_icon_path).pixmap(24, 24)
            tinted = QPixmap(pix.size())
            tinted.fill(Qt.transparent)
            p = QPainter(tinted)
            p.drawPixmap(0, 0, pix)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            p.fillRect(tinted.rect(), QColor(accent if is_dark else "#111214"))
            p.end()
            self.badge_icon.setPixmap(tinted)

        # Header titles (enlarged)
        self.lbl_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {'#ffffff' if is_dark else '#18191c'}; background: transparent; border: none;")
        self.lbl_sub.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {'#8ea3b0' if is_dark else '#4b5563'}; background: transparent; border: none;")

        # Dropzone styling
        if self._is_drag_over:
            bg_dz = hex_to_rgba(accent, 0.22 if is_dark else 0.16)
            border_dz = accent
        else:
            bg_dz = hex_to_rgba(accent, 0.05 if is_dark else 0.03)
            border_dz = hex_to_rgba(accent, 0.45 if is_dark else 0.35)

        self.dropzone.setStyleSheet(f"""
            QFrame#ApkDashedDropzone {{
                background-color: {bg_dz};
                border: 1.5px dashed {border_dz};
                border-radius: 10px;
            }}
        """)

        # Upload icon (enlarged and tinted)
        up_icon_path = resource_path("upload_cloud_icon.svg")
        if os.path.exists(up_icon_path):
            pix_up = QIcon(up_icon_path).pixmap(30, 30)
            tinted_up = QPixmap(pix_up.size())
            tinted_up.fill(Qt.transparent)
            p = QPainter(tinted_up)
            p.drawPixmap(0, 0, pix_up)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            p.fillRect(tinted_up.rect(), QColor(accent))
            p.end()
            self.lbl_upload_icon.setPixmap(tinted_up)

        # Drop text (centered)
        self.lbl_drop_main.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {'#ffffff' if is_dark else '#18191c'}; background: transparent; border: none;")
        self.lbl_drop_sub.setStyleSheet(f"font-size: 11px; color: {'#8ea3b0' if is_dark else '#6b7280'}; background: transparent; border: none;")

        # Mini Button "✕ Quitar"
        if hasattr(self, "btn_clear"):
            self.btn_clear.setStyleSheet(f"""
                QPushButton {{
                    background-color: {"rgba(244, 67, 54, 0.12)" if is_dark else "rgba(239, 68, 68, 0.10)"};
                    color: {"#ff6b6b" if is_dark else "#dc2626"};
                    border: 1px solid {"rgba(244, 67, 54, 0.40)" if is_dark else "rgba(239, 68, 68, 0.35)"};
                    border-radius: 8px;
                    padding: 0 10px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {"rgba(244, 67, 54, 0.25)" if is_dark else "rgba(239, 68, 68, 0.22)"};
                    border: 1px solid {"#ff6b6b" if is_dark else "#dc2626"};
                }}
                QPushButton:pressed {{
                    background-color: {"rgba(244, 67, 54, 0.35)" if is_dark else "rgba(239, 68, 68, 0.30)"};
                }}
            """)

        # Button "Examinar"
        folder_icon_path = resource_path("folder_browse_icon.svg")
        if os.path.exists(folder_icon_path):
            self.btn_browse.setIcon(QIcon(folder_icon_path))
            self.btn_browse.setIconSize(QSize(16, 16))

        self.btn_browse.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {adjust_color(accent, 1.12)};
            }}
            QPushButton:pressed {{
                background-color: {adjust_color(accent, 0.88)};
            }}
        """)

    def retranslate_ui(self):
        if hasattr(self, "lbl_title"):
            self.lbl_title.setText(c.t("UI_INSTALL_APK_TITLE"))
        if hasattr(self, "lbl_sub"):
            self.lbl_sub.setText(c.t("UI_INSTALL_APK_SUB"))
        if hasattr(self, "btn_clear"):
            self.btn_clear.setText(c.t("UI_INSTALL_APK_BTN_CLEAR"))
            self.btn_clear.setToolTip(c.t("UI_INSTALL_APK_CLEAR_TIP"))
        if hasattr(self, "btn_browse"):
            self.btn_browse.setText(c.t("UI_INSTALL_BTN_BROWSE"))
        if not self._selected_apk:
            if hasattr(self, "lbl_drop_main"):
                self.lbl_drop_main.setText(c.t("UI_INSTALL_APK_DROP_MAIN"))
            if hasattr(self, "lbl_drop_sub"):
                self.lbl_drop_sub.setText(c.t("UI_INSTALL_APK_DROP_SUB"))


class LocalApkTab(QWidget):
    """Tab widget for installing Minecraft from a local APK file."""

    def __init__(self, parent_dialog):
        super().__init__()
        self.dialog = parent_dialog
        self.app = getattr(parent_dialog, 'parent_app', None) or getattr(parent_dialog, 'app', None)
        self.setAcceptDrops(True)
        self.setup_ui()

    def _set_apk_path(self, path):
        if hasattr(self, "card_apk"):
            self.card_apk.setApkPath(path)
        else:
            self.entry_apk.setText(path)
            base = os.path.basename(path)
            match = re.search(r"(\d+\.\d+(\.\d+)?)", base)
            if match:
                self.entry_name.setText(match.group(1))
            self.check_architecture(path)

    def _on_apk_selected(self, path):
        if not path:
            self.entry_apk.setText("")
            self.entry_name.setText("")
            self.lbl_arch.setText("")
            self.lbl_arch.hide()
            self.btn_install.setEnabled(False)
            return
        self.entry_apk.setText(path)
        base = os.path.basename(path)
        match = re.search(r"(\d+\.\d+(\.\d+)?)", base)
        if match:
            self.entry_name.setText(match.group(1))
        self.check_architecture(path)

    def setup_ui(self):
        """Build the UI layout for the local APK installation tab."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 2, 0, 2)
        self.layout.setSpacing(10)

        # 1. Selección de APK (Sleek Card con Icono, Dashed Dropzone y Botón Examinar)
        self.card_apk = SleekApkDropzoneCard(app=self.app)
        self.card_apk.apkSelected.connect(self._on_apk_selected)
        self.layout.addWidget(self.card_apk)

        # Hidden entry_apk for compatibility
        self.entry_apk = QLineEdit()
        self.entry_apk.hide()

        # Label de Estado de Arquitectura
        self.lbl_arch = QLabel("")
        self.lbl_arch.setWordWrap(True)
        self.lbl_arch.setAlignment(Qt.AlignCenter)
        self.lbl_arch.setStyleSheet("font-weight: bold; font-size: 11px;")
        self.lbl_arch.hide()
        self.layout.addWidget(self.lbl_arch)

        # 2. Nombre de la Versión Card
        self.frame_name = QFrame()
        self.frame_name.setObjectName("FrameVersionName")
        name_layout = QVBoxLayout(self.frame_name)
        name_layout.setContentsMargins(14, 8, 14, 8)
        name_layout.setSpacing(4)

        self.lbl_name_title = QLabel(c.t("UI_VERSION_NAME_LABEL"))
        name_layout.addWidget(self.lbl_name_title)

        self.entry_name = QLineEdit()
        self.entry_name.setPlaceholderText(c.t("UI_VERSION_NAME_PLACEHOLDER"))
        self.entry_name.setFixedHeight(34)
        name_layout.addWidget(self.entry_name)

        self.layout.addWidget(self.frame_name)

        # Watermark illustration of Steve with Diamond Ore (on the right)
        self.watermark = SteveWatermarkWidget(app=self.app)
        self.layout.addWidget(self.watermark, 1)

        # Botón de Acción
        self.btn_install = Tactile3DActionButton(text=c.t("UI_BUTTON_INSTALL_NOW"), app=self.app)
        self.btn_install.setEnabled(False)
        self.btn_install.clicked.connect(self.start_install)
        self.layout.addWidget(self.btn_install)

        self.update_theme_styles()

    def update_theme_styles(self):
        """Update styling of Local APK Tab elements based on current theme."""
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        if hasattr(self, "card_apk"):
            self.card_apk.update_theme_styles()

        if hasattr(self, "frame_name"):
            self.frame_name.setStyleSheet(f"""
                QFrame#FrameVersionName {{
                    background-color: {"rgba(255, 255, 255, 0.055)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                    border: 1px solid {hex_to_rgba(accent, 0.45) if is_dark else hex_to_rgba(accent, 0.35)};
                    border-radius: 14px;
                }}
            """)

        if hasattr(self, "lbl_name_title"):
            self.lbl_name_title.setStyleSheet(
                f"font-size: 13px; font-weight: bold; color: {'#ffffff' if is_dark else '#18191c'}; background: transparent; border: none;"
            )

        if hasattr(self, "entry_name"):
            input_bg = hex_to_rgba("#000000", 0.25) if is_dark else hex_to_rgba("#000000", 0.05)
            self.entry_name.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {input_bg};
                    color: {'#ffffff' if is_dark else '#1a1a1a'};
                    border: 1px solid {hex_to_rgba(accent, 0.40) if is_dark else hex_to_rgba(accent, 0.30)};
                    border-radius: 8px;
                    padding: 0 10px;
                    font-size: 12px;
                }}
                QLineEdit:focus {{
                    border: 1.5px solid {accent};
                }}
            """)

        if hasattr(self, "watermark"):
            self.watermark.update()

        if hasattr(self, "btn_install"):
            self.btn_install.update()

    def browse_apk(self):
        """Open a file picker to select an APK and analyze its architecture."""
        if hasattr(self, "card_apk"):
            self.card_apk._on_browse_clicked()
        else:
            path = ask_open_filename_native(self, title=c.t("UI_SELECT_APK_TITLE"), filetypes=[(c.t("UI_APK_FILES_TYPE"), "*.apk")])
            if path:
                self._set_apk_path(path)

    def check_architecture(self, apk_path):
        """Inspect the APK to determine x86, ARM support and compatibility."""
        found_x86 = False
        found_x64 = False
        found_arm = False
        has_assets = False
        has_lib = False

        try:
            with zipfile.ZipFile(apk_path, "r") as z:
                for n in z.namelist():
                    if n.startswith("assets/"):
                        has_assets = True
                    if n.startswith("lib/"):
                        has_lib = True
                    if "lib/x86/" in n:
                        found_x86 = True
                    if "lib/x86_64/" in n:
                        found_x64 = True
                    if "lib/armeabi" in n or "lib/arm64" in n:
                        found_arm = True
        except Exception as e:
            self.lbl_arch.setText(c.t("UI_ERROR_READING_APK", e=e))
            self.lbl_arch.show()
            self.lbl_arch.setStyleSheet("color: red; font-weight: bold;")
            self.btn_install.setEnabled(False)
            return

        is_compatible = False
        msg = ""
        color = "gray"

        if not has_assets or not has_lib:
            msg = c.t("UI_APK_INVALID")
            color = "red"
        elif found_x86 or found_x64:
            msg = c.t("UI_APK_COMPATIBLE_X86")
            color = "green"
            is_compatible = True
        elif found_arm:
            msg = c.t("UI_APK_INCOMPATIBLE_ARM")
            color = "red"
        else:
            msg = c.t("UI_APK_INVALID")
            color = "orange"

        self.lbl_arch.setText(msg)
        self.lbl_arch.setVisible(bool(msg))
        self.lbl_arch.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.btn_install.setEnabled(is_compatible)

    def start_install(self):
        """Validate inputs and trigger APK installation via the app logic."""
        apk = self.entry_apk.text().strip()
        name = self.entry_name.text().strip()
        if not apk or not os.path.exists(apk):
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), c.t("UI_ERROR_SELECT_VALID_APK"))
            return
        if not name:
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), c.t("UI_ERROR_WRITE_VERSION_NAME"))
            return

        warning = self.dialog.get_warning_for_version(name)
        if warning:
            messagebox.showwarning(
                self,
                c.t("UI_INSTALL_COMPAT_WARN_TITLE"),
                c.t("UI_INSTALL_COMPAT_WARN_MSG", version=name, warning=warning)
            )

        target_root = self.dialog.get_target_root()
        is_target_flatpak = (self.dialog.target_mode_val == c.MODE_INSTALL_FLATPAK)
        f_id = self.dialog.entry_flatpak_id.text().strip() if is_target_flatpak else None

        self.dialog.parent_app.logic.process_apk(
            self.dialog.parent_app, apk, name, target_root=target_root,
            is_target_flatpak=is_target_flatpak, flatpak_id=f_id
        )
        self.dialog.accept()

    def retranslate_ui(self):
        if hasattr(self, "card_apk") and hasattr(self.card_apk, "retranslate_ui"):
            self.card_apk.retranslate_ui()
        if hasattr(self, "lbl_name_title"):
            self.lbl_name_title.setText(c.t("UI_VERSION_NAME_LABEL"))
        if hasattr(self, "entry_name"):
            self.entry_name.setPlaceholderText(c.t("UI_VERSION_NAME_PLACEHOLDER"))
        if hasattr(self, "btn_install") and not self.btn_install.is_cancel_mode():
            self.btn_install.setText(c.t("UI_BUTTON_INSTALL_NOW"))


class InstallSegmentedTabBar(QWidget):
    """
    Segmented tab bar with smooth sliding pill animation, theme glow,
    press sink compression, and hover highlights. Spans full width of the card.
    """
    def __init__(self, parent_widget=None, app=None):
        super().__init__(parent_widget)
        self.app = app
        self.setFixedHeight(38)
        self.setMinimumWidth(240)
        self.setMaximumWidth(560)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._tabs = [c.t("UI_INSTALL_TAB_LOCAL"), c.t("UI_INSTALL_TAB_GOOGLE")]
        self._current_index = 0
        self._indicator_x = 4.0
        self._hover_index = -1
        self._hover_opacity = 0.0
        self._sink_factor = 0.0
        self.on_tab_clicked = None
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        self._anim_pos = QPropertyAnimation(self, b"indicatorX", self)
        self._anim_pos.setDuration(200)
        self._anim_pos.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_hover = QPropertyAnimation(self, b"hoverOpacity", self)
        self._anim_hover.setDuration(120)

        self._anim_sink = QPropertyAnimation(self, b"sinkFactor", self)
        self._anim_sink.setDuration(90)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if 0 <= self._current_index < len(self._tabs):
            self._indicator_x = self._get_tab_rect(self._current_index).x()
            self.update()

    @Property(float)
    def indicatorX(self):
        return self._indicator_x

    @indicatorX.setter
    def indicatorX(self, val):
        self._indicator_x = float(val)
        self.update()

    @Property(float)
    def hoverOpacity(self):
        return self._hover_opacity

    @hoverOpacity.setter
    def hoverOpacity(self, val):
        self._hover_opacity = float(val)
        self.update()

    @Property(float)
    def sinkFactor(self):
        return self._sink_factor

    @sinkFactor.setter
    def sinkFactor(self, val):
        self._sink_factor = float(val)
        self.update()

    def _get_tab_rect(self, index):
        w = (self.width() - 8) / len(self._tabs)
        return QRectF(4 + index * w, 4, w, self.height() - 8)

    tabChanged = Signal(int)

    def setCurrentIndex(self, index, emit_signal=True):
        if index < 0 or index >= len(self._tabs):
            return
        self._current_index = index
        target_rect = self._get_tab_rect(index)
        self._anim_pos.stop()
        self._anim_pos.setStartValue(self._indicator_x)
        self._anim_pos.setEndValue(target_rect.x())
        self._anim_pos.start()
        if emit_signal:
            self.tabChanged.emit(index)
            if self.on_tab_clicked:
                self.on_tab_clicked(index)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._anim_sink.stop()
            self._anim_sink.setStartValue(self._sink_factor)
            self._anim_sink.setEndValue(1.0)
            self._anim_sink.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._anim_sink.stop()
        self._anim_sink.setStartValue(self._sink_factor)
        self._anim_sink.setEndValue(0.0)
        self._anim_sink.start()
        for i in range(len(self._tabs)):
            if self._get_tab_rect(i).contains(event.position()):
                self.setCurrentIndex(i, emit_signal=True)
                break
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position()
        old_hover = self._hover_index
        new_hover = -1
        for i in range(len(self._tabs)):
            if self._get_tab_rect(i).contains(pos):
                new_hover = i
                break
        if new_hover != old_hover:
            self._hover_index = new_hover
            self._anim_hover.stop()
            self._anim_hover.setStartValue(self._hover_opacity)
            self._anim_hover.setEndValue(1.0 if new_hover >= 0 and new_hover != self._current_index else 0.0)
            self._anim_hover.start()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_index = -1
        self._anim_hover.stop()
        self._anim_hover.setStartValue(self._hover_opacity)
        self._anim_hover.setEndValue(0.0)
        self._anim_hover.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        accent_qcolor = QColor(accent)

        bg_rect = QRectF(0, 0, self.width(), self.height())
        track_color = QColor(255, 255, 255, 14) if is_dark else QColor(0, 0, 0, 10)
        painter.setBrush(track_color)
        painter.setPen(QPen(QColor(255, 255, 255, 20) if is_dark else QColor(0, 0, 0, 15), 1))
        painter.drawRoundedRect(bg_rect, 10.0, 10.0)

        if self._hover_index >= 0 and self._hover_index != self._current_index and self._hover_opacity > 0:
            h_rect = self._get_tab_rect(self._hover_index)
            h_color = QColor(255, 255, 255, int(22 * self._hover_opacity)) if is_dark else QColor(0, 0, 0, int(15 * self._hover_opacity))
            painter.setBrush(h_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(h_rect, 8.0, 8.0)

        w_tab = (self.width() - 8) / len(self._tabs)
        sink_inset = self._sink_factor * 1.5
        draw_rect = QRectF(self._indicator_x + sink_inset, 4 + sink_inset, w_tab - (sink_inset * 2), self.height() - 8 - (sink_inset * 2))
        radius = 8.0

        if is_dark:
            steps = 10
            max_expand = 6.0
            max_alpha = 32
            for i in range(steps, 0, -1):
                t = i / steps
                alpha = int(max_alpha * ((1.0 - t) ** 1.7))
                if alpha <= 0:
                    continue
                exp = max_expand * t
                glow_rect = draw_rect.adjusted(-exp, -exp, exp, exp)
                glow_color = QColor(accent_qcolor)
                glow_color.setAlpha(alpha)
                painter.setBrush(glow_color)
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(glow_rect, radius + exp * 0.5, radius + exp * 0.5)

            painter.setBrush(accent_qcolor)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(draw_rect, radius, radius)
        else:
            shadow_steps = 8
            for i in range(shadow_steps, 0, -1):
                t = i / shadow_steps
                alpha = int(22 * ((1.0 - t) ** 1.6))
                if alpha <= 0:
                    continue
                s_rect = draw_rect.adjusted(0, 1.0 * t, 0, 3.5 * t)
                painter.setBrush(QColor(0, 0, 0, alpha))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(s_rect, radius, radius)

            painter.setBrush(accent_qcolor)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(draw_rect, radius, radius)

        font = painter.font()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)

        for i, title in enumerate(self._tabs):
            tab_rect = self._get_tab_rect(i)
            if i == self._current_index:
                text_color = QColor("#ffffff")
            else:
                text_color = QColor("#c2c6cf" if is_dark else "#2a2d34")
            painter.setPen(text_color)
            painter.drawText(tab_rect, Qt.AlignCenter, title)

        painter.end()

    def retranslate_ui(self):
        self._tabs = [c.t("UI_INSTALL_TAB_LOCAL"), c.t("UI_INSTALL_TAB_GOOGLE")]
        if 0 <= self._current_index < len(self._tabs):
            self._indicator_x = self._get_tab_rect(self._current_index).x()
        self.update()


class InstallViewWidget(QWidget):
    """Reusable widget for installing Minecraft versions from APK or Google Play."""
    
    def __init__(self, parent_app, parent=None, is_embedded=False):
        super().__init__(parent)
        self.parent_app = parent_app
        self.is_embedded = is_embedded
        self.dialog_parent = parent if isinstance(parent, QDialog) else None

        mode, self.accent = _find_theme(parent_app)
        self.light = mode != "Dark"
        self.bg = "#f4f5f7" if self.light else "#242424"
        self.frame_bg = "#e8e8e8" if self.light else "#333333"
        self.drop_highlight = "#d6dade" if self.light else "#3a3a3a"
        self.text_color = "#1a1a1a" if self.light else "white"
        self.muted_color = "#666666" if self.light else "#888888"

        self.target_mode_val = c.MODE_INSTALL_FLATPAK if parent_app.running_in_flatpak else c.MODE_INSTALL_LOCAL
        self.warnings_data = []
        self._warnings_fetcher = None
        self._fetch_warnings()
        self.setup_ui()

    def setup_ui(self):
        """Build the full installer UI with animated segmented tabs, mode selection, and styling."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 10, 14, 10)
        self.main_layout.setSpacing(10)

        # 1. Custom Animated Segmented Tab Bar (APK Local / Google Play) Centered
        tab_bar_row = QHBoxLayout()
        tab_bar_row.setContentsMargins(0, 0, 0, 0)
        tab_bar_row.setAlignment(Qt.AlignCenter)
        self.tab_bar = InstallSegmentedTabBar(self, app=self.parent_app)
        tab_bar_row.addWidget(self.tab_bar)
        self.main_layout.addLayout(tab_bar_row)

        # 2. Stacked Content Area for the two install sources
        self.tab_stack = AdaptiveStackedWidget()
        self.local_tab = LocalApkTab(self)
        self.google_tab = GooglePlayTab(self)

        self.tab_stack.addWidget(self.local_tab)
        self.tab_stack.addWidget(self.google_tab)

        def _on_tab_changed(idx):
            self.tab_stack.setCurrentIndex(idx)
            self.tab_stack.updateGeometry()
            self.updateGeometry()

        self.tab_bar.tabChanged.connect(_on_tab_changed)

        self.main_layout.addWidget(self.tab_stack, 1)

        # 3. Modo de Instalación (Global para ambas pestañas)
        self.frame_mode = QFrame()
        self.frame_mode.setObjectName("FrameMode")
        mode_layout = QVBoxLayout(self.frame_mode)
        mode_layout.setContentsMargins(14, 8, 14, 8)
        mode_layout.setSpacing(4)

        self.lbl_mode_title = QLabel(c.t("UI_INSTALL_MODE_DEST_LABEL"))
        mode_layout.addWidget(self.lbl_mode_title)

        if self.parent_app.running_in_flatpak:
            modes_available = [
                (c.MODE_INSTALL_OWN, c.t("UI_INSTALL_MODE_OWN")),
                (c.MODE_INSTALL_SHARED, c.t("UI_INSTALL_MODE_SHARED")),
                (c.MODE_INSTALL_FLATPAK, c.t("UI_INSTALL_MODE_FLATPAK_DESC")),
            ]
            default_mode = c.MODE_INSTALL_OWN
        else:
            modes_available = [
                (c.MODE_INSTALL_LOCAL, c.t("UI_INSTALL_MODE_LOCAL")),
                (c.MODE_INSTALL_FLATPAK, c.t("UI_INSTALL_MODE_FLATPAK_DESC")),
            ]
            default_mode = c.MODE_INSTALL_LOCAL

        self.target_mode_val = default_mode
        self.radio_buttons = []

        for mode_key, mode_display in modes_available:
            rb = QRadioButton(mode_display if mode_key != c.MODE_INSTALL_FLATPAK else c.t("UI_FLATPAK_CUSTOM_ID_LABEL"))
            rb.setChecked(mode_key == default_mode)
            rb.toggled.connect(lambda checked, k=mode_key: self.set_target_mode(k) if checked else None)
            mode_layout.addWidget(rb)
            self.radio_buttons.append((rb, mode_key))

            if mode_key == c.MODE_INSTALL_FLATPAK:
                self.frame_flatpak_container = QWidget()
                fp_layout = QHBoxLayout(self.frame_flatpak_container)
                fp_layout.setContentsMargins(24, 2, 0, 4)
                fp_layout.setSpacing(6)

                self.entry_flatpak_id = QLineEdit()
                self.entry_flatpak_id.setText(self.parent_app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.DEFAULT_FLATPAK_ID))
                self.entry_flatpak_id.setPlaceholderText(c.t("UI_FLATPAK_ID_PLACEHOLDER"))
                self.entry_flatpak_id.setFixedHeight(34)
                fp_layout.addWidget(self.entry_flatpak_id)
                mode_layout.addWidget(self.frame_flatpak_container)
                self.frame_flatpak_container.setVisible(default_mode == c.MODE_INSTALL_FLATPAK)

        self.main_layout.addWidget(self.frame_mode)
        self.update_theme_styles()

    def set_target_mode(self, mode_key):
        """Update the selected installation mode and toggle the Flatpak ID field."""
        self.target_mode_val = mode_key
        if hasattr(self, 'frame_flatpak_container'):
            self.frame_flatpak_container.setVisible(mode_key == c.MODE_INSTALL_FLATPAK)
        if hasattr(self, 'entry_flatpak_id'):
            self.entry_flatpak_id.setEnabled(mode_key == c.MODE_INSTALL_FLATPAK)

    def _fetch_warnings(self):
        self._warnings_fetcher = VersionWarningsFetcher()
        self._warnings_fetcher.finished.connect(self._on_warnings_fetched)
        self._warnings_fetcher.start()

    def _on_warnings_fetched(self, warnings):
        self.warnings_data = warnings

    def get_warning_for_version(self, version_name):
        if not version_name or not self.warnings_data:
            return None
        for entry in self.warnings_data:
            if entry.get("version") == version_name:
                return entry.get("reason")
        return None

    def accept(self):
        """Triggered on successful installation."""
        try:
            if hasattr(self.parent_app, 'load_installed_versions'):
                self.parent_app.load_installed_versions()
        except Exception as e:
            logger.warning(f"Failed to reload installed versions: {e}")
        if self.dialog_parent:
            self.dialog_parent.accept()

    def _safe_stop_thread(self, thread):
        """Stop a background fetch thread without freezing the UI or throwing deleted C++ object errors."""
        if thread is None:
            return
        try:
            import shiboken6
            if not shiboken6.isValid(thread):
                return
        except Exception:
            pass
        try:
            if not thread.isRunning():
                return
            thread.requestInterruption()
            if thread.wait(250):
                return
            thread.finished.connect(thread.deleteLater)
            thread.setParent(None)
        except (RuntimeError, ReferenceError, TypeError):
            pass

    def cleanup(self):
        self._safe_stop_thread(self._warnings_fetcher)
        if hasattr(self, 'google_tab'):
            self._safe_stop_thread(self.google_tab.fetcher)

    def update_theme_styles(self):
        """Update inner tabs, tab bar, and mode card when theme switches."""
        is_dark = getattr(self.parent_app, "is_dark_mode", True) if self.parent_app else True
        accent = getattr(self.parent_app, "current_accent_color", "#1f6aa5") if self.parent_app else "#1f6aa5"

        if hasattr(self, 'tab_bar'):
            self.tab_bar.update()
        if hasattr(self, 'local_tab') and hasattr(self.local_tab, 'update_theme_styles'):
            self.local_tab.update_theme_styles()
        if hasattr(self, 'google_tab') and hasattr(self.google_tab, 'update_theme_styles'):
            self.google_tab.update_theme_styles()

        if hasattr(self, 'frame_mode'):
            self.frame_mode.setStyleSheet(f"""
                QFrame#FrameMode {{
                    background-color: {"rgba(255, 255, 255, 0.055)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                    border: 1px solid {hex_to_rgba(accent, 0.45) if is_dark else hex_to_rgba(accent, 0.35)};
                    border-radius: 14px;
                }}
                QRadioButton {{
                    color: {'#d1d5db' if is_dark else '#2c2f36'};
                    font-size: 12px;
                    spacing: 8px;
                }}
                QRadioButton::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 8px;
                    border: 1.5px solid {hex_to_rgba(accent, 0.60) if is_dark else hex_to_rgba(accent, 0.50)};
                    background-color: {"rgba(0, 0, 0, 0.20)" if is_dark else "rgba(0, 0, 0, 0.05)"};
                }}
                QRadioButton::indicator:checked {{
                    background-color: {accent};
                    border: 1.5px solid {accent};
                }}
            """)

        if hasattr(self, 'lbl_mode_title'):
            self.lbl_mode_title.setStyleSheet(
                f"font-size: 13px; font-weight: bold; color: {'#ffffff' if is_dark else '#18191c'}; background: transparent; border: none;"
            )

        if hasattr(self, 'entry_flatpak_id'):
            input_bg = hex_to_rgba("#000000", 0.25) if is_dark else hex_to_rgba("#000000", 0.05)
            self.entry_flatpak_id.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {input_bg};
                    color: {'#ffffff' if is_dark else '#1a1a1a'};
                    border: 1px solid {hex_to_rgba(accent, 0.40) if is_dark else hex_to_rgba(accent, 0.30)};
                    border-radius: 8px;
                    padding: 0 10px;
                    font-size: 12px;
                }}
                QLineEdit:focus {{
                    border: 1.5px solid {accent};
                }}
            """)

    def get_target_root(self):
        """Resolve the installation root path based on the selected mode."""
        mode_key = self.target_mode_val
        if mode_key == c.MODE_INSTALL_FLATPAK:
            custom_id = self.entry_flatpak_id.text().strip() or c.DEFAULT_FLATPAK_ID
            return os.path.join(self.parent_app.home, f".var/app/{custom_id}/data/mcpelauncher")
        elif mode_key == c.MODE_INSTALL_OWN:
            return self.parent_app.our_data_path if self.parent_app.running_in_flatpak else self.parent_app.compiled_path
        elif mode_key == c.MODE_INSTALL_SHARED:
            return os.path.join(self.parent_app.home, c.LOCAL_SHARE_DIR)
        else: # MODE_INSTALL_LOCAL
            return self.parent_app.compiled_path

    def retranslate_ui(self):
        if hasattr(self, "tab_bar") and hasattr(self.tab_bar, "retranslate_ui"):
            self.tab_bar.retranslate_ui()
        if hasattr(self, "local_tab") and hasattr(self.local_tab, "retranslate_ui"):
            self.local_tab.retranslate_ui()
        if hasattr(self, "google_tab") and hasattr(self.google_tab, "retranslate_ui"):
            self.google_tab.retranslate_ui()
        if hasattr(self, "lbl_mode_title"):
            self.lbl_mode_title.setText(c.t("UI_INSTALL_MODE_DEST_LABEL"))
        if hasattr(self, "radio_buttons"):
            for rb, mode_key in self.radio_buttons:
                if mode_key == c.MODE_INSTALL_FLATPAK:
                    rb.setText(c.t("UI_FLATPAK_CUSTOM_ID_LABEL"))
                elif mode_key == c.MODE_INSTALL_OWN:
                    rb.setText(c.t("UI_INSTALL_MODE_OWN"))
                elif mode_key == c.MODE_INSTALL_SHARED:
                    rb.setText(c.t("UI_INSTALL_MODE_SHARED"))
                elif mode_key == c.MODE_INSTALL_LOCAL:
                    rb.setText(c.t("UI_INSTALL_MODE_LOCAL"))
        if hasattr(self, "entry_flatpak_id"):
            self.entry_flatpak_id.setPlaceholderText(c.t("UI_FLATPAK_ID_PLACEHOLDER"))


class InstallDialog(QDialog):
    """Dialog for installing new Minecraft versions from APK files or Google Play."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_app = parent
        self.setWindowTitle(c.t("UI_INSTALL_NEW_VERSION_TITLE"))
        self.resize(600, 700)

        self.widget = InstallViewWidget(parent, self, is_embedded=False)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.widget)

        mode, accent = _find_theme(parent)
        bg = "#f4f5f7" if mode != "Dark" else "#242424"
        text_color = "#1a1a1a" if mode != "Dark" else "white"
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {text_color};
            }}
            QLabel {{
                background-color: transparent;
            }}
        """)

    def retranslate_ui(self):
        self.setWindowTitle(c.t("UI_INSTALL_NEW_VERSION_TITLE"))
        if hasattr(self, "widget") and hasattr(self.widget, "retranslate_ui"):
            self.widget.retranslate_ui()

    def closeEvent(self, event):
        self.widget.cleanup()
        super().closeEvent(event)

    def __getattr__(self, name):
        """Proxy missing attributes to the inner widget for full backward compatibility."""
        return getattr(self.widget, name)
