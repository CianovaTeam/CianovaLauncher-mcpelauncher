import os
import shutil
import math
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QScrollArea, QCheckBox, QPushButton, QFrame,
                             QStackedWidget, QGraphicsOpacityEffect, QSizePolicy)
from PySide6.QtCore import (Qt, QRectF, Property, QPropertyAnimation, QEasingCurve,
                            QTimer, QSize, QRect, QPoint, QParallelAnimationGroup, QUrl, Signal)
from PySide6.QtGui import (QPainter, QColor, QFont, QPen, QConicalGradient, QIcon, QPixmap,
                           QMovie, QImage, QLinearGradient, QDesktopServices, QPainterPath)
from src import constants as c
from src.core.ui_utils import FlowLayout
from src.utils.resource_path import resource_path
from src.utils.image_manager import ImageManager
from src.utils.colors import adjust_color, blend_colors, hex_to_rgba
from src.utils.logger import logger
from src.gui import custom_dialogs as messagebox
from src.gui.install_dialog import InstallViewWidget
from src.gui.tabs.screenshots_tab import ScreenshotsTab
from src.gui.tabs.worlds_tab import WorldsTab
from src.gui.tabs.packs_tab import PacksTab
from src.gui.tabs.mods_tab import ModsTab
from src.gui.tabs.settings_tab import ModernToggle


class QuickToggleSwitch(QCheckBox):
    """
    High-performance, instant-response animated toggle switch for quick preference cards.
    Immune to feedback loops from synchronous UI state callers.
    """
    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(44, 24)
        self._thumb_pos = 23.0 if self.isChecked() else 3.0
        self._anim = QPropertyAnimation(self, b"thumbPos", self)
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.OutQuad)

    def _get_thumb_pos(self):
        return self._thumb_pos

    def _set_thumb_pos(self, val):
        self._thumb_pos = float(val)
        self.update()

    thumbPos = Property(float, _get_thumb_pos, _set_thumb_pos)

    def _start_anim(self, target):
        if abs(self._thumb_pos - target) < 0.2:
            self._thumb_pos = target
            self.update()
            return
        self._anim.stop()
        self._anim.setStartValue(self._thumb_pos)
        self._anim.setEndValue(target)
        self._anim.start()

    def setChecked(self, checked):
        checked = bool(checked)
        if self.isChecked() == checked:
            target = 23.0 if checked else 3.0
            if abs(self._thumb_pos - target) > 0.5:
                self._start_anim(target)
            return
        super().setChecked(checked)
        self._start_anim(23.0 if checked else 3.0)

    def nextCheckState(self):
        super().nextCheckState()
        self._start_anim(23.0 if self.isChecked() else 3.0)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        w, h = float(self.width()), float(self.height())
        radius = h / 2.0

        accent_hex = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        accent_color = QColor(accent_hex)

        # Track background
        if self.isChecked():
            track_color = accent_color
        else:
            track_color = QColor(255, 255, 255, 45) if is_dark else QColor(0, 0, 0, 50)

        p.setBrush(track_color)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        # Thumb
        thumb_d = h - 6.0
        p.setBrush(QColor("#ffffff"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(self._thumb_pos, 3.0, thumb_d, thumb_d))
        p.end()


class QuickSubCard(QFrame):
    """Interactive sub-card container for quick actions and preference toggles."""
    def __init__(self, parent=None, on_click=None):
        super().__init__(parent)
        self.setObjectName("QuickSubCard")
        self.setCursor(Qt.PointingHandCursor)
        self._on_click = on_click

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._on_click:
            child = self.childAt(event.pos())
            if not isinstance(child, (QCheckBox, QPushButton)):
                self._on_click()
        super().mousePressEvent(event)


class NewsCarouselCard(QFrame):
    """
    Sleek News Carousel card following the launcher aesthetic:
    - Uppercase 'NOVEDADES' section header
    - Rounded empty image placeholder frame ('el hueco')
    - Indicator news title and multi-line description
    - Interactive 4-dot pagination indicator with smooth page switching and auto-slide
    """
    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.setObjectName("RightTopCard")
        self.app = app
        self._current_index = 0
        self._items = self._get_items()

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 12, 14, 12)
        self._layout.setSpacing(8)

        # 1. Header
        header_text = c.t("UI_NEWS_HEADER") if hasattr(c, "t") else "NEWS"
        self.lbl_header = QLabel(header_text)
        self.lbl_header.setObjectName("NewsPanelHeader")
        self._layout.addWidget(self.lbl_header, 0)

        # 2. Image Placeholder Frame (horizontal banner filling card width)
        self.frame_image = QFrame()
        self.frame_image.setObjectName("NewsImagePlaceholder")
        self.frame_image.setMinimumHeight(105)
        self.frame_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._layout.addWidget(self.frame_image, 1)

        # 3. Title
        self.lbl_title = QLabel(self._items[0]["title"])
        self.lbl_title.setObjectName("NewsItemTitle")
        self.lbl_title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._layout.addWidget(self.lbl_title, 0)

        # 4. Description
        self.lbl_desc = QLabel(self._items[0]["desc"])
        self.lbl_desc.setObjectName("NewsItemDesc")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._layout.addWidget(self.lbl_desc, 0)

        # 5. Carousel Dots
        self.row_dots = QHBoxLayout()
        self.row_dots.setContentsMargins(0, 0, 0, 2)
        self.row_dots.setSpacing(7)
        self.row_dots.setAlignment(Qt.AlignCenter)

        self.dots = []
        for i in range(len(self._items)):
            dot = QPushButton()
            dot.setFixedSize(8, 8)
            dot.setCursor(Qt.PointingHandCursor)
            dot.clicked.connect(lambda _, idx=i: self.set_page(idx))
            self.dots.append(dot)
            self.row_dots.addWidget(dot)

        self._layout.addLayout(self.row_dots)

        # Auto-slide timer (7 seconds)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._auto_next)
        self._timer.start(7000)

        self.update_theme_styles()

    def _auto_next(self):
        next_idx = (self._current_index + 1) % len(self._items)
        self.set_page(next_idx)

    def set_page(self, index):
        if 0 <= index < len(self._items):
            self._current_index = index
            item = self._items[index]
            self.lbl_title.setText(item["title"])
            self.lbl_desc.setText(item["desc"])
            self._update_dots_style()
            if hasattr(self, "_timer") and self._timer.isActive():
                self._timer.start(7000)

    def _update_dots_style(self):
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        active_color = "#00c0f0" if is_dark else accent
        inactive_color = "rgba(255, 255, 255, 0.18)" if is_dark else "rgba(0, 0, 0, 0.20)"

        for i, dot in enumerate(self.dots):
            if i == self._current_index:
                dot.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {active_color};
                        border: none;
                        border-radius: 4px;
                    }}
                """)
            else:
                dot.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {inactive_color};
                        border: none;
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        background-color: {"rgba(255, 255, 255, 0.35)" if is_dark else "rgba(0, 0, 0, 0.35)"};
                    }}
                """)

    def update_theme_styles(self):
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        self.lbl_header.setStyleSheet(
            f"font-size: 11px; font-weight: 800; letter-spacing: 0.8px; color: {'#94a3b8' if is_dark else '#475569'}; background: transparent; border: none; padding-left: 2px;"
        )
        self.frame_image.setStyleSheet(f"""
            QFrame#NewsImagePlaceholder {{
                background-color: {"rgba(255, 255, 255, 0.035)" if is_dark else "rgba(0, 0, 0, 0.03)"};
                border: 1px solid {"rgba(255, 255, 255, 0.07)" if is_dark else "rgba(0, 0, 0, 0.08)"};
                border-radius: 10px;
            }}
        """)
        self.lbl_title.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {'#ffffff' if is_dark else '#0f172a'}; background: transparent; border: none;"
        )
        self.lbl_desc.setStyleSheet(
            f"font-size: 11.5px; color: {'#94a3b8' if is_dark else '#64748b'}; background: transparent; border: none;"
        )
        self._update_dots_style()

    def _get_items(self):
        return [
            {
                "title": c.t("UI_NEWS_TITLE_1") if hasattr(c, "t") else "Spring to Life",
                "desc": c.t("UI_NEWS_DESC_1") if hasattr(c, "t") else "Discover new features and improvements in the latest update."
            },
            {
                "title": c.t("UI_NEWS_TITLE_2") if hasattr(c, "t") else "Updates & Changes",
                "desc": c.t("UI_NEWS_DESC_2") if hasattr(c, "t") else "Explore full release notes and new features in Minecraft Bedrock."
            },
            {
                "title": c.t("UI_NEWS_TITLE_3") if hasattr(c, "t") else "Mods & Performance",
                "desc": c.t("UI_NEWS_DESC_3") if hasattr(c, "t") else "Optimize smoothness and manage addons easily from the launcher."
            },
            {
                "title": c.t("UI_NEWS_TITLE_4") if hasattr(c, "t") else "Screenshots Gallery",
                "desc": c.t("UI_NEWS_DESC_4") if hasattr(c, "t") else "View, edit with filters, and share your in-game screenshots."
            }
        ]

    def retranslate_ui(self):
        self.lbl_header.setText(c.t("UI_NEWS_HEADER") if hasattr(c, "t") else "NEWS")
        self._items = self._get_items()
        if 0 <= self._current_index < len(self._items):
            self.lbl_title.setText(self._items[self._current_index]["title"])
            self.lbl_desc.setText(self._items[self._current_index]["desc"])

    def resizeEvent(self, event):
        super().resizeEvent(event)


