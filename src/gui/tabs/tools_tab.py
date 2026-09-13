"""
Tools Tab for Cianova Launcher.
Displays standalone utility cards for data migration, skin pack creation,
game configuration, shaders toggling, file browsing, dependency verification,
hardware requirement analysis, and compatible version inspection.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QRect, QRectF, QEasingCurve, QVariantAnimation
from PySide6.QtGui import (
    QPixmap, QPainter, QImage, QLinearGradient, QRadialGradient,
    QColor, QPen
)
from src import constants as c
from src.utils.resource_path import resource_path
from src.utils.colors import hex_to_rgba
from src.core.ui_utils import ResponsiveGridLayout, clear_layout
from src.gui import custom_dialogs as messagebox

_TOOL_CARD_PIXMAP_CACHE = {}


class TactileToolButton(QPushButton):
    """
    Action button with springy tactile press animation (sinks down on press and bounces back),
    matching the top bar tab tactile interaction.
    """

    def __init__(self, text="", accent="#38bdf8", app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self.accent = accent
        self._btn_text = text
        self._sink_factor = 0.0
        self._hover_factor = 0.0

        self.setFixedHeight(42)
        self.setCursor(Qt.PointingHandCursor)

        # Tactile press animation (180ms InOutQuad like top bar)
        self._sink_anim = QVariantAnimation(self)
        self._sink_anim.setDuration(180)
        self._sink_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._sink_anim.setStartValue(0.0)
        self._sink_anim.setKeyValueAt(0.5, 1.0)
        self._sink_anim.setEndValue(0.0)
        self._sink_anim.valueChanged.connect(self._on_sink_val)

        # Smooth hover fade animation (140ms OutQuad)
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(140)
        self._hover_anim.setEasingCurve(QEasingCurve.OutQuad)
        self._hover_anim.valueChanged.connect(self._on_hover_val)

    def _on_sink_val(self, val):
        self._sink_factor = val
        self.update()

    def _on_hover_val(self, val):
        self._hover_factor = val
        self.update()

    def enterEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_factor)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_factor)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.trigger_press_animation()
        super().mousePressEvent(event)

    def trigger_press_animation(self):
        self._sink_anim.stop()
        self._sink_anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = float(self.width())
        h = float(self.height())
        if w <= 0 or h <= 0:
            return

        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        # Tactile press scaling and inset (sink factor matching top bar tabs)
        sink_inset = self._sink_factor * 1.8
        scale = 1.0 - (0.045 * self._sink_factor)
        if self.isDown():
            scale = min(scale, 0.955)

        cx = w / 2.0
        cy = h / 2.0
        painter.translate(cx, cy)
        painter.scale(scale, scale)
        painter.translate(-cx, -cy)

        btn_rect = QRectF(1.5 + sink_inset, 1.5 + sink_inset, (w - 3.0) - 2 * sink_inset, (h - 3.0) - 2 * sink_inset)
        radius = 9.0

        accent_color = QColor(self.accent)

        if is_dark:
            # Dark mode: tinted background, accent border, and luminous text
            bg_alpha = int(24 + 42 * self._hover_factor + 30 * self._sink_factor)
            if self.isDown():
                bg_alpha = int(bg_alpha * 1.4)
            bg_color = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), min(255, bg_alpha))

            border_alpha = int(55 + 140 * self._hover_factor + 50 * self._sink_factor)
            border_color = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), min(255, border_alpha))
            pen_width = 1.1 + 0.6 * self._hover_factor

            if self._hover_factor > 0.05:
                t = self._hover_factor
                txt_r = int(accent_color.lighter(125).red() * (1 - t) + 255 * t)
                txt_g = int(accent_color.lighter(125).green() * (1 - t) + 255 * t)
                txt_b = int(accent_color.lighter(125).blue() * (1 - t) + 255 * t)
                text_color = QColor(txt_r, txt_g, txt_b)
            else:
                text_color = accent_color.lighter(120)
        else:
            # Light mode: clean crisp pill button with rich accent, fills on hover with crisp white text
            bg_alpha = int(16 + 215 * self._hover_factor + 24 * self._sink_factor)
            if self.isDown():
                bg_alpha = min(255, int(bg_alpha * 1.12))
            bg_color = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), min(255, bg_alpha))

            border_alpha = int(75 + 160 * self._hover_factor + 20 * self._sink_factor)
            border_color = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), min(255, border_alpha))
            pen_width = 1.1 + 0.5 * self._hover_factor

            if self._hover_factor > 0.05:
                # Smoothly transitions to crisp white text as button fills with accent
                t = self._hover_factor
                base_c = accent_color.darker(115)
                txt_r = int(base_c.red() * (1 - t) + 255 * t)
                txt_g = int(base_c.green() * (1 - t) + 255 * t)
                txt_b = int(base_c.blue() * (1 - t) + 255 * t)
                text_color = QColor(txt_r, txt_g, txt_b)
            else:
                text_color = accent_color.darker(115)

        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, pen_width))
        painter.drawRoundedRect(btn_rect, radius, radius)

        # Centered bold text
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(text_color)
        painter.drawText(btn_rect, Qt.AlignCenter, self._btn_text)
        painter.end()


class ToolCardWidget(QFrame):
    """
    Standalone tool card with individual color accent, floating Minecraft voxel cubes,
    smooth hover expansion and displacement, and tactile action button.
    """

    def __init__(self, tool_data: dict, app=None, parent_tab=None):
        super().__init__()
        self.tool_data = tool_data
        self.app = app
        self.parent_tab = parent_tab
        self.accent = tool_data.get("accent", "#38bdf8")
        self.setObjectName("ToolCard")
        self.setFixedHeight(345)
        self.setMinimumWidth(190)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)

        self._hover_factor = 0.0
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(190)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._hover_anim.valueChanged.connect(self._on_hover_val)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 16)
        self._layout.setSpacing(6)

        # 1. 3D Graphic (large, prominent asset)
        self.lbl_image = QLabel()
        self.lbl_image.setFixedHeight(116)
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setStyleSheet("background: transparent;")
        img_name = tool_data.get("image", "")
        if img_name:
            if img_name in _TOOL_CARD_PIXMAP_CACHE:
                self.lbl_image.setPixmap(_TOOL_CARD_PIXMAP_CACHE[img_name])
            else:
                img_path = resource_path(img_name)
                if os.path.exists(img_path):
                    pix = QPixmap(img_path)
                    if not pix.isNull():
                        scaled = pix.scaled(180, 116, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        _TOOL_CARD_PIXMAP_CACHE[img_name] = scaled
                        self.lbl_image.setPixmap(scaled)
        self._layout.addWidget(self.lbl_image)

        # 2. Title (larger and prominent with word-wrap)
        self.lbl_title = QLabel(tool_data.get("title", ""))
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setFixedHeight(44)
        self.lbl_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff; background: transparent;")
        self._layout.addWidget(self.lbl_title)

        # 3. Description (larger font and generous height)
        self.lbl_desc = QLabel(tool_data.get("desc", ""))
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setFixedHeight(48)
        self.lbl_desc.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lbl_desc.setStyleSheet("font-size: 12px; color: #94a3b8; line-height: 1.35; background: transparent;")
        self._layout.addWidget(self.lbl_desc)

        # 4. Status Row (or height spacer)
        self.row_status = QWidget()
        self.row_status.setFixedHeight(20)
        self.row_status.setStyleSheet("background: transparent;")
        self.layout_status = QHBoxLayout(self.row_status)
        self.layout_status.setContentsMargins(0, 0, 0, 0)
        self.layout_status.setSpacing(6)
        self.layout_status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.lbl_status_dot = QLabel("●")
        self.lbl_status_dot.setStyleSheet(f"color: {self.accent}; font-size: 10px; background: transparent;")
        self.lbl_status_text = QLabel("")
        self.lbl_status_text.setStyleSheet(f"color: {self.accent}; font-size: 11px; font-weight: 600; background: transparent;")

        status_kind = tool_data.get("status_kind")
        if status_kind == "shaders":
            self.layout_status.addWidget(self.lbl_status_dot)
            self.lbl_status_text.setText(f"{c.t('UI_TOOL_TITLE_SHADERS')}: ...")
            self.layout_status.addWidget(self.lbl_status_text)
            self.layout_status.addStretch(1)
            if parent_tab:
                parent_tab.lbl_shader_status = self.lbl_status_text
        elif status_kind == "compat":
            self.layout_status.addWidget(self.lbl_status_dot)
            range_txt = self.app.logic.get_compatibility_range(self.app) if hasattr(self.app, "logic") else "1.13.0 - 1.26.0+"
            self.lbl_status_text.setText(range_txt)
            self.layout_status.addWidget(self.lbl_status_text)
            self.layout_status.addStretch(1)
        else:
            self.layout_status.addStretch(1)

        self._layout.addWidget(self.row_status)

        # 5. Bottom Tactile Action Button (with springy press effect and accent styling)
        btn_text = tool_data.get("btn_text", tool_data.get("title", ""))
        self.btn_action = TactileToolButton(btn_text, accent=self.accent, app=self.app)
        self.btn_action.clicked.connect(self._trigger_action)
        self._layout.addWidget(self.btn_action)

        self.update_theme_styles()

    def _on_hover_val(self, val):
        self._hover_factor = val
        self.update()

    def enterEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_factor)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_factor)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.btn_action.trigger_press_animation()
            self._trigger_action()
        super().mousePressEvent(event)

    def _effective_accent(self):
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        if is_dark:
            return self.accent
        light_map = {
            "#10b981": "#059669",  # Emerald Green (deep & vibrant)
            "#8b5cf6": "#7c3aed",  # Violet Purple
            "#38bdf8": "#0284c7",  # Ocean Blue
            "#f59e0b": "#d97706",  # Warm Amber / Bronze
            "#f43f5e": "#e11d48",  # Ruby Crimson
            "#06b6d4": "#0891b2",  # Deep Teal Cyan
            "#a855f7": "#9333ea",  # Royal Magenta
            "#22c55e": "#16a34a",  # Crisp Mint Green
        }
        return light_map.get(self.accent.lower(), self.accent)

    def _trigger_action(self):
        cmd = self.tool_data.get("cmd")
        if cmd and callable(cmd):
            cmd()

    def update_theme_styles(self):
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        eff_accent = self._effective_accent()
        self.lbl_title.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {'#ffffff' if is_dark else '#0f172a'}; background: transparent;"
        )
        self.lbl_desc.setStyleSheet(
            f"font-size: 12px; color: {'#94a3b8' if is_dark else '#64748b'}; line-height: 1.35; background: transparent;"
        )
        self.lbl_status_dot.setStyleSheet(f"color: {eff_accent}; font-size: 10px; background: transparent;")
        self.lbl_status_text.setStyleSheet(f"color: {eff_accent}; font-size: 11px; font-weight: 600; background: transparent;")
        if hasattr(self, "btn_action"):
            self.btn_action.accent = eff_accent
            self.btn_action.update()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        if w <= 0 or h <= 0:
            return

        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        eff_accent_hex = self._effective_accent()
        accent_color = QColor(eff_accent_hex)

        # Expansion & displacement on hover (safe insets prevent any top/side clipping)
        pad_top = 8.0
        pad_side = 5.0
        pad_bottom = 5.0

        exp = 3.0 * self._hover_factor
        dy = -4.0 * self._hover_factor

        left = pad_side - exp
        top = pad_top - exp + dy
        card_w = (w - 2.0 * pad_side) + 2.0 * exp
        card_h = (h - (pad_top + pad_bottom)) + 2.0 * exp
        card_rect = QRectF(left, top, card_w, card_h)
        radius = 13.0

        # Elevation shadow beneath card
        if is_dark:
            shadow_alpha = int(18 + 75 * self._hover_factor)
            shadow_rect = card_rect.adjusted(2, 4 - dy * 0.3, -2, 6 - dy * 0.5)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, shadow_alpha))
            painter.drawRoundedRect(shadow_rect, radius + 2, radius + 2)
        else:
            # Soft ambient drop shadow in light mode
            shadow_alpha = int(16 + 28 * self._hover_factor)
            shadow_rect = card_rect.adjusted(1, 3 - dy * 0.25, -1, 5 - dy * 0.4)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(15, 23, 42, shadow_alpha))
            painter.drawRoundedRect(shadow_rect, radius + 2, radius + 2)
            # Subtle accent-tinted bottom glow on hover
            if self._hover_factor > 0.05:
                tint_alpha = int(32 * self._hover_factor)
                tint_shadow = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), tint_alpha)
                painter.setBrush(tint_shadow)
                painter.drawRoundedRect(card_rect.adjusted(-1, 2, 1, 5), radius + 2, radius + 2)

        # Base card container
        base_bg = QColor(14, 18, 25, 245) if is_dark else QColor(255, 255, 255, 255)
        painter.setPen(Qt.NoPen)
        painter.setBrush(base_bg)
        painter.drawRoundedRect(card_rect, radius, radius)

        # Top-centered Accent Header Glow
        if is_dark:
            # Dark mode: vibrant radial neon glow
            glow_grad = QRadialGradient(card_rect.center().x(), card_rect.top() + 75, card_rect.width() * 0.80)
            glow_alpha = int(38 + 78 * self._hover_factor)
            glow_grad.setColorAt(0.0, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), glow_alpha))
            glow_grad.setColorAt(0.55, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), int(glow_alpha * 0.42)))
            glow_grad.setColorAt(1.0, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 0))
            painter.setBrush(glow_grad)
        else:
            # Light mode: clean, fresh vertical aura that never looks muddy or like a watercolor smudge
            glow_grad = QLinearGradient(0, card_rect.top(), 0, card_rect.top() + 120)
            glow_alpha = int(16 + 26 * self._hover_factor)
            glow_grad.setColorAt(0.0, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), glow_alpha))
            glow_grad.setColorAt(0.65, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), int(glow_alpha * 0.35)))
            glow_grad.setColorAt(1.0, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 0))
            painter.setBrush(glow_grad)
        painter.drawRoundedRect(card_rect, radius, radius)

        # Floating decorative voxel cubes (Minecraft aesthetic particles)
        float_dy = -5.0 * self._hover_factor
        voxel_cubes = [
            # Top-left cluster: (rel_x_from_left, rel_y_from_top, size, is_highlight)
            (14, 18, 12, False),
            (28, 30, 8, True),    # prominent voxel cube
            (15, 50, 14, False),
            (36, 68, 10, True),   # prominent voxel cube
            (22, 94, 8, False),

            # Top-right cluster
            (-26, 16, 14, True),  # prominent voxel cube
            (-44, 30, 9, False),
            (-18, 48, 11, False),
            (-38, 72, 12, True),  # prominent voxel cube
            (-28, 100, 8, False),
        ]

        for rx, ry, csize, is_high in voxel_cubes:
            cx = card_rect.left() + rx if rx >= 0 else card_rect.right() + rx
            cy = card_rect.top() + ry + (float_dy * (1.25 if is_high else 0.8))

            if is_dark:
                if is_high:
                    c_alpha = int(120 + 95 * self._hover_factor)
                    c_fill = accent_color.lighter(135)
                    c_fill.setAlpha(min(255, c_alpha))
                    c_border = accent_color.lighter(150)
                    c_border.setAlpha(min(255, int(c_alpha * 1.15)))
                    painter.setBrush(c_fill)
                    painter.setPen(QPen(c_border, 1.2))
                else:
                    c_alpha = int(28 + 45 * self._hover_factor)
                    c_fill = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), c_alpha)
                    c_border = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), int(c_alpha * 0.85))
                    painter.setBrush(c_fill)
                    painter.setPen(QPen(c_border, 1.0))
            else:
                # Light mode: crisp, punchy, saturated voxel gems that pop on white
                if is_high:
                    c_alpha = int(160 + 80 * self._hover_factor)
                    c_fill = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), min(255, c_alpha))
                    c_border = accent_color.darker(115)
                    c_border.setAlpha(min(255, int(c_alpha * 1.1)))
                    painter.setBrush(c_fill)
                    painter.setPen(QPen(c_border, 1.2))
                else:
                    c_alpha = int(22 + 35 * self._hover_factor)
                    c_fill = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), c_alpha)
                    c_border = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), int(c_alpha * 1.6))
                    painter.setBrush(c_fill)
                    painter.setPen(QPen(c_border, 1.0))

            painter.drawRoundedRect(QRectF(cx, cy, csize, csize), 2.0, 2.0)

        # Border with accent glow
        if is_dark:
            border_alpha = int(45 + 185 * self._hover_factor)
            border_color = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), min(255, border_alpha))
            pen_width = 1.2 + 0.8 * self._hover_factor
        else:
            border_alpha = int(60 + 130 * self._hover_factor)
            border_color = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), min(255, border_alpha))
            pen_width = 1.1 + 0.6 * self._hover_factor

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(border_color, pen_width))
        painter.drawRoundedRect(card_rect, radius, radius)
        painter.end()


class ToolsHeroBannerWidget(QWidget):
    """
    Hero banner for Tools tab displaying tools_wallpaper.png with smooth bottom gradient fade,
    hosting the clean title and subtitle with compact height to avoid unnecessary scrolling.
    """

    def __init__(self, image_path=None, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self._image_path = image_path
        self._pixmap = None
        self._cached_target_img = None
        self._cached_key = None
        self.setFixedHeight(175)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_StyledBackground, False)

        if image_path and os.path.exists(image_path):
            self._pixmap = QPixmap(image_path)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 18, 28, 10)
        layout.setSpacing(3)

        # Title: Clean tools header without wrench icon or status pills
        self.lbl_brand_title = QLabel(c.t("UI_TAB_TOOLS").strip().upper() if c.t("UI_TAB_TOOLS") else "TOOLS")
        self.lbl_brand_title.setStyleSheet(
            "font-size: 24px; font-weight: 800; color: #ffffff; background: transparent; letter-spacing: 0.5px;"
        )
        layout.addWidget(self.lbl_brand_title)

        # Subtitle
        self.lbl_brand_sub = QLabel(c.t("UI_TOOLS_HERO_SUB"))
        self.lbl_brand_sub.setStyleSheet("font-size: 13px; color: #cbd5e1; background: transparent;")
        layout.addWidget(self.lbl_brand_sub)

        layout.addStretch(1)

    def setImagePath(self, path):
        self._image_path = path
        if path and os.path.exists(path):
            self._pixmap = QPixmap(path)
        else:
            self._pixmap = None
        self._cached_target_img = None
        self._cached_key = None
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._pixmap or self._pixmap.isNull():
            return

        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        cache_key = (w, h, is_dark)

        if self._cached_key != cache_key or self._cached_target_img is None:
            target_img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
            target_img.fill(Qt.transparent)

            p_img = QPainter(target_img)
            p_img.setRenderHint(QPainter.RenderHint.Antialiasing)
            p_img.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            scaled_pm = self._pixmap.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            src_x = max(0, (scaled_pm.width() - w) // 2)
            src_y = max(0, int((scaled_pm.height() - h) * 0.48))

            p_img.drawPixmap(0, 0, scaled_pm, src_x, src_y, w, h)

            # Dim/darken wallpaper: subtle 55 in light mode, deeper 145 in dark mode
            dim_alpha = 145 if is_dark else 55
            p_img.fillRect(target_img.rect(), QColor(8, 12, 18, dim_alpha))

            # Vertical Gradient mask: cleanly fades out bottom edge
            grad_v = QLinearGradient(0, 0, 0, h)
            grad_v.setColorAt(0.00, QColor(0, 0, 0, 255))
            grad_v.setColorAt(0.60, QColor(0, 0, 0, 255))
            grad_v.setColorAt(0.85, QColor(0, 0, 0, 140))
            grad_v.setColorAt(1.00, QColor(0, 0, 0, 0))

            p_img.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            p_img.fillRect(target_img.rect(), grad_v)

            # Soft dark gradient on the left to ensure crisp text contrast
            p_img.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            grad_scrim = QLinearGradient(0, 0, min(w, 650), 0)
            if is_dark:
                grad_scrim.setColorAt(0.00, QColor(11, 15, 21, 140))
                grad_scrim.setColorAt(0.65, QColor(11, 15, 21, 60))
                grad_scrim.setColorAt(1.00, QColor(11, 15, 21, 0))
            else:
                grad_scrim.setColorAt(0.00, QColor(15, 23, 42, 150))
                grad_scrim.setColorAt(0.65, QColor(15, 23, 42, 70))
                grad_scrim.setColorAt(1.00, QColor(15, 23, 42, 0))
            p_img.fillRect(QRect(0, 0, min(w, 650), h), grad_scrim)

            p_img.end()
            self._cached_key = cache_key
            self._cached_target_img = target_img
        else:
            target_img = self._cached_target_img

        painter = QPainter(self)
        painter.drawImage(0, 0, target_img)
        painter.end()


class ToolsTab(QWidget):
    """Tools tab displaying standalone cards for management, customization, files, and system utilities."""

    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Scroll area with responsive grid: exactly 4 columns max (2 rows of 4 cards)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        self.scroll_content = QWidget()
        self.layout_content = QVBoxLayout(self.scroll_content)
        self.layout_content.setContentsMargins(0, 0, 0, 16)
        self.layout_content.setSpacing(0)

        # 1. Hero banner with tools_wallpaper.png, header labels & generous spacing
        wallpaper_path = resource_path("tools_wallpaper.png")
        self.hero_banner = ToolsHeroBannerWidget(wallpaper_path, parent=self.scroll_content, app=self.app)
        self.lbl_brand_title = self.hero_banner.lbl_brand_title
        self.lbl_brand_sub = self.hero_banner.lbl_brand_sub
        self.lbl_current_profile = QLabel()
        self.lbl_tools_status = QLabel()
        self.layout_content.addWidget(self.hero_banner)

        # 2. Cards container with 28px left/right margins and spacing
        self.cards_wrapper = QWidget()
        self.cards_wrapper_layout = QVBoxLayout(self.cards_wrapper)
        self.cards_wrapper_layout.setContentsMargins(28, 2, 28, 0)
        self.cards_wrapper_layout.setSpacing(16)

        self.cards_container = QWidget()
        self.cards_grid = ResponsiveGridLayout(
            self.cards_container,
            margin=0,
            h_spacing=16,
            v_spacing=18,
            min_item_width=190,
            item_height=345,
            max_columns=4
        )
        self.cards_wrapper_layout.addWidget(self.cards_container)
        self.layout_content.addWidget(self.cards_wrapper)

        self.layout_content.addStretch(1)

        # Footer Credits
        self.lbl_footer = QLabel(c.t("CREDITOS"))
        self.lbl_footer.setAlignment(Qt.AlignCenter)
        self.layout_content.addWidget(self.lbl_footer)

        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area, 1)

        self.lbl_shader_status = None
        self._cards_initialized = False
        self.retranslate_ui()
        self.update_theme_styles()

    def _accent(self):
        theme = self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue") if self.app and hasattr(self.app, "config") else "blue"
        return c.THEME_COLOR_MAP.get(theme, "#1f6aa5")

    def _muted(self):
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        return "#94a3b8" if is_dark else "#64748b"

    def retranslate_ui(self):
        self.lbl_brand_title.setText(c.t("UI_TAB_TOOLS").strip().upper() if c.t("UI_TAB_TOOLS") else "TOOLS")
        if hasattr(self, "hero_banner") and hasattr(self.hero_banner, "lbl_brand_sub"):
            self.hero_banner.lbl_brand_sub.setText(c.t("UI_TOOLS_HERO_SUB"))
        self.lbl_footer.setText(c.t("CREDITOS"))
        if self._cards_initialized:
            self.refresh_tools_ui()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._cards_initialized:
            self._cards_initialized = True
            self.refresh_tools_ui()

    def get_tools_data(self):
        """Return the 8 standalone tool definitions matching the tools design with unique color accents."""
        return [
            {
                "id": "migrate",
                "title": c.t("UI_TOOL_TITLE_MIGRATE"),
                "desc": c.t("UI_TOOL_DESC_MIGRATE"),
                "btn_text": c.t("UI_TOOL_BTN_MIGRATE"),
                "btn_icon": "swap",
                "accent": "#10b981",  # Emerald Green
                "image": "tools_data.png",
                "cmd": self.app.open_migration_tool if self.app and hasattr(self.app, "open_migration_tool") else None,
            },
            {
                "id": "skin_creator",
                "title": c.t("UI_TOOL_TITLE_SKIN"),
                "desc": c.t("UI_TOOL_DESC_SKIN"),
                "btn_text": c.t("UI_TOOL_BTN_SKIN"),
                "btn_icon": "shirt",
                "accent": "#8b5cf6",  # Violet Purple
                "image": "tools_skin.png",
                "cmd": self.app.open_skin_tool if self.app and hasattr(self.app, "open_skin_tool") else None,
            },
            {
                "id": "game_config",
                "title": c.t("UI_TOOL_TITLE_CONFIG"),
                "desc": c.t("UI_TOOL_DESC_CONFIG"),
                "btn_text": c.t("UI_TOOL_BTN_CONFIG"),
                "btn_icon": "sliders",
                "accent": "#38bdf8",  # Sky Blue
                "image": "tool_settings.png",
                "cmd": self.app.open_game_config_tool if self.app and hasattr(self.app, "open_game_config_tool") else None,
            },
            {
                "id": "shaders",
                "title": c.t("UI_TOOL_TITLE_SHADERS"),
                "desc": c.t("UI_TOOL_DESC_SHADERS"),
                "btn_text": c.t("UI_TOOL_BTN_SHADERS"),
                "btn_icon": "sparkle",
                "accent": "#f59e0b",  # Amber / Warm Gold
                "image": "tools_shaders.png",
                "status_kind": "shaders",
                "cmd": (lambda: self.app.logic.disable_shaders(self.app)) if self.app and hasattr(self.app, "logic") else None,
            },
            {
                "id": "data_folder",
                "title": c.t("UI_TOOL_TITLE_FOLDER"),
                "desc": c.t("UI_TOOL_DESC_FOLDER"),
                "btn_text": c.t("UI_TOOL_BTN_FOLDER"),
                "btn_icon": "folder",
                "accent": "#f43f5e",  # Crimson / Rose Red
                "image": "tools_file.png",
                "cmd": (lambda: self.app.logic.open_data_folder(self.app)) if self.app and hasattr(self.app, "logic") else None,
            },
            {
                "id": "dependencies",
                "title": c.t("UI_TOOL_TITLE_DEPS"),
                "desc": c.t("UI_TOOL_DESC_DEPS"),
                "btn_text": c.t("UI_TOOL_BTN_DEPS"),
                "btn_icon": "shield",
                "accent": "#06b6d4",  # Cyan / Teal
                "image": "tools_dependencies.png",
                "cmd": (lambda: self.app.logic.verify_dependencies(self.app)) if self.app and hasattr(self.app, "logic") else None,
            },
            {
                "id": "hardware",
                "title": c.t("UI_TOOL_TITLE_HW"),
                "desc": c.t("UI_TOOL_DESC_HW"),
                "btn_text": c.t("UI_TOOL_BTN_HW"),
                "btn_icon": "search",
                "accent": "#a855f7",  # Deep Purple / Magenta
                "image": "tools_hardware.png",
                "cmd": (lambda: self.app.logic.check_requirements_dialog(self.app)) if self.app and hasattr(self.app, "logic") else None,
            },
            {
                "id": "compat",
                "title": c.t("UI_TOOL_TITLE_COMPAT"),
                "desc": c.t("UI_TOOL_DESC_COMPAT"),
                "btn_text": c.t("UI_TOOL_BTN_COMPAT"),
                "btn_icon": "cube",
                "accent": "#22c55e",  # Mint / Emerald Green
                "image": "tools_versions.png",
                "status_kind": "compat",
                "cmd": self._on_compat_clicked,
            },
        ]

    def _on_compat_clicked(self):
        try:
            from src.gui.compatible_versions_dialog import CompatibleVersionsDialog
            dlg = CompatibleVersionsDialog(self.app)
            dlg.exec()
        except Exception as e:
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), f"{c.t('UI_TOOL_TITLE_COMPAT')}: {e}")

    def refresh_tools_ui(self):
        """Populate standalone cards into the responsive grid."""
        clear_layout(self.cards_grid)
        self.lbl_shader_status = None

        tools = self.get_tools_data()
        for tool in tools:
            card = ToolCardWidget(tool, app=self.app, parent_tab=self)
            self.cards_grid.addWidget(card)

        if self.app and hasattr(self.app, "logic") and hasattr(self.app.logic, "update_shader_status_label"):
            self.app.logic.update_shader_status_label(self.app)

    def update_theme_styles(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        # Header Titles inside hero banner
        self.lbl_brand_title.setStyleSheet(
            "font-size: 24px; font-weight: 800; letter-spacing: 0.5px; color: #ffffff; background: transparent;"
        )
        self.lbl_brand_sub.setStyleSheet(
            f"font-size: 13px; color: {'#cbd5e1' if is_dark else '#e2e8f0'}; background: transparent;"
        )
        self.lbl_footer.setStyleSheet(
            f"font-size: 11px; color: {'#94a3b8' if is_dark else '#64748b'};"
        )
        self.hero_banner.update()

        # Right-spaced sleek auto-hiding scrollbar styling
        scrollbar_style = f"""
            QScrollBar:vertical {{
                width: 6px;
                background: transparent;
                margin: 0px 0px 0px 0px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {"rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.14)"};
                min-height: 28px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {"rgba(255, 255, 255, 0.35)" if is_dark else "rgba(0, 0, 0, 0.30)"};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
                border: none;
            }}
        """
        self.scroll_area.verticalScrollBar().setStyleSheet(scrollbar_style)

        # Update cards
        for i in range(self.cards_grid.count()):
            item = self.cards_grid.itemAt(i)
            if item and item.widget() and hasattr(item.widget(), "update_theme_styles"):
                item.widget().update_theme_styles()