class VerticalAnimatedStackedWidget(QStackedWidget):
    """
    QStackedWidget with smooth vertical slide and cross-fade transition
    between views (Inicio <-> Instalación) matching the topbar aesthetic.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._prev_index = -1
        self._anim_group = None
        self._anim_effect = None
        self._anim_target = None
        self.currentChanged.connect(self._on_index_changed)

    def minimumSizeHint(self):
        cur = self.currentWidget()
        if cur:
            return cur.minimumSizeHint()
        return QSize(200, 200)

    def sizeHint(self):
        cur = self.currentWidget()
        if cur:
            return cur.sizeHint()
        return super().sizeHint()

    def _on_index_changed(self, index):
        if index < 0:
            return
        if self._prev_index == -1:
            self._prev_index = index
            return
        if index == self._prev_index:
            return

        direction = 1 if index > self._prev_index else -1
        self._prev_index = index

        current_widget = self.widget(index)
        if not current_widget or not self.isVisible():
            return

        if self._anim_group and self._anim_group.state() == QParallelAnimationGroup.Running:
            self._anim_group.stop()
        if self._anim_target and self._anim_effect:
            try:
                self._anim_target.setGraphicsEffect(None)
            except RuntimeError:
                pass

        effect = QGraphicsOpacityEffect(current_widget)
        current_widget.setGraphicsEffect(effect)
        self._anim_effect = effect
        self._anim_target = current_widget

        anim_fade = QPropertyAnimation(effect, b"opacity", self)
        anim_fade.setDuration(190)
        anim_fade.setStartValue(0.0)
        anim_fade.setEndValue(1.0)
        anim_fade.setEasingCurve(QEasingCurve.OutCubic)

        def _cleanup():
            if current_widget == self._anim_target:
                current_widget.setGraphicsEffect(None)
                self._anim_effect = None
                self._anim_target = None

        anim_fade.finished.connect(_cleanup)
        anim_fade.start()

class SidebarNavButton(QPushButton):
    """
    Sidebar navigation item with clean muted styling, 8px rounded corners,
    and responsive hover/press states.
    """
    def __init__(self, text, icon_name=None, app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self._text = text
        self._is_active = False
        self._is_hovered = False
        self._hover_opacity = 0.0
        self.setObjectName("SidebarNavButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(260, 40)
        self.setStyleSheet("background: transparent; border: none;")

        if icon_name:
            self._icon = ImageManager.get_icon(icon_name)
        else:
            self._icon = QIcon()

        self._anim_hover = QPropertyAnimation(self, b"hoverOpacity", self)
        self._anim_hover.setDuration(120)

    def setText(self, text: str):
        self._text = text
        super().setText(text)
        self.update()

    @Property(float)
    def hoverOpacity(self):
        return self._hover_opacity

    @hoverOpacity.setter
    def hoverOpacity(self, val):
        self._hover_opacity = float(val)
        self.update()

    def enterEvent(self, event):
        self._is_hovered = True
        self._anim_hover.stop()
        self._anim_hover.setStartValue(self._hover_opacity)
        self._anim_hover.setEndValue(1.0)
        self._anim_hover.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self._anim_hover.stop()
        self._anim_hover.setStartValue(self._hover_opacity)
        self._anim_hover.setEndValue(0.0)
        self._anim_hover.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0, 0, w, h)
        radius = 10.0

        # Inactive subtle hover pill
        if not self._is_active and self._hover_opacity > 0:
            h_color = QColor(255, 255, 255, int(18 * self._hover_opacity)) if is_dark else QColor(0, 0, 0, int(14 * self._hover_opacity))
            painter.setBrush(h_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, radius, radius)

        # Draw icon and text: In Light mode, always crisp solid black (#111214)
        if is_dark:
            text_color = QColor("#ffffff" if self._is_active else "#c2c6cf")
        else:
            text_color = QColor("#111214")

        painter.setPen(text_color)
        font = painter.font()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)

        icon_size = 18
        icon_x = 16
        icon_y = int((h - icon_size) / 2.0)
        if not self._icon.isNull():
            icon_rect = QRect(icon_x, icon_y, icon_size, icon_size)
            if not is_dark:
                pix = self._icon.pixmap(icon_size, icon_size)
                tinted = QPixmap(pix.size())
                tinted.fill(Qt.transparent)
                p_tint = QPainter(tinted)
                p_tint.drawPixmap(0, 0, pix)
                p_tint.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                p_tint.fillRect(tinted.rect(), QColor("#111214"))
                p_tint.end()
                painter.drawPixmap(icon_rect, tinted)
            else:
                self._icon.paint(painter, icon_rect)
            text_rect = QRect(icon_x + icon_size + 12, 0, int(w - (icon_x + icon_size + 12)), int(h))
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self._text)
        else:
            painter.drawText(QRect(16, 0, int(w - 16), int(h)), Qt.AlignVCenter | Qt.AlignLeft, self._text)

        painter.end()


class SidebarNavGroup(QWidget):
    """
    Container managing vertical sidebar navigation with a smooth, rapid 'elevator'
    sliding indicator animation and clean muted styling.
    """
    def __init__(self, app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self.setFixedWidth(260)
        self.group_layout = QVBoxLayout(self)
        self.group_layout.setContentsMargins(0, 0, 0, 0)
        self.group_layout.setSpacing(6)

        self._buttons = []
        self._current_index = 0
        self._indicator_y = 0.0
        self._indicator_height = 42.0

        self._anim = QPropertyAnimation(self, b"indicatorY", self)
        self._anim.setDuration(190)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    @Property(float)
    def indicatorY(self):
        return self._indicator_y

    @indicatorY.setter
    def indicatorY(self, val):
        self._indicator_y = float(val)
        self.update()

    def addButton(self, btn, callback=None):
        idx = len(self._buttons)
        self._buttons.append(btn)
        self.group_layout.addWidget(btn)
        self.setFixedHeight(len(self._buttons) * 40 + max(0, len(self._buttons) - 1) * 6)
        if idx == 0:
            btn._is_active = True

        def on_click():
            self.setCurrentIndex(idx)
            if callback:
                callback()

        btn.clicked.connect(on_click)

    def setCurrentIndex(self, idx):
        if idx < 0 or idx >= len(self._buttons):
            return
        self._current_index = idx
        for i, b in enumerate(self._buttons):
            b._is_active = (i == idx)
            b.update()

        target_btn = self._buttons[idx]
        target_y = float(target_btn.y())
        if target_y == 0.0 and idx > 0:
            target_y = float(idx * (40 + 6))
        self._indicator_height = float(target_btn.height()) if target_btn.height() > 0 else 40.0

        self._anim.stop()
        self._anim.setStartValue(self._indicator_y)
        self._anim.setEndValue(target_y)
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        accent_color = QColor(accent)
        bg_alpha = 70 if is_dark else 100  # Subido el color de selección en modo claro
        pill_bg = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), bg_alpha)

        rect = QRectF(0, self._indicator_y, float(self.width()), self._indicator_height)
        radius = 10.0  # Esquinas redondeadas suaves (10px)

        painter.setBrush(pill_bg)
        painter.setPen(Qt.NoPen)  # Sin borde
        painter.drawRoundedRect(rect, radius, radius)
        painter.end()


class PlaySidebarCard(QFrame):
    """
    Encapsulated vertical card sidebar for Play tab matching the full-height
    wallpaper presentation of the previous settings sidebar.
    Displays wallpaper background (settings-win.png) scaled to full height and
    anchored at the bottom, smooth dark gradient overlay, and rounded border.
    """
    def __init__(self, parent=None, app=None, image_path=None):
        super().__init__(parent)
        self.app = app
        self.setObjectName("PlaySidebarCard")
        self.setFixedWidth(280)
        self._movie = None
        self._bg_pixmap = None

        if not image_path:
            image_path = resource_path("settings-win.png")
            if not os.path.exists(image_path):
                image_path = resource_path("assets/media/settings-win.png")
            if not os.path.exists(image_path):
                image_path = resource_path("main-win.png")

        self.setImagePath(image_path)

    def _on_frame_changed(self, frame_num):
        self.update()

    def setImagePath(self, path):
        if self._movie:
            self._movie.stop()
            self._movie.deleteLater()
            self._movie = None
        self._bg_pixmap = None
        self._image_path = path

        if path and os.path.exists(path):
            if path.lower().endswith(".gif"):
                self._movie = QMovie(path)
                self._movie.frameChanged.connect(self._on_frame_changed)
                self._movie.start()
            else:
                self._bg_pixmap = QPixmap(path)
        self.update()

    def paintEvent(self, event):
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        pm = None
        if self._movie and self._movie.isValid():
            pm = self._movie.currentPixmap()
        elif self._bg_pixmap and not self._bg_pixmap.isNull():
            pm = self._bg_pixmap

        if not pm or pm.isNull():
            return

        target_img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        target_img.fill(Qt.transparent)

        p_img = QPainter(target_img)
        p_img.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p_img.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        pw = pm.width()
        ph = pm.height()
        scale = max(w / float(pw), h / float(ph))
        target_w = int(pw * scale)
        target_h = int(ph * scale)
        target_y = int(h - target_h)
        # Flush to the left edge while covering full width to the right edge
        target_x = 0

        p_img.drawPixmap(target_x, target_y, target_w, target_h, pm)

        # Gradient mask:
        # 1. Top transparent (removes blue sky, leaving only smooth diffusion)
        # 2. Middle smooth diffusion into landscape and glowing sunset
        # 3. Full opacity through tree and riverbank
        # 4. Small bottom diffusion fading softly behind social buttons
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.00, QColor(0, 0, 0, 0))
        grad.setColorAt(0.36, QColor(0, 0, 0, 0))
        grad.setColorAt(0.50, QColor(0, 0, 0, 45))
        grad.setColorAt(0.66, QColor(0, 0, 0, 180))
        grad.setColorAt(0.76, QColor(0, 0, 0, 255))
        grad.setColorAt(0.88, QColor(0, 0, 0, 255))
        grad.setColorAt(0.96, QColor(0, 0, 0, 80))
        grad.setColorAt(1.00, QColor(0, 0, 0, 0))

        p_img.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        p_img.fillRect(target_img.rect(), grad)
        p_img.end()

        # Borderless render: seamlessly blends into window
        p = QPainter(self)
        p.drawImage(0, 0, target_img)
        p.end()


class SidebarSocialButton(QPushButton):
    """
    Sleek translucent icon button with hover animations and theme-aware borders
    for community links (Discord, Web, GitHub).
    """
    def __init__(self, icon_filename, url, tooltip="", app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self.url = url
        self.setFixedSize(38, 38)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setStyleSheet("background: transparent; border: none;")

        icon_path = resource_path(icon_filename)
        self._raw_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self._hover_scale = 1.0
        self._anim_hover = QPropertyAnimation(self, b"hoverScale", self)
        self._anim_hover.setDuration(120)
        self._anim_hover.setEasingCurve(QEasingCurve.OutCubic)

        self.clicked.connect(self._open_link)

    def getHoverScale(self):
        return self._hover_scale

    def setHoverScale(self, val):
        self._hover_scale = float(val)
        self.update()

    hoverScale = Property(float, getHoverScale, setHoverScale)

    def enterEvent(self, event):
        self._anim_hover.stop()
        self._anim_hover.setStartValue(self._hover_scale)
        self._anim_hover.setEndValue(1.08)
        self._anim_hover.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._anim_hover.stop()
        self._anim_hover.setStartValue(self._hover_scale)
        self._anim_hover.setEndValue(1.0)
        self._anim_hover.start()
        super().leaveEvent(event)

    def _open_link(self):
        if self.url:
            QDesktopServices.openUrl(QUrl(self.url))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h = float(self.width()), float(self.height())
        cx, cy = w / 2.0, h / 2.0

        painter.save()
        painter.translate(cx, cy)
        painter.scale(self._hover_scale, self._hover_scale)
        painter.translate(-cx, -cy)

        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        is_hovered = self.underMouse()

        rect = QRectF(2, 2, w - 4, h - 4)

        if is_hovered:
            bg_col = QColor(hex_to_rgba(accent, 0.22 if is_dark else 0.16))
            border_col = QColor(accent)
        else:
            bg_col = QColor(255, 255, 255, 14) if is_dark else QColor(0, 0, 0, 10)
            border_col = QColor(255, 255, 255, 28) if is_dark else QColor(0, 0, 0, 20)

        painter.setBrush(bg_col)
        painter.setPen(QPen(border_col, 1.2 if is_hovered else 1.0))
        painter.drawRoundedRect(rect, 8.0, 8.0)

        if not self._raw_icon.isNull():
            pix = self._raw_icon.pixmap(20, 20)
            tinted = QPixmap(pix.size())
            tinted.fill(Qt.transparent)
            p_tint = QPainter(tinted)
            p_tint.drawPixmap(0, 0, pix)
            p_tint.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            icon_color = QColor(accent) if is_hovered else (QColor("#dedede") if is_dark else QColor("#222224"))
            p_tint.fillRect(tinted.rect(), icon_color)
            p_tint.end()

            ix = int(cx - 10)
            iy = int(cy - 10)
            painter.drawPixmap(ix, iy, tinted)

        painter.restore()
        painter.end()


class SleekLaunchActionCard(QFrame):
    """
    Sleek theme-aware launch action card with bold current action,
    accent arrow, subtle subtitle 'Al lanzar el juego', and animated sleek popup.
    """
    actionChanged = Signal(str)

    def __init__(self, app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self.setObjectName("LaunchComboCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(150)
        self.setMaximumWidth(220)
        self.setFixedHeight(50)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 7, 14, 7)
        self._layout.setSpacing(2)

        self._top_row = QHBoxLayout()
        self._top_row.setContentsMargins(0, 0, 0, 0)
        self._top_row.setSpacing(6)

        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; background: transparent; border: none;")
        self._top_row.addWidget(self.lbl_title, 1)

        self.lbl_chevron = QLabel("▼")
        self.lbl_chevron.setStyleSheet("font-size: 9px; background: transparent; border: none;")
        self._top_row.addWidget(self.lbl_chevron, 0, Qt.AlignVCenter)
        self._layout.addLayout(self._top_row)

        sub_text = (c.t("UI_LAUNCH_ACTION_LABEL") if hasattr(c, "t") else "When launching the game:").rstrip(":")
        self.lbl_sub = QLabel(sub_text)
        self.lbl_sub.setStyleSheet("font-size: 10px; color: #888888; background: transparent; border: none;")
        self._layout.addWidget(self.lbl_sub)

        self._actions = [
            (c.t("UI_LAUNCH_ACTION_NONE"), c.LAUNCH_ACTION_NONE),
            (c.t("UI_LAUNCH_ACTION_CLOSE"), c.LAUNCH_ACTION_CLOSE),
            (c.t("UI_LAUNCH_ACTION_HIDE"), c.LAUNCH_ACTION_HIDE),
        ]

        current_action = self.app.config.get(c.CONFIG_KEY_LAUNCH_ACTION, c.LAUNCH_ACTION_NONE) if self.app else c.LAUNCH_ACTION_NONE
        self._current_action = current_action
        self._update_display_text()

    def _update_display_text(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        text_color = "#ffffff" if is_dark else "#111214"
        sub_color = "#888888" if is_dark else "#4a4d55"
        self.lbl_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {text_color}; background: transparent; border: none;")
        self.lbl_chevron.setStyleSheet(f"font-size: 9px; font-weight: bold; color: {accent}; background: transparent; border: none;")
        self.lbl_sub.setStyleSheet(f"font-size: 10px; font-weight: {'normal' if is_dark else 'bold'}; color: {sub_color}; background: transparent; border: none;")

        for label, val in self._actions:
            if val == self._current_action:
                self.lbl_title.setText(label)
                break
        else:
            self.lbl_title.setText(c.t("UI_LAUNCH_ACTION_NONE"))

    def setCurrentAction(self, action_key):
        self._current_action = action_key
        self._update_display_text()

    def currentAction(self):
        return self._current_action

    def currentData(self):
        return self._current_action

    def setCurrentIndex(self, idx):
        if 0 <= idx < len(self._actions):
            self.setCurrentAction(self._actions[idx][1])

    def findData(self, action_key):
        for idx, (_, val) in enumerate(self._actions):
            if val == action_key:
                return idx
        return -1

    def retranslate_ui(self):
        self._actions = [
            (c.t("UI_LAUNCH_ACTION_NONE"), c.LAUNCH_ACTION_NONE),
            (c.t("UI_LAUNCH_ACTION_CLOSE"), c.LAUNCH_ACTION_CLOSE),
            (c.t("UI_LAUNCH_ACTION_HIDE"), c.LAUNCH_ACTION_HIDE),
        ]
        sub_text = (c.t("UI_LAUNCH_ACTION_LABEL") if hasattr(c, "t") else "When launching the game:").rstrip(":")
        self.lbl_sub.setText(sub_text)
        self._update_display_text()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._open_popup()
        super().mousePressEvent(event)

    def _open_popup(self):
        options = [label for label, _ in self._actions]
        curr_label = self.lbl_title.text()
        from src.gui.install_dialog import SleekDropdownPopup
        popup = SleekDropdownPopup(options, current_text=curr_label, app=self.app, parent=self)
        popup.setMinimumWidth(self.width())

        def _on_select(selected_label):
            for label, val in self._actions:
                if label == selected_label:
                    self._current_action = val
                    self._update_display_text()
                    self.actionChanged.emit(val)
                    if self.app:
                        self.app.sync_launch_action_ui(val)
                    break

        popup.optionSelected.connect(_on_select)
        p = self.mapToGlobal(QPoint(0, 0))
        popup.adjustSize()
        target_y = p.y() - popup.sizeHint().height() - 6
        if target_y < 40:
            target_y = p.y() + self.height() + 4
        popup.move(p.x(), target_y + 10)
        popup._anim.stop()
        popup._anim.setStartValue(QPoint(p.x(), target_y + 10))
        popup._anim.setEndValue(QPoint(p.x(), target_y))
        popup.show()
        popup._anim.start()


class Tactile3DPlayButton(QPushButton):
    """
    Tactile 3D push-down arcade button with rotating theme-adaptive conical glowing aura,
    subtle hover expansion, smooth hover slowdown, and mechanical 3D click response.
    """
    def __init__(self, text="", app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self._text = text or (c.t("UI_PLAY_BUTTON").upper() if hasattr(c, "t") else "PLAY")
        self._is_running = False
        self._press_offset = 0.0
        self._button_scale = 1.0
        self._is_hovered = False
        self._is_pressed = False
        self._glow_angle = 0.0
        self.setObjectName("PlayButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(68)
        self.setMinimumWidth(180)
        self.setMaximumWidth(750)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setStyleSheet("background: transparent; border: none;")

        self._anim_offset = QPropertyAnimation(self, b"pressOffset", self)
        self._anim_offset.setEasingCurve(QEasingCurve.OutQuad)

        self._anim_scale = QPropertyAnimation(self, b"buttonScale", self)
        self._anim_scale.setEasingCurve(QEasingCurve.OutCubic)

        # Rotating glowing aura timer
        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._on_glow_tick)
        self._glow_timer.start(25)

    def sizeHint(self):
        return QSize(680, 68)

    def minimumSizeHint(self):
        return QSize(180, 68)

    def set_running_state(self, is_running: bool):
        if self._is_running != is_running:
            self._is_running = is_running
            self.update()

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

    def _on_glow_tick(self):
        # Circulates continuously around the perimeter; slows down on hover
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
        self._is_hovered = True
        self._animate_scale(1.018, 140)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self._is_pressed = False
        self._animate_scale(1.0, 140)
        if self._press_offset > 0:
            self._animate_offset(0.0, 80)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_pressed = True
            # Keeps normal 1.0 scale on press and triggers mechanical 3D push-down
            self._animate_scale(1.0, 45)
            self._animate_offset(6.0, 40)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._is_pressed = False
        target_scale = 1.018 if self._is_hovered else 1.0
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

    def setText(self, text: str):
        self._text = text
        super().setText(text)
        self.update()

    def set_accent_color(self, color_hex):
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = float(self.width())
        h = float(self.height())
        cx, cy = w / 2.0, h / 2.0

        # Scale transform centered on the button
        painter.save()
        painter.translate(cx, cy)
        painter.scale(self._button_scale, self._button_scale)
        painter.translate(-cx, -cy)

        # Active theme accent color or running crimson red
        if self._is_running:
            accent = "#e53935"
        else:
            accent = "#1f6aa5"
            if self.app and hasattr(self.app, "current_accent_color"):
                accent = self.app.current_accent_color
            elif hasattr(self.window(), "current_accent_color"):
                accent = self.window().current_accent_color

        c_accent = QColor(accent)
        base_h, base_s, base_v, _ = c_accent.getHsv()

        # 0. Rotating Conical Gradient orbiting around the button perimeter
        grad = QConicalGradient(cx, cy, self._glow_angle)
        if self._is_running:
            theme_glow_stops = [
                (0.00, QColor("#ff1744")),
                (0.20, QColor("#d50000")),
                (0.40, QColor("#ff5252")),
                (0.60, QColor("#ff1744")),
                (0.80, QColor("#b71c1c")),
                (1.00, QColor("#ff1744")),
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

        # Silky-smooth 14-step subpixel quadratic diffusion blur (Zero banding)
        base_body_rect = QRectF(14.0, 8.0, w - 28.0, h - 18.0)
        n_steps = 14
        max_expand = 7.0
        for i in range(n_steps):
            t = float(i) / (n_steps - 1)
            expand = 0.5 + t * (max_expand - 0.5)
            alpha = int(170.0 * math.pow(1.0 - t, 1.8))
            if alpha <= 0: continue
            glow_pen = QPen(grad, 1.8)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.NoBrush)
            painter.setOpacity(alpha / 255.0)
            glow_rect = base_body_rect.adjusted(-expand, -expand, expand, expand)
            rad = 8.0 + expand * 0.8
            painter.drawRoundedRect(glow_rect, rad, rad)

        painter.setOpacity(1.0)

        is_disabled = not self.isEnabled()
        if is_disabled:
            top_color_hex = "#4a4a50"
            top_highlight_hex = "#606068"
            bevel_color_hex = "#2e2e34"
            socket_color_hex = "#1a1a1e"
        elif self._is_running:
            top_color_hex = "#f44336" if self._is_hovered and not self._is_pressed else "#e53935"
            top_highlight_hex = "#ff8a80"
            bevel_color_hex = "#b71c1c"
            socket_color_hex = "#2b0606"
        else:
            top_color_hex = adjust_color(accent, 24 if self._is_hovered and not self._is_pressed else 12)
            top_highlight_hex = adjust_color(accent, 60)
            bevel_color_hex = adjust_color(accent, -45)
            socket_color_hex = blend_colors("#0a0a0a", accent, 0.22)

        offset = float(self._press_offset) if not is_disabled else 0.0

        # 1. Base socket / chassis underneath (.button:after)
        socket_radius = 8.0
        socket_rect = QRectF(14.0, 10.0, w - 28.0, h - 20.0)
        painter.setBrush(QColor(socket_color_hex))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(socket_rect, socket_radius, socket_radius)

        # 2. 3D Bevel Body (box-shadow: 0 10px 0 #915100)
        btn_radius = 6.0
        bevel_rect = QRectF(16.0, 7.0 + offset, w - 32.0, h - 21.0 - offset)
        painter.setBrush(QColor(bevel_color_hex))
        painter.drawRoundedRect(bevel_rect, btn_radius, btn_radius)

        # 3. Top Face (.button a)
        top_h = h - 27.0
        top_rect = QRectF(16.0, 7.0 + offset, w - 32.0, top_h)
        painter.setBrush(QColor(top_color_hex))
        painter.drawRoundedRect(top_rect, btn_radius, btn_radius)

        # Inset highlight line at top edge (box-shadow: inset 0 1px 0 #FFE5C4)
        highlight_pen = QPen(QColor(top_highlight_hex), 1.2)
        painter.setPen(highlight_pen)
        painter.drawLine(
            int(top_rect.left() + 6),
            int(top_rect.top() + 1),
            int(top_rect.right() - 6),
            int(top_rect.top() + 1)
        )

        # 4. Text (PLAY or Close Game with text-shadow: 0px 1px 0px #000)
        if w >= 500:
            font_size = 17 if self._is_running else 19
            spacing = 2.4 if self._is_running else 3.0
        elif w < 260:
            font_size = 12 if self._is_running else 13
            spacing = 1.0
        else:
            font_size = 14 if self._is_running else 16
            spacing = 1.8 if self._is_running else 2.2
        font = QFont("Helvetica", font_size, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
        painter.setFont(font)

        close_text = (c.t("UI_BUTTON_CLOSE_GAME") if c.t("UI_BUTTON_CLOSE_GAME") else "Cerrar Juego").upper()
        display_text = close_text if self._is_running else self._text

        # Text Shadow (1.2px down)
        shadow_rect = QRectF(top_rect.x(), top_rect.y() + 1.2, top_rect.width(), top_rect.height())
        painter.setPen(QColor(0, 0, 0, 190))
        painter.drawText(shadow_rect, Qt.AlignCenter, display_text)

        # Text Main (Crisp White or disabled muted)
        painter.setPen(QColor("#ffffff") if not is_disabled else QColor("#9e9e9e"))
        painter.drawText(top_rect, Qt.AlignCenter, display_text)

        painter.restore()
        painter.end()


class VersionContainerCard(QFrame):
    """
    Center card container for installed versions, featuring a subtle faded
    adventure characters watermark in the bottom-right corner.
    """
    def __init__(self, parent=None, show_watermark=True):
        super().__init__(parent)
        self.setObjectName("VersionContainerCard")
        self.show_watermark = show_watermark
        self.watermark = None

        if self.show_watermark:
            self.watermark = QLabel(self)
            self.watermark.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.watermark.setStyleSheet("background: transparent; border: none;")
            self._init_watermark()

    def _init_watermark(self):
        char_path = resource_path("adventure_characters.png")
        if not os.path.exists(char_path):
            char_path = resource_path("assets/media/adventure_characters.png")

        if not os.path.exists(char_path):
            return

        orig = QPixmap(char_path)
        if orig.isNull():
            return

        # Compact size (~210px width) and soft faded opacity
        target_w = 210
        scaled = orig.scaledToWidth(target_w, Qt.SmoothTransformation)
        faded = QPixmap(scaled.size())
        faded.fill(Qt.transparent)

        p = QPainter(faded)
        p.setOpacity(0.38)
        p.drawPixmap(0, 0, scaled)
        p.end()

        self.watermark.setPixmap(faded)
        self.watermark.setFixedSize(faded.size())

    def update_watermark_position(self):
        if self.watermark and self.watermark.pixmap() and not self.watermark.pixmap().isNull():
            if self.height() < 220 or self.width() < 240:
                self.watermark.hide()
                return
            self.watermark.show()
            margin_right = 22
            margin_bottom = 16
            x = max(0, self.width() - self.watermark.width() - margin_right)
            y = max(0, self.height() - self.watermark.height() - margin_bottom)
            self.watermark.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_watermark_position()

    def showEvent(self, event):
        super().showEvent(event)
        self.update_watermark_position()


class PlayTab(QWidget):
    """Main play tab with version list, launch options, and the play button."""
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # Layout principal horizontal (Panel Izquierdo fijo + Stack de Contenido flexible)
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 12, c.SECTION_PADDING, 16)
        self.main_layout.setSpacing(12)

        self.lbl_status = QLabel("") # Kept for backend compatibility
        self.lbl_profile_indicator = QLabel("") # Kept for backend compatibility

        # Main 3-Column Content Area (Left Wireframe, Center Versions, Right Wireframe)
        self.columns_layout = QHBoxLayout()
        self.columns_layout.setContentsMargins(0, 0, 0, 0)
        self.columns_layout.setSpacing(12)

        # 2a. Left Panel (Perfil / Sidebar Nav / Dual Status Card)
        self.panel_left = PlaySidebarCard(self, app=self.app)
        self.panel_left_layout = QVBoxLayout(self.panel_left)
        self.panel_left_layout.setContentsMargins(10, 14, 10, 16)
        self.panel_left_layout.setSpacing(8)
        self.panel_left_layout.setAlignment(Qt.AlignTop)

        # Dual Compact Capsule Card: Game Mode (top) | Divider | Status (bottom)
        self.card_dual_status = QFrame()
        self.card_dual_status.setObjectName("DualStatusCard")
        self.card_dual_status.setFixedWidth(260)
        self.card_dual_layout = QVBoxLayout(self.card_dual_status)
        self.card_dual_layout.setContentsMargins(14, 10, 14, 10)
        self.card_dual_layout.setSpacing(6)

        # 1. Top Row: Game Mode
        row_mode = QHBoxLayout()
        row_mode.setContentsMargins(0, 0, 0, 0)
        row_mode.setSpacing(10)

        self.dot_mode = QLabel()
        self.dot_mode.setFixedSize(10, 10)
        self.dot_mode.setStyleSheet("background-color: #2ed573; border-radius: 5px; border: none;")
        row_mode.addWidget(self.dot_mode, 0, Qt.AlignVCenter)

        col_mode_text = QVBoxLayout()
        col_mode_text.setContentsMargins(0, 0, 0, 0)
        col_mode_text.setSpacing(1)

        self.lbl_install = QLabel(c.t("UI_LABEL_GAME_MODE"))
        self.lbl_install.setStyleSheet("font-size: 10px; color: #8c8c8c; background: transparent; border: none;")
        col_mode_text.addWidget(self.lbl_install)

        mode_key = self.app.config.get(c.CONFIG_KEY_INSTALL_MODE, c.MODE_INSTALL_LOCAL)
        mode_name = c.t("UI_INSTALL_MODES").get(mode_key, mode_key)
        self.lbl_mode_value = QLabel(mode_name)
        self.lbl_mode_value.setObjectName("ModeValueLabel")
        col_mode_text.addWidget(self.lbl_mode_value)

        # Dummy hidden combo for backend compatibility
        self.combo_mode = QComboBox()
        self.combo_mode.hide()

        row_mode.addLayout(col_mode_text, 1)
        self.card_dual_layout.addLayout(row_mode)

        # Central divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Plain)
        divider.setObjectName("DualCardDivider")
        divider.setFixedHeight(1)
        self.card_dual_layout.addWidget(divider)

        # 2. Bottom Row: Game Status
        row_status = QHBoxLayout()
        row_status.setContentsMargins(0, 0, 0, 0)
        row_status.setSpacing(10)

        self.dot_game_status = QLabel()
        self.dot_game_status.setFixedSize(10, 10)
        self.dot_game_status.setStyleSheet("background-color: #777777; border-radius: 5px; border: none;")
        row_status.addWidget(self.dot_game_status, 0, Qt.AlignVCenter)

        col_status_text = QVBoxLayout()
        col_status_text.setContentsMargins(0, 0, 0, 0)
        col_status_text.setSpacing(1)

        self.lbl_status_caption = QLabel(c.t("UI_LABEL_STATUS"))
        self.lbl_status_caption.setStyleSheet("font-size: 10px; color: #8c8c8c; background: transparent; border: none;")
        col_status_text.addWidget(self.lbl_status_caption)

        self.lbl_game_status = QLabel(c.t("UI_GAME_STATUS_IDLE"))
        self.lbl_game_status.setStyleSheet("font-size: 12px; font-weight: bold; color: #dedede; background: transparent; border: none;")
        col_status_text.addWidget(self.lbl_game_status)

        row_status.addLayout(col_status_text, 1)
        self.card_dual_layout.addLayout(row_status)

        self.panel_left_layout.addWidget(self.card_dual_status, 0, Qt.AlignHCenter)

        # 2. Vertical navigation group with sliding indicator ("elevator")
        self.sidebar_nav_group = SidebarNavGroup(app=self.app)
        self.btn_nav_home = SidebarNavButton(c.t("UI_SIDEBAR_HOME"), "home_pixel.svg", app=self.app)
        self.btn_nav_install = SidebarNavButton(c.t("UI_SIDEBAR_INSTALL"), "install_pixel.svg", app=self.app)
        self.btn_nav_worlds = SidebarNavButton(c.t("UI_SIDEBAR_WORLDS"), "world_pixel.svg", app=self.app)
        self.btn_nav_packs = SidebarNavButton(c.t("UI_SIDEBAR_PACKS"), "pack_pixel.svg", app=self.app)
        self.btn_nav_mods = SidebarNavButton(c.t("UI_SIDEBAR_MODS"), "mod_pixel.svg", app=self.app)
        self.btn_nav_screenshots = SidebarNavButton(c.t("UI_SIDEBAR_SCREENSHOTS"), "camera_pixel.svg", app=self.app)
        self.sidebar_nav_group.addButton(self.btn_nav_home, self.show_home_view)
        self.sidebar_nav_group.addButton(self.btn_nav_install, self.show_install_view)
        self.sidebar_nav_group.addButton(self.btn_nav_worlds, self.show_worlds_view)
        self.sidebar_nav_group.addButton(self.btn_nav_packs, self.show_packs_view)
        self.sidebar_nav_group.addButton(self.btn_nav_mods, self.show_mods_view)
        self.sidebar_nav_group.addButton(self.btn_nav_screenshots, self.show_screenshots_view)
        self.panel_left_layout.addWidget(self.sidebar_nav_group, 0, Qt.AlignHCenter)

        # Spacer to push the navigation/status up and reveal the wallpaper scenery
        self.panel_left_layout.addStretch(1)

        # 4. Social & Community Quick Links (Discord, Web, GitHub)
        row_social = QHBoxLayout()
        row_social.setContentsMargins(0, 0, 0, 0)
        row_social.setSpacing(10)
        row_social.setAlignment(Qt.AlignCenter)

        self.btn_discord = SidebarSocialButton(
            "discord_icon.svg",
            "https://discord.gg/las-tortuguitas-de-ezku-1214414622111567892",
            tooltip=c.t("UI_TOOLTIP_DISCORD"),
            app=self.app,
            parent=self.panel_left
        )
        self.btn_web = SidebarSocialButton(
            "globe_icon.svg",
            "https://cianovalauncher.org/",
            tooltip=c.t("UI_TOOLTIP_WEB"),
            app=self.app,
            parent=self.panel_left
        )
        self.btn_github = SidebarSocialButton(
            "github_icon.svg",
            "https://github.com/CianovaTeam/CianovaLauncher-mcpelauncher",
            tooltip=c.t("UI_TOOLTIP_GITHUB"),
            app=self.app,
            parent=self.panel_left
        )

        row_social.addWidget(self.btn_discord)
        row_social.addWidget(self.btn_web)
        row_social.addWidget(self.btn_github)

        self.panel_left_layout.addLayout(row_social)

        # ── Stacked Views for Main Content Area (Home vs Installation) ──
        self.content_stack = VerticalAnimatedStackedWidget(self)

        # ─────────────────────────────────────────────────────────────
        # VIEW 0: HOME (Versions + Right Panel + Play Controls)
        # ─────────────────────────────────────────────────────────────
        self.view_home = QWidget()
        self.view_home_layout = QVBoxLayout(self.view_home)
        self.view_home_layout.setContentsMargins(0, 0, 0, 0)
        self.view_home_layout.setSpacing(12)

        # 2b. Center Column (Versions Card occupying center stage harmoniously)
        self.panel_center = VersionContainerCard(show_watermark=True)
        self.panel_center_layout = QVBoxLayout(self.panel_center)
        self.panel_center_layout.setContentsMargins(14, 14, 14, 14)
        # Clean centered title within card with edit mode button
        self._is_edit_mode = False
        version_title_container = QHBoxLayout()
        version_title_container.setContentsMargins(4, 0, 4, 0)
        version_title_container.addStretch()
        self.lbl_version_title = QLabel(c.t("UI_LABEL_INSTALLED_VERSIONS"))
        self.lbl_version_title.setAlignment(Qt.AlignCenter)
        self.lbl_version_title.setStyleSheet("font-size: 15px; font-weight: bold; background: transparent; border: none;")
        version_title_container.addWidget(self.lbl_version_title)
        version_title_container.addStretch()

        # Button to toggle News and Quick Access on compact screens
        self.btn_toggle_right_panel = QPushButton()
        self.btn_toggle_right_panel.setCheckable(True)
        self.btn_toggle_right_panel.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_right_panel.setFixedHeight(30)
        self.btn_toggle_right_panel.setToolTip(c.t("UI_TOOLTIP_TOGGLE_RIGHT"))
        self.btn_toggle_right_panel.clicked.connect(self._on_toggle_right_panel_clicked)
        self.btn_toggle_right_panel.hide()
        version_title_container.addWidget(self.btn_toggle_right_panel)

        self.btn_edit_mode = QPushButton()
        self.btn_edit_mode.setFixedSize(30, 30)
        self.btn_edit_mode.setCursor(Qt.PointingHandCursor)
        self.btn_edit_mode.setToolTip(c.t("UI_TOOLTIP_EDIT_MODE"))
        pencil_icon = ImageManager.get_icon("edit_pencil_icon.svg")
        if not pencil_icon.isNull():
            self.btn_edit_mode.setIcon(pencil_icon)
            self.btn_edit_mode.setIconSize(QSize(16, 16))
        self.btn_edit_mode.clicked.connect(self.toggle_edit_mode)
        version_title_container.addWidget(self.btn_edit_mode)

        self.panel_center_layout.addLayout(version_title_container)

        # Action bar in Edit Mode (hidden by default)
        self.edit_mode_bar = QFrame()
        self.edit_mode_bar.setObjectName("EditModeBar")
        self.edit_mode_bar.setFixedHeight(42)
        bar_layout = QHBoxLayout(self.edit_mode_bar)
        bar_layout.setContentsMargins(10, 4, 10, 4)
        bar_layout.setSpacing(8)

        self.btn_select_all = QPushButton(c.t("UI_EDIT_MODE_SELECT_ALL"))
        self.btn_select_all.setFixedHeight(28)
        self.btn_select_all.setCursor(Qt.PointingHandCursor)
        self.btn_select_all.clicked.connect(self.toggle_select_all_versions)
        bar_layout.addWidget(self.btn_select_all)

        bar_layout.addStretch(1)

        self.btn_delete_selected = QPushButton(c.t("UI_EDIT_MODE_DELETE_SELECTED"))
        self.btn_delete_selected.setFixedHeight(28)
        self.btn_delete_selected.setCursor(Qt.PointingHandCursor)
        trash_icon = ImageManager.get_icon("trash_delete_icon.svg")
        if not trash_icon.isNull():
            self.btn_delete_selected.setIcon(trash_icon)
            self.btn_delete_selected.setIconSize(QSize(14, 14))
        self.btn_delete_selected.clicked.connect(self.delete_selected_versions)
        bar_layout.addWidget(self.btn_delete_selected)

        self.btn_done_edit = QPushButton(c.t("UI_EDIT_MODE_DONE"))
        self.btn_done_edit.setFixedHeight(28)
        self.btn_done_edit.setCursor(Qt.PointingHandCursor)
        check_icon = ImageManager.get_icon("check_mark_icon.svg")
        if not check_icon.isNull():
            self.btn_done_edit.setIcon(check_icon)
            self.btn_done_edit.setIconSize(QSize(14, 14))
        self.btn_done_edit.clicked.connect(self.toggle_edit_mode)
        bar_layout.addWidget(self.btn_done_edit)

        self.edit_mode_bar.hide()
        self.panel_center_layout.addWidget(self.edit_mode_bar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll_area.viewport().setStyleSheet("background: transparent;")
        self.scroll_area.viewport().setAutoFillBackground(False)

        self.version_list_widget = QWidget()
        self.version_list_widget.setObjectName("VersionList")
        self.version_list_widget.setStyleSheet("background: transparent;")
        self.version_list_layout = QVBoxLayout(self.version_list_widget)
        self.version_list_layout.setContentsMargins(0, 4, 0, 4)
        self.version_list_layout.setSpacing(10)
        self.version_list_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.version_list_widget)
        self.panel_center_layout.addWidget(self.scroll_area, 1)

        if self.panel_center.watermark:
            self.panel_center.watermark.stackUnder(self.scroll_area)

        # 2c. Adaptive right panel with smooth vertical scroll (avoids crushing on smaller heights)
        self.panel_right = QWidget()
        self.panel_right.setObjectName("RightPanelContainer")
        self.panel_right.setMinimumWidth(310)
        self.panel_right.setMaximumWidth(380)
        self.panel_right.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        pr_outer_layout = QVBoxLayout(self.panel_right)
        pr_outer_layout.setContentsMargins(0, 0, 0, 0)
        pr_outer_layout.setSpacing(0)

        self.scroll_right = QScrollArea(self.panel_right)
        self.scroll_right.setWidgetResizable(True)
        self.scroll_right.setFrameShape(QFrame.NoFrame)
        self.scroll_right.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_right.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_right.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll_right.viewport().setStyleSheet("background: transparent;")

        self.panel_right_content = QWidget()
        self.panel_right_content.setStyleSheet("background: transparent;")
        self.panel_right_layout = QVBoxLayout(self.panel_right_content)
        self.panel_right_layout.setContentsMargins(0, 0, 6, 0)
        self.panel_right_layout.setSpacing(10)
        self.scroll_right.setWidget(self.panel_right_content)
        pr_outer_layout.addWidget(self.scroll_right)

        # Top right card: News Carousel (vertically adaptive content)
        self.card_right_top = NewsCarouselCard(self, app=self.app)
        self.card_right_top_layout = self.card_right_top._layout
        self.panel_right_layout.addWidget(self.card_right_top, 4)

        # Bottom right card: Preferences and Quick Shortcuts
        self.card_right_bottom = QFrame()
        self.card_right_bottom.setObjectName("RightBottomCard")
        self.card_right_bottom.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.card_right_bottom_layout = QVBoxLayout(self.card_right_bottom)
        self.card_right_bottom_layout.setContentsMargins(14, 14, 14, 14)
        self.card_right_bottom_layout.setSpacing(10)

        # Header
        quick_header_text = c.t("UI_QUICK_PREFS_HEADER") if hasattr(c, "t") else "PREFERENCES & SHORTCUTS"
        self.lbl_quick_header = QLabel(quick_header_text)
        self.lbl_quick_header.setObjectName("QuickPanelHeader")
        self.card_right_bottom_layout.addWidget(self.lbl_quick_header, 0)

        # Helper to create monochromatic SVG icon badge
        def _make_icon_badge():
            b = QFrame()
            b.setObjectName("QuickSubCardIcon")
            b.setFixedSize(36, 36)
            bl = QVBoxLayout(b)
            bl.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("background: transparent; border: none;")
            bl.addWidget(lbl)
            return b, lbl

        def _make_text_block(title_text, subtitle_text):
            box = QWidget()
            box.setStyleSheet("background: transparent; border: none;")
            bl = QVBoxLayout(box)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(2)
            t = QLabel(title_text)
            t.setObjectName("QuickRowTitle")
            t.setStyleSheet("font-size: 13.5px; font-weight: 700; background: transparent; border: none;")
            t.setWordWrap(True)
            s = QLabel(subtitle_text)
            s.setObjectName("QuickRowSubtitle")
            s.setStyleSheet("font-size: 11px; font-weight: 400; background: transparent; border: none;")
            s.setWordWrap(True)
            bl.addWidget(t)
            bl.addWidget(s)
            return box, t, s

        # 1. GameMode Sub-card
        self.card_sub_gamemode = QuickSubCard(on_click=lambda: self.check_gamemode.nextCheckState())
        self.card_sub_gamemode.setMinimumHeight(48)
        self.card_sub_gamemode.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        l_gm = QHBoxLayout(self.card_sub_gamemode)
        l_gm.setContentsMargins(14, 8, 14, 8)
        l_gm.setSpacing(12)
        badge_gm, self.lbl_icon_gamemode = _make_icon_badge()
        l_gm.addWidget(badge_gm, 0, Qt.AlignVCenter)
        box_gm, self.lbl_gamemode_title, self.lbl_gamemode_sub = _make_text_block(
            c.t("UI_CHECKBOX_GAMEMODE") if c.t("UI_CHECKBOX_GAMEMODE") else "Activar GameMode",
            c.t("UI_QUICK_GAMEMODE_SUB")
        )
        l_gm.addWidget(box_gm, 1, Qt.AlignVCenter)
        self.check_gamemode = QuickToggleSwitch(app=self.app)
        self.check_gamemode.setChecked(self.app.config.get(c.CONFIG_KEY_GAMEMODE_ENABLED, False))
        self.check_gamemode.stateChanged.connect(
            lambda state: QTimer.singleShot(0, lambda: self.app.sync_gamemode_ui(state == Qt.Checked.value))
        )
        l_gm.addWidget(self.check_gamemode, 0, Qt.AlignVCenter)
        self.card_right_bottom_layout.addWidget(self.card_sub_gamemode, 1)

        # 2. Discord Rich Presence Sub-card
        self.card_sub_discord = QuickSubCard(on_click=lambda: self.check_discord.nextCheckState())
        self.card_sub_discord.setMinimumHeight(48)
        self.card_sub_discord.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        l_dc = QHBoxLayout(self.card_sub_discord)
        l_dc.setContentsMargins(14, 8, 14, 8)
        l_dc.setSpacing(12)
        badge_dc, self.lbl_icon_discord = _make_icon_badge()
        l_dc.addWidget(badge_dc, 0, Qt.AlignVCenter)
        box_dc, self.lbl_discord_title, self.lbl_discord_sub = _make_text_block(
            c.t("UI_CHECKBOX_DISCORD_RPC") if c.t("UI_CHECKBOX_DISCORD_RPC") else "Mostrar en Discord",
            c.t("UI_QUICK_DISCORD_SUB")
        )
        l_dc.addWidget(box_dc, 1, Qt.AlignVCenter)
        self.check_discord = QuickToggleSwitch(app=self.app)
        self.check_discord.setChecked(self.app.config.get(c.CONFIG_KEY_DISCORD_RPC_ENABLED, False))
        self.check_discord.stateChanged.connect(
            lambda state: QTimer.singleShot(0, lambda: (self.app.sync_discord_rpc_ui(state == Qt.Checked.value), self.save_quick_opts()))
        )
        l_dc.addWidget(self.check_discord, 0, Qt.AlignVCenter)
        self.card_right_bottom_layout.addWidget(self.card_sub_discord, 1)

        # 3. Game Folder Sub-card
        self.card_sub_folder = QuickSubCard(on_click=self._open_game_folder)
        self.card_sub_folder.setMinimumHeight(48)
        self.card_sub_folder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        l_fo = QHBoxLayout(self.card_sub_folder)
        l_fo.setContentsMargins(14, 8, 14, 8)
        l_fo.setSpacing(12)
        badge_fo, self.lbl_icon_folder = _make_icon_badge()
        l_fo.addWidget(badge_fo, 0, Qt.AlignVCenter)
        box_fo, self.lbl_folder_title, self.lbl_folder_sub = _make_text_block(
            c.t("UI_QUICK_FOLDER_TITLE"),
            c.t("UI_QUICK_FOLDER_SUB")
        )
        l_fo.addWidget(box_fo, 1, Qt.AlignVCenter)
        self.btn_open_game_folder = QPushButton(c.t("UI_QUICK_BTN_OPEN"))
        self.btn_open_game_folder.setObjectName("QuickActionBtn")
        self.btn_open_game_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_game_folder.setFixedHeight(30)
        self.btn_open_game_folder.clicked.connect(self._open_game_folder)
        l_fo.addWidget(self.btn_open_game_folder, 0, Qt.AlignVCenter)
        self.card_right_bottom_layout.addWidget(self.card_sub_folder, 1)

        # 4. Clear Cache Sub-card
        self.card_sub_cache = QuickSubCard(on_click=self._clean_game_cache)
        self.card_sub_cache.setMinimumHeight(48)
        self.card_sub_cache.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        l_ca = QHBoxLayout(self.card_sub_cache)
        l_ca.setContentsMargins(14, 8, 14, 8)
        l_ca.setSpacing(12)
        badge_ca, self.lbl_icon_cache = _make_icon_badge()
        l_ca.addWidget(badge_ca, 0, Qt.AlignVCenter)
        box_ca, self.lbl_cache_title, self.lbl_cache_sub = _make_text_block(
            c.t("UI_QUICK_CACHE_TITLE"),
            c.t("UI_QUICK_CACHE_SUB")
        )
        l_ca.addWidget(box_ca, 1, Qt.AlignVCenter)
        self.btn_clean_cache = QPushButton(c.t("UI_QUICK_BTN_CLEAN"))
        self.btn_clean_cache.setObjectName("QuickActionBtn")
        self.btn_clean_cache.setCursor(Qt.PointingHandCursor)
        self.btn_clean_cache.setFixedHeight(30)
        self.btn_clean_cache.clicked.connect(self._clean_game_cache)
        l_ca.addWidget(self.btn_clean_cache, 0, Qt.AlignVCenter)
        self.card_right_bottom_layout.addWidget(self.card_sub_cache, 1)

        self.panel_right_layout.addWidget(self.card_right_bottom, 5)

        # Add to columns layout: Center (flexible stretch), Right (flexible width)
        self.columns_layout.addWidget(self.panel_center, 1)
        self.columns_layout.addWidget(self.panel_right, 0)

        self.view_home_layout.addLayout(self.columns_layout, 1)

        # Launch Controls Bottom Card (Clean and responsive horizontal layout)
        self.card_launch = QFrame()
        self.card_launch.setObjectName("LaunchControlCard")
        self.card_launch_layout = QHBoxLayout(self.card_launch)
        self.card_launch_layout.setContentsMargins(16, 10, 16, 10)
        self.card_launch_layout.setSpacing(14)
        self.card_launch_layout.setAlignment(Qt.AlignVCenter)

        # 3a. Launch action dropdown card
        self.box_launch_action = SleekLaunchActionCard(app=self.app)
        self.combo_launch_action = self.box_launch_action
        self.card_launch_layout.addWidget(self.box_launch_action, 0, Qt.AlignVCenter | Qt.AlignLeft)

        # Flexible spacing stretching to keep launch action left and play button anchored right
        self.card_launch_layout.addStretch(1)

        # 3b. Tactile 3D Play Button (prominent expanding width anchored right)
        play_label = (c.t("UI_PLAY_BUTTON") if c.t("UI_PLAY_BUTTON") else "JUGAR").upper()
        self.btn_launch = Tactile3DPlayButton(text=play_label, app=self.app)
        self.btn_launch.clicked.connect(self._on_launch_btn_clicked)
        self.card_launch_layout.addWidget(self.btn_launch, 0, Qt.AlignVCenter | Qt.AlignRight)

        self.view_home_layout.addWidget(self.card_launch, 0)
        self.content_stack.addWidget(self.view_home)

        # ─────────────────────────────────────────────────────────────
        # VIEW 1: INSTALLATION (Integral APK / Google Play Version Installer)
        # ─────────────────────────────────────────────────────────────
        self.view_install = QWidget()
        self.view_install_layout = QVBoxLayout(self.view_install)
        self.view_install_layout.setContentsMargins(0, 0, 0, 0)
        self.view_install_layout.setSpacing(12)

        self.card_install_container = QFrame()
        self.card_install_container.setObjectName("VersionContainerCard")
        self.card_install_container_layout = QVBoxLayout(self.card_install_container)
        self.card_install_container_layout.setContentsMargins(16, 12, 16, 12)
        self.card_install_container_layout.setSpacing(8)

        # 1. Header con branding (Logo Minecraft SVG + Título + Subtítulo)
        install_header = QHBoxLayout()
        install_header.setContentsMargins(6, 4, 6, 6)
        install_header.setSpacing(14)

        # Logo Minecraft Grass Block SVG
        self.lbl_install_logo = QLabel()
        logo_pix = ImageManager.get_image("minecraft_logo.svg", (46, 46)) or ImageManager.get_image("minecraft_logo.png", (46, 46))
        if logo_pix and not logo_pix.isNull():
            self.lbl_install_logo.setPixmap(logo_pix)
        self.lbl_install_logo.setFixedSize(46, 46)
        self.lbl_install_logo.setStyleSheet("background: transparent; border: none;")
        install_header.addWidget(self.lbl_install_logo, 0, Qt.AlignVCenter)

        # Text Column (Title + Subtitle)
        header_text_col = QVBoxLayout()
        header_text_col.setContentsMargins(0, 0, 0, 0)
        header_text_col.setSpacing(4)

        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        self.lbl_install_view_title = QLabel(c.t("UI_INSTALL_VIEW_TITLE"))
        self.lbl_install_view_title.setWordWrap(True)
        self.lbl_install_view_title.setStyleSheet(
            f"font-size: 16px; font-weight: 900; letter-spacing: 0.6px; color: {'#ffffff' if is_dark else '#1a1a1a'}; background: transparent; border: none;"
        )
        header_text_col.addWidget(self.lbl_install_view_title)

        self.lbl_install_view_sub = QLabel(c.t("UI_INSTALL_VIEW_SUBTITLE"))
        self.lbl_install_view_sub.setWordWrap(True)
        self.lbl_install_view_sub.setStyleSheet(
            f"font-size: 13px; color: {'#9aa0a6' if is_dark else '#666666'}; background: transparent; border: none;"
        )
        header_text_col.addWidget(self.lbl_install_view_sub)

        install_header.addLayout(header_text_col, 1)
        install_header.addStretch()
        self.card_install_container_layout.addLayout(install_header)

        # Reusable Installation Widget with smooth scroll area
        self.scroll_install = QScrollArea()
        self.scroll_install.setWidgetResizable(True)
        self.scroll_install.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_install.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_install.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll_install.viewport().setStyleSheet("background: transparent;")
        self.installer_widget = InstallViewWidget(self.app, parent=self.scroll_install, is_embedded=True)
        self.scroll_install.setWidget(self.installer_widget)
        self.card_install_container_layout.addWidget(self.scroll_install, 1)

        self.view_install_layout.addWidget(self.card_install_container, 1)
        self.content_stack.addWidget(self.view_install)

        # View 2: Worlds Management View
        self.view_worlds = WorldsTab(app=self.app)
        self.content_stack.addWidget(self.view_worlds)

        # View 3: Resource & Behavior Packs View
        self.view_packs = PacksTab(app=self.app)
        self.content_stack.addWidget(self.view_packs)

        # View 4: MCPELauncher Native Mods View
        self.view_mods = ModsTab(app=self.app)
        self.content_stack.addWidget(self.view_mods)

        # View 5: Screenshots Gallery & Manager View
        self.view_screenshots = ScreenshotsTab(app=self.app)
        self.content_stack.addWidget(self.view_screenshots)

        # Add to main layout: Left Panel (fixed) + Content Stack (flexible)
        self.main_layout.addWidget(self.panel_left, 0)
        self.main_layout.addWidget(self.content_stack, 1)

        # Mock version_var for compatibility
        self._selected_version = ""
        self.update_theme_styles()

    def update_theme_styles(self):
        """Update captions, headers and custom widgets when theme changes between Light and Dark."""
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"

        # 1. Mini Status Card captions & values (black/dark in light mode, lighter in dark mode)
        if hasattr(self, "lbl_install"):
            self.lbl_install.setStyleSheet(
                f"font-size: 10px; font-weight: {'normal' if is_dark else 'bold'}; color: {'#8c8c8c' if is_dark else '#18191c'}; background: transparent; border: none;"
            )
        if hasattr(self, "lbl_status_caption"):
            self.lbl_status_caption.setStyleSheet(
                f"font-size: 10px; font-weight: {'normal' if is_dark else 'bold'}; color: {'#8c8c8c' if is_dark else '#18191c'}; background: transparent; border: none;"
            )
        if hasattr(self, "lbl_game_status"):
            running = getattr(self.app, "_game_process", None) is not None
            self.set_game_status(running)
        if hasattr(self, "lbl_mode_value"):
            self.lbl_mode_value.setStyleSheet(
                f"font-size: 12px; font-weight: bold; color: {accent}; background: transparent; border: none;"
            )
        if hasattr(self, "box_launch_action") and hasattr(self.box_launch_action, "_update_display_text"):
            self.box_launch_action._update_display_text()

        # 2. Installation View branding header
        if hasattr(self, "lbl_install_view_title"):
            self.lbl_install_view_title.setStyleSheet(
                f"font-size: 16px; font-weight: 900; letter-spacing: 0.6px; color: {'#ffffff' if is_dark else '#111214'}; background: transparent; border: none;"
            )
        if hasattr(self, "lbl_install_view_sub"):
            self.lbl_install_view_sub.setStyleSheet(
                f"font-size: 13px; font-weight: {'normal' if is_dark else '500'}; color: {'#9aa0a6' if is_dark else '#2c2f36'}; background: transparent; border: none;"
            )

        # 3. Mass edit mode controls
        if hasattr(self, "btn_edit_mode"):
            pencil_icon = ImageManager.get_tinted_icon("edit_pencil_icon.svg", "#18191c" if not is_dark else "#ffffff", (16, 16))
            if not pencil_icon.isNull():
                self.btn_edit_mode.setIcon(pencil_icon)
            self.btn_edit_mode.setStyleSheet(f"""
                QPushButton {{
                    background: {hex_to_rgba(accent, 0.20) if getattr(self, "_is_edit_mode", False) else ("rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)")};
                    border: 1px solid {accent if getattr(self, "_is_edit_mode", False) else ("rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.12)")};
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background: {hex_to_rgba(accent, 0.30)};
                    border: 1px solid {accent};
                }}
            """)
        if hasattr(self, "edit_mode_bar"):
            self.edit_mode_bar.setStyleSheet(f"""
                QFrame#EditModeBar {{
                    background-color: {"rgba(255, 255, 255, 0.055)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                    border: 1px solid {hex_to_rgba(accent, 0.40)};
                    border-radius: 8px;
                }}
            """)
        if hasattr(self, "btn_select_all"):
            self.btn_select_all.setStyleSheet(f"""
                QPushButton {{
                    background: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
                    color: {'#ffffff' if is_dark else '#111214'};
                    border: 1px solid {'rgba(255, 255, 255, 0.15)' if is_dark else 'rgba(0, 0, 0, 0.12)'};
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 0 10px;
                }}
                QPushButton:hover {{
                    background: {"rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.12)"};
                }}
            """)
        if hasattr(self, "btn_delete_selected"):
            self.btn_delete_selected.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(239, 68, 68, 0.15);
                    color: #ef4444;
                    border: 1px solid rgba(239, 68, 68, 0.40);
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 0 10px;
                }}
                QPushButton:hover {{
                    background: #ef4444;
                    color: white;
                }}
            """)
        if hasattr(self, "btn_done_edit"):
            self.btn_done_edit.setStyleSheet(f"""
                QPushButton {{
                    background: {accent};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 0 12px;
                }}
                QPushButton:hover {{
                    background: {adjust_color(accent, 20)};
                }}
            """)

        # 4. Trigger repainting of custom sidebar & tabs
        if hasattr(self, "panel_left"):
            self.panel_left.update()
        if hasattr(self, "sidebar_nav_group"):
            self.sidebar_nav_group.update()
        if hasattr(self, "btn_nav_home"):
            self.btn_nav_home.update()
        if hasattr(self, "btn_nav_install"):
            self.btn_nav_install.update()
        if hasattr(self, "btn_nav_screenshots"):
            self.btn_nav_screenshots.update()
        if hasattr(self, "btn_nav_worlds"):
            self.btn_nav_worlds.update()
        if hasattr(self, "btn_nav_packs"):
            self.btn_nav_packs.update()
        if hasattr(self, "btn_nav_mods"):
            self.btn_nav_mods.update()
        if hasattr(self, "installer_widget"):
            if hasattr(self.installer_widget, "update_theme_styles"):
                self.installer_widget.update_theme_styles()
            elif hasattr(self.installer_widget, "tab_bar"):
                self.installer_widget.tab_bar.update()
        if hasattr(self, "view_screenshots") and hasattr(self.view_screenshots, "update_theme_styles"):
            self.view_screenshots.update_theme_styles()
        if hasattr(self, "view_worlds") and hasattr(self.view_worlds, "update_theme_styles"):
            self.view_worlds.update_theme_styles()
        if hasattr(self, "view_packs") and hasattr(self.view_packs, "update_theme_styles"):
            self.view_packs.update_theme_styles()
        if hasattr(self, "view_mods") and hasattr(self.view_mods, "update_theme_styles"):
            self.view_mods.update_theme_styles()

        # 4. Quick Preferences & Access Sub-Cards styling
        if hasattr(self, "lbl_quick_header"):
            self.lbl_quick_header.setStyleSheet(
                f"font-size: 11px; font-weight: 800; letter-spacing: 0.8px; color: {accent}; background: transparent; border: none; padding-left: 4px;"
            )
        row_title_color = "#ffffff" if is_dark else "#111214"
        row_sub_color = "#9aa0a6" if is_dark else "#5f6368"
        for attr in ("lbl_gamemode_title", "lbl_discord_title", "lbl_folder_title", "lbl_cache_title"):
            if hasattr(self, attr):
                getattr(self, attr).setStyleSheet(
                    f"font-size: 13.5px; font-weight: 700; color: {row_title_color}; background: transparent; border: none;"
                )
        for attr in ("lbl_gamemode_sub", "lbl_discord_sub", "lbl_folder_sub", "lbl_cache_sub"):
            if hasattr(self, attr):
                getattr(self, attr).setStyleSheet(
                    f"font-size: 11px; font-weight: 400; color: {row_sub_color}; background: transparent; border: none;"
                )

        # Update monochrome SVG icons
        icon_color = "#ffffff" if is_dark else "#1e2025"
        if hasattr(self, "lbl_icon_gamemode"):
            self.lbl_icon_gamemode.setPixmap(ImageManager.get_tinted_icon("quick_icon_gamemode.svg", icon_color, (20, 20)).pixmap(20, 20))
        if hasattr(self, "lbl_icon_discord"):
            self.lbl_icon_discord.setPixmap(ImageManager.get_tinted_icon("quick_icon_discord.svg", icon_color, (20, 20)).pixmap(20, 20))
        if hasattr(self, "lbl_icon_folder"):
            self.lbl_icon_folder.setPixmap(ImageManager.get_tinted_icon("quick_icon_folder.svg", icon_color, (20, 20)).pixmap(20, 20))
        if hasattr(self, "lbl_icon_cache"):
            self.lbl_icon_cache.setPixmap(ImageManager.get_tinted_icon("quick_icon_clean.svg", icon_color, (20, 20)).pixmap(20, 20))

        subcard_qss = f"""
            QFrame#QuickSubCard {{
                background-color: {"rgba(255, 255, 255, 0.055)" if is_dark else "rgba(0, 0, 0, 0.035)"};
                border: 1px solid {"rgba(255, 255, 255, 0.09)" if is_dark else "rgba(0, 0, 0, 0.08)"};
                border-radius: 12px;
            }}
            QFrame#QuickSubCard:hover {{
                background-color: {"rgba(255, 255, 255, 0.085)" if is_dark else "rgba(0, 0, 0, 0.06)"};
                border: 1px solid {"rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.14)"};
            }}
            QFrame#QuickSubCardIcon {{
                background-color: {"rgba(255, 255, 255, 0.065)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                border: 1px solid {"rgba(255, 255, 255, 0.09)" if is_dark else "rgba(0, 0, 0, 0.08)"};
                border-radius: 9px;
            }}
        """
        for sc in self.findChildren(QFrame, "QuickSubCard"):
            sc.setStyleSheet(subcard_qss)

        action_btn_qss = f"""
            QPushButton#QuickActionBtn {{
                background-color: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.05)"};
                color: {"#ffffff" if is_dark else "#1a1c22"};
                border: 1px solid {"rgba(255, 255, 255, 0.14)" if is_dark else "rgba(0, 0, 0, 0.12)"};
                border-radius: 7px;
                padding: 5px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#QuickActionBtn:hover {{
                background-color: {hex_to_rgba(accent, 0.25) if is_dark else hex_to_rgba(accent, 0.15)};
                color: {"#ffffff" if is_dark else accent};
                border: 1px solid {accent};
            }}
            QPushButton#QuickActionBtn:pressed {{
                background-color: {accent};
                color: #ffffff;
            }}
        """
        if hasattr(self, "btn_open_game_folder"):
            self.btn_open_game_folder.setStyleSheet(action_btn_qss)
        if hasattr(self, "btn_clean_cache"):
            self.btn_clean_cache.setStyleSheet(action_btn_qss)
        if hasattr(self, "check_gamemode"):
            self.check_gamemode.update()
        if hasattr(self, "check_discord"):
            self.check_discord.update()
        if hasattr(self, "card_right_top") and hasattr(self.card_right_top, "update_theme_styles"):
            self.card_right_top.update_theme_styles()
        if hasattr(self, "btn_toggle_right_panel"):
            is_active = self.btn_toggle_right_panel.isChecked()
            panel_ic = ImageManager.get_tinted_icon("settings_more_dots.svg", accent if is_active else ("#ffffff" if is_dark else "#18191c"), (14, 14))
            if not panel_ic.isNull():
                self.btn_toggle_right_panel.setIcon(panel_ic)
            self.btn_toggle_right_panel.setText(c.t("UI_BTN_NEWS"))
            self.btn_toggle_right_panel.setStyleSheet(f"""
                QPushButton {{
                    background: {hex_to_rgba(accent, 0.22) if is_active else ("rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)")};
                    color: {accent if is_active else ("#ffffff" if is_dark else "#18191c")};
                    font-size: 11.5px;
                    font-weight: bold;
                    border: 1px solid {accent if is_active else ("rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.12)")};
                    border-radius: 6px;
                    padding: 0 10px;
                }}
                QPushButton:hover {{
                    background: {hex_to_rgba(accent, 0.32)};
                    border: 1px solid {accent};
                }}
            """)

    def showEvent(self, event):
        super().showEvent(event)
        self._update_responsive_layout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_responsive_layout()

    def _update_responsive_layout(self):
        w = self.width()
        compact_mode = w < 1035
        if not getattr(self, "_manual_right_panel_toggle", False):
            self.panel_right.setVisible(not compact_mode)
            if hasattr(self, "btn_toggle_right_panel"):
                self.btn_toggle_right_panel.setVisible(compact_mode)
                if compact_mode:
                    self.btn_toggle_right_panel.setChecked(self.panel_right.isVisible())
        else:
            if not compact_mode:
                self._manual_right_panel_toggle = False
                self.panel_right.setVisible(True)
                if hasattr(self, "btn_toggle_right_panel"):
                    self.btn_toggle_right_panel.setVisible(False)
            elif hasattr(self, "btn_toggle_right_panel"):
                self.btn_toggle_right_panel.setVisible(True)
                self.btn_toggle_right_panel.setChecked(self.panel_right.isVisible())

    def _on_toggle_right_panel_clicked(self):
        self._manual_right_panel_toggle = True
        new_vis = not self.panel_right.isVisible()
        self.panel_right.setVisible(new_vis)
        self.btn_toggle_right_panel.setChecked(new_vis)
        self.update_theme_styles()

    def toggle_edit_mode(self):
        """Toggle mass edit mode on installed version cards."""
        self._is_edit_mode = not getattr(self, "_is_edit_mode", False)
        if hasattr(self, "edit_mode_bar"):
            self.edit_mode_bar.setVisible(self._is_edit_mode)
        if hasattr(self.app, "version_cards"):
            for card in self.app.version_cards.values():
                if hasattr(card, "cb_select") and card.cb_select:
                    card.cb_select.setVisible(self._is_edit_mode)
                if hasattr(card, "drag_grip") and card.drag_grip:
                    card.drag_grip.setVisible(self._is_edit_mode)
        self.update_theme_styles()

    def toggle_select_all_versions(self):
        """Select or deselect all version checkboxes in edit mode."""
        cards = getattr(self.app, "version_cards", {}).values()
        all_checked = all(card.cb_select.isChecked() for card in cards if hasattr(card, "cb_select"))
        for card in cards:
            if hasattr(card, "cb_select"):
                card.cb_select.setChecked(not all_checked)

    def delete_selected_versions(self):
        """Delete all versions currently checked in edit mode."""
        selected_vers = []
        for v, card in getattr(self.app, "version_cards", {}).items():
            if hasattr(card, "cb_select") and card.cb_select.isChecked():
                selected_vers.append(v)
        if not selected_vers:
            messagebox.showwarning(self, c.t("UI_ERROR_TITLE"), "No has seleccionado ninguna versión.")
            return
        count = len(selected_vers)
        confirm = messagebox.askyesno(
            self,
            c.t("UI_CONFIRM_DELETE_TITLE"),
            f"¿Estás seguro de que deseas eliminar permanentemente {count} versión(es) seleccionada(s)?"
        )
        if confirm:
            for v in selected_vers:
                try:
                    vdir = os.path.join(self.app.active_path, c.VERSIONS_DIR, v)
                    if os.path.exists(vdir):
                        shutil.rmtree(vdir)
                except Exception as e:
                    logger.error(f"Error deleting version {v}: {e}")
            if hasattr(self.app.logic, "refresh_version_list"):
                self.app.logic.refresh_version_list(self.app)
            messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), f"Se eliminaron {count} versión(es) correctamente.")

    def show_home_view(self):
        """Switch sidebar to Inicio and display the version list and launch card."""
        if hasattr(self, "sidebar_nav_group") and self.sidebar_nav_group._current_index != 0:
            self.sidebar_nav_group.setCurrentIndex(0)
        self.content_stack.setCurrentIndex(0)

    def show_install_view(self):
        """Switch sidebar to Instalación and display the embedded version installer card."""
        if hasattr(self, "sidebar_nav_group") and self.sidebar_nav_group._current_index != 1:
            self.sidebar_nav_group.setCurrentIndex(1)
        self.content_stack.setCurrentIndex(1)

    def show_worlds_view(self):
        """Switch sidebar to Mundos and display the worlds manager."""
        if hasattr(self, "sidebar_nav_group") and self.sidebar_nav_group._current_index != 2:
            self.sidebar_nav_group.setCurrentIndex(2)
        self.content_stack.setCurrentIndex(2)
        if hasattr(self, "view_worlds") and hasattr(self.view_worlds, "load_worlds"):
            self.view_worlds.load_worlds()

    def show_packs_view(self):
        """Switch sidebar to Packs and display the RP/BP manager."""
        if hasattr(self, "sidebar_nav_group") and self.sidebar_nav_group._current_index != 3:
            self.sidebar_nav_group.setCurrentIndex(3)
        self.content_stack.setCurrentIndex(3)
        if hasattr(self, "view_packs") and hasattr(self.view_packs, "load_packs"):
            self.view_packs.load_packs()

    def show_mods_view(self):
        """Switch sidebar to Mods and display the MCPELauncher mods manager."""
        if hasattr(self, "sidebar_nav_group") and self.sidebar_nav_group._current_index != 4:
            self.sidebar_nav_group.setCurrentIndex(4)
        self.content_stack.setCurrentIndex(4)
        if hasattr(self, "view_mods") and hasattr(self.view_mods, "load_mods"):
            self.view_mods.load_mods()

    def show_screenshots_view(self):
        """Switch sidebar to Capturas and display the screenshots gallery."""
        if hasattr(self, "sidebar_nav_group") and self.sidebar_nav_group._current_index != 5:
            self.sidebar_nav_group.setCurrentIndex(5)
        self.content_stack.setCurrentIndex(5)
        if hasattr(self, "view_screenshots") and hasattr(self.view_screenshots, "load_screenshots"):
            self.view_screenshots.load_screenshots()

    @property
    def version_var(self):
        return self

    def get(self):
        """Return the currently selected version string."""
        return self._selected_version

    def set(self, value):
        """Set the currently selected version string."""
        self._selected_version = value

    def update_profile_indicator(self):
        """Refresh the profile name shown in the top bar badge."""
        if hasattr(self.app, "update_top_profile_badge"):
            self.app.update_top_profile_badge()

    def _on_launch_btn_clicked(self):
        if getattr(self.app, "_game_process", None) is not None and self.app._game_process.poll() is None:
            from src.gui import custom_dialogs as messagebox
            title = c.t("UI_CONFIRM_TITLE")
            msg = "¿Estás seguro de que deseas forzar el cierre de Minecraft?\nCualquier progreso no guardado se perderá."
            if messagebox.askyesno(self.app, title, msg):
                self.app.logic.kill_game(self.app)
        else:
            self.app.logic.launch_game(self.app)

    def set_game_status(self, running):
        raw_running = c.t("UI_GAME_STATUS_RUNNING").replace("▶", "").replace("⏹", "").replace("●", "").strip()
        raw_idle = c.t("UI_GAME_STATUS_IDLE").replace("▶", "").replace("⏹", "").replace("●", "").strip()
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        if hasattr(self, "btn_launch"):
            self.btn_launch.set_running_state(running)
        if running:
            self.dot_game_status.setStyleSheet("background-color: #2ed573; border-radius: 5px; border: none;")
            self.lbl_game_status.setText(raw_running)
            self.lbl_game_status.setStyleSheet("font-size: 12px; font-weight: bold; color: #2ed573; background: transparent; border: none;")
            self.lbl_game_status.setToolTip(raw_running)
        else:
            idle_color = "#dedede" if is_dark else "#24272e"
            self.dot_game_status.setStyleSheet("background-color: #777777; border-radius: 5px; border: none;")
            self.lbl_game_status.setText(raw_idle)
            self.lbl_game_status.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {idle_color}; background: transparent; border: none;")
            self.lbl_game_status.setToolTip(raw_idle)

    def retranslate_ui(self):
        running = self.app._game_process is not None
        self.set_game_status(running)
        self.lbl_install.setText(c.t("UI_LABEL_GAME_MODE"))
        mode_key = self.app.config.get(c.CONFIG_KEY_INSTALL_MODE, c.MODE_INSTALL_LOCAL)
        mode_name = c.t("UI_INSTALL_MODES").get(mode_key, mode_key)
        self.lbl_mode_value.setText(mode_name)
        self.lbl_status_caption.setText(c.t("UI_LABEL_STATUS"))
        self.lbl_version_title.setText(c.t("UI_LABEL_INSTALLED_VERSIONS"))
        self.update_profile_indicator()
        if hasattr(self, "box_launch_action") and hasattr(self.box_launch_action, "retranslate_ui"):
            self.box_launch_action.retranslate_ui()
        if hasattr(self, "card_news") and hasattr(self.card_news, "retranslate_ui"):
            self.card_news.retranslate_ui()
        if hasattr(self, "lbl_gamemode_title"):
            self.lbl_gamemode_title.setText(c.t("UI_CHECKBOX_GAMEMODE") if c.t("UI_CHECKBOX_GAMEMODE") else "Activar GameMode")
        if hasattr(self, "lbl_discord_title"):
            self.lbl_discord_title.setText(c.t("UI_CHECKBOX_DISCORD_RPC") if c.t("UI_CHECKBOX_DISCORD_RPC") else "Mostrar en Discord")
        if hasattr(self, "btn_launch") and not getattr(self.btn_launch, "_is_running", False):
            self.btn_launch.setText((c.t("UI_PLAY_BUTTON") if c.t("UI_PLAY_BUTTON") else "JUGAR").upper())
        if hasattr(self, "lbl_install_view_title"):
            self.lbl_install_view_title.setText(c.t("UI_INSTALL_VIEW_TITLE"))
        if hasattr(self, "lbl_install_view_sub"):
            self.lbl_install_view_sub.setText(c.t("UI_INSTALL_VIEW_SUBTITLE"))
        if hasattr(self, "btn_nav_home"):
            self.btn_nav_home.setText(c.t("UI_SIDEBAR_HOME"))
            self.btn_nav_install.setText(c.t("UI_SIDEBAR_INSTALL"))
            self.btn_nav_worlds.setText(c.t("UI_SIDEBAR_WORLDS"))
            self.btn_nav_packs.setText(c.t("UI_SIDEBAR_PACKS"))
            self.btn_nav_mods.setText(c.t("UI_SIDEBAR_MODS"))
            self.btn_nav_screenshots.setText(c.t("UI_SIDEBAR_SCREENSHOTS"))
        if hasattr(self, "btn_discord"):
            self.btn_discord.setToolTip(c.t("UI_TOOLTIP_DISCORD"))
            self.btn_web.setToolTip(c.t("UI_TOOLTIP_WEB"))
            self.btn_github.setToolTip(c.t("UI_TOOLTIP_GITHUB"))
        if hasattr(self, "btn_edit_mode"):
            self.btn_edit_mode.setToolTip(c.t("UI_TOOLTIP_EDIT_MODE"))
        if hasattr(self, "btn_toggle_right_panel"):
            self.btn_toggle_right_panel.setToolTip(c.t("UI_TOOLTIP_TOGGLE_RIGHT"))
        if hasattr(self, "lbl_quick_header"):
            self.lbl_quick_header.setText(c.t("UI_QUICK_PREFS_HEADER"))
        if hasattr(self, "lbl_gamemode_sub"):
            self.lbl_gamemode_sub.setText(c.t("UI_QUICK_GAMEMODE_SUB"))
        if hasattr(self, "lbl_discord_sub"):
            self.lbl_discord_sub.setText(c.t("UI_QUICK_DISCORD_SUB"))
        if hasattr(self, "lbl_folder_title"):
            self.lbl_folder_title.setText(c.t("UI_QUICK_FOLDER_TITLE"))
            self.lbl_folder_sub.setText(c.t("UI_QUICK_FOLDER_SUB"))
            self.btn_open_game_folder.setText(c.t("UI_QUICK_BTN_OPEN"))
        if hasattr(self, "lbl_cache_title"):
            self.lbl_cache_title.setText(c.t("UI_QUICK_CACHE_TITLE"))
            self.lbl_cache_sub.setText(c.t("UI_QUICK_CACHE_SUB"))
            self.btn_clean_cache.setText(c.t("UI_QUICK_BTN_CLEAN"))
        if hasattr(self, "btn_select_all"):
            self.btn_select_all.setText(c.t("UI_EDIT_MODE_SELECT_ALL"))
        if hasattr(self, "btn_delete_selected"):
            self.btn_delete_selected.setText(c.t("UI_EDIT_MODE_DELETE_SELECTED"))
        if hasattr(self, "btn_done_edit"):
            self.btn_done_edit.setText(c.t("UI_EDIT_MODE_DONE"))
        if hasattr(self, "btn_toggle_right_panel"):
            self.btn_toggle_right_panel.setText(c.t("UI_BTN_NEWS"))
        if hasattr(self, "installer_widget") and self.installer_widget and hasattr(self.installer_widget, "retranslate_ui"):
            self.installer_widget.retranslate_ui()
        if hasattr(self, "view_worlds") and self.view_worlds and hasattr(self.view_worlds, "retranslate_ui"):
            self.view_worlds.retranslate_ui()
        if hasattr(self, "view_packs") and self.view_packs and hasattr(self.view_packs, "retranslate_ui"):
            self.view_packs.retranslate_ui()
        if hasattr(self, "view_mods") and self.view_mods and hasattr(self.view_mods, "retranslate_ui"):
            self.view_mods.retranslate_ui()
        if hasattr(self, "view_screenshots") and self.view_screenshots and hasattr(self.view_screenshots, "retranslate_ui"):
            self.view_screenshots.retranslate_ui()
        if hasattr(self, "version_rows"):
            for row in self.version_rows:
                if hasattr(row, "retranslate_ui"):
                    row.retranslate_ui()

    def save_quick_opts(self):
        """Persist the launch option checkboxes to config."""
        self.app.config_manager.set(c.CONFIG_KEY_DISCORD_RPC_ENABLED, self.check_discord.isChecked())

    def _open_game_folder(self):
        """Open the active Minecraft games/com.mojang folder in desktop file manager."""
        from src.utils.process_utils import open_path
        target = None
        if self.app and hasattr(self.app, "active_path") and self.app.active_path:
            p = os.path.join(self.app.active_path, "games", "com.mojang")
            if os.path.exists(p):
                target = p
            elif os.path.exists(self.app.active_path):
                target = self.app.active_path
        if not target:
            default_mojang = os.path.expanduser("~/.local/share/mcpelauncher/games/com.mojang")
            if os.path.exists(default_mojang):
                target = default_mojang
        if target and os.path.exists(target):
            open_path(target)
        else:
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), "No se encontró la carpeta del juego (com.mojang).")

    def _clean_game_cache(self):
        """Clean game shader caches and temporary files."""
        if not messagebox.askyesno(
            self,
            "Limpiar Caché",
            "¿Deseas limpiar la memoria caché de shaders y archivos temporales de Minecraft?\n\nEsto puede solucionar problemas gráficos o de arranque tras actualizar versiones."
        ):
            return

        freed_bytes = 0
        deleted_count = 0
        home = os.path.expanduser("~")
        candidate_dirs = [
            os.path.join(home, ".cache", "mcpelauncher"),
            os.path.join(home, ".var", "app", "io.mrarm.mcpelauncher", "cache"),
        ]
        if self.app and hasattr(self.app, "active_path") and self.app.active_path:
            candidate_dirs.append(os.path.join(self.app.active_path, "cache"))
            candidate_dirs.append(os.path.join(self.app.active_path, "games", "com.mojang", "minecraftpe", "cache"))

        for d in candidate_dirs:
            if os.path.exists(d) and os.path.isdir(d):
                try:
                    for root, dirs, files in os.walk(d, topdown=False):
                        for f in files:
                            fp = os.path.join(root, f)
                            try:
                                freed_bytes += os.path.getsize(fp)
                                os.remove(fp)
                                deleted_count += 1
                            except Exception:
                                pass
                        for sub_d in dirs:
                            sp = os.path.join(root, sub_d)
                            try:
                                os.rmdir(sp)
                            except Exception:
                                pass
                except Exception:
                    pass

        try:
            ImageManager.clear_cache()
        except Exception:
            pass

        if deleted_count > 0:
            freed_mb = freed_bytes / (1024 * 1024)
            if freed_mb >= 1.0:
                size_str = f"{freed_mb:.1f} MB"
            else:
                size_str = f"{freed_bytes / 1024:.1f} KB"
            messagebox.showinfo(self, "Caché Limpia", f"Se limpiaron {deleted_count} archivos temporales ({size_str} liberados).")
        else:
            messagebox.showinfo(self, "Caché Limpia", "La memoria caché ya se encuentra limpia.")

    # Helpers to clean children (replacement for winfo_children)
    @property
    def version_listbox(self):
        return self.version_list_widget
