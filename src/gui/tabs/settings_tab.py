from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QScrollArea, QFrame, QLineEdit, QPushButton,
                             QCheckBox, QSlider, QGridLayout, QFormLayout, QGroupBox,
                             QStackedWidget, QStyledItemDelegate, QButtonGroup, QSizePolicy,
                             QMenu, QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QBoxLayout)
from PySide6.QtCore import (Qt, QSize, QRect, QRectF, QPoint, QPointF, Property,
                            QPropertyAnimation, QEasingCurve, Signal, QByteArray,
                            QParallelAnimationGroup, QEvent)
from PySide6.QtGui import (QDragEnterEvent, QDropEvent, QPainter, QColor, QPen,
                           QBrush, QPixmap, QImage, QPainterPath, QLinearGradient, QFont,
                           QFontMetrics, QAction, QMouseEvent, QIcon)
from src.utils.voxel_icons import category_icon, profile_icon, block_icon
import os
from src import constants as c
from src.core import language_manager
from src.utils.dialogs import ask_open_filename_native, ask_directory_native
from src.utils.resource_path import resource_path
from src.utils.logger import logger
from src.utils.colors import blend_colors, hex_to_rgba
from src.utils.process_utils import open_folder, open_path
from PySide6.QtSvg import QSvgRenderer


_SVG_GENERAL = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="3"/>
  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
</svg>"""

_SVG_LAUNCH = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/>
  <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/>
  <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/>
  <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>
</svg>"""

_SVG_APPEARANCE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="13.5" cy="6.5" r=".7" fill="{color}"/>
  <circle cx="17.5" cy="10.5" r=".7" fill="{color}"/>
  <circle cx="8.5" cy="7.5" r=".7" fill="{color}"/>
  <circle cx="6.5" cy="12.5" r=".7" fill="{color}"/>
  <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>
</svg>"""


class LiquidGlassMenuItem(QPushButton):
    """
    Pill navigation item adhering to the liquid glass menu specification:
    - Displays unicolor SVG icon on top and category name underneath
    - Inactive: unicolor white (dark mode) or slate (light mode)
    - Hover: soft white illumination and specular inset highlight
    - Active: liquid pill highlight with accent tinted text & icon
    - Press: tactile scale compression animation
    """
    def __init__(self, key, label_key, svg_template, parent=None, app=None):
        super().__init__(parent)
        self.key = key
        self.label_key = label_key
        self.label_text = ""
        self.svg_template = svg_template
        self.app = app
        self._is_active = False
        self._hover_factor = 0.0
        self._sink_factor = 0.0
        self._renderer_cache = {}

        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._hover_anim = QPropertyAnimation(self, b"hoverFactor", self)
        self._hover_anim.setDuration(160)
        self._hover_anim.setEasingCurve(QEasingCurve.OutQuad)

        self._sink_anim = QPropertyAnimation(self, b"sinkFactor", self)
        self._sink_anim.setDuration(120)
        self._sink_anim.setEasingCurve(QEasingCurve.InOutQuad)

    def _get_hover_factor(self):
        return self._hover_factor

    def _set_hover_factor(self, val):
        self._hover_factor = float(val)
        self.update()

    hoverFactor = Property(float, _get_hover_factor, _set_hover_factor)

    def _get_sink_factor(self):
        return self._sink_factor

    def _set_sink_factor(self, val):
        self._sink_factor = float(val)
        self.update()

    sinkFactor = Property(float, _get_sink_factor, _set_sink_factor)

    def set_active(self, active):
        self._is_active = bool(active)
        self.update()

    def setChecked(self, val):
        self.set_active(val)

    def isChecked(self):
        return self._is_active

    def setText(self, text):
        self.label_text = text
        self.update()

    def text(self):
        return self._get_label_text()

    def _get_label_text(self):
        if self.label_text:
            return self.label_text
        val = c.t(self.label_key)
        if not val or val == self.label_key or val.startswith("!"):
            return {"general": "General", "launch": "Lanzamiento", "appearance": "Apariencia"}.get(self.key, self.key.capitalize())
        return val

    def sizeHint(self):
        fm = QFontMetrics(QFont("Segoe UI", 9, QFont.Bold))
        text_w = fm.horizontalAdvance(self._get_label_text())
        w = max(124, text_w + 40)
        return QSize(w, 50)

    def minimumSizeHint(self):
        return self.sizeHint()

    def setProperty(self, prop, val):
        if prop == "active":
            self.set_active(val)
        super().setProperty(prop, val)

    def style(self):
        return self

    def unpolish(self, w):
        pass

    def polish(self, w):
        pass

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

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._sink_anim.stop()
            self._sink_anim.setStartValue(self._sink_factor)
            self._sink_anim.setEndValue(1.0)
            self._sink_anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._sink_anim.stop()
        self._sink_anim.setStartValue(self._sink_factor)
        self._sink_anim.setEndValue(0.0)
        self._sink_anim.start()
        super().mouseReleaseEvent(event)

    def _render_svg_icon(self, painter, rect, color_hex):
        if color_hex not in self._renderer_cache:
            raw = self.svg_template.replace("{color}", color_hex)
            self._renderer_cache[color_hex] = QSvgRenderer(QByteArray(raw.encode("utf-8")))
        self._renderer_cache[color_hex].render(painter, rect)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        w = float(self.width())
        h = float(self.height())
        radius = h / 2.0

        if self._sink_factor > 0.001:
            p.save()
            scale = 1.0 - 0.03 * self._sink_factor
            p.translate(w / 2.0, h / 2.0)
            p.scale(scale, scale)
            p.translate(-w / 2.0, -h / 2.0)

        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        accent_hex = getattr(self.app, "current_accent_color", "#007aff") if self.app else "#007aff"

        if self._is_active:
            text_col = QColor(accent_hex)
            icon_col_hex = accent_hex
        elif self._hover_factor > 0.01:
            alpha = int(75 * self._hover_factor)
            bg_col = QColor(255, 255, 255, alpha) if is_dark else QColor(255, 255, 255, int(150 * self._hover_factor))
            p.setBrush(bg_col)
            p.setPen(QPen(QColor(255, 255, 255, int(110 * self._hover_factor)), 1.0))
            p.drawRoundedRect(rect, radius, radius)
            text_col = QColor("#ffffff" if is_dark else "#0f172a")
            icon_col_hex = "#ffffff" if is_dark else "#0f172a"
        else:
            text_col = QColor(255, 255, 255, 230) if is_dark else QColor(51, 65, 85, 230)
            icon_col_hex = "#ffffff" if is_dark else "#334155"

        icon_size = 19.0
        ix = (w - icon_size) / 2.0
        iy = 5.0
        self._render_svg_icon(p, QRectF(ix, iy, icon_size, icon_size), icon_col_hex)

        font = QFont("Segoe UI", 9)
        font.setBold(True)
        p.setFont(font)
        p.setPen(text_col)
        text_rect = QRectF(2.0, iy + icon_size + 2.0, w - 4.0, 17.0)
        p.drawText(text_rect, Qt.AlignCenter, self._get_label_text())

        if self._sink_factor > 0.001:
            p.restore()

        p.end()


class LiquidGlassBottomMenu(QFrame):
    """
    Bottom menu widget replicating the liquid glass design:
    - Width max ~520px, height 58px, pill shape (border-radius: 99rem)
    - Liquid glass styling with theme accent tint, border, and specular top shine
    - 3 unicolor navigation items (General, Lanzamiento, Apariencia)
    - Smooth sliding indicator pill gliding across items without disappearing
    """
    categoryChanged = Signal(str)

    ITEMS = [
        ("general", "UI_CATEGORY_GENERAL", _SVG_GENERAL),
        ("launch", "UI_CATEGORY_LAUNCH", _SVG_LAUNCH),
        ("appearance", "UI_CATEGORY_APPEARANCE", _SVG_APPEARANCE),
    ]

    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.setObjectName("LiquidGlassBottomMenu")
        self.setFixedHeight(60)
        self.setMinimumWidth(410)
        self.setMaximumWidth(470)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self._active_cat = "general"
        self._items = {}
        self.buttons = {}
        self._indicator_rect = QRectF()

        self._slide_anim = QPropertyAnimation(self, b"indicatorRect", self)
        self._slide_anim.setDuration(220)
        self._slide_anim.setEasingCurve(QEasingCurve.OutCubic)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 5, 7, 5)
        layout.setSpacing(7)

        for key, label_key, svg in self.ITEMS:
            item = LiquidGlassMenuItem(key, label_key, svg, parent=self, app=self.app)
            item.clicked.connect(lambda checked=False, k=key: self.set_active_category(k, notify=True))
            layout.addWidget(item)
            self._items[key] = item
            self.buttons[key] = item

        self._items["general"].set_active(True)

    def _get_indicator_rect(self):
        return self._indicator_rect

    def _set_indicator_rect(self, rect):
        self._indicator_rect = rect
        self.update()

    indicatorRect = Property(QRectF, _get_indicator_rect, _set_indicator_rect)

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_indicator()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_indicator()

    def _sync_indicator(self):
        if self._active_cat in self._items:
            it = self._items[self._active_cat]
            geom = it.geometry()
            if geom.width() > 0:
                self._indicator_rect = QRectF(geom)
                self.update()

    def set_active_category(self, key, notify=False):
        if key not in self._items:
            return
        self._active_cat = key
        for k, it in self._items.items():
            it.set_active(k == key)

        target_item = self._items[key]
        target_rect = QRectF(target_item.geometry())

        if self._indicator_rect.isEmpty() or not self.isVisible() or target_rect.width() <= 0:
            self._indicator_rect = target_rect
            self.update()
        else:
            self._slide_anim.stop()
            self._slide_anim.setStartValue(self._indicator_rect)
            self._slide_anim.setEndValue(target_rect)
            self._slide_anim.start()

        if notify:
            self.categoryChanged.emit(key)

    def sizeHint(self):
        w = 14
        for it in self._items.values():
            w += it.sizeHint().width()
        w += max(0, len(self._items) - 1) * 7
        return QSize(max(410, min(w, 470)), 60)

    def minimumSizeHint(self):
        return QSize(410, 60)

    def retranslate_ui(self):
        for it in self._items.values():
            it.updateGeometry()
            it.update()
        self.updateGeometry()
        self._sync_indicator()
        self.update()

    def update_styles(self):
        for it in self._items.values():
            it.update()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing, True)

            w = float(self.width())
            h = float(self.height())
            rect = QRectF(1.0, 1.0, w - 2.0, h - 2.0)
            radius = rect.height() / 2.0

            is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
            accent_hex = getattr(self.app, "current_accent_color", "#007aff") if self.app else "#007aff"
            ac = QColor(accent_hex)
            ar, ag, ab = ac.red(), ac.green(), ac.blue()

            if is_dark:
                bg_col = QColor(ar, ag, ab, 96)
                border_col = QColor(255, 255, 255, 60)
                inner_highlight = QColor(255, 255, 255, 95)
            else:
                bg_col = QColor(ar, ag, ab, 45)
                border_col = QColor(ar, ag, ab, 75)
                inner_highlight = QColor(255, 255, 255, 190)

            p.setBrush(bg_col)
            p.setPen(QPen(border_col, 1.2))
            p.drawRoundedRect(rect, radius, radius)

            # Inset specular top shine (matching CSS ::after)
            top_arc = QRectF(rect.x() + 2.0, rect.y() + 1.5, rect.width() - 4.0, rect.height() - 3.0)
            arc_path = QPainterPath()
            arc_path.addRoundedRect(top_arc, radius - 1.0, radius - 1.0)

            grad_shine = QLinearGradient(0, 0, 0, h / 2.0)
            grad_shine.setColorAt(0.0, inner_highlight)
            grad_shine.setColorAt(0.6, QColor(255, 255, 255, 25 if is_dark else 60))
            grad_shine.setColorAt(1.0, QColor(255, 255, 255, 0))

            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(grad_shine, 1.2))
            p.drawPath(arc_path)

            # Sliding active indicator pill
            if not self._indicator_rect.isEmpty() and self._indicator_rect.width() > 0:
                pill_rect = QRectF(self._indicator_rect.x() + 0.5, self._indicator_rect.y() + 0.5,
                                   self._indicator_rect.width() - 1.0, self._indicator_rect.height() - 1.0)
                pill_r = pill_rect.height() / 2.0
                pill_bg = QColor(237, 237, 237, 185) if is_dark else QColor(255, 255, 255, 240)
                pill_pen = QPen(QColor(255, 255, 255, 160) if is_dark else QColor(0, 0, 0, 25), 1.0)
                p.setBrush(pill_bg)
                p.setPen(pill_pen)
                p.drawRoundedRect(pill_rect, pill_r, pill_r)
        finally:
            p.end()


class SlidingStackedWidget(QStackedWidget):
    """
    QStackedWidget with smooth horizontal slide and cross-fade transition
    between category pages.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._prev_index = -1
        self._anim_group = None
        self._anim_effect = None
        self._anim_target = None
        self.currentChanged.connect(self._on_current_changed)

    def _on_current_changed(self, index):
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
        anim_fade.setDuration(220)
        anim_fade.setStartValue(0.0)
        anim_fade.setEndValue(1.0)
        anim_fade.setEasingCurve(QEasingCurve.OutCubic)

        offset = 28 * direction
        orig_pos = current_widget.pos()
        start_pos = QPoint(orig_pos.x() + offset, orig_pos.y())
        current_widget.move(start_pos)

        anim_pos = QPropertyAnimation(current_widget, b"pos", self)
        anim_pos.setDuration(220)
        anim_pos.setStartValue(start_pos)
        anim_pos.setEndValue(orig_pos)
        anim_pos.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(anim_fade)
        self._anim_group.addAnimation(anim_pos)

        def _cleanup():
            if current_widget == self._anim_target:
                current_widget.move(orig_pos)
                try:
                    current_widget.setGraphicsEffect(None)
                except RuntimeError:
                    pass
                self._anim_effect = None
                self._anim_target = None

        self._anim_group.finished.connect(_cleanup)
        self._anim_group.start()


class UnsavedChangesFloatingCard(QFrame):
    """
    Floating pill/card alerting the user about unsaved settings changes.
    Features:
    - Pure black background with theme accent border and styling
    - Accent indicator dot and 'Cambios sin guardar' text
    - 'Cancelar' and 'Guardar configuración' action buttons
    - Lightweight, zero-lag hardware-accelerated movement
    - Tactile shake animation when user attempts blocked navigation
    - Smooth, snappy slide transitions
    """
    cancelRequested = Signal()
    saveRequested = Signal()

    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.setObjectName("UnsavedChangesFloatingCard")
        self.setFixedSize(470, 48)
        self.setAttribute(Qt.WA_Hover, True)

        self._shake_offset = 0.0
        self._slide_y_offset = 20.0
        self._is_visible_state = False
        self._is_shaking = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(10)

        self.lbl_icon = QLabel("●")
        self.lbl_icon.setObjectName("UnsavedIcon")
        layout.addWidget(self.lbl_icon, 0, Qt.AlignVCenter)

        self.lbl_text = QLabel(c.t("UI_UNSAVED_CHANGES"))
        self.lbl_text.setObjectName("UnsavedText")
        layout.addWidget(self.lbl_text, 0, Qt.AlignVCenter)

        layout.addSpacing(4)

        self.btn_cancel = QPushButton(c.t("UI_CANCEL"))
        self.btn_cancel.setObjectName("UnsavedCancelBtn")
        self.btn_cancel.setFixedHeight(32)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.cancelRequested.emit)
        layout.addWidget(self.btn_cancel, 0, Qt.AlignVCenter)

        self.btn_save = QPushButton(c.t("UI_BUTTON_SAVE_SETTINGS"))
        self.btn_save.setObjectName("UnsavedSaveBtn")
        self.btn_save.setFixedHeight(32)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self.saveRequested.emit)
        layout.addWidget(self.btn_save, 0, Qt.AlignVCenter)

        # Snappy animations without CPU drop shadow re-filtering
        self._fade_anim = QPropertyAnimation(self, b"slideYOffset", self)
        self._fade_anim.setDuration(160)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.finished.connect(self._on_fade_finished)

        self._shake_anim = QPropertyAnimation(self, b"shakeOffset", self)
        self._shake_anim.setDuration(220)
        self._shake_anim.setEasingCurve(QEasingCurve.OutQuad)
        self._shake_anim.finished.connect(self._on_shake_finished)

        self.update_styles()
        self.hide()

    def retranslate_ui(self):
        self.lbl_text.setText(c.t("UI_UNSAVED_CHANGES"))
        self.btn_cancel.setText(c.t("UI_CANCEL"))
        self.btn_save.setText(c.t("UI_BUTTON_SAVE_SETTINGS"))

    def _get_accent(self):
        if self.app and hasattr(self.app, "current_accent_color") and self.app.current_accent_color:
            return self.app.current_accent_color
        if self.app and hasattr(self.app, "config"):
            theme_name = self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
            return c.THEME_COLOR_MAP.get(theme_name, "#1f6aa5")
        return "#1f6aa5"

    def _get_shake_offset(self):
        return self._shake_offset

    def _set_shake_offset(self, val):
        self._shake_offset = float(val)
        if self.parent() and hasattr(self.parent(), "_reposition_unsaved_card"):
            self.parent()._reposition_unsaved_card()

    shakeOffset = Property(float, _get_shake_offset, _set_shake_offset)

    def _get_slide_y_offset(self):
        return self._slide_y_offset

    def _set_slide_y_offset(self, val):
        self._slide_y_offset = float(val)
        if self.parent() and hasattr(self.parent(), "_reposition_unsaved_card"):
            self.parent()._reposition_unsaved_card()

    slideYOffset = Property(float, _get_slide_y_offset, _set_slide_y_offset)

    def _on_shake_finished(self):
        self._is_shaking = False
        self.update_styles()

    def _on_fade_finished(self):
        if not self._is_visible_state:
            self.hide()

    def trigger_shake(self):
        self._shake_anim.stop()
        self._shake_anim.setKeyValues([
            (0.0, 0.0),
            (0.12, -10.0),
            (0.28, 10.0),
            (0.44, -7.0),
            (0.60, 7.0),
            (0.76, -3.0),
            (0.88, 3.0),
            (1.0, 0.0)
        ])
        self._is_shaking = True
        self.update_styles()
        self._shake_anim.start()

    def set_visible_animated(self, visible):
        if self._is_visible_state == visible:
            return
        self._is_visible_state = visible
        self._fade_anim.stop()
        if visible:
            self.update_styles()
            self.show()
            self.raise_()
            if self.parent() and hasattr(self.parent(), "_reposition_unsaved_card"):
                self.parent()._reposition_unsaved_card()
            self._fade_anim.setStartValue(self._slide_y_offset)
            self._fade_anim.setEndValue(0.0)
            self._fade_anim.start()
        else:
            self._fade_anim.setStartValue(self._slide_y_offset)
            self._fade_anim.setEndValue(25.0)
            self._fade_anim.start()

    def update_styles(self):
        accent_hex = self._get_accent()
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        # Deep black background ("asla negra")
        card_bg = "rgba(10, 11, 14, 0.98)" if is_dark else "rgba(20, 22, 28, 0.97)"

        # Border with accent color ("del color del acento")
        if self._is_shaking:
            card_border = "2px solid rgba(239, 68, 68, 0.95)"
        else:
            card_border = f"1.5px solid {hex_to_rgba(accent_hex, 0.65)}"

        self.lbl_icon.setStyleSheet(f"color: {accent_hex}; font-size: 14px; font-weight: bold; background: transparent; border: none;")

        self.setStyleSheet(f"""
            QFrame#UnsavedChangesFloatingCard {{
                background-color: {card_bg};
                border: {card_border};
                border-radius: 24px;
            }}
            QLabel#UnsavedText {{
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
            QPushButton#UnsavedCancelBtn {{
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 16px;
                color: #e2e8f0;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#UnsavedCancelBtn:hover {{
                background-color: rgba(239, 68, 68, 0.25);
                border-color: rgba(239, 68, 68, 0.60);
                color: #ffffff;
            }}
            QPushButton#UnsavedCancelBtn:pressed {{
                background-color: rgba(239, 68, 68, 0.40);
            }}
            QPushButton#UnsavedSaveBtn {{
                background-color: {accent_hex};
                border: 1px solid {accent_hex};
                border-radius: 16px;
                color: #ffffff;
                padding: 0 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton#UnsavedSaveBtn:hover {{
                background-color: {blend_colors(accent_hex, "#ffffff", 0.22)};
                border-color: {blend_colors(accent_hex, "#ffffff", 0.35)};
            }}
            QPushButton#UnsavedSaveBtn:pressed {{
                background-color: {blend_colors(accent_hex, "#000000", 0.20)};
            }}
        """)


# Alias for backward compatibility
SettingsSidebarCard = LiquidGlassBottomMenu



class ModernToggle(QCheckBox):
    """
    Smooth animated switch toggle matching modern UI standards.
    Subclasses QCheckBox for 100% API compatibility.
    """
    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(44, 24)
        self._thumb_pos = 3.0
        self._anim = QPropertyAnimation(self, b"thumbPos", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.stateChanged.connect(self._on_state_changed)

    def _get_thumb_pos(self):
        return self._thumb_pos

    def _set_thumb_pos(self, val):
        self._thumb_pos = float(val)
        self.update()

    thumbPos = Property(float, _get_thumb_pos, _set_thumb_pos)

    def _on_state_changed(self, state):
        target = float(self.width() - 21) if self.isChecked() else 3.0
        self._anim.stop()
        self._anim.setStartValue(self._thumb_pos)
        self._anim.setEndValue(target)
        self._anim.start()

    def setChecked(self, checked):
        super().setChecked(checked)
        self._thumb_pos = float(self.width() - 21) if checked else 3.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        w, h = float(self.width()), float(self.height())
        radius = h / 2.0

        accent_hex = "#22c55e"
        if self.app and hasattr(self.app, "config"):
            theme_name = self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "green")
            accent_hex = c.THEME_COLOR_MAP.get(theme_name, "#22c55e")
        accent_color = QColor(accent_hex)

        # Track background
        if self.isChecked():
            track_color = accent_color
        else:
            track_color = QColor(255, 255, 255, 38) if is_dark else QColor(0, 0, 0, 48)

        p.setBrush(track_color)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        # Thumb
        thumb_d = h - 6.0
        p.setBrush(QColor("#ffffff"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(self._thumb_pos, 3.0, thumb_d, thumb_d))
        p.end()


class SettingsHelpButton(QPushButton):
    """
    Compact circular info '?' button with explicit sizing and borders,
    immune to global QPushButton styles.
    """
    def __init__(self, tooltip_title="", tooltip_text="", parent=None, app=None):
        super().__init__("?", parent)
        self.app = app
        self._tooltip_title = tooltip_title
        self._tooltip_text = tooltip_text
        self.setObjectName("SettingsHelpCircle")
        self.setFixedSize(20, 20)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self._show_info)
        self.update_styles()

    def _show_info(self):
        if self.app:
            self.app.show_info(self._tooltip_title, self._tooltip_text)

    def update_info(self, tooltip_title, tooltip_text):
        self._tooltip_title = tooltip_title
        self._tooltip_text = tooltip_text

    def update_styles(self):
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        self.setStyleSheet(f"""
            QPushButton#SettingsHelpCircle {{
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                padding: 0px;
                margin: 0px;
                border-radius: 10px;
                background-color: {'rgba(255, 255, 255, 0.08)' if is_dark else 'rgba(0, 0, 0, 0.06)'};
                color: {'#94a3b8' if is_dark else '#475569'};
                font-weight: bold;
                font-size: 11px;
                border: 1px solid {'rgba(255, 255, 255, 0.16)' if is_dark else 'rgba(0, 0, 0, 0.14)'};
            }}
            QPushButton#SettingsHelpCircle:hover {{
                background-color: {'rgba(255, 255, 255, 0.20)' if is_dark else 'rgba(0, 0, 0, 0.12)'};
                color: {'#ffffff' if is_dark else '#0f172a'};
                border-color: {'rgba(255, 255, 255, 0.32)' if is_dark else 'rgba(0, 0, 0, 0.24)'};
            }}
        """)


class SleekComboBoxPopup(QWidget):
    """Floating animated dropdown menu matching launcher's sleek popup aesthetics."""
    itemSelected = Signal(int)

    def __init__(self, items, current_index=-1, app=None, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.app = app
        self._items = items
        self._current_index = current_index

        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(0)

        self.container = QFrame(self)
        self.container.setObjectName("SleekPopupContainer")
        bg_col = "#16181c" if is_dark else "#ffffff"
        border_col = "rgba(255, 255, 255, 0.18)" if is_dark else "rgba(0, 0, 0, 0.15)"
        self.container.setStyleSheet(f"""
            QFrame#SleekPopupContainer {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-radius: 10px;
            }}
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(6, 6, 6, 6)
        container_layout.setSpacing(3)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.verticalScrollBar().setStyleSheet(f"""
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {'rgba(255, 255, 255, 0.25)' if is_dark else 'rgba(0, 0, 0, 0.25)'};
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        items_layout = QVBoxLayout(scroll_content)
        items_layout.setContentsMargins(2, 2, 2, 2)
        items_layout.setSpacing(3)

        for idx, itm in enumerate(items):
            text = itm.get("text", "")
            icon = itm.get("icon", None)
            btn = QPushButton(text)
            if icon and isinstance(icon, QIcon) and not icon.isNull():
                btn.setIcon(icon)
                btn.setIconSize(QSize(16, 16))
            btn.setFixedHeight(34)
            btn.setCursor(Qt.PointingHandCursor)
            is_active = (idx == current_index)

            active_bg = blend_colors("#1e293b", accent, 0.20) if is_dark else blend_colors("#e2e8f0", accent, 0.16)
            hover_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.05)"
            text_color = "#ffffff" if is_dark else "#0f172a"
            active_color = accent if is_active else text_color

            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {active_bg if is_active else 'transparent'};
                    color: {active_color};
                    border: none;
                    border-radius: 6px;
                    text-align: left;
                    padding-left: 12px;
                    font-size: 13px;
                    font-weight: {'bold' if is_active else '500'};
                }}
                QPushButton:hover {{
                    background-color: {hover_bg};
                    color: {accent};
                }}
            """)
            def make_handler(i=idx):
                return lambda: self._on_select(i)
            btn.clicked.connect(make_handler(idx))
            items_layout.addWidget(btn)

        scroll.setWidget(scroll_content)

        max_visible = 6
        item_h = 37
        content_h = len(items) * item_h + 16
        if len(items) > max_visible:
            scroll.setFixedHeight(max_visible * item_h)
        else:
            scroll.setFixedHeight(content_h)

        container_layout.addWidget(scroll)
        main_layout.addWidget(self.container)

    def _on_select(self, idx):
        self.itemSelected.emit(idx)
        self.close()

    def show_below(self, target_widget):
        p = target_widget.mapToGlobal(QPoint(0, target_widget.height() + 4))
        self.setMinimumWidth(max(target_widget.width(), 220))
        self.adjustSize()
        self.move(p.x(), p.y())
        self.show()


class SleekComboTrigger(QPushButton):
    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self._text = ""
        self._icon = None
        self.setFixedHeight(38)
        self.setMinimumWidth(220)
        self.setCursor(Qt.PointingHandCursor)

    def set_display(self, text, icon=None):
        self._text = text
        self._icon = icon
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        w, h = float(self.width()), float(self.height())
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)

        is_hover = self.underMouse() and self.isEnabled()
        if is_dark:
            bg_col = QColor(255, 255, 255, 22 if is_hover else 12)
            border_col = QColor(accent) if is_hover else QColor(255, 255, 255, 28)
            text_col = QColor("#ffffff")
        else:
            bg_col = QColor(0, 0, 0, 18 if is_hover else 10)
            border_col = QColor(accent) if is_hover else QColor(0, 0, 0, 24)
            text_col = QColor("#0f172a")

        if not self.isEnabled():
            bg_col = QColor(255, 255, 255, 6) if is_dark else QColor(0, 0, 0, 6)
            border_col = QColor(255, 255, 255, 14) if is_dark else QColor(0, 0, 0, 14)
            text_col = QColor("#64748b") if is_dark else QColor("#94a3b8")

        painter.setBrush(bg_col)
        painter.setPen(QPen(border_col, 1.0))
        painter.drawRoundedRect(rect, 8.0, 8.0)

        # Icon if present
        text_x = 14
        if self._icon and isinstance(self._icon, QIcon) and not self._icon.isNull():
            pix = self._icon.pixmap(18, 18)
            painter.drawPixmap(14, int((h - 18) / 2), pix)
            text_x = 38

        # Text
        font = painter.font()
        font.setPointSize(10)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(text_col)
        text_rect = QRect(text_x, 0, int(w - text_x - 30), int(h))
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self._text)

        # Right arrow
        painter.setPen(QColor(accent if self.isEnabled() else ("#64748b" if is_dark else "#94a3b8")))
        painter.drawText(QRect(int(w - 26), 0, 18, int(h)), Qt.AlignVCenter | Qt.AlignCenter, "▼")
        painter.end()


class SleekComboBox(QWidget):
    """
    Modern sleek dropdown replacing default QComboBox with custom floating popup,
    hover highlights, rounded borders, and 100% duck-typed QComboBox API.
    """
    currentIndexChanged = Signal(int)
    currentTextChanged = Signal(str)
    activated = Signal(int)

    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self._items = []
        self._current_index = -1
        self._popup = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.trigger = SleekComboTrigger(self, app=self.app)
        self.trigger.clicked.connect(self._open_popup)
        layout.addWidget(self.trigger)

    def _open_popup(self):
        if not self._items or not self.isEnabled():
            return
        self._popup = SleekComboBoxPopup(self._items, self._current_index, app=self.app, parent=self)
        self._popup.itemSelected.connect(self.setCurrentIndex)
        self._popup.show_below(self.trigger)

    def _update_trigger(self):
        if 0 <= self._current_index < len(self._items):
            itm = self._items[self._current_index]
            self.trigger.set_display(itm["text"], itm["icon"])
        else:
            self.trigger.set_display("", None)

    def addItem(self, *args):
        if len(args) == 1:
            self._items.append({"text": str(args[0]), "data": args[0], "icon": None})
        elif len(args) == 2:
            if isinstance(args[0], (QIcon, QPixmap)):
                icon = args[0] if isinstance(args[0], QIcon) else QIcon(args[0])
                self._items.append({"text": str(args[1]), "data": args[1], "icon": icon})
            else:
                self._items.append({"text": str(args[0]), "data": args[1], "icon": None})
        elif len(args) >= 3:
            icon = args[0] if isinstance(args[0], QIcon) else QIcon(args[0])
            self._items.append({"text": str(args[1]), "data": args[2], "icon": icon})

        if len(self._items) == 1 and self._current_index == -1:
            self.setCurrentIndex(0)
        else:
            self._update_trigger()

    def addItems(self, texts):
        for t in texts:
            self.addItem(t)

    def clear(self):
        self._items.clear()
        self._current_index = -1
        self._update_trigger()

    def count(self):
        return len(self._items)

    def currentIndex(self):
        return self._current_index

    def setCurrentIndex(self, idx):
        if 0 <= idx < len(self._items):
            old = self._current_index
            self._current_index = idx
            self._update_trigger()
            if not self.signalsBlocked():
                self.currentIndexChanged.emit(idx)
                self.currentTextChanged.emit(self._items[idx]["text"])
                self.activated.emit(idx)
        elif idx == -1:
            self._current_index = -1
            self._update_trigger()

    def currentText(self):
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index]["text"]
        return ""

    def currentData(self):
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index]["data"]
        return None

    def setCurrentText(self, text):
        for idx, itm in enumerate(self._items):
            if itm["text"] == text:
                self.setCurrentIndex(idx)
                return

    def findData(self, data):
        for idx, itm in enumerate(self._items):
            if str(itm["data"]) == str(data):
                return idx
        return -1

    def findText(self, text):
        for idx, itm in enumerate(self._items):
            if itm["text"] == text:
                return idx
        return -1

    def setItemText(self, idx, text):
        if 0 <= idx < len(self._items):
            self._items[idx]["text"] = text
            if idx == self._current_index:
                self._update_trigger()

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self.trigger.setEnabled(enabled)

    def setToolTip(self, tip):
        super().setToolTip(tip)
        self.trigger.setToolTip(tip)

    def setMinimumWidth(self, w):
        super().setMinimumWidth(w)
        self.trigger.setMinimumWidth(w)

    def setSizeAdjustPolicy(self, policy):
        pass

    def update_styles(self):
        self.trigger.update()


class NotchedModeSelector(QWidget):
    """
    Custom notched / tabbed dropdown selector matching the user's mockup:
    ┌─ Modo de Binarios ─┐
    │                    └─────────────────┐
    │ Personalizado                       ▼ │
    └──────────────────────────────────────┘
    """
    currentIndexChanged = Signal(int)
    currentTextChanged = Signal(str)

    def __init__(self, tab_title="Modo de Binarios", parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self._tab_title = tab_title
        self._items = []  # list of (text, data)
        self._current_index = 0
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)
        self.setMinimumWidth(145)

        self._hover_opacity = 0.0
        self._hover_anim = QPropertyAnimation(self, b"hoverOpacity", self)
        self._hover_anim.setDuration(150)
        self._hover_anim.setEasingCurve(QEasingCurve.OutQuad)

    def _get_hover_opacity(self):
        return self._hover_opacity

    def _set_hover_opacity(self, val):
        self._hover_opacity = float(val)
        self.update()

    hoverOpacity = Property(float, _get_hover_opacity, _set_hover_opacity)

    def enterEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_opacity)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_opacity)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def addItem(self, text, data=None):
        self._items.append((text, data))
        self.update()

    def clear(self):
        self._items.clear()
        self._current_index = 0
        self.update()

    def count(self):
        return len(self._items)

    def currentText(self):
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index][0]
        return ""

    def currentData(self):
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index][1]
        return None

    def currentIndex(self):
        return self._current_index

    def setCurrentIndex(self, idx):
        if 0 <= idx < len(self._items) and idx != self._current_index:
            self._current_index = idx
            self.currentIndexChanged.emit(idx)
            self.currentTextChanged.emit(self.currentText())
            self.update()

    def findData(self, data):
        for i, (_, d) in enumerate(self._items):
            if d == data:
                return i
        return -1

    def setTabTitle(self, title):
        self._tab_title = title
        self.update()

    def update_styles(self):
        self.update()

    def setSizeAdjustPolicy(self, policy):
        pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.show_popup()
        super().mousePressEvent(event)

    def show_popup(self):
        if not self._items:
            return
        menu = QMenu(self)
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        menu_bg = "#1e2430" if is_dark else "#ffffff"
        menu_text = "#f8fafc" if is_dark else "#0f172a"
        menu_border = "#334155" if is_dark else "#cbd5e1"
        menu_hover = "#2a3447" if is_dark else "#f1f5f9"
        accent = getattr(self.app, "current_accent_color", "#38bdf8") if self.app else "#38bdf8"

        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {menu_bg};
                color: {menu_text};
                border: 1px solid {menu_border};
                border-radius: 8px;
                padding: 4px;
                min-width: {self.width()}px;
            }}
            QMenu::item {{
                padding: 7px 16px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
            }}
            QMenu::item:selected {{
                background-color: {menu_hover};
                color: {accent};
            }}
        """)

        for i, (text, data) in enumerate(self._items):
            prefix = "✓  " if i == self._current_index else "    "
            act = QAction(f"{prefix}{text}", self)
            act.triggered.connect(lambda checked=False, idx=i: self.setCurrentIndex(idx))
            menu.addAction(act)

        menu.exec(self.mapToGlobal(QPoint(0, self.height() + 3)))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        r = 6.0         # corner radius
        tab_h = 15.0    # height of top notch tab

        fm_tab = QFontMetrics(QFont(self.font().family(), 8))
        text_w = fm_tab.horizontalAdvance(self._tab_title)
        tab_w = max(80.0, text_w + 14.0)
        tab_w = min(tab_w, w - 22.0)

        # Build Notched Outline Path matching image 2
        path = QPainterPath()
        path.moveTo(0.5, r)
        path.quadTo(0.5, 0.5, r, 0.5)
        path.lineTo(tab_w - r, 0.5)
        path.quadTo(tab_w, 0.5, tab_w, r)
        path.lineTo(tab_w, tab_h - r)
        path.quadTo(tab_w, tab_h, tab_w + r, tab_h)
        path.lineTo(w - r, tab_h)
        path.quadTo(w - 0.5, tab_h, w - 0.5, tab_h + r)
        path.lineTo(w - 0.5, h - r)
        path.quadTo(w - 0.5, h - 0.5, w - r, h - 0.5)
        path.lineTo(r, h - 0.5)
        path.quadTo(0.5, h - 0.5, 0.5, h - r)
        path.lineTo(0.5, r)
        path.closeSubpath()

        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        if is_dark:
            bg_alpha = int(14 + 14 * self._hover_opacity)
            border_alpha = int(32 + 30 * self._hover_opacity)
            bg_color = QColor(255, 255, 255, bg_alpha)
            border_color = QColor(255, 255, 255, border_alpha) if self._hover_opacity < 0.2 else QColor(56, 189, 248, int(100 + 100 * self._hover_opacity))
            tab_text_color = QColor("#94a3b8")
            main_text_color = QColor("#ffffff")
            arrow_color = QColor("#cbd5e1")
        else:
            bg_alpha = int(14 + 16 * self._hover_opacity)
            border_alpha = int(45 + 35 * self._hover_opacity)
            bg_color = QColor(0, 0, 0, bg_alpha)
            border_color = QColor(0, 0, 0, border_alpha) if self._hover_opacity < 0.2 else QColor(2, 132, 199, int(120 + 100 * self._hover_opacity))
            tab_text_color = QColor("#64748b")
            main_text_color = QColor("#0f172a")
            arrow_color = QColor("#475569")

        p.setBrush(bg_color)
        p.setPen(QPen(border_color, 1.2))
        p.drawPath(path)

        f_tab = QFont(self.font().family(), 8, QFont.Medium)
        p.setFont(f_tab)
        p.setPen(tab_text_color)
        tab_rect = QRectF(8.0, 1.0, tab_w - 10.0, tab_h - 1.0)
        p.drawText(tab_rect, Qt.AlignVCenter | Qt.AlignLeft, self._tab_title)

        f_main = QFont(self.font().family(), 10, QFont.Bold)
        p.setFont(f_main)
        p.setPen(main_text_color)
        body_rect = QRectF(10.0, tab_h, w - 28.0, h - tab_h)
        p.drawText(body_rect, Qt.AlignVCenter | Qt.AlignLeft, self.currentText())

        p.setPen(QPen(arrow_color, 1.4))
        arrow_cx = w - 14.0
        arrow_cy = tab_h + (h - tab_h) / 2.0
        arrow_path = QPainterPath()
        arrow_path.moveTo(arrow_cx - 3.5, arrow_cy - 1.8)
        arrow_path.lineTo(arrow_cx, arrow_cy + 2.0)
        arrow_path.lineTo(arrow_cx + 3.5, arrow_cy - 1.8)
        p.drawPath(arrow_path)


class ComicColorSwatch(QPushButton):
    """Individual color button with thick comic border and hard drop shadow."""
    hovered = Signal(str, str)
    unhovered = Signal()

    def __init__(self, key, name, hex_color, parent=None):
        super().__init__(parent)
        self.key = key
        self.name = name
        self.hex_color = hex_color
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(62, 64)
        self.setToolTip(f"{name} ({hex_color})")

    def enterEvent(self, event):
        self.hovered.emit(self.name, self.hex_color)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.unhovered.emit()
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        is_hover = self.underMouse()
        is_checked = self.isChecked()
        is_pressed = self.isDown()

        w, h = 50.0, 52.0
        r = 8.0

        if is_pressed or is_checked:
            ox, oy = 7.0, 7.0
            s_dist = 2.0
        elif is_hover:
            ox, oy = 2.0, 2.0
            s_dist = 7.0
        else:
            ox, oy = 5.0, 5.0
            s_dist = 5.0

        # Hard comic drop shadow (box-shadow: 4px 4px 0 0 #000)
        p.setBrush(QColor("#000000"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(ox + s_dist, oy + s_dist, w, h), r, r)

        # Swatch body (background-color: var(--color); border: 3px solid #000)
        p.setBrush(QColor(self.hex_color))
        p.setPen(QPen(QColor("#000000"), 3.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawRoundedRect(QRectF(ox, oy, w, h), r, r)

        # Checked state indicator (crisp comic white checkmark)
        if is_checked:
            p.setPen(QPen(QColor("#ffffff"), 3.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            cx = ox + w / 2.0
            cy = oy + h / 2.0
            p.drawLine(QPointF(cx - 8, cy), QPointF(cx - 2, cy + 5.5))
            p.drawLine(QPointF(cx - 2, cy + 5.5), QPointF(cx + 8, cy - 5.5))

        p.end()


class ComicColorPanel(QFrame):
    """
    Comic panel card container replicating Uiverse.io chase2k25 design:
    .comic-panel {
      background: #ffffff;
      border: 4px solid #000;
      padding: 1.2rem;
      border-radius: 8px;
      box-shadow: 4px 4px 0px rgba(0, 0, 0, 1);
    }
    """
    themeSelected = Signal(str)

    def __init__(self, selected_key="blue", is_dark=True, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.is_dark = is_dark
        self.setObjectName("ComicColorPanel")
        self.setContentsMargins(0, 0, 0, 0)

        main_v = QVBoxLayout(self)
        main_v.setContentsMargins(14, 10, 14, 10)
        main_v.setSpacing(10)

        # Header row: Title + Comic speech badge
        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 4, 0)

        self.lbl_title = QLabel(c.t("UI_LABEL_COLOR_THEME").rstrip(":").upper())
        self.lbl_title.setObjectName("ComicPanelTitle")
        header.addWidget(self.lbl_title)
        header.addStretch()

        self.badge = QLabel()
        self.badge.setObjectName("ComicSpeechBadge")
        header.addWidget(self.badge)
        main_v.addLayout(header)

        # Centered container for swatches
        center_h = QHBoxLayout()
        center_h.addStretch()
        grid = QGridLayout()
        grid.setContentsMargins(0, 4, 0, 2)
        grid.setSpacing(14)
        self.swatches = []

        theme_names = c.t("UI_THEME_NAMES")
        for i, (k, hex_c) in enumerate(c.THEME_COLOR_MAP.items()):
            name = theme_names.get(k, k.capitalize())
            sw = ComicColorSwatch(k, name, hex_c, self)
            if k == selected_key:
                sw.setChecked(True)
                self.badge.setText(f"{name} • {hex_c}")
            sw.hovered.connect(lambda n, h: self.badge.setText(f"{n} • {h}"))
            sw.unhovered.connect(self._reset_badge)
            sw.clicked.connect(lambda checked=False, k=k, n=name, h=hex_c: self._on_select(k, n, h))
            grid.addWidget(sw, i // 6, i % 6)
            self.swatches.append(sw)

        center_h.addLayout(grid)
        center_h.addStretch()
        main_v.addLayout(center_h)
        self.update_styles(is_dark)

    def update_styles(self, is_dark):
        self.is_dark = is_dark
        self.bg_color = "#181b24" if is_dark else "#ffffff"
        title_col = "#f8fafc" if is_dark else "#0f172a"
        self.lbl_title.setStyleSheet(f"background: transparent; font-weight: 900; font-size: 13px; color: {title_col}; letter-spacing: 0.8px;")
        self.badge.setStyleSheet("""
            QLabel#ComicSpeechBadge {
                background-color: #fef3c7;
                color: #000000;
                border: 2.5px solid #000000;
                border-radius: 6px;
                padding: 4px 12px;
                font-weight: 800;
                font-size: 12px;
            }
        """)
        self._reset_badge()
        self.update()

    def _on_select(self, key, name, hex_c):
        for s in self.swatches:
            s.setChecked(s.key == key)
        self.badge.setText(f"{name} • {hex_c}")
        self.themeSelected.emit(key)

    def _reset_badge(self):
        for s in self.swatches:
            if s.isChecked():
                self.badge.setText(f"{s.name} • {s.hex_color}")
                return

    def setSelectedTheme(self, key):
        for s in self.swatches:
            if s.key == key:
                s.setChecked(True)
                self.badge.setText(f"{s.name} • {s.hex_color}")
            else:
                s.setChecked(False)

    def retranslate(self):
        theme_names = c.t("UI_THEME_NAMES")
        self.lbl_title.setText(c.t("UI_LABEL_COLOR_THEME").rstrip(":").upper())
        for s in self.swatches:
            s.name = theme_names.get(s.key, s.key.capitalize())
            s.setToolTip(f"{s.name} ({s.hex_color})")
        self._reset_badge()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = float(self.width()), float(self.height())
        r = 10.0

        # Hard comic shadow (box-shadow: 4px 4px 0px rgba(0, 0, 0, 1))
        p.setBrush(QColor("#000000"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(4.0, 4.0, w - 5.0, h - 5.0), r, r)

        # Panel body (background: #ffffff / #181b24, border: 3.5px solid #000)
        p.setBrush(QColor(self.bg_color))
        p.setPen(QPen(QColor("#000000"), 3.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 5.0, h - 5.0), r, r)
        p.end()
        super().paintEvent(event)


class SettingsOptionCard(QFrame):
    """
    Horizontal card container for settings with neutral base background,
    soft illumination on hover, monochrome icon badge on the left,
    title/subtitle, and controls on the right.
    """
    def __init__(self, icon_path=None, title="", subtitle="", warning_note="", parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.setObjectName("SettingsOptionCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumHeight(96)
        self._icon_path = icon_path

        self._hover_opacity = 0.0
        self._hover_anim = QPropertyAnimation(self, b"hoverOpacity", self)
        self._hover_anim.setDuration(160)
        self._hover_anim.setEasingCurve(QEasingCurve.OutQuad)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(20, 14, 20, 14)
        self._main_layout.setSpacing(6)

        # Top row: [Badge + Texts] ... [Control Widget]
        self.top_row = QHBoxLayout()
        self.top_row.setContentsMargins(0, 0, 0, 0)
        self.top_row.setSpacing(14)
        self._main_layout.addLayout(self.top_row)

        # 1. Left badge (monochrome icon inside subtle rounded square)
        if icon_path and os.path.exists(icon_path):
            self.badge = QLabel()
            self.badge.setFixedSize(46, 46)
            self.badge.setAlignment(Qt.AlignCenter)
            self.badge.setObjectName("SettingsCardIconBadge")
            self.top_row.addWidget(self.badge, 0, Qt.AlignVCenter)
        else:
            self.badge = None

        # 2. Texts column
        self.text_layout = QVBoxLayout()
        self.text_layout.setContentsMargins(0, 0, 0, 0)
        self.text_layout.setSpacing(3)
        self.text_layout.setAlignment(Qt.AlignVCenter)

        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("SettingsCardTitle")
        self.text_layout.addWidget(self.lbl_title)

        if subtitle:
            self.lbl_subtitle = QLabel(subtitle)
            self.lbl_subtitle.setObjectName("SettingsCardSubtitle")
            self.lbl_subtitle.setWordWrap(True)
            self.text_layout.addWidget(self.lbl_subtitle)
        else:
            self.lbl_subtitle = None

        if warning_note:
            self.lbl_warning = QLabel(warning_note)
            self.lbl_warning.setObjectName("SettingsCardWarning")
            self.lbl_warning.setWordWrap(True)
            self.text_layout.addWidget(self.lbl_warning)
        else:
            self.lbl_warning = None

        self.top_row.addLayout(self.text_layout, 1)

        # 3. Control container on right
        self.ctrl_layout = QHBoxLayout()
        self.ctrl_layout.setContentsMargins(0, 0, 0, 0)
        self.ctrl_layout.setSpacing(10)
        self.ctrl_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.top_row.addLayout(self.ctrl_layout, 0)

        self.update_styles()

    def update_styles(self):
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        title_color = "#ffffff" if is_dark else "#0f172a"
        sub_color = "#94a3b8" if is_dark else "#475569"

        if self.badge and self._icon_path and os.path.exists(self._icon_path):
            orig_pix = QPixmap(self._icon_path)
            if not orig_pix.isNull():
                tinted = QPixmap(orig_pix.size())
                tinted.fill(Qt.transparent)
                tp = QPainter(tinted)
                tp.drawPixmap(0, 0, orig_pix)
                tp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                tp.fillRect(tinted.rect(), QColor("#ffffff" if is_dark else "#1e293b"))
                tp.end()
                self.badge.setPixmap(tinted.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        if self.lbl_title:
            is_bin_paths = (self.lbl_title.text() == c.t("UI_LABEL_BINARY_PATHS"))
            f_size = "17px" if is_bin_paths else "16px"
            self.lbl_title.setStyleSheet(f"font-weight: bold; font-size: {f_size}; color: {title_color}; background: transparent; border: none;")
        if self.lbl_subtitle:
            self.lbl_subtitle.setStyleSheet(f"font-size: 11.5px; color: {sub_color}; background: transparent; border: none;")
        if self.lbl_warning:
            self.lbl_warning.setStyleSheet("font-size: 12px; font-weight: 500; color: #f59e0b; background: transparent; border: none;")
        self.update()

    def setTitle(self, text):
        if self.lbl_title:
            self.lbl_title.setText(text)
            self.update_styles()

    def _get_hover_opacity(self):
        return self._hover_opacity

    def _set_hover_opacity(self, val):
        self._hover_opacity = float(val)
        self.update()

    hoverOpacity = Property(float, _get_hover_opacity, _set_hover_opacity)

    def enterEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_opacity)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_opacity)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        w, h = float(self.width()), float(self.height())
        radius = 12.0
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)

        # Base background + soft hover illumination
        if is_dark:
            bg_alpha = int(10 + 14 * self._hover_opacity)
            border_alpha = int(18 + 26 * self._hover_opacity)
            bg_color = QColor(255, 255, 255, bg_alpha)
            border_color = QColor(255, 255, 255, border_alpha)
        else:
            bg_alpha = int(14 + 18 * self._hover_opacity)
            border_alpha = int(32 + 36 * self._hover_opacity)
            bg_color = QColor(0, 0, 0, bg_alpha)
            border_color = QColor(0, 0, 0, border_alpha)

        p.setBrush(bg_color)
        p.setPen(QPen(border_color, 1.0))
        p.drawRoundedRect(rect, radius, radius)

        # Badge container
        if self.badge and self.badge.isVisible():
            b_geo = self.badge.geometry()
            b_rect = QRectF(float(b_geo.x()), float(b_geo.y()), float(b_geo.width()), float(b_geo.height()))
            badge_bg = QColor(255, 255, 255, 14) if is_dark else QColor(0, 0, 0, 16)
            badge_border = QColor(255, 255, 255, 22) if is_dark else QColor(0, 0, 0, 30)
            p.setBrush(badge_bg)
            p.setPen(QPen(badge_border, 1.0))
            p.drawRoundedRect(b_rect, 13.0, 13.0)

        p.end()
        super().paintEvent(event)


class SettingsSectionCard(QFrame):
    """
    Card container matching SettingsOptionCard design language:
    - 12px rounded corners
    - Translucent neutral fill + soft hover illumination
    - Clean title + optional subtitle header
    """
    def __init__(self, title="", subtitle="", parent=None, is_dark=True, app=None):
        super().__init__(parent)
        self.app = app
        self.is_dark = is_dark
        self.setObjectName("SettingsSectionCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self._hover_opacity = 0.0
        self._hover_anim = QPropertyAnimation(self, b"hoverOpacity", self)
        self._hover_anim.setDuration(160)
        self._hover_anim.setEasingCurve(QEasingCurve.OutQuad)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(18, 12, 18, 14)
        self.main_layout.setSpacing(10)

        if title or subtitle:
            self.header_layout = QVBoxLayout()
            self.header_layout.setContentsMargins(0, 0, 0, 0)
            self.header_layout.setSpacing(3)

            if title:
                self.lbl_title = QLabel(title)
                self.lbl_title.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {'#ffffff' if is_dark else '#0f172a'}; background: transparent;")
                self.header_layout.addWidget(self.lbl_title)
            else:
                self.lbl_title = None

            if subtitle:
                self.lbl_subtitle = QLabel(subtitle)
                self.lbl_subtitle.setStyleSheet(f"font-size: 11.5px; color: {'#94a3b8' if is_dark else '#475569'}; background: transparent;")
                self.lbl_subtitle.setWordWrap(True)
                self.header_layout.addWidget(self.lbl_subtitle)
            else:
                self.lbl_subtitle = None

            self.main_layout.addLayout(self.header_layout)

    def _get_hover_opacity(self):
        return self._hover_opacity

    def _set_hover_opacity(self, val):
        self._hover_opacity = float(val)
        self.update()

    hoverOpacity = Property(float, _get_hover_opacity, _set_hover_opacity)

    def enterEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_opacity)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_opacity)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def setTitle(self, text):
        if hasattr(self, "lbl_title") and self.lbl_title:
            self.lbl_title.setText(text)

    def update_styles(self, is_dark=None):
        if is_dark is not None:
            self.is_dark = is_dark
        elif self.app:
            self.is_dark = getattr(self.app, "is_dark_mode", True)
        if hasattr(self, "lbl_title") and self.lbl_title:
            self.lbl_title.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {'#ffffff' if self.is_dark else '#0f172a'}; background: transparent;")
        if hasattr(self, "lbl_subtitle") and self.lbl_subtitle:
            self.lbl_subtitle.setStyleSheet(f"font-size: 11.5px; color: {'#94a3b8' if self.is_dark else '#475569'}; background: transparent;")
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = float(self.width()), float(self.height())
        radius = 12.0
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)

        if self.is_dark:
            bg_alpha = int(10 + 14 * self._hover_opacity)
            border_alpha = int(18 + 26 * self._hover_opacity)
            bg_color = QColor(255, 255, 255, bg_alpha)
            border_color = QColor(255, 255, 255, border_alpha)
        else:
            bg_alpha = int(14 + 18 * self._hover_opacity)
            border_alpha = int(32 + 36 * self._hover_opacity)
            bg_color = QColor(0, 0, 0, bg_alpha)
            border_color = QColor(0, 0, 0, border_alpha)

        p.setBrush(bg_color)
        p.setPen(QPen(border_color, 1.0))
        p.drawRoundedRect(rect, radius, radius)
        p.end()
        
class ImagePreviewCard(QFrame):
    """
    Preview card displaying the currently loaded background or sticker image:
    - 10px rounded container with soft theme-reactive translucent fill.
    - Preserves aspect ratio with smooth bilinear filtering.
    - Informational badge with dimensions and file name.
    - Drag & drop support for dropping images directly into the preview area.
    - Clean empty state with icon and helpful hint when no image is loaded.
    """
    imageDropped = Signal(str)

    def __init__(self, placeholder_title="Sin imagen seleccionada",
                 placeholder_hint="Arrastra una imagen o pulsa en examinar",
                 parent=None, is_dark=True, app=None):
        super().__init__(parent)
        self.app = app
        self.placeholder_title = placeholder_title
        self.placeholder_hint = placeholder_hint
        self.is_dark = is_dark
        self.image_path = ""
        self._pixmap = None
        self._img_size_str = ""
        self._img_name_str = ""
        self._text_content = ""
        self._mode = "image"
        self._is_drag_over = False

        self.setFixedHeight(128)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

    def set_is_dark(self, is_dark):
        self.is_dark = is_dark
        self.update()

    def set_placeholders(self, title, hint):
        self.placeholder_title = title
        self.placeholder_hint = hint
        self.update()

    def set_image(self, path):
        self._mode = "image"
        self.image_path = path or ""
        if self.image_path and os.path.exists(self.image_path):
            pix = QPixmap(self.image_path)
            if not pix.isNull():
                self._pixmap = pix
                self._img_size_str = f"{pix.width()} × {pix.height()} px"
                self._img_name_str = os.path.basename(self.image_path)
            else:
                self._pixmap = None
                self._img_size_str = ""
                self._img_name_str = ""
        else:
            self._pixmap = None
            self._img_size_str = ""
            self._img_name_str = ""
        self.update()

    def set_text_preview(self, text):
        self._mode = "text"
        self._text_content = text or ""
        self._pixmap = None
        self.update()

    def clear_image(self):
        self.set_image("")

    def clear_preview(self):
        self._mode = "image"
        self.image_path = ""
        self._pixmap = None
        self._img_size_str = ""
        self._img_name_str = ""
        self._text_content = ""
        self.update()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = url.toLocalFile().lower()
                if any(p.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")):
                    self._is_drag_over = True
                    event.acceptProposedAction()
                    self.update()
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._is_drag_over = False
        self.update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        self._is_drag_over = False
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if any(p.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")):
                self.set_image(p)
                self.imageDropped.emit(p)
                event.acceptProposedAction()
                self.update()
                return
        event.ignore()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        radius = 10.0

        accent_hex = getattr(self.app, "current_accent_color", "#06b6d4") if self.app else "#06b6d4"
        accent_col = QColor(accent_hex)

        # Background container
        if self._is_drag_over:
            p.setBrush(QColor(accent_col.red(), accent_col.green(), accent_col.blue(), 30))
            p.setPen(QPen(accent_col, 2.0, Qt.DashLine))
            p.drawRoundedRect(rect, radius, radius)
        else:
            if self.is_dark:
                bg_col = QColor(0, 0, 0, 95)
                border_col = QColor(255, 255, 255, 28)
            else:
                bg_col = QColor(0, 0, 0, 14)
                border_col = QColor(0, 0, 0, 32)
            p.setBrush(bg_col)
            p.setPen(QPen(border_col, 1.0))
            p.drawRoundedRect(rect, radius, radius)

        # Draw content
        if self._mode == "image" and self._pixmap and not self._pixmap.isNull():
            pad = 8.0
            avail_w = w - pad * 2.0
            avail_h = h - pad * 2.0
            pw = float(self._pixmap.width())
            ph = float(self._pixmap.height())

            scale = min(avail_w / pw, avail_h / ph)
            dw = pw * scale
            dh = ph * scale
            dx = (w - dw) / 2.0
            dy = (h - dh) / 2.0
            thumb_rect = QRectF(dx, dy, dw, dh)

            # Draw image with rounded corners
            p.save()
            path = QPainterPath()
            path.addRoundedRect(thumb_rect, 6.0, 6.0)
            p.setClipPath(path)
            p.drawPixmap(QRect(int(dx), int(dy), int(dw), int(dh)), self._pixmap)
            p.restore()

            # Thumbnail border
            p.setPen(QPen(QColor(255, 255, 255, 45) if self.is_dark else QColor(0, 0, 0, 35), 1.0))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(thumb_rect, 6.0, 6.0)

            # Info badge in bottom-right
            if self._img_size_str:
                badge_text = f"{self._img_name_str}  •  {self._img_size_str}"
                font = QFont("Segoe UI", 8)
                font.setBold(True)
                p.setFont(font)
                fm = QFontMetrics(font)
                bw = fm.horizontalAdvance(badge_text) + 18
                bh = 22.0
                bx = w - bw - 12.0
                by = h - bh - 10.0
                badge_rect = QRectF(bx, by, bw, bh)

                p.setPen(Qt.NoPen)
                p.setBrush(QColor(10, 12, 16, 215) if self.is_dark else QColor(255, 255, 255, 225))
                p.drawRoundedRect(badge_rect, 11.0, 11.0)

                p.setPen(QColor("#f8fafc" if self.is_dark else "#0f172a"))
                p.drawText(badge_rect, Qt.AlignCenter, badge_text)
        elif self._mode == "text" and self._text_content:
            font = QFont("Segoe UI", 12)
            font.setBold(True)
            p.setFont(font)
            fm = QFontMetrics(font)
            bw = fm.horizontalAdvance(self._text_content) + 24
            bh = 34.0
            bx = (w - bw) / 2.0
            by = (h - bh) / 2.0
            t_rect = QRectF(bx, by, bw, bh)

            p.setPen(Qt.NoPen)
            p.setBrush(QColor(accent_col.red(), accent_col.green(), accent_col.blue(), 180))
            p.drawRoundedRect(t_rect, 8.0, 8.0)
            p.setPen(QColor("#ffffff"))
            p.drawText(t_rect, Qt.AlignCenter, self._text_content)
        else:
            center_x = w / 2.0
            center_y = h / 2.0

            icon_size = 28.0
            ix = center_x - icon_size / 2.0
            iy = center_y - 28.0

            icon_col = QColor("#94a3b8" if self.is_dark else "#64748b")
            p.setPen(QPen(icon_col, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(ix, iy, icon_size, 20.0), 3.0, 3.0)
            p.setBrush(icon_col)
            p.drawEllipse(QRectF(ix + 5.0, iy + 4.0, 4.0, 4.0))
            p.setBrush(Qt.NoBrush)
            m_path = QPainterPath()
            m_path.moveTo(ix + 3.0, iy + 17.0)
            m_path.lineTo(ix + 11.0, iy + 10.0)
            m_path.lineTo(ix + 18.0, iy + 15.0)
            m_path.lineTo(ix + 21.0, iy + 12.0)
            m_path.lineTo(ix + 25.0, iy + 17.0)
            p.drawPath(m_path)

            font_title = QFont("Segoe UI", 9)
            font_title.setBold(True)
            p.setFont(font_title)
            p.setPen(QColor("#cbd5e1" if self.is_dark else "#334155"))
            title_rect = QRectF(10.0, iy + 25.0, w - 20.0, 18.0)
            p.drawText(title_rect, Qt.AlignCenter, self.placeholder_title)

            font_sub = QFont("Segoe UI", 8)
            p.setFont(font_sub)
            p.setPen(QColor("#64748b" if self.is_dark else "#94a3b8"))
            sub_rect = QRectF(10.0, iy + 42.0, w - 20.0, 16.0)
            p.drawText(sub_rect, Qt.AlignCenter, self.placeholder_hint)

        p.end()


class TopBarModeButton(QPushButton):
    """
    Capsule pill mode button replicating the launcher top bar tabs:
    - Pill shape (radius = height / 2.0)
    - Active: accent color background, white bold text, multi-step accent glow in dark mode
    - Inactive: dark translucent / soft neutral gray background with subtle border
    - Hover: soft illumination transition
    - Click/Press: tactile sink compression animation
    """
    def __init__(self, text="", parent=None, app=None):
        super().__init__(text, parent)
        self.app = app
        self.setCheckable(True)
        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        self._accent = "#06b6d4"
        self._is_dark = True
        self._hover_opacity = 0.0
        self._sink_factor = 0.0

        self._hover_anim = QPropertyAnimation(self, b"hoverOpacity", self)
        self._hover_anim.setDuration(150)
        self._hover_anim.setEasingCurve(QEasingCurve.OutQuad)

        self._sink_anim = QPropertyAnimation(self, b"sinkFactor", self)
        self._sink_anim.setDuration(130)
        self._sink_anim.setEasingCurve(QEasingCurve.InOutQuad)

    def _get_hover_opacity(self):
        return self._hover_opacity

    def _set_hover_opacity(self, val):
        self._hover_opacity = float(val)
        self.update()

    hoverOpacity = Property(float, _get_hover_opacity, _set_hover_opacity)

    def _get_sink_factor(self):
        return self._sink_factor

    def _set_sink_factor(self, val):
        self._sink_factor = float(val)
        self.update()

    sinkFactor = Property(float, _get_sink_factor, _set_sink_factor)

    def set_accent_color(self, hex_color):
        self._accent = hex_color
        self.update()

    def set_is_dark(self, is_dark):
        self._is_dark = is_dark
        self.update()

    def enterEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_opacity)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_opacity)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._sink_anim.stop()
            self._sink_anim.setStartValue(self._sink_factor)
            self._sink_anim.setEndValue(1.0)
            self._sink_anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._sink_anim.stop()
        self._sink_anim.setStartValue(self._sink_factor)
        self._sink_anim.setEndValue(0.0)
        self._sink_anim.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = float(self.width()), float(self.height())
        accent_c = QColor(self._accent)

        # Tactile sink compression offset (press animation)
        sink_inset = self._sink_factor * 1.6
        rect = QRectF(sink_inset + 2.0, sink_inset + 2.0, w - 2 * sink_inset - 4.0, h - 2 * sink_inset - 4.0)
        radius = rect.height() / 2.0

        if self.isChecked():
            # Active button: Accent background with multi-step glow (like top bar tabs)
            if self._is_dark:
                glow_steps = 8
                max_expand = 5.0
                max_alpha = 32
                for i in range(glow_steps, 0, -1):
                    t = i / float(glow_steps)
                    alpha = int(max_alpha * ((1.0 - t) ** 1.6))
                    if alpha <= 0:
                        continue
                    exp = max_expand * t
                    g_rect = rect.adjusted(-exp, -exp, exp, exp)
                    g_rad = g_rect.height() / 2.0
                    g_col = QColor(accent_c)
                    g_col.setAlpha(alpha)
                    p.setBrush(g_col)
                    p.setPen(Qt.NoPen)
                    p.drawRoundedRect(g_rect, g_rad, g_rad)
            else:
                # Soft shadow in light mode
                s_steps = 6
                for i in range(s_steps, 0, -1):
                    t = i / float(s_steps)
                    alpha = int(22 * ((1.0 - t) ** 1.5))
                    if alpha <= 0:
                        continue
                    s_rect = rect.adjusted(0.5 * t, 1.0 * t, 4.0 * t, 5.0 * t)
                    p.setBrush(QColor(0, 0, 0, alpha))
                    p.setPen(Qt.NoPen)
                    p.drawRoundedRect(s_rect, s_rect.height() / 2.0, s_rect.height() / 2.0)

            p.setBrush(accent_c)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(rect, radius, radius)
            text_color = QColor("#ffffff")
        else:
            # Inactive button: translucent neutral base + hover highlight
            if self._is_dark:
                base_alpha = int(14 + 18 * self._hover_opacity)
                border_alpha = int(24 + 30 * self._hover_opacity)
                bg_col = QColor(255, 255, 255, base_alpha)
                border_col = QColor(255, 255, 255, border_alpha)
                text_color = QColor("#ffffff" if self._hover_opacity > 0.5 else "#cbd5e1")
            else:
                base_alpha = int(16 + 20 * self._hover_opacity)
                border_alpha = int(36 + 36 * self._hover_opacity)
                bg_col = QColor(0, 0, 0, base_alpha)
                border_col = QColor(0, 0, 0, border_alpha)
                text_color = QColor("#0f172a" if self._hover_opacity > 0.5 else "#475569")

            p.setBrush(bg_col)
            p.setPen(QPen(border_col, 1.1))
            p.drawRoundedRect(rect, radius, radius)

        # Text
        f = p.font()
        f.setBold(True)
        f.setPointSize(10)
        p.setFont(f)
        p.setPen(text_color)
        p.drawText(rect, Qt.AlignCenter, self.text())

        p.end()


class GlassCapsuleSlider(QSlider):
    """
    Modern glass capsule slider replicating the CSS/JS design by Maxuiux:
    - Pill track with neutral muted background
    - Dynamic linear gradient progress synchronized with the active theme color
    - Capsule glass thumb with specular highlight, drop shadow, and active expansion response
    - Direct jump-to-position on mouse click and smooth dragging
    """
    def __init__(self, orientation=Qt.Horizontal, parent=None, app=None):
        super().__init__(orientation, parent)
        self.app = app
        self._accent = "#06b6d4"
        self._is_dark = True
        self._active_factor = 0.0
        self._hover_factor = 0.0
        self._is_dragging = False

        self.setMouseTracking(True)
        self.setFixedHeight(30)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

        self._active_anim = QPropertyAnimation(self, b"activeFactor", self)
        self._active_anim.setDuration(150)
        self._active_anim.setEasingCurve(QEasingCurve.OutQuad)

        self._hover_anim = QPropertyAnimation(self, b"hoverFactor", self)
        self._hover_anim.setDuration(150)
        self._hover_anim.setEasingCurve(QEasingCurve.OutQuad)

    def _get_active_factor(self):
        return self._active_factor

    def _set_active_factor(self, val):
        self._active_factor = float(val)
        self.update()

    activeFactor = Property(float, _get_active_factor, _set_active_factor)

    def _get_hover_factor(self):
        return self._hover_factor

    def _set_hover_factor(self, val):
        self._hover_factor = float(val)
        self.update()

    hoverFactor = Property(float, _get_hover_factor, _set_hover_factor)

    def set_accent_color(self, hex_color):
        self._accent = hex_color
        self.update()

    def set_is_dark(self, is_dark):
        self._is_dark = is_dark
        self.update()

    def _track_geometry(self):
        h = 10.0
        margin_x = 24.0
        y = (self.height() - h) / 2.0
        w = max(10.0, self.width() - 2 * margin_x)
        return margin_x, y, w, h

    def _pos_from_value(self, val):
        mx, my, tw, th = self._track_geometry()
        rng = self.maximum() - self.minimum()
        if rng <= 0:
            return mx
        ratio = (val - self.minimum()) / float(rng)
        ratio = max(0.0, min(1.0, ratio))
        return mx + ratio * tw

    def _value_from_pos(self, x):
        mx, my, tw, th = self._track_geometry()
        ratio = (x - mx) / float(tw)
        ratio = max(0.0, min(1.0, ratio))
        rng = self.maximum() - self.minimum()
        return int(round(self.minimum() + ratio * rng))

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
            self._is_dragging = True
            val = self._value_from_pos(event.position().x())
            self.setValue(val)
            self._active_anim.stop()
            self._active_anim.setStartValue(self._active_factor)
            self._active_anim.setEndValue(1.0)
            self._active_anim.start()
            self.sliderPressed.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            val = self._value_from_pos(event.position().x())
            if val != self.value():
                self.setValue(val)
                self.sliderMoved.emit(val)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._is_dragging:
            self._is_dragging = False
            self._active_anim.stop()
            self._active_anim.setStartValue(self._active_factor)
            self._active_anim.setEndValue(0.0)
            self._active_anim.start()
            self.sliderReleased.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        event.ignore()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        mx, ty, tw, th = self._track_geometry()
        val_pos = self._pos_from_value(self.value())

        # 1. Track background (pill)
        track_rect = QRectF(mx, ty, tw, th)
        r_track = th / 2.0
        track_bg = QColor("#282b35" if self._is_dark else "#D6D6DA")
        p.setPen(Qt.NoPen)
        p.setBrush(track_bg)
        p.drawRoundedRect(track_rect, r_track, r_track)

        # 2. Progress fill gradient (117deg matching accent)
        prog_w = max(0.0, val_pos - mx)
        if prog_w > 0:
            prog_rect = QRectF(mx, ty, prog_w, th)
            ac = QColor(self._accent)
            c_light = ac.lighter(125)
            c_dark = ac.darker(110)

            grad = QLinearGradient(mx, ty, mx + prog_w, ty + th)
            grad.setColorAt(0.0, c_light)
            grad.setColorAt(1.0, c_dark)

            p.setBrush(grad)
            p.drawRoundedRect(prog_rect, r_track, r_track)

        # 3. Glass Capsule Thumb
        base_w = 40.0
        base_h = 20.0
        # Active scaling: scaleX = 1.10, scaleY = 0.98
        w = base_w * (1.0 + 0.10 * self._active_factor)
        h = base_h * (1.0 - 0.02 * self._active_factor)
        r_thumb = h / 2.0

        cx = val_pos
        cy = ty + th / 2.0
        thumb_rect = QRectF(cx - w / 2.0, cy - h / 2.0, w, h)

        # Drop shadow
        shadow_steps = 5
        for i in range(shadow_steps, 0, -1):
            t = i / float(shadow_steps)
            alpha = int(28 * (1.0 - t))
            if alpha > 0:
                s_rect = thumb_rect.adjusted(-1.5 * t, 0.5 * t, 1.5 * t, 3.0 * t)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(0, 0, 0, alpha))
                p.drawRoundedRect(s_rect, s_rect.height() / 2.0, s_rect.height() / 2.0)

        # Glass body gradient fill
        glass_grad = QLinearGradient(thumb_rect.topLeft(), thumb_rect.bottomLeft())
        if self._is_dark:
            top_c = QColor(255, 255, 255, int(230 - 30 * self._active_factor))
            bot_c = QColor(210, 225, 240, int(190 - 40 * self._active_factor))
        else:
            top_c = QColor(255, 255, 255, 255)
            bot_c = QColor(238, 242, 246, 245)

        glass_grad.setColorAt(0.0, top_c)
        glass_grad.setColorAt(1.0, bot_c)

        ac = QColor(self._accent)
        if self._active_factor > 0:
            border_c = QColor(ac.red(), ac.green(), ac.blue(), int(160 * self._active_factor + 60))
        else:
            border_c = QColor(255, 255, 255, 180) if self._is_dark else QColor(0, 0, 0, 40)

        p.setBrush(glass_grad)
        p.setPen(QPen(border_c, 1.2))
        p.drawRoundedRect(thumb_rect, r_thumb, r_thumb)

        # Top specular highlight sheen
        inner_sheen = QRectF(thumb_rect.x() + 3, thumb_rect.y() + 1.5, thumb_rect.width() - 6, thumb_rect.height() * 0.42)
        sheen_grad = QLinearGradient(inner_sheen.topLeft(), inner_sheen.bottomLeft())
        sheen_grad.setColorAt(0.0, QColor(255, 255, 255, 140))
        sheen_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(sheen_grad)
        p.drawRoundedRect(inner_sheen, inner_sheen.height() / 2.0, inner_sheen.height() / 2.0)

        # Grip reflection detail (center notch / glass lens dot)
        p.setPen(Qt.NoPen)
        grip_col = QColor(ac.red(), ac.green(), ac.blue(), int(90 + 90 * self._active_factor))
        p.setBrush(grip_col)
        p.drawRoundedRect(QRectF(cx - 3.0, cy - 3.5, 6.0, 7.0), 2.0, 2.0)

        p.end()


class SettingsTab(QWidget):
    """Settings tab with categorized sections, stacked pages, and a sticky footer bar."""

    CATEGORIES = [
        ("general", "UI_CATEGORY_GENERAL"),
        ("launch", "UI_CATEGORY_LAUNCH"),
        ("appearance", "UI_CATEGORY_APPEARANCE"),
    ]

    CATEGORY_METHODS = {
        "general": [
            "setup_language_section",
            "setup_launch_action_section",
            "setup_profiles_section",
            "setup_discord_section",
            "setup_restore_defaults_section",
        ],
        "launch": [
            "setup_binaries_section",
            "setup_extras_section",
        ],
        "appearance": [
            "setup_appearance_section",
            "setup_section_opacity_section",
            "setup_background_section",
            "setup_sticker_section",
        ],
    }

    _DROP_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")

    ICONS = {}
    SIDEBAR_EXPANDED = 236
    SIDEBAR_COLLAPSED = 236

    def __init__(self, parent, app):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.app = app
        self._pages = {}
        self._cat_buttons = {}
        self._active_cat = None
        self._groups = {}
        self.checks = {}
        self._retranslate_labels = []
        self._appearance_labels = []
        self._bg_labels = []
        self._bg_val_labels = []
        self._sticker_labels = []
        self._sticker_val_labels = []
        self._clear_buttons = []
        self.lbl_binary_version = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 8, 12, 6)
        self.main_layout.setSpacing(6)

        # Sliding stacked widget for smooth category page transitions
        self.stack = SlidingStackedWidget(self)
        self.main_layout.addWidget(self.stack, 1)

        for key, _ in self.CATEGORIES:
            self._init_page(key)

        for cat_key, methods in self.CATEGORY_METHODS.items():
            self._set_active_page(cat_key)
            for method_name in methods:
                getattr(self, method_name)()

        # Centered Liquid Glass bottom navigation menu with project text at right
        self._menu_bar_layout = QHBoxLayout()
        self._menu_bar_layout.setContentsMargins(18, 6, 18, 8)
        self._menu_bar_layout.setSpacing(10)

        self._footer_left_spacer = QWidget(self)
        self._footer_left_spacer.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.bottom_menu = LiquidGlassBottomMenu(self, app=self.app)
        self.bottom_menu.categoryChanged.connect(self._switch_category)
        self._cat_buttons = self.bottom_menu.buttons
        self._sidebar_card = self.bottom_menu

        self.lbl_footer_version = QPushButton(
            f"{c.t('UI_FOOTER_PROJECT_NAME')} - v{c.VERSION_LAUNCHER}"
        )
        self.lbl_footer_version.setObjectName("FooterVersion")
        self.lbl_footer_version.setFlat(True)
        self.lbl_footer_version.setCursor(Qt.PointingHandCursor)
        _mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark") if self.app else "Dark"
        muted = "#aaaaaa" if _mode == "Dark" else "#555555"
        self.lbl_footer_version.setStyleSheet(
            f"QPushButton#FooterVersion {{ color: {muted}; font-size: 11px; "
            f"background: transparent; border: none; text-decoration: underline; }}"
        )
        self.lbl_footer_version.setToolTip(c.t("UI_FOOTER_CHANGELOG_TOOLTIP"))
        self.lbl_footer_version.clicked.connect(self._open_changelog)

        self._menu_bar_layout.addWidget(self._footer_left_spacer, 1, Qt.AlignLeft)
        self._menu_bar_layout.addWidget(self.bottom_menu, 0, Qt.AlignCenter)
        self._menu_bar_layout.addWidget(self.lbl_footer_version, 1, Qt.AlignRight | Qt.AlignVCenter)
        self.main_layout.addLayout(self._menu_bar_layout)

        # Floating Unsaved Changes Card
        self.unsaved_card = UnsavedChangesFloatingCard(parent=self, app=self.app)
        self.unsaved_card.cancelRequested.connect(self.cancel_changes)
        self.unsaved_card.saveRequested.connect(self.confirm_save_settings)
        self.has_unsaved_changes = False

        self._set_active_page("launch")
        self.on_settings_mode_change(self.combo_settings_mode.currentText())
        self.toggle_custom_env()
        self._refresh_per_widget_styles()
        self._switch_category("general")

        # Snapshot and change signal connections
        self._connect_change_signals()
        self._saved_snapshot = self._get_current_state()
        self._is_restoring = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_unsaved_card()
        self._update_launch_layout_responsiveness()

    def _update_launch_layout_responsiveness(self):
        if not hasattr(self, "launch_grid") or not hasattr(self, "launch_left_widget"):
            return
        is_compact = self.width() < 870
        if getattr(self, "_launch_is_compact", None) == is_compact:
            return
        self._launch_is_compact = is_compact
        if is_compact:
            self.launch_grid.setDirection(QBoxLayout.TopToBottom)
        else:
            self.launch_grid.setDirection(QBoxLayout.LeftToRight)

    def _reposition_unsaved_card(self):
        if hasattr(self, "unsaved_card") and self.unsaved_card:
            card_w = self.unsaved_card.width()
            card_h = self.unsaved_card.height()
            x = self.width() - card_w - 24 + getattr(self.unsaved_card, "_shake_offset", 0.0)
            y = self.height() - card_h - 76 + getattr(self.unsaved_card, "_slide_y_offset", 0.0)
            self.unsaved_card.move(int(x), int(y))

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Wheel:
            if isinstance(watched, (QSlider, GlassCapsuleSlider)):
                event.ignore()
                return True
        return super().eventFilter(watched, event)

    def trigger_unsaved_shake(self):
        if hasattr(self, "unsaved_card") and self.unsaved_card:
            self.unsaved_card.trigger_shake()

    def _get_current_state(self):
        state = {}
        combos = [
            "combo_lang", "combo_scale", "combo_launch_action", "combo_profile",
            "combo_settings_mode", "combo_appearance", "combo_theme",
            "combo_version_style", "combo_tools_layout", "combo_sticker_mode", "combo_sticker_corner"
        ]
        for attr in combos:
            if hasattr(self, attr):
                cb = getattr(self, attr)
                state[attr] = cb.currentData() if hasattr(cb, "currentData") and cb.currentData() is not None else cb.currentText()

        lineedits = [
            "entry_flatpak_id", "entry_custom_vars", "entry_discord_client_id",
            "entry_mc_libs", "entry_bin_folder", "entry_bg_path", "entry_sticker_content"
        ]
        for attr in lineedits:
            if hasattr(self, attr):
                le = getattr(self, attr)
                state[attr] = le.text()

        if hasattr(self, "inputs"):
            for k, (e, b, p) in self.inputs.items():
                if e:
                    state[f"input_{k}"] = e.text()

        if hasattr(self, "checks"):
            for k, cb in self.checks.items():
                if cb:
                    state[f"check_{k}"] = cb.isChecked()

        sliders = [
            "slider_icon", "slider_title", "slider_card_width", "slider_card_height",
            "slider_section_opacity", "slider_bg_x", "slider_bg_y", "slider_bg_opacity",
            "slider_bg_zoom", "slider_sticker_x", "slider_sticker_y", "slider_sticker_zoom",
            "slider_sticker_opacity"
        ]
        for attr in sliders:
            if hasattr(self, attr):
                sl = getattr(self, attr)
                state[attr] = sl.value()

        return state

    def _restore_snapshot(self, snapshot):
        if not snapshot:
            return
        combos = [
            "combo_lang", "combo_scale", "combo_launch_action", "combo_profile",
            "combo_settings_mode", "combo_appearance", "combo_theme",
            "combo_version_style", "combo_tools_layout", "combo_sticker_mode", "combo_sticker_corner"
        ]
        for attr in combos:
            if hasattr(self, attr) and attr in snapshot:
                cb = getattr(self, attr)
                val = snapshot[attr]
                idx = cb.findData(val)
                if idx >= 0:
                    cb.setCurrentIndex(idx)
                else:
                    idx = cb.findText(str(val))
                    if idx >= 0:
                        cb.setCurrentIndex(idx)

        lineedits = [
            "entry_flatpak_id", "entry_custom_vars", "entry_discord_client_id",
            "entry_mc_libs", "entry_bin_folder", "entry_bg_path", "entry_sticker_content"
        ]
        for attr in lineedits:
            if hasattr(self, attr) and attr in snapshot:
                le = getattr(self, attr)
                le.setText(str(snapshot[attr]))

        if hasattr(self, "inputs"):
            for k, (e, b, p) in self.inputs.items():
                s_key = f"input_{k}"
                if s_key in snapshot and e:
                    e.setText(str(snapshot[s_key]))

        if hasattr(self, "checks"):
            for k, cb in self.checks.items():
                s_key = f"check_{k}"
                if s_key in snapshot and cb:
                    cb.setChecked(bool(snapshot[s_key]))

        sliders = [
            "slider_icon", "slider_title", "slider_card_width", "slider_card_height",
            "slider_section_opacity", "slider_bg_x", "slider_bg_y", "slider_bg_opacity",
            "slider_bg_zoom", "slider_sticker_x", "slider_sticker_y", "slider_sticker_zoom",
            "slider_sticker_opacity"
        ]
        for attr in sliders:
            if hasattr(self, attr) and attr in snapshot:
                sl = getattr(self, attr)
                sl.setValue(int(snapshot[attr]))

        self.save_settings(silent=True)

    def _connect_change_signals(self):
        combos = [
            getattr(self, attr, None) for attr in [
                "combo_lang", "combo_scale", "combo_launch_action", "combo_profile",
                "combo_settings_mode", "combo_appearance", "combo_theme",
                "combo_version_style", "combo_tools_layout", "combo_sticker_mode", "combo_sticker_corner"
            ]
        ]
        for cb in combos:
            if cb and hasattr(cb, "currentIndexChanged"):
                cb.currentIndexChanged.connect(self._on_control_value_changed)

        lineedits = [
            getattr(self, attr, None) for attr in [
                "entry_flatpak_id", "entry_custom_vars", "entry_discord_client_id",
                "entry_mc_libs", "entry_bin_folder", "entry_bg_path", "entry_sticker_content"
            ]
        ]
        for le in lineedits:
            if le and hasattr(le, "textChanged"):
                le.textChanged.connect(self._on_control_value_changed)

        if hasattr(self, "inputs"):
            for k, (e, b, p) in self.inputs.items():
                if e and hasattr(e, "textChanged"):
                    e.textChanged.connect(self._on_control_value_changed)

        if hasattr(self, "checks"):
            for k, cb in self.checks.items():
                if cb and hasattr(cb, "stateChanged"):
                    cb.stateChanged.connect(self._on_control_value_changed)

        sliders = [
            getattr(self, attr, None) for attr in [
                "slider_icon", "slider_title", "slider_card_width", "slider_card_height",
                "slider_section_opacity", "slider_bg_x", "slider_bg_y", "slider_bg_opacity",
                "slider_bg_zoom", "slider_sticker_x", "slider_sticker_y", "slider_sticker_zoom",
                "slider_sticker_opacity"
            ]
        ]
        for sl in sliders:
            if sl:
                if hasattr(sl, "valueChanged"):
                    sl.valueChanged.connect(self._on_control_value_changed)
                sl.installEventFilter(self)

    def _on_control_value_changed(self, *args):
        if getattr(self, "_is_restoring", False):
            return
        if not hasattr(self, "_saved_snapshot"):
            return
        curr = self._get_current_state()
        dirty = (curr != self._saved_snapshot)
        self.has_unsaved_changes = dirty
        if hasattr(self, "unsaved_card") and self.unsaved_card:
            self.unsaved_card.set_visible_animated(dirty)

    def cancel_changes(self):
        self._is_restoring = True
        try:
            self._restore_snapshot(self._saved_snapshot)
        finally:
            self._is_restoring = False
        self.has_unsaved_changes = False
        if hasattr(self, "unsaved_card") and self.unsaved_card:
            self.unsaved_card.set_visible_animated(False)

    def confirm_save_settings(self):
        self.save_settings(silent=False)

    # ── Drag & drop ──────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if any(url.toLocalFile().lower().endswith(e) for e in self._DROP_IMAGE_EXTS):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if any(path.lower().endswith(e) for e in self._DROP_IMAGE_EXTS):
                self.entry_bg_path.setText(path)
                return

    # ── Category infrastructure ──────────────────────────────────

    def _init_page(self, key):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName(f"SettingsCategoryPage_{key}")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content.setObjectName("SettingsPageContent")
        scroll_layout = QVBoxLayout(content)
        scroll_layout.setContentsMargins(0, 0, 6, 0)
        scroll_layout.setSpacing(6)
        scroll_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.stack.addWidget(page)
        self._pages[key] = (page, scroll_layout)

    def _set_active_page(self, key):
        _, self.scroll_layout = self._pages[key]

    def _switch_category(self, key):
        page, _ = self._pages[key]
        self.stack.setCurrentWidget(page)
        self._active_cat = key
        if hasattr(self, "bottom_menu") and self.bottom_menu:
            if self.bottom_menu._active_cat != key:
                self.bottom_menu.set_active_category(key, notify=False)
        for k, btn in self._cat_buttons.items():
            active = (k == key)
            if hasattr(btn, "setChecked"):
                btn.setChecked(active)
            if hasattr(btn, "setProperty"):
                btn.setProperty("active", active)
            if hasattr(btn, "style") and callable(btn.style):
                s = btn.style()
                if hasattr(s, "unpolish"):
                    s.unpolish(btn)
                    s.polish(btn)

    def setup_sidebar(self):
        pass

    def _toggle_sidebar(self):
        pass

    def _add_tooltip_button(self, layout, title, tooltip):
        btn_info = QPushButton("?")
        btn_info.setObjectName("ToolButton")
        btn_info.setFixedSize(22, 18)
        btn_info.clicked.connect(lambda checked=False, t=title, m=tooltip: self.app.show_info(t, m))
        layout.addWidget(btn_info)

    def _open_changelog(self):
        self.app.show_update_changelog(c.VERSION_LAUNCHER)

    # ── General ──────────────────────────────────────────────────

    def setup_language_section(self):
        # ── Card 1: Idioma ──
        globe_icon_path = resource_path("assets/media/settings_icon_globe.svg")
        self.card_lang = SettingsOptionCard(
            icon_path=globe_icon_path,
            title=c.t("UI_LABEL_LANGUAGE"),
            subtitle=c.t("UI_SETTINGS_DESC_LANG"),
            app=self.app,
            parent=self
        )
        self._groups["UI_LABEL_LANGUAGE"] = self.card_lang

        self.langs_dict = language_manager.get_available_languages()
        self.combo_lang = SleekComboBox(parent=self, app=self.app)
        globe_ic = QIcon(globe_icon_path) if os.path.exists(globe_icon_path) else QIcon()
        for k, v in self.langs_dict.items():
            self.combo_lang.addItem(globe_ic, v, k)
        current_lang = self.app.config.get(c.CONFIG_KEY_LANGUAGE, "en")
        idx = self.combo_lang.findData(current_lang)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        self.combo_lang.currentTextChanged.connect(self.on_language_change)
        self.card_lang.ctrl_layout.addWidget(self.combo_lang)
        self.scroll_layout.addWidget(self.card_lang)
        self._add_spacer()

        # ── Card 2: Escalado de Interfaz (DPI) ──
        display_icon_path = resource_path("assets/media/settings_icon_display.svg")
        self.card_scale = SettingsOptionCard(
            icon_path=display_icon_path,
            title=c.t("UI_LABEL_UI_SCALE"),
            subtitle=c.t("UI_SETTINGS_DESC_SCALE"),
            warning_note=f"⚠️ {c.t('UI_RESTART_SCALE_MSG')}",
            app=self.app,
            parent=self
        )
        self._groups["UI_LABEL_UI_SCALE"] = self.card_scale

        self.combo_scale = SleekComboBox(parent=self, app=self.app)
        scale_options = [
            ("1.0 (100%)", "1.0"),
            ("1.25 (125%)", "1.25"),
            ("1.5 (150%)", "1.5"),
            ("1.75 (175%)", "1.75"),
            ("2.0 (200%)", "2.0")
        ]
        for label, val in scale_options:
            self.combo_scale.addItem(label, val)
        curr_scale = str(self.app.config.get(c.CONFIG_KEY_UI_SCALE, "1.0"))
        idx_s = self.combo_scale.findData(curr_scale)
        if idx_s >= 0:
            self.combo_scale.setCurrentIndex(idx_s)
        self.combo_scale.currentTextChanged.connect(self.on_scale_change)
        self.card_scale.ctrl_layout.addWidget(self.combo_scale)
        self.scroll_layout.addWidget(self.card_scale)
        self._add_spacer()

    def setup_launch_action_section(self):
        # ── Card 3: Acción al Iniciar el Juego ──
        launch_icon_path = resource_path("assets/media/settings_icon_launch.svg")
        self.card_launch_action = SettingsOptionCard(
            icon_path=launch_icon_path,
            title=c.t("UI_LAUNCH_ACTION_LABEL"),
            subtitle=c.t("UI_SETTINGS_DESC_LAUNCH_ACTION"),
            app=self.app,
            parent=self
        )
        self._groups["UI_LAUNCH_ACTION_LABEL"] = self.card_launch_action

        self.combo_launch_action = SleekComboBox(parent=self, app=self.app)
        self.combo_launch_action.addItem(c.t("UI_LAUNCH_ACTION_NONE"), c.LAUNCH_ACTION_NONE)
        self.combo_launch_action.addItem(c.t("UI_LAUNCH_ACTION_HIDE"), c.LAUNCH_ACTION_HIDE)
        self.combo_launch_action.addItem(c.t("UI_LAUNCH_ACTION_CLOSE"), c.LAUNCH_ACTION_CLOSE)
        current_action = self.app.config.get(c.CONFIG_KEY_LAUNCH_ACTION, c.LAUNCH_ACTION_NONE)
        idx = self.combo_launch_action.findData(current_action)
        if idx >= 0:
            self.combo_launch_action.setCurrentIndex(idx)
        self.combo_launch_action.currentIndexChanged.connect(
            lambda: (self.app.sync_launch_action_ui(self.combo_launch_action.currentData()),
                     self.app.config_manager.set(c.CONFIG_KEY_LAUNCH_ACTION, self.combo_launch_action.currentData()))
        )
        self.card_launch_action.ctrl_layout.addWidget(self.combo_launch_action)
        self.scroll_layout.addWidget(self.card_launch_action)
        self._add_spacer()

    def setup_profiles_section(self):
        # ── Card 4: Gestor de Perfiles ──
        profile_icon_path = resource_path("assets/media/settings_icon_profile.svg")
        self.card_profiles = SettingsOptionCard(
            icon_path=profile_icon_path,
            title=c.t("UI_PROFILES_MANAGER_TITLE"),
            subtitle=c.t("UI_SETTINGS_DESC_PROFILES"),
            app=self.app,
            parent=self
        )
        self._groups["UI_PROFILES_MANAGER_TITLE"] = self.card_profiles

        self.combo_profile = SleekComboBox(parent=self, app=self.app)
        self.combo_profile.setMinimumWidth(220)
        self._populate_profile_combo()
        self.combo_profile.currentTextChanged.connect(self.on_profile_change)
        self.card_profiles.ctrl_layout.addWidget(self.combo_profile)

        self.btn_manage_prof = QPushButton("⚙")
        self.btn_manage_prof.setObjectName("ToolButton")
        self.btn_manage_prof.setFixedSize(38, 38)
        self.btn_manage_prof.setCursor(Qt.PointingHandCursor)
        self.btn_manage_prof.setToolTip(c.t("UI_PROFILES_MANAGER_TITLE"))
        self.btn_manage_prof.clicked.connect(self.open_profile_manager)
        self.card_profiles.ctrl_layout.addWidget(self.btn_manage_prof)

        if not getattr(self.app, "profiles_supported", True):
            self.combo_profile.setEnabled(False)
            self.btn_manage_prof.setEnabled(False)
            self.combo_profile.setToolTip(c.t("UI_SYMLINK_NOT_SUPPORTED_MSG"))
            if self.card_profiles.lbl_subtitle:
                self.card_profiles.lbl_subtitle.setText(c.t("UI_SYMLINK_NOT_SUPPORTED_TITLE"))

        self.scroll_layout.addWidget(self.card_profiles)
        self._add_spacer()

    # ── Launch ────────────────────────────────────────────────────

    def setup_binaries_section(self):
        # ── Launch Page Container ──
        # Remove layout-level top-alignment constraint so the 2-column grid expands vertically
        self.scroll_layout.setAlignment(Qt.Alignment())
        self.scroll_layout.setContentsMargins(4, 2, 8, 4)
        self.scroll_layout.setSpacing(8)

        # 1. Top Section Header (clean, no slogan, subtitle)
        launch_header = QFrame()
        launch_header.setObjectName("LaunchHeaderFrame")
        launch_header_layout = QHBoxLayout(launch_header)
        launch_header_layout.setContentsMargins(4, 0, 4, 4)
        launch_header_layout.setSpacing(10)

        header_text_col = QVBoxLayout()
        header_text_col.setContentsMargins(0, 0, 0, 0)
        header_text_col.setSpacing(1)

        self.lbl_launch_header_title = QLabel(c.t("UI_CATEGORY_LAUNCH"))
        self.lbl_launch_header_title.setObjectName("LaunchHeaderTitle")
        self.lbl_launch_header_title.setStyleSheet("font-size: 17px; font-weight: bold;")
        header_text_col.addWidget(self.lbl_launch_header_title)

        self.lbl_launch_header_sub = QLabel("Configura las rutas, librerías y opciones avanzadas del launcher.")
        self.lbl_launch_header_sub.setObjectName("LaunchHeaderSub")
        self.lbl_launch_header_sub.setStyleSheet("font-size: 11px;")
        header_text_col.addWidget(self.lbl_launch_header_sub)
        launch_header_layout.addLayout(header_text_col, 1)

        self.lbl_launch_slogan = None

        self.scroll_layout.addWidget(launch_header, 0)

        # 2. Responsive Layout (switches to single vertical column when window is compact)
        self.launch_grid = QBoxLayout(QBoxLayout.LeftToRight)
        self.launch_grid.setContentsMargins(0, 0, 0, 0)
        self.launch_grid.setSpacing(12)
        self.scroll_layout.addLayout(self.launch_grid, 1)

        # ── Left Column (52% width): Rutas de Binarios ──
        self.launch_left_widget = QWidget()
        self.launch_left_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.launch_left_col = QVBoxLayout(self.launch_left_widget)
        self.launch_left_col.setContentsMargins(0, 0, 0, 0)
        self.launch_left_col.setSpacing(10)
        self.launch_grid.addWidget(self.launch_left_widget, 52)

        # Card: Rutas de Binarios (stretches to fill vertical area)
        bin_paths_icon = resource_path("assets/media/settings_icon_binary_paths.svg")
        self.card_bin_paths = SettingsOptionCard(
            icon_path=bin_paths_icon,
            title=c.t("UI_LABEL_BINARY_PATHS"),
            subtitle=c.t("UI_SETTINGS_DESC_BINARY_PATHS"),
            app=self.app,
            parent=self
        )
        self.card_bin_paths.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.card_bin_paths._main_layout.setContentsMargins(18, 10, 18, 10)
        self.card_bin_paths._main_layout.setSpacing(6)
        self._groups["UI_LABEL_BINARY_PATHS"] = self.card_bin_paths

        # Mode selector integrated in card_bin_paths header (ctrl_layout)
        if not self.app.running_in_flatpak:
            mode_keys = [c.MODE_BIN_SYSTEM, c.MODE_BIN_LOCAL, c.MODE_BIN_CUSTOM, c.MODE_BIN_FLATPAK]
        else:
            mode_keys = [c.MODE_BIN_SYSTEM, c.MODE_BIN_CUSTOM, c.MODE_BIN_FLATPAK]

        self.combo_settings_mode = NotchedModeSelector(
            tab_title=c.t("UI_LABEL_BIN_MODE").rstrip(":"),
            parent=self,
            app=self.app
        )
        self.combo_settings_mode.setFixedWidth(152)
        for k in mode_keys:
            self.combo_settings_mode.addItem(c.t("UI_BIN_MODES")[k], k)
        current_mode = self.app.config.get(c.CONFIG_KEY_MODE, c.MODE_BIN_SYSTEM)
        idx = self.combo_settings_mode.findData(current_mode)
        if idx >= 0:
            self.combo_settings_mode.setCurrentIndex(idx)
        self.card_bin_paths.ctrl_layout.addWidget(self.combo_settings_mode)
        self.lbl_bin_mode_title = None

        # Flatpak ID row
        self.frame_flatpak_id = QFrame()
        fid_layout = QHBoxLayout(self.frame_flatpak_id)
        fid_layout.setContentsMargins(0, 2, 0, 2)
        fid_layout.setSpacing(8)
        self.lbl_flatpak_id = QLabel(c.t("UI_LABEL_FLATPAK_ID"))
        self.lbl_flatpak_id.setStyleSheet("font-size: 11px; font-weight: 500;")
        fid_layout.addWidget(self.lbl_flatpak_id)
        self.entry_flatpak_id = QLineEdit()
        self.entry_flatpak_id.setText(
            self.app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.MCPELAUNCHER_FLATPAK_ID)
        )
        self.entry_flatpak_id.setFixedHeight(28)
        fid_layout.addWidget(self.entry_flatpak_id, 1)
        self.card_bin_paths._main_layout.addWidget(self.frame_flatpak_id)

        # Binary rows container (expands to distribute rows across available height)
        self.binary_rows_container = QWidget()
        self.binary_rows_container.setStyleSheet("background: transparent;")
        self.binary_rows_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        bin_rows_layout = QVBoxLayout(self.binary_rows_container)
        bin_rows_layout.setContentsMargins(0, 2, 0, 0)
        bin_rows_layout.setSpacing(0)

        self.inputs = {}
        self._binary_labels_map = {}
        self._browse_buttons = []
        self._more_buttons = []
        binary_slots_data = [
            (c.CONFIG_KEY_CLIENT, c.t("UI_LABEL_CLIENT_GAME"), c.t("UI_BIN_DESC_CLIENT")),
            (c.CONFIG_KEY_EXTRACT, c.t("UI_LABEL_EXTRACTOR_APK"), c.t("UI_BIN_DESC_EXTRACT")),
            (c.CONFIG_KEY_SIGNIN_UI, c.t("UI_LABEL_SIGNIN_UI"), c.t("UI_BIN_DESC_SIGNIN_UI")),
            (c.CONFIG_KEY_GPLAYDL, c.t("UI_LABEL_GPLAYDL"), c.t("UI_BIN_DESC_GPLAYDL")),
            (c.CONFIG_KEY_GPLAYVER, c.t("UI_LABEL_GPLAYVER"), c.t("UI_BIN_DESC_GPLAYVER")),
            (c.CONFIG_KEY_WEBVIEW, c.t("UI_LABEL_WEBVIEW_OPTIONAL"), c.t("UI_BIN_DESC_WEBVIEW")),
            (c.CONFIG_KEY_ERROR, c.t("UI_LABEL_ERROR_HANDLER_OPTIONAL"), c.t("UI_BIN_DESC_ERROR")),
            (c.CONFIG_KEY_MSA_DAEMON, c.t("UI_LABEL_MSA_DAEMON"), c.t("UI_BIN_DESC_MSA_DAEMON")),
        ]

        folder_svg = resource_path("assets/media/folder_browse_icon.svg")
        folder_ic = self._get_tinted_icon(folder_svg, 15)
        more_svg = resource_path("assets/media/settings_more_dots.svg")
        more_ic = self._get_tinted_icon(more_svg, 13)
        for key, label_text, desc_text in binary_slots_data:
            clean_title = label_text.rstrip(":")
            row_widget = QWidget()
            row_widget.setStyleSheet("background: transparent;")
            row_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 1, 0, 1)
            row_layout.setSpacing(8)
            row_layout.setAlignment(Qt.AlignVCenter)

            # Left text column: title and description
            t_col = QVBoxLayout()
            t_col.setContentsMargins(0, 0, 0, 0)
            t_col.setSpacing(0)
            t_col.setAlignment(Qt.AlignVCenter)
            lbl_title = QLabel(clean_title)
            lbl_title.setObjectName("BinaryRowTitle")
            lbl_title.setStyleSheet("font-weight: 600; font-size: 11.5px;")
            lbl_desc = QLabel(desc_text)
            lbl_desc.setObjectName("BinaryRowSubtitle")
            lbl_desc.setStyleSheet("font-size: 9.5px;")
            lbl_desc.setWordWrap(True)
            t_col.addWidget(lbl_title)
            t_col.addWidget(lbl_desc)
            t_col_widget = QWidget()
            t_col_widget.setLayout(t_col)
            t_col_widget.setFixedWidth(142)
            row_layout.addWidget(t_col_widget, 0)

            # Path entry
            e = QLineEdit()
            e.setObjectName("BinaryPathEntry")
            e.setText(self.app.config[c.CONFIG_KEY_BINARY_PATHS].get(key, ""))
            e.setFixedHeight(29)
            row_layout.addWidget(e, 1)

            # Browse folder button
            b = QPushButton()
            b.setObjectName("BinaryBrowseBtn")
            b.setIcon(folder_ic)
            b.setIconSize(QSize(15, 15))
            b.setFixedSize(29, 29)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(f"Examinar {clean_title}")
            b.clicked.connect(lambda checked=False, k=key, ent=e: self.browse_path(k, ent))
            row_layout.addWidget(b, 0)
            self._browse_buttons.append(b)

            # More options button (...)
            b_more = QPushButton()
            b_more.setObjectName("BinaryMoreBtn")
            b_more.setIcon(more_ic)
            b_more.setIconSize(QSize(13, 13))
            b_more.setFixedSize(29, 29)
            b_more.setCursor(Qt.PointingHandCursor)
            b_more.setToolTip(f"Opciones de {clean_title}")
            b_more.clicked.connect(lambda checked=False, k=key, ent=e: self._on_binary_more_clicked(k, ent))
            row_layout.addWidget(b_more, 0)
            self._more_buttons.append(b_more)

            bin_rows_layout.addWidget(row_widget, 1)
            self.inputs[key] = (e, b, self.binary_rows_container)
            self._binary_labels_map[key] = (lbl_title, lbl_desc, b_more)

        self.card_bin_paths._main_layout.addWidget(self.binary_rows_container, 1)

        self.lbl_non_custom_mode_info = QLabel("Los binarios se detectan y gestionan automáticamente según el modo seleccionado.")
        self.lbl_non_custom_mode_info.setObjectName("BinaryNonCustomInfo")
        self.lbl_non_custom_mode_info.setStyleSheet("font-size: 11px; padding: 6px 2px;")
        self.lbl_non_custom_mode_info.setWordWrap(True)
        self.card_bin_paths._main_layout.addWidget(self.lbl_non_custom_mode_info)

        # Version info label at bottom of left card
        self.lbl_binary_version = QLabel("")
        self.lbl_binary_version.setObjectName("BinaryVersionInfo")
        self.lbl_binary_version.setStyleSheet("font-size: 10px; padding-top: 1px;")
        self.lbl_binary_version.setWordWrap(True)
        self.card_bin_paths._main_layout.addWidget(self.lbl_binary_version)

        self.launch_left_col.addWidget(self.card_bin_paths, 1)

        # ── Right Column (48% width): Folders + Graphics ──
        self.launch_right_widget = QWidget()
        self.launch_right_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.launch_right_col = QVBoxLayout(self.launch_right_widget)
        self.launch_right_col.setContentsMargins(0, 0, 0, 0)
        self.launch_right_col.setSpacing(6)
        self.launch_grid.addWidget(self.launch_right_widget, 48)

        # Card 2 (Top Right): Carpeta de Binarios (auto-resolución)
        folder_icon_path = resource_path("assets/media/settings_icon_folder.svg")
        self.card_bin_folder = SettingsOptionCard(
            icon_path=folder_icon_path,
            title=c.t("UI_LABEL_BIN_FOLDER").rstrip(":"),
            subtitle=c.t("UI_SETTINGS_DESC_BIN_FOLDER"),
            app=self.app,
            parent=self
        )
        self.card_bin_folder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.card_bin_folder.setMinimumHeight(68)
        self.card_bin_folder._main_layout.setContentsMargins(16, 6, 16, 6)
        self._groups["UI_LABEL_BIN_FOLDER"] = self.card_bin_folder
        self.binfolder_group = self.card_bin_folder

        row_bf = QHBoxLayout()
        row_bf.setContentsMargins(0, 0, 0, 0)
        row_bf.setSpacing(8)

        self.entry_bin_folder = QLineEdit()
        self.entry_bin_folder.setObjectName("BinFolderEntry")
        self.entry_bin_folder.setPlaceholderText(c.t("UI_LABEL_BIN_FOLDER").rstrip(":"))
        self.entry_bin_folder.setFixedHeight(28)
        row_bf.addWidget(self.entry_bin_folder, 1)

        btn_bf = QPushButton()
        btn_bf.setObjectName("FolderBrowseBtn")
        btn_bf.setIcon(folder_ic)
        btn_bf.setIconSize(QSize(14, 14))
        btn_bf.setFixedSize(28, 28)
        btn_bf.setCursor(Qt.PointingHandCursor)
        btn_bf.clicked.connect(self.browse_bin_folder)
        row_bf.addWidget(btn_bf)
        self._browse_buttons.append(btn_bf)

        self.btn_resolve = QPushButton(f"🔍 {c.t('UI_BUTTON_AUTO_RESOLVE')}")
        self.btn_resolve.setObjectName("ResolveButton")
        self.btn_resolve.setFixedHeight(28)
        self.btn_resolve.setCursor(Qt.PointingHandCursor)
        self.btn_resolve.clicked.connect(self.auto_resolve_binaries)
        row_bf.addWidget(self.btn_resolve)

        self.card_bin_folder._main_layout.addLayout(row_bf)
        self.launch_right_col.addWidget(self.card_bin_folder, 0)

        # Card 3 (Middle Right): Carpeta en PATH (mcpelauncher libs)
        self.card_libs = SettingsOptionCard(
            icon_path=folder_icon_path,
            title=c.t("UI_LABEL_MC_LIBS_PATH").rstrip(":"),
            subtitle=c.t("UI_SETTINGS_DESC_MC_LIBS"),
            app=self.app,
            parent=self
        )
        self.card_libs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.card_libs.setMinimumHeight(76)
        self.card_libs._main_layout.setContentsMargins(16, 6, 16, 6)
        self._groups["UI_LABEL_MC_LIBS_PATH"] = self.card_libs
        self.libs_group = self.card_libs

        row_libs = QHBoxLayout()
        row_libs.setContentsMargins(0, 0, 0, 0)
        row_libs.setSpacing(8)

        self.entry_mc_libs = QLineEdit()
        self.entry_mc_libs.setObjectName("LibsEntry")
        self.entry_mc_libs.setText(self.app.config.get(c.CONFIG_KEY_MC_LIBS_PATH, ""))
        self.entry_mc_libs.setPlaceholderText(c.t("UI_LABEL_MC_LIBS_PATH").rstrip(":"))
        self.entry_mc_libs.setFixedHeight(28)
        row_libs.addWidget(self.entry_mc_libs, 1)

        btn_libs = QPushButton()
        btn_libs.setObjectName("FolderBrowseBtn")
        btn_libs.setIcon(folder_ic)
        btn_libs.setIconSize(QSize(14, 14))
        btn_libs.setFixedSize(28, 28)
        btn_libs.setCursor(Qt.PointingHandCursor)
        btn_libs.clicked.connect(self.browse_libs)
        row_libs.addWidget(btn_libs)
        self._browse_buttons.append(btn_libs)

        self.btn_resolve_libs = QPushButton(f"🔍 {c.t('UI_BUTTON_AUTO_RESOLVE')}")
        self.btn_resolve_libs.setObjectName("ResolveButton")
        self.btn_resolve_libs.setFixedHeight(28)
        self.btn_resolve_libs.setCursor(Qt.PointingHandCursor)
        self.btn_resolve_libs.clicked.connect(self.auto_resolve_libs)
        row_libs.addWidget(self.btn_resolve_libs)

        self.card_libs._main_layout.addLayout(row_libs)

        # Info Note below card_libs
        info_note = QFrame()
        info_note.setObjectName("LibsInfoNote")
        info_note_layout = QHBoxLayout(info_note)
        info_note_layout.setContentsMargins(6, 2, 6, 2)
        info_note_layout.setSpacing(6)
        self.lbl_info_icon = QLabel("ℹ")
        self.lbl_info_icon.setObjectName("LibsInfoIcon")
        theme_color = self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
        accent = c.THEME_COLOR_MAP.get(theme_color, "#1f6aa5")
        self.lbl_info_icon.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {accent};")
        info_note_layout.addWidget(self.lbl_info_icon, 0, Qt.AlignVCenter)
        self.lbl_auto_detect_note = QLabel(c.t("UI_SETTINGS_NOTE_AUTO_DETECT"))
        self.lbl_auto_detect_note.setObjectName("AutoDetectNoteText")
        self.lbl_auto_detect_note.setStyleSheet("font-size: 10px;")
        self.lbl_auto_detect_note.setWordWrap(True)
        info_note_layout.addWidget(self.lbl_auto_detect_note, 1)
        self.card_libs._main_layout.addWidget(info_note)

        self.launch_right_col.addWidget(self.card_libs, 0)

        # Connect mode change
        self.combo_settings_mode.currentIndexChanged.connect(
            lambda *args: self.on_settings_mode_change(self.combo_settings_mode.currentText())
        )
        self.on_settings_mode_change(self.combo_settings_mode.currentText())

    def setup_extras_section(self):
        graphics_icon = resource_path("assets/media/settings_icon_graphics.svg")
        self.card_graphics = SettingsOptionCard(
            icon_path=graphics_icon,
            title=c.t("UI_GC_GRAPHICS"),
            subtitle=c.t("UI_SETTINGS_DESC_GRAPHICS"),
            app=self.app,
            parent=self
        )
        self.card_graphics.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.card_graphics._main_layout.setContentsMargins(16, 8, 16, 8)
        self.card_graphics._main_layout.setSpacing(2)
        self._groups["UI_GC_GRAPHICS"] = self.card_graphics

        # Custom args row
        row_custom_env = QHBoxLayout()
        row_custom_env.setContentsMargins(0, 0, 0, 0)
        row_custom_env.setSpacing(8)

        self.cb_custom_env = QCheckBox(c.t("UI_CUSTOM_ARGS_CHECKBOX"))
        self.cb_custom_env.setObjectName("SettingsCheckbox")
        self.cb_custom_env.setChecked(self.app.config.get(c.CONFIG_KEY_CUSTOM_ENV_ENABLED, False))
        self.cb_custom_env.stateChanged.connect(
            lambda state: (self.toggle_custom_env(),
                           self.app.config_manager.set(c.CONFIG_KEY_CUSTOM_ENV_ENABLED, state == Qt.Checked.value))
        )
        row_custom_env.addWidget(self.cb_custom_env)

        self.btn_help_env = SettingsHelpButton(
            c.t("UI_CUSTOM_ARGS_CHECKBOX"),
            c.t("UI_CUSTOM_ARGS_TOOLTIP"),
            parent=self, app=self.app
        )
        row_custom_env.addWidget(self.btn_help_env)
        row_custom_env.addStretch()
        self.card_graphics._main_layout.addLayout(row_custom_env)

        # Custom args input field (fixed height so it does not balloon vertically)
        self.f_custom_vars = QFrame()
        self.f_custom_vars.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.f_custom_vars.setFixedHeight(30)
        cv_layout = QHBoxLayout(self.f_custom_vars)
        cv_layout.setContentsMargins(16, 0, 0, 0)
        cv_layout.setSpacing(8)
        self.lbl_custom_vars_title = QLabel(c.t("UI_CUSTOM_ARGS_LABEL"))
        self.lbl_custom_vars_title.setStyleSheet("font-size: 11px; font-weight: 500;")
        cv_layout.addWidget(self.lbl_custom_vars_title)
        self.entry_custom_vars = QLineEdit()
        self.entry_custom_vars.setObjectName("CustomVarsEntry")
        self.entry_custom_vars.setText(self.app.config.get(c.CONFIG_KEY_CUSTOM_ENV_VARS, ""))
        self.entry_custom_vars.setFixedHeight(26)
        self.entry_custom_vars.editingFinished.connect(
            lambda: self.app.config_manager.set(c.CONFIG_KEY_CUSTOM_ENV_VARS, self.entry_custom_vars.text())
        )
        cv_layout.addWidget(self.entry_custom_vars, 1)
        self.card_graphics._main_layout.addWidget(self.f_custom_vars)

        # Divider line
        sep = QFrame()
        sep.setObjectName("GraphicsDivider")
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        self.card_graphics._main_layout.addWidget(sep)

        # 7 performance checkboxes container (expands proportionally across card height)
        self.perf_checkboxes_container = QWidget()
        self.perf_checkboxes_container.setStyleSheet("background: transparent;")
        self.perf_checkboxes_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        perf_layout = QVBoxLayout(self.perf_checkboxes_container)
        perf_layout.setContentsMargins(0, 4, 0, 4)
        perf_layout.setSpacing(0)

        self._perf_checkboxes_map = []
        checkboxes_data = [
            ("UI_GAMEMODE_CHECKBOX", c.CONFIG_KEY_GAMEMODE_ENABLED, "UI_GAMEMODE_TOOLTIP"),
            ("UI_NVIDIA_PRIME_CHECKBOX", c.CONFIG_KEY_NVIDIA_PRIME, "UI_NVIDIA_PRIME_TOOLTIP"),
            ("UI_ZINK_CHECKBOX", c.CONFIG_KEY_ZINK_MODE, "UI_ZINK_TOOLTIP"),
            ("UI_FORCE_OPENGL_CHECKBOX", c.CONFIG_KEY_FORCE_OPENGL, "UI_FORCE_OPENGL_TOOLTIP"),
            ("UI_FORCE_GLES32_CHECKBOX", c.CONFIG_KEY_FORCE_GLES32, "UI_FORCE_GLES32_TOOLTIP"),
            ("UI_DISABLE_VSYNC_CHECKBOX", c.CONFIG_KEY_DISABLE_VSYNC, "UI_DISABLE_VSYNC_TOOLTIP"),
            ("UI_FORCE_DISCRETE_GPU_CHECKBOX", c.CONFIG_KEY_FORCE_DISCRETE_GPU, "UI_FORCE_DISCRETE_GPU_TOOLTIP"),
        ]

        for label_key, key, tooltip_key in checkboxes_data:
            label = c.t(label_key)
            tooltip = c.t(tooltip_key)
            row_w = QWidget()
            row_w.setStyleSheet("background: transparent;")
            row_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            row = QHBoxLayout(row_w)
            row.setContentsMargins(0, 1, 0, 1)
            row.setSpacing(6)
            row.setAlignment(Qt.AlignVCenter)
            cb = QCheckBox(label)
            cb.setObjectName("SettingsCheckbox")
            cb.setChecked(self.app.config.get(key, False))
            cb.stateChanged.connect(lambda state, k=key: self.app.config_manager.set(k, state == Qt.Checked.value))
            row.addWidget(cb)
            btn_info = SettingsHelpButton(label, tooltip, parent=self, app=self.app)
            row.addWidget(btn_info)
            row.addStretch()
            perf_layout.addWidget(row_w, 1)
            self.checks[key] = cb
            self._perf_checkboxes_map.append((cb, btn_info, label_key, tooltip_key))

        if c.CONFIG_KEY_GAMEMODE_ENABLED in self.checks:
            self.checks[c.CONFIG_KEY_GAMEMODE_ENABLED].stateChanged.connect(
                lambda state: self.app.sync_gamemode_ui(state == Qt.Checked.value)
            )

        self.card_graphics._main_layout.addWidget(self.perf_checkboxes_container, 1)

        if hasattr(self, "launch_right_col"):
            self.launch_right_col.addWidget(self.card_graphics, 1)
        else:
            self.scroll_layout.addWidget(self.card_graphics)
        self.toggle_custom_env()

    def setup_compatibility_section(self):
        """Backward-compatible alias kept for imports/reference."""
        return self.setup_extras_section()

    # ── Appearance ────────────────────────────────────────────────

    def setup_appearance_section(self):
        mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        theme_color = self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
        accent = c.THEME_COLOR_MAP.get(theme_color, "#1f6aa5")
        text_color = "#DCE4EE" if mode == "Dark" else "#242424"

        # ── Card 1: Modo de Apariencia & Tema de Color ──
        self.card_theme_mode = SettingsSectionCard(
            title=c.t("UI_SECTION_APPEARANCE"),
            parent=self,
            is_dark=(mode == "Dark"),
            app=self.app
        )
        self._groups["UI_SECTION_APPEARANCE"] = self.card_theme_mode

        # Mode row: Label + Capsule Top-Bar Style Buttons
        mode_header = QHBoxLayout()
        mode_header.setSpacing(12)
        mode_label = QLabel(c.t("UI_LABEL_APPEARANCE_MODE"))
        mode_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {text_color}; background: transparent;")
        self._appearance_labels.append(mode_label)
        mode_header.addWidget(mode_label)

        self.mode_group = QButtonGroup(self)
        self.modes = {}
        for k, v in c.t("UI_APPEARANCE_MODES").items():
            btn = TopBarModeButton(v, parent=self, app=self.app)
            btn.set_accent_color(accent)
            btn.set_is_dark(mode == "Dark")
            btn.setFixedWidth(112)
            self.mode_group.addButton(btn)
            self.modes[k] = btn
            if k == mode:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked=False, k=k: self._on_mode_btn_clicked(k))
            mode_header.addWidget(btn)
        mode_header.addStretch()
        self.card_theme_mode.main_layout.addLayout(mode_header)

        # Comic color panel (without 🎨 emoji)
        self.comic_color_panel = ComicColorPanel(
            selected_key=theme_color,
            is_dark=(mode == "Dark"),
            parent=self,
            app=self.app
        )
        self.comic_color_panel.themeSelected.connect(self._on_theme_btn_clicked)
        self.card_theme_mode.main_layout.addWidget(self.comic_color_panel)

        self.scroll_layout.addWidget(self.card_theme_mode)
        self._add_spacer()

        # ── Card 2: Estilo de Lista de Versiones ──
        self.card_version_style = SettingsSectionCard(
            title=c.t("UI_LABEL_VERSION_LIST_STYLE").rstrip(":"),
            parent=self,
            is_dark=(mode == "Dark"),
            app=self.app
        )
        self._groups["UI_LABEL_VERSION_LIST_STYLE"] = self.card_version_style

        style_row = QHBoxLayout()
        lbl_style = QLabel(c.t("UI_LABEL_STYLE"))
        lbl_style.setFixedWidth(150)
        lbl_style.setStyleSheet(f"font-weight: bold; font-size: 12.5px; color: {text_color}; background: transparent;")
        style_row.addWidget(lbl_style)

        self.combo_list_style = QComboBox()
        for k, v in c.t("UI_LIST_STYLES").items():
            self.combo_list_style.addItem(v, k)
        current_style = self.app.config.get(c.CONFIG_KEY_VERSION_LIST_STYLE, c.STYLE_LIST)
        idx = self.combo_list_style.findData(current_style)
        if idx >= 0:
            self.combo_list_style.setCurrentIndex(idx)
        self.combo_list_style.setFixedWidth(170)
        self.combo_list_style.currentTextChanged.connect(self.on_style_combo_changed)
        style_row.addWidget(self.combo_list_style)
        style_row.addStretch()
        self.card_version_style.main_layout.addLayout(style_row)

        self._version_style_labels = [lbl_style]

        # 4 Version Sliders with GlassCapsuleSlider
        # 1. Icon Size
        row_icon = QHBoxLayout()
        lbl_icon = QLabel(c.t("UI_LABEL_ICON_SIZE"))
        lbl_icon.setFixedWidth(150)
        lbl_icon.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        row_icon.addWidget(lbl_icon)
        self.slider_icon = GlassCapsuleSlider(Qt.Horizontal, parent=self, app=self.app)
        self.slider_icon.set_accent_color(accent)
        self.slider_icon.set_is_dark(mode == "Dark")
        self.slider_icon.setRange(16, 128)
        self.slider_icon.setValue(self.app.config.get(c.CONFIG_KEY_VERSION_ICON_SIZE, 96))
        self.slider_icon.valueChanged.connect(self.on_appearance_setting_change)
        self.slider_icon.sliderReleased.connect(self.on_appearance_released)
        row_icon.addWidget(self.slider_icon, 1)
        self.lbl_icon_val = QLabel(str(self.slider_icon.value()))
        self.lbl_icon_val.setFixedWidth(40)
        self.lbl_icon_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_icon_val.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color}; background: transparent;")
        self.slider_icon.valueChanged.connect(lambda v: self.lbl_icon_val.setText(str(v)))
        row_icon.addWidget(self.lbl_icon_val)
        self.card_version_style.main_layout.addLayout(row_icon)

        # 2. Title Size
        row_title = QHBoxLayout()
        lbl_title = QLabel(c.t("UI_LABEL_TITLE_SIZE"))
        lbl_title.setFixedWidth(150)
        lbl_title.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        row_title.addWidget(lbl_title)
        self.slider_title = GlassCapsuleSlider(Qt.Horizontal, parent=self, app=self.app)
        self.slider_title.set_accent_color(accent)
        self.slider_title.set_is_dark(mode == "Dark")
        self.slider_title.setRange(8, 32)
        self.slider_title.setValue(self.app.config.get(c.CONFIG_KEY_VERSION_TITLE_SIZE, 16))
        self.slider_title.valueChanged.connect(self.on_appearance_setting_change)
        self.slider_title.sliderReleased.connect(self.on_appearance_released)
        row_title.addWidget(self.slider_title, 1)
        self.lbl_title_val = QLabel(str(self.slider_title.value()))
        self.lbl_title_val.setFixedWidth(40)
        self.lbl_title_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_title_val.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color}; background: transparent;")
        self.slider_title.valueChanged.connect(lambda v: self.lbl_title_val.setText(str(v)))
        row_title.addWidget(self.lbl_title_val)
        self.card_version_style.main_layout.addLayout(row_title)

        # 3. Card Width
        row_cw = QHBoxLayout()
        lbl_cw = QLabel(c.t("UI_LABEL_CARD_WIDTH"))
        lbl_cw.setFixedWidth(150)
        lbl_cw.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        row_cw.addWidget(lbl_cw)
        self.slider_card_width = GlassCapsuleSlider(Qt.Horizontal, parent=self, app=self.app)
        self.slider_card_width.set_accent_color(accent)
        self.slider_card_width.set_is_dark(mode == "Dark")
        self.slider_card_width.setRange(80, 400)
        self.slider_card_width.setValue(self.app.config.get(c.CONFIG_KEY_VERSION_CARD_WIDTH, 200))
        self.slider_card_width.valueChanged.connect(self.on_appearance_setting_change)
        self.slider_card_width.sliderReleased.connect(self.on_appearance_released)
        row_cw.addWidget(self.slider_card_width, 1)
        self.lbl_card_width_val = QLabel(str(self.slider_card_width.value()))
        self.lbl_card_width_val.setFixedWidth(40)
        self.lbl_card_width_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_card_width_val.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color}; background: transparent;")
        self.slider_card_width.valueChanged.connect(lambda v: self.lbl_card_width_val.setText(str(v)))
        row_cw.addWidget(self.lbl_card_width_val)
        self.card_version_style.main_layout.addLayout(row_cw)

        # 4. Card Height
        row_ch = QHBoxLayout()
        lbl_ch = QLabel(c.t("UI_LABEL_CARD_HEIGHT"))
        lbl_ch.setFixedWidth(150)
        lbl_ch.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        row_ch.addWidget(lbl_ch)
        self.slider_card_height = GlassCapsuleSlider(Qt.Horizontal, parent=self, app=self.app)
        self.slider_card_height.set_accent_color(accent)
        self.slider_card_height.set_is_dark(mode == "Dark")
        self.slider_card_height.setRange(60, 300)
        self.slider_card_height.setValue(self.app.config.get(c.CONFIG_KEY_VERSION_CARD_HEIGHT, 200))
        self.slider_card_height.valueChanged.connect(self.on_appearance_setting_change)
        self.slider_card_height.sliderReleased.connect(self.on_appearance_released)
        row_ch.addWidget(self.slider_card_height, 1)
        self.lbl_card_height_val = QLabel(str(self.slider_card_height.value()))
        self.lbl_card_height_val.setFixedWidth(40)
        self.lbl_card_height_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_card_height_val.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color}; background: transparent;")
        self.slider_card_height.valueChanged.connect(lambda v: self.lbl_card_height_val.setText(str(v)))
        row_ch.addWidget(self.lbl_card_height_val)
        self.card_version_style.main_layout.addLayout(row_ch)

        self._version_style_labels = [lbl_style, lbl_icon, lbl_title, lbl_cw, lbl_ch]
        self._version_val_labels = [self.lbl_icon_val, self.lbl_title_val, self.lbl_card_width_val, self.lbl_card_height_val]
        self.lbl_appearance_mode = mode_label
        self.lbl_title_list_style = lbl_style
        self.lbl_title_icon_size = lbl_icon
        self.lbl_title_title_size = lbl_title
        self.lbl_title_card_width = lbl_cw
        self.lbl_title_card_height = lbl_ch

        self.scroll_layout.addWidget(self.card_version_style)
        self._add_spacer()

    def setup_section_opacity_section(self):
        mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        theme_color = self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
        accent = c.THEME_COLOR_MAP.get(theme_color, "#1f6aa5")
        text_color = "#DCE4EE" if mode == "Dark" else "#242424"

        # ── Card 3: Opacidad de Sección ──
        self.card_section_opacity = SettingsSectionCard(
            title=c.t("UI_LABEL_SECTION_OPACITY").rstrip(":"),
            parent=self,
            is_dark=(mode == "Dark"),
            app=self.app
        )
        self._groups["UI_LABEL_SECTION_OPACITY"] = self.card_section_opacity

        row = QHBoxLayout()
        self.slider_section_opacity = GlassCapsuleSlider(Qt.Horizontal, parent=self, app=self.app)
        self.slider_section_opacity.set_accent_color(accent)
        self.slider_section_opacity.set_is_dark(mode == "Dark")
        self.slider_section_opacity.setRange(0, 100)
        self.slider_section_opacity.setValue(self.app.config.get(c.CONFIG_KEY_SECTION_OPACITY, 100))
        self.slider_section_opacity.valueChanged.connect(self.on_section_opacity_change)
        self.slider_section_opacity.sliderReleased.connect(self.on_section_opacity_released)
        row.addWidget(self.slider_section_opacity, 1)

        self.lbl_section_opacity = QLabel(str(self.slider_section_opacity.value()))
        self.lbl_section_opacity.setFixedWidth(40)
        self.lbl_section_opacity.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_section_opacity.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color}; background: transparent;")
        self.slider_section_opacity.valueChanged.connect(lambda v: self.lbl_section_opacity.setText(str(v)))
        row.addWidget(self.lbl_section_opacity)

        self.card_section_opacity.main_layout.addLayout(row)
        self.scroll_layout.addWidget(self.card_section_opacity)
        self._add_spacer()

    def setup_background_section(self):
        mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        theme_color = self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
        accent = c.THEME_COLOR_MAP.get(theme_color, "#1f6aa5")
        is_dark = (mode == "Dark")
        text_color = "#DCE4EE" if is_dark else "#242424"

        folder_svg = resource_path("assets/media/settings_icon_folder.svg")
        folder_ic = self._get_tinted_icon(folder_svg, 15)
        trash_svg = resource_path("assets/media/trash_delete_icon.svg")
        trash_ic = self._get_tinted_icon(trash_svg, 14, color="#ef4444")

        # ── Card 4: Fondo Personalizado ──
        self.card_background = SettingsSectionCard(
            title=c.t("UI_SECTION_BACKGROUND"),
            parent=self,
            is_dark=is_dark,
            app=self.app
        )
        self._groups["UI_SECTION_BACKGROUND"] = self.card_background

        # 1. Preview Widget for Background Image
        self.bg_preview = ImagePreviewCard(
            placeholder_title=c.t("UI_BG_PREVIEW_TITLE"),
            placeholder_hint=c.t("UI_BG_PREVIEW_HINT"),
            parent=self,
            is_dark=is_dark,
            app=self.app
        )
        bg_curr = self.app.config.get(c.CONFIG_KEY_BG_PATH, "")
        self.bg_preview.set_image(bg_curr)
        self.card_background.main_layout.addWidget(self.bg_preview)

        # 2. Path input row (Label + QLineEdit + Browse Button + Delete Button)
        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        lbl_bg_path = QLabel(c.t("UI_LABEL_BG_PATH"))
        lbl_bg_path.setFixedWidth(150)
        lbl_bg_path.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        path_row.addWidget(lbl_bg_path)
        self.lbl_title_bg_path = lbl_bg_path

        self.entry_bg_path = QLineEdit()
        self.entry_bg_path.setObjectName("BackgroundPathEntry")
        self.entry_bg_path.setText(bg_curr)
        self.entry_bg_path.setPlaceholderText(c.t("UI_BG_PLACEHOLDER_PATH"))
        self.entry_bg_path.setFixedHeight(29)
        self.entry_bg_path.textChanged.connect(self.on_bg_change)
        path_row.addWidget(self.entry_bg_path, 1)

        # Allow dragging image onto preview to set text
        self.bg_preview.imageDropped.connect(self.entry_bg_path.setText)

        self.btn_browse_bg = QPushButton()
        self.btn_browse_bg.setObjectName("FolderBrowseBtn")
        self.btn_browse_bg.setIcon(folder_ic)
        self.btn_browse_bg.setIconSize(QSize(15, 15))
        self.btn_browse_bg.setFixedSize(29, 29)
        self.btn_browse_bg.setCursor(Qt.PointingHandCursor)
        self.btn_browse_bg.setToolTip(c.t("UI_TOOLTIP_BROWSE_BG"))
        self.btn_browse_bg.clicked.connect(self.browse_bg)
        path_row.addWidget(self.btn_browse_bg)
        self._browse_buttons.append(self.btn_browse_bg)

        self.btn_clear_bg = QPushButton()
        self.btn_clear_bg.setObjectName("FolderClearBtn")
        self.btn_clear_bg.setIcon(trash_ic)
        self.btn_clear_bg.setIconSize(QSize(14, 14))
        self.btn_clear_bg.setFixedSize(29, 29)
        self.btn_clear_bg.setCursor(Qt.PointingHandCursor)
        self.btn_clear_bg.setToolTip(c.t("UI_SETTINGS_RESET_BG_TOOLTIP"))
        self.btn_clear_bg.clicked.connect(self.clear_bg)
        path_row.addWidget(self.btn_clear_bg)
        self._clear_buttons.append(self.btn_clear_bg)

        self.card_background.main_layout.addLayout(path_row)

        self._bg_labels = [lbl_bg_path]
        self._bg_val_labels = []

        # 3. Sliders: Posición X, Posición Y, Opacidad, Zoom
        # Posición X
        row_x = QHBoxLayout()
        lbl_x = QLabel(c.t("UI_LABEL_BG_X"))
        lbl_x.setFixedWidth(150)
        lbl_x.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        row_x.addWidget(lbl_x)
        self._bg_labels.append(lbl_x)
        self.lbl_title_bg_x = lbl_x

        self.slider_bg_x = GlassCapsuleSlider(Qt.Horizontal, parent=self, app=self.app)
        self.slider_bg_x.set_accent_color(accent)
        self.slider_bg_x.set_is_dark(is_dark)
        self.slider_bg_x.setRange(-1000, 1000)
        self.slider_bg_x.setValue(self.app.config.get(c.CONFIG_KEY_BG_X, 0))
        self.slider_bg_x.valueChanged.connect(self.on_bg_change)
        self.slider_bg_x.sliderReleased.connect(self.on_bg_released)
        row_x.addWidget(self.slider_bg_x, 1)

        self.lbl_bg_x = QLabel(str(self.slider_bg_x.value()))
        self.lbl_bg_x.setFixedWidth(40)
        self.lbl_bg_x.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_bg_x.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color}; background: transparent;")
        self.slider_bg_x.valueChanged.connect(lambda v: self.lbl_bg_x.setText(str(v)))
        row_x.addWidget(self.lbl_bg_x)
        self._bg_val_labels.append(self.lbl_bg_x)
        self.card_background.main_layout.addLayout(row_x)

        # Posición Y
        row_y = QHBoxLayout()
        lbl_y = QLabel(c.t("UI_LABEL_BG_Y"))
        lbl_y.setFixedWidth(150)
        lbl_y.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        row_y.addWidget(lbl_y)
        self._bg_labels.append(lbl_y)
        self.lbl_title_bg_y = lbl_y

        self.slider_bg_y = GlassCapsuleSlider(Qt.Horizontal, parent=self, app=self.app)
        self.slider_bg_y.set_accent_color(accent)
        self.slider_bg_y.set_is_dark(is_dark)
        self.slider_bg_y.setRange(-1000, 1000)
        self.slider_bg_y.setValue(self.app.config.get(c.CONFIG_KEY_BG_Y, 0))
        self.slider_bg_y.valueChanged.connect(self.on_bg_change)
        self.slider_bg_y.sliderReleased.connect(self.on_bg_released)
        row_y.addWidget(self.slider_bg_y, 1)

        self.lbl_bg_y = QLabel(str(self.slider_bg_y.value()))
        self.lbl_bg_y.setFixedWidth(40)
        self.lbl_bg_y.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_bg_y.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color}; background: transparent;")
        self.slider_bg_y.valueChanged.connect(lambda v: self.lbl_bg_y.setText(str(v)))
        row_y.addWidget(self.lbl_bg_y)
        self._bg_val_labels.append(self.lbl_bg_y)
        self.card_background.main_layout.addLayout(row_y)

        # Opacidad
        row_op = QHBoxLayout()
        lbl_op = QLabel(c.t("UI_LABEL_BG_OPACITY"))
        lbl_op.setFixedWidth(150)
        lbl_op.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        row_op.addWidget(lbl_op)
        self._bg_labels.append(lbl_op)
        self.lbl_title_bg_opacity = lbl_op

        self.slider_bg_opacity = GlassCapsuleSlider(Qt.Horizontal, parent=self, app=self.app)
        self.slider_bg_opacity.set_accent_color(accent)
        self.slider_bg_opacity.set_is_dark(is_dark)
        self.slider_bg_opacity.setRange(0, 100)
        self.slider_bg_opacity.setValue(self.app.config.get(c.CONFIG_KEY_BG_OPACITY, 100))
        self.slider_bg_opacity.valueChanged.connect(self.on_bg_change)
        self.slider_bg_opacity.sliderReleased.connect(self.on_bg_released)
        row_op.addWidget(self.slider_bg_opacity, 1)

        self.lbl_bg_opacity = QLabel(str(self.slider_bg_opacity.value()))
        self.lbl_bg_opacity.setFixedWidth(40)
        self.lbl_bg_opacity.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_bg_opacity.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color}; background: transparent;")
        self.slider_bg_opacity.valueChanged.connect(lambda v: self.lbl_bg_opacity.setText(str(v)))
        row_op.addWidget(self.lbl_bg_opacity)
        self._bg_val_labels.append(self.lbl_bg_opacity)
        self.card_background.main_layout.addLayout(row_op)

        # Zoom
        row_zm = QHBoxLayout()
        lbl_zm = QLabel(c.t("UI_LABEL_BG_ZOOM"))
        lbl_zm.setFixedWidth(150)
        lbl_zm.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        row_zm.addWidget(lbl_zm)
        self._bg_labels.append(lbl_zm)
        self.lbl_title_bg_zoom = lbl_zm

        self.slider_bg_zoom = GlassCapsuleSlider(Qt.Horizontal, parent=self, app=self.app)
        self.slider_bg_zoom.set_accent_color(accent)
        self.slider_bg_zoom.set_is_dark(is_dark)
        self.slider_bg_zoom.setRange(10, 500)
        self.slider_bg_zoom.setValue(self.app.config.get(c.CONFIG_KEY_BG_ZOOM, 100))
        self.slider_bg_zoom.valueChanged.connect(self.on_bg_change)
        self.slider_bg_zoom.sliderReleased.connect(self.on_bg_released)
        row_zm.addWidget(self.slider_bg_zoom, 1)

        self.lbl_bg_zoom = QLabel(str(self.slider_bg_zoom.value()))
        self.lbl_bg_zoom.setFixedWidth(40)
        self.lbl_bg_zoom.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_bg_zoom.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color}; background: transparent;")
        self.slider_bg_zoom.valueChanged.connect(lambda v: self.lbl_bg_zoom.setText(str(v)))
        row_zm.addWidget(self.lbl_bg_zoom)
        self._bg_val_labels.append(self.lbl_bg_zoom)
        self.card_background.main_layout.addLayout(row_zm)

        self.scroll_layout.addWidget(self.card_background)
        self._add_spacer()

    def setup_sticker_section(self):
        mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        theme_color = self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
        accent = c.THEME_COLOR_MAP.get(theme_color, "#1f6aa5")
        is_dark = (mode == "Dark")
        text_color = "#DCE4EE" if is_dark else "#242424"

        folder_svg = resource_path("assets/media/settings_icon_folder.svg")
        folder_ic = self._get_tinted_icon(folder_svg, 15)
        trash_svg = resource_path("assets/media/trash_delete_icon.svg")
        trash_ic = self._get_tinted_icon(trash_svg, 14, color="#ef4444")

        # ── Card 5: Sticker / Watermark ──
        self.card_sticker = SettingsSectionCard(
            title=c.t("UI_SECTION_STICKER"),
            parent=self,
            is_dark=is_dark,
            app=self.app
        )
        self._groups["UI_SECTION_STICKER"] = self.card_sticker

        self._sticker_labels = []
        self._sticker_val_labels = []

        # 1. Preview Widget for Sticker
        self.sticker_preview = ImagePreviewCard(
            placeholder_title=c.t("UI_STICKER_PREVIEW_TITLE"),
            placeholder_hint=c.t("UI_STICKER_PREVIEW_HINT"),
            parent=self,
            is_dark=is_dark,
            app=self.app
        )
        self.card_sticker.main_layout.addWidget(self.sticker_preview)

        # 2. Dropdown rows: Modo & Esquina
        # Modo
        row_mode = QHBoxLayout()
        row_mode.setSpacing(8)
        lbl_sm = QLabel(c.t("UI_LABEL_STICKER_MODE"))
        lbl_sm.setFixedWidth(150)
        lbl_sm.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        row_mode.addWidget(lbl_sm)
        self._sticker_labels.append(lbl_sm)
        self.lbl_title_sticker_mode = lbl_sm

        self.combo_sticker_mode = QComboBox()
        mode_map = c.t("UI_STICKER_MODES")
        for k, v in mode_map.items():
            self.combo_sticker_mode.addItem(v, k)
        curr_mode = self.app.config.get(c.CONFIG_KEY_STICKER_MODE, "none")
        idx = self.combo_sticker_mode.findData(curr_mode)
        if idx >= 0:
            self.combo_sticker_mode.setCurrentIndex(idx)
        self.combo_sticker_mode.setFixedWidth(170)
        self.combo_sticker_mode.currentTextChanged.connect(self.on_sticker_change)
        row_mode.addWidget(self.combo_sticker_mode)
        row_mode.addStretch()
        self.card_sticker.main_layout.addLayout(row_mode)

        # Esquina
        row_corner = QHBoxLayout()
        row_corner.setSpacing(8)
        lbl_sc = QLabel(c.t("UI_LABEL_STICKER_CORNER"))
        lbl_sc.setFixedWidth(150)
        lbl_sc.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        row_corner.addWidget(lbl_sc)
        self._sticker_labels.append(lbl_sc)
        self.lbl_title_sticker_corner = lbl_sc

        self.combo_sticker_corner = QComboBox()
        corner_map = c.t("UI_STICKER_CORNERS")
        for k, v in corner_map.items():
            self.combo_sticker_corner.addItem(v, k)
        curr_corner = self.app.config.get(c.CONFIG_KEY_STICKER_CORNER, "bottom-right")
        idx = self.combo_sticker_corner.findData(curr_corner)
        if idx >= 0:
            self.combo_sticker_corner.setCurrentIndex(idx)
        self.combo_sticker_corner.setFixedWidth(170)
        self.combo_sticker_corner.currentTextChanged.connect(self.on_sticker_change)
        row_corner.addWidget(self.combo_sticker_corner)
        row_corner.addStretch()
        self.card_sticker.main_layout.addLayout(row_corner)

        # 3. Content input row (Label + QLineEdit + Browse Button + Delete Button)
        content_row = QHBoxLayout()
        content_row.setSpacing(8)

        lbl_content = QLabel(c.t("UI_LABEL_STICKER_CONTENT"))
        lbl_content.setFixedWidth(150)
        lbl_content.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        content_row.addWidget(lbl_content)
        self._sticker_labels.append(lbl_content)
        self.lbl_title_sticker_content = lbl_content

        st_content = self.app.config.get(c.CONFIG_KEY_STICKER_CONTENT, "")
        self.entry_sticker_content = QLineEdit()
        self.entry_sticker_content.setObjectName("StickerContentEntry")
        self.entry_sticker_content.setText(st_content)
        self.entry_sticker_content.setPlaceholderText(c.t("UI_STICKER_PLACEHOLDER_CONTENT"))
        self.entry_sticker_content.setFixedHeight(29)
        self.entry_sticker_content.textChanged.connect(self.on_sticker_change)
        content_row.addWidget(self.entry_sticker_content, 1)

        self.sticker_preview.imageDropped.connect(self.entry_sticker_content.setText)

        self.btn_browse_sticker = QPushButton()
        self.btn_browse_sticker.setObjectName("FolderBrowseBtn")
        self.btn_browse_sticker.setIcon(folder_ic)
        self.btn_browse_sticker.setIconSize(QSize(15, 15))
        self.btn_browse_sticker.setFixedSize(29, 29)
        self.btn_browse_sticker.setCursor(Qt.PointingHandCursor)
        self.btn_browse_sticker.setToolTip(c.t("UI_TOOLTIP_BROWSE_STICKER"))
        self.btn_browse_sticker.clicked.connect(self.browse_sticker)
        content_row.addWidget(self.btn_browse_sticker)
        self._browse_buttons.append(self.btn_browse_sticker)

        self.btn_clear_sticker = QPushButton()
        self.btn_clear_sticker.setObjectName("FolderClearBtn")
        self.btn_clear_sticker.setIcon(trash_ic)
        self.btn_clear_sticker.setIconSize(QSize(14, 14))
        self.btn_clear_sticker.setFixedSize(29, 29)
        self.btn_clear_sticker.setCursor(Qt.PointingHandCursor)
        self.btn_clear_sticker.setToolTip(c.t("UI_TOOLTIP_CLEAR_STICKER"))
        self.btn_clear_sticker.clicked.connect(self.clear_sticker)
        content_row.addWidget(self.btn_clear_sticker)
        self._clear_buttons.append(self.btn_clear_sticker)

        self.card_sticker.main_layout.addLayout(content_row)

        # 4. Sliders: Distancia X, Distancia Y, Zoom Sticker, Opacidad
        # Distancia X
        row_sx = QHBoxLayout()
        lbl_sx = QLabel(c.t("UI_LABEL_STICKER_X"))
        lbl_sx.setFixedWidth(150)
        lbl_sx.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        row_sx.addWidget(lbl_sx)
        self._sticker_labels.append(lbl_sx)
        self.lbl_title_sticker_x = lbl_sx

        self.slider_sticker_x = GlassCapsuleSlider(Qt.Horizontal, parent=self, app=self.app)
        self.slider_sticker_x.set_accent_color(accent)
        self.slider_sticker_x.set_is_dark(is_dark)
        self.slider_sticker_x.setRange(0, 500)
        self.slider_sticker_x.setValue(self.app.config.get(c.CONFIG_KEY_STICKER_X, 10))
        self.slider_sticker_x.valueChanged.connect(self.on_sticker_change)
        self.slider_sticker_x.sliderReleased.connect(self.on_sticker_released)
        row_sx.addWidget(self.slider_sticker_x, 1)

        self.lbl_sticker_x = QLabel(str(self.slider_sticker_x.value()))
        self.lbl_sticker_x.setFixedWidth(40)
        self.lbl_sticker_x.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_sticker_x.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color}; background: transparent;")
        self.slider_sticker_x.valueChanged.connect(lambda v: self.lbl_sticker_x.setText(str(v)))
        row_sx.addWidget(self.lbl_sticker_x)
        self._sticker_val_labels.append(self.lbl_sticker_x)
        self.card_sticker.main_layout.addLayout(row_sx)

        # Distancia Y
        row_sy = QHBoxLayout()
        lbl_sy = QLabel(c.t("UI_LABEL_STICKER_Y"))
        lbl_sy.setFixedWidth(150)
        lbl_sy.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        row_sy.addWidget(lbl_sy)
        self._sticker_labels.append(lbl_sy)
        self.lbl_title_sticker_y = lbl_sy

        self.slider_sticker_y = GlassCapsuleSlider(Qt.Horizontal, parent=self, app=self.app)
        self.slider_sticker_y.set_accent_color(accent)
        self.slider_sticker_y.set_is_dark(is_dark)
        self.slider_sticker_y.setRange(0, 500)
        self.slider_sticker_y.setValue(self.app.config.get(c.CONFIG_KEY_STICKER_Y, 10))
        self.slider_sticker_y.valueChanged.connect(self.on_sticker_change)
        self.slider_sticker_y.sliderReleased.connect(self.on_sticker_released)
        row_sy.addWidget(self.slider_sticker_y, 1)

        self.lbl_sticker_y = QLabel(str(self.slider_sticker_y.value()))
        self.lbl_sticker_y.setFixedWidth(40)
        self.lbl_sticker_y.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_sticker_y.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color}; background: transparent;")
        self.slider_sticker_y.valueChanged.connect(lambda v: self.lbl_sticker_y.setText(str(v)))
        row_sy.addWidget(self.lbl_sticker_y)
        self._sticker_val_labels.append(self.lbl_sticker_y)
        self.card_sticker.main_layout.addLayout(row_sy)

        # Zoom Sticker
        row_sz = QHBoxLayout()
        lbl_sz = QLabel(c.t("UI_LABEL_STICKER_ZOOM"))
        lbl_sz.setFixedWidth(150)
        lbl_sz.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        row_sz.addWidget(lbl_sz)
        self._sticker_labels.append(lbl_sz)
        self.lbl_title_sticker_zoom = lbl_sz

        self.slider_sticker_zoom = GlassCapsuleSlider(Qt.Horizontal, parent=self, app=self.app)
        self.slider_sticker_zoom.set_accent_color(accent)
        self.slider_sticker_zoom.set_is_dark(is_dark)
        self.slider_sticker_zoom.setRange(10, 500)
        self.slider_sticker_zoom.setValue(self.app.config.get(c.CONFIG_KEY_STICKER_ZOOM, 100))
        self.slider_sticker_zoom.valueChanged.connect(self.on_sticker_change)
        self.slider_sticker_zoom.sliderReleased.connect(self.on_sticker_released)
        row_sz.addWidget(self.slider_sticker_zoom, 1)

        self.lbl_sticker_zoom = QLabel(str(self.slider_sticker_zoom.value()))
        self.lbl_sticker_zoom.setFixedWidth(40)
        self.lbl_sticker_zoom.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_sticker_zoom.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color}; background: transparent;")
        self.slider_sticker_zoom.valueChanged.connect(lambda v: self.lbl_sticker_zoom.setText(str(v)))
        row_sz.addWidget(self.lbl_sticker_zoom)
        self._sticker_val_labels.append(self.lbl_sticker_zoom)
        self.card_sticker.main_layout.addLayout(row_sz)

        # Opacidad
        row_so = QHBoxLayout()
        lbl_so = QLabel(c.t("UI_LABEL_STICKER_OPACITY"))
        lbl_so.setFixedWidth(150)
        lbl_so.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {text_color}; background: transparent;")
        row_so.addWidget(lbl_so)
        self._sticker_labels.append(lbl_so)
        self.lbl_title_sticker_opacity = lbl_so

        self.slider_sticker_opacity = GlassCapsuleSlider(Qt.Horizontal, parent=self, app=self.app)
        self.slider_sticker_opacity.set_accent_color(accent)
        self.slider_sticker_opacity.set_is_dark(is_dark)
        self.slider_sticker_opacity.setRange(0, 100)
        self.slider_sticker_opacity.setValue(self.app.config.get(c.CONFIG_KEY_STICKER_OPACITY, 100))
        self.slider_sticker_opacity.valueChanged.connect(self.on_sticker_change)
        self.slider_sticker_opacity.sliderReleased.connect(self.on_sticker_released)
        row_so.addWidget(self.slider_sticker_opacity, 1)

        self.lbl_sticker_opacity = QLabel(str(self.slider_sticker_opacity.value()))
        self.lbl_sticker_opacity.setFixedWidth(40)
        self.lbl_sticker_opacity.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_sticker_opacity.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color}; background: transparent;")
        self.slider_sticker_opacity.valueChanged.connect(lambda v: self.lbl_sticker_opacity.setText(str(v)))
        row_so.addWidget(self.lbl_sticker_opacity)
        self._sticker_val_labels.append(self.lbl_sticker_opacity)
        self.card_sticker.main_layout.addLayout(row_so)

        # Update initial sticker preview
        self._update_sticker_preview_display()

        self.scroll_layout.addWidget(self.card_sticker)
        self._add_spacer()

    # ── Integrations ─────────────────────────────────────────────

    def setup_discord_section(self):
        # ── Card 5: Discord Rich Presence ──
        discord_icon_path = resource_path("assets/media/settings_icon_discord.svg")
        self.card_discord = SettingsOptionCard(
            icon_path=discord_icon_path,
            title=c.t("UI_DISCORD_RPC_SECTION_TITLE"),
            subtitle=c.t("UI_SETTINGS_DESC_DISCORD"),
            app=self.app,
            parent=self
        )
        self.card_discord.setMinimumHeight(175)
        self._groups["UI_DISCORD_RPC_SECTION_TITLE"] = self.card_discord

        # Body row 1: [Toggle] Activar Discord Rich Presence  [?]
        row_toggle = QHBoxLayout()
        row_toggle.setContentsMargins(60, 10, 0, 0)
        row_toggle.setSpacing(12)

        self.check_discord_rpc = ModernToggle(self, app=self.app)
        self.check_discord_rpc.setChecked(self.app.config.get(c.CONFIG_KEY_DISCORD_RPC_ENABLED, False))
        row_toggle.addWidget(self.check_discord_rpc)

        self.lbl_discord_toggle = QLabel(c.t("UI_DISCORD_RPC_CHECKBOX"))
        self.lbl_discord_toggle.setStyleSheet("font-size: 13px; font-weight: 500; color: #e2e8f0; background: transparent;")
        row_toggle.addWidget(self.lbl_discord_toggle)

        self.btn_discord_info = SettingsHelpButton(
            c.t("UI_DISCORD_RPC_CHECKBOX"), c.t("UI_DISCORD_RPC_TOOLTIP"),
            parent=self, app=self.app
        )
        row_toggle.addWidget(self.btn_discord_info)
        row_toggle.addStretch()
        self.card_discord._main_layout.addLayout(row_toggle)

        self.checks[c.CONFIG_KEY_DISCORD_RPC_ENABLED] = self.check_discord_rpc
        self.check_discord_rpc.stateChanged.connect(
            lambda state: self.app.sync_discord_rpc_ui(state == Qt.Checked.value)
        )

        # Body row 2: Discord Client ID  [ input field ]
        row_cid = QHBoxLayout()
        row_cid.setContentsMargins(60, 8, 0, 0)
        row_cid.setSpacing(14)

        self.lbl_discord_cid = QLabel(c.t("UI_DISCORD_RPC_CLIENT_ID_LABEL"))
        self.lbl_discord_cid.setStyleSheet("font-size: 13px; color: #94a3b8; font-weight: 500; background: transparent;")
        row_cid.addWidget(self.lbl_discord_cid)

        self.entry_discord_client_id = QLineEdit()
        self.entry_discord_client_id.setText(self.app.config.get(c.CONFIG_KEY_DISCORD_RPC_CLIENT_ID, ""))
        self.entry_discord_client_id.setPlaceholderText(c.DISCORD_DEFAULT_CLIENT_ID)
        self.entry_discord_client_id.setFixedHeight(36)
        row_cid.addWidget(self.entry_discord_client_id, 1)
        self.card_discord._main_layout.addLayout(row_cid)

        self.scroll_layout.addWidget(self.card_discord)
        self._add_spacer()

    def setup_restore_defaults_section(self):
        # ── Card 6: Restaurar Valores por Defecto ──
        reset_icon_path = resource_path("assets/media/backup_box_icon.svg")
        if not os.path.exists(reset_icon_path):
            reset_icon_path = resource_path("assets/media/settings_icon_folder.svg")
        self.card_restore = SettingsOptionCard(
            icon_path=reset_icon_path,
            title=c.t("UI_BUTTON_RESTORE_DEFAULTS"),
            subtitle="Restablece todos los parámetros y configuraciones del launcher a sus valores predeterminados de fábrica.",
            app=self.app,
            parent=self
        )
        self._groups["UI_BUTTON_RESTORE_DEFAULTS"] = self.card_restore

        self.btn_restore = QPushButton(c.t("UI_BUTTON_RESTORE_DEFAULTS"))
        self.btn_restore.setObjectName("SaveButton")
        self.btn_restore.setFixedHeight(36)
        self.btn_restore.setCursor(Qt.PointingHandCursor)
        self.btn_restore.clicked.connect(self.app.restore_default_settings)
        self.card_restore.ctrl_layout.addWidget(self.btn_restore)
        self.scroll_layout.addWidget(self.card_restore)
        self._add_spacer()

    def retranslate_ui(self):
        for key, label_key in self.CATEGORIES:
            if key in self._cat_buttons:
                self._cat_buttons[key].setText(c.t(label_key))
        if hasattr(self, "_sidebar_card") and self._sidebar_card:
            self._sidebar_card.update()
        if hasattr(self, "bottom_menu") and self.bottom_menu:
            self.bottom_menu.retranslate_ui()
        for key, group in self._groups.items():
            text = c.t(key)
            if key in ("UI_LABEL_SECTION_OPACITY", "UI_LABEL_VERSION_LIST_STYLE"):
                text = text.rstrip(":")
            if hasattr(group, "setTitle"):
                group.setTitle(text)
        # General Cards dynamic retranslation
        if hasattr(self, "card_lang") and self.card_lang:
            self.card_lang.setTitle(c.t("UI_LABEL_LANGUAGE"))
            if self.card_lang.lbl_subtitle:
                self.card_lang.lbl_subtitle.setText(c.t("UI_SETTINGS_DESC_LANG"))
        if hasattr(self, "card_scale") and self.card_scale:
            self.card_scale.setTitle(c.t("UI_LABEL_UI_SCALE"))
            if self.card_scale.lbl_subtitle:
                self.card_scale.lbl_subtitle.setText(c.t("UI_SETTINGS_DESC_SCALE"))
            if hasattr(self.card_scale, "lbl_warning") and self.card_scale.lbl_warning:
                self.card_scale.lbl_warning.setText(f"⚠️ {c.t('UI_RESTART_SCALE_MSG')}")
        if hasattr(self, "card_launch_action") and self.card_launch_action:
            self.card_launch_action.setTitle(c.t("UI_LAUNCH_ACTION_LABEL"))
            if self.card_launch_action.lbl_subtitle:
                self.card_launch_action.lbl_subtitle.setText(c.t("UI_SETTINGS_DESC_LAUNCH_ACTION"))
            if hasattr(self, "combo_launch_action"):
                curr_act = self.combo_launch_action.currentData()
                self.combo_launch_action.blockSignals(True)
                self.combo_launch_action.clear()
                self.combo_launch_action.addItem(c.t("UI_LAUNCH_ACTION_NONE"), c.LAUNCH_ACTION_NONE)
                self.combo_launch_action.addItem(c.t("UI_LAUNCH_ACTION_HIDE"), c.LAUNCH_ACTION_HIDE)
                self.combo_launch_action.addItem(c.t("UI_LAUNCH_ACTION_CLOSE"), c.LAUNCH_ACTION_CLOSE)
                idx_act = self.combo_launch_action.findData(curr_act)
                if idx_act >= 0:
                    self.combo_launch_action.setCurrentIndex(idx_act)
                self.combo_launch_action.blockSignals(False)
        if hasattr(self, "card_profiles") and self.card_profiles:
            self.card_profiles.setTitle(c.t("UI_PROFILES_MANAGER_TITLE"))
            if self.card_profiles.lbl_subtitle:
                self.card_profiles.lbl_subtitle.setText(c.t("UI_SETTINGS_DESC_PROFILES"))
        if hasattr(self, "card_discord") and self.card_discord:
            self.card_discord.setTitle(c.t("UI_DISCORD_RPC_SECTION_TITLE"))
            if self.card_discord.lbl_subtitle:
                self.card_discord.lbl_subtitle.setText(c.t("UI_SETTINGS_DESC_DISCORD"))
        if hasattr(self, "lbl_discord_toggle"):
            self.lbl_discord_toggle.setText(c.t("UI_DISCORD_RPC_CHECKBOX"))
        if hasattr(self, "lbl_discord_cid"):
            self.lbl_discord_cid.setText(c.t("UI_DISCORD_RPC_CLIENT_ID_LABEL"))
        if hasattr(self, "card_restore") and self.card_restore:
            self.card_restore.setTitle(c.t("UI_BUTTON_RESTORE_DEFAULTS"))

        # Launch Cards dynamic retranslation
        if hasattr(self, "lbl_launch_header_title"):
            self.lbl_launch_header_title.setText(c.t("UI_CATEGORY_LAUNCH"))
        if hasattr(self, "lbl_launch_slogan") and self.lbl_launch_slogan:
            self.lbl_launch_slogan.setText(c.t("UI_SETTINGS_SLOGAN_LAUNCH"))
        if hasattr(self, "lbl_bin_mode_title") and self.lbl_bin_mode_title:
            self.lbl_bin_mode_title.setText(c.t("UI_LABEL_BIN_MODE").rstrip(":"))
        if hasattr(self, "combo_settings_mode") and hasattr(self.combo_settings_mode, "setTabTitle"):
            self.combo_settings_mode.setTabTitle(c.t("UI_LABEL_BIN_MODE").rstrip(":"))

        if hasattr(self, "card_bin_paths") and self.card_bin_paths:
            self.card_bin_paths.setTitle(c.t("UI_LABEL_BINARY_PATHS"))
            if self.card_bin_paths.lbl_subtitle:
                self.card_bin_paths.lbl_subtitle.setText(c.t("UI_SETTINGS_DESC_BINARY_PATHS"))
        if hasattr(self, "card_bin_folder") and self.card_bin_folder:
            self.card_bin_folder.setTitle(c.t("UI_LABEL_BIN_FOLDER").rstrip(":"))
            if self.card_bin_folder.lbl_subtitle:
                self.card_bin_folder.lbl_subtitle.setText(c.t("UI_SETTINGS_DESC_BIN_FOLDER"))
        if hasattr(self, "card_libs") and self.card_libs:
            self.card_libs.setTitle(c.t("UI_LABEL_MC_LIBS_PATH").rstrip(":"))
            if self.card_libs.lbl_subtitle:
                self.card_libs.lbl_subtitle.setText(c.t("UI_SETTINGS_DESC_MC_LIBS"))
        if hasattr(self, "card_graphics") and self.card_graphics:
            self.card_graphics.setTitle(c.t("UI_GC_GRAPHICS"))
            if self.card_graphics.lbl_subtitle:
                self.card_graphics.lbl_subtitle.setText(c.t("UI_SETTINGS_DESC_GRAPHICS"))

        if hasattr(self, "lbl_auto_detect_note"):
            self.lbl_auto_detect_note.setText(c.t("UI_SETTINGS_NOTE_AUTO_DETECT"))
        if hasattr(self, "btn_resolve"):
            self.btn_resolve.setText(f"🔍 {c.t('UI_BUTTON_AUTO_RESOLVE')}")
        if hasattr(self, "btn_resolve_libs"):
            self.btn_resolve_libs.setText(f"🔍 {c.t('UI_BUTTON_AUTO_RESOLVE')}")
        if hasattr(self, "cb_custom_env"):
            self.cb_custom_env.setText(c.t("UI_CUSTOM_ARGS_CHECKBOX"))
        if hasattr(self, "lbl_custom_vars_title"):
            self.lbl_custom_vars_title.setText(c.t("UI_CUSTOM_ARGS_LABEL"))
        if hasattr(self, "btn_help_env") and self.btn_help_env:
            self.btn_help_env.update_info(c.t("UI_CUSTOM_ARGS_CHECKBOX"), c.t("UI_CUSTOM_ARGS_TOOLTIP"))

        if hasattr(self, "_perf_checkboxes_map"):
            for cb, btn_info, label_key, tooltip_key in self._perf_checkboxes_map:
                cb.setText(c.t(label_key))
                btn_info.update_info(c.t(label_key), c.t(tooltip_key))

        if hasattr(self, "_binary_labels_map"):
            binary_titles_map = {
                c.CONFIG_KEY_CLIENT: (c.t("UI_LABEL_CLIENT_GAME"), c.t("UI_BIN_DESC_CLIENT")),
                c.CONFIG_KEY_EXTRACT: (c.t("UI_LABEL_EXTRACTOR_APK"), c.t("UI_BIN_DESC_EXTRACT")),
                c.CONFIG_KEY_SIGNIN_UI: (c.t("UI_LABEL_SIGNIN_UI"), c.t("UI_BIN_DESC_SIGNIN_UI")),
                c.CONFIG_KEY_GPLAYDL: (c.t("UI_LABEL_GPLAYDL"), c.t("UI_BIN_DESC_GPLAYDL")),
                c.CONFIG_KEY_GPLAYVER: (c.t("UI_LABEL_GPLAYVER"), c.t("UI_BIN_DESC_GPLAYVER")),
                c.CONFIG_KEY_WEBVIEW: (c.t("UI_LABEL_WEBVIEW_OPTIONAL"), c.t("UI_BIN_DESC_WEBVIEW")),
                c.CONFIG_KEY_ERROR: (c.t("UI_LABEL_ERROR_HANDLER_OPTIONAL"), c.t("UI_BIN_DESC_ERROR")),
                c.CONFIG_KEY_MSA_DAEMON: (c.t("UI_LABEL_MSA_DAEMON"), c.t("UI_BIN_DESC_MSA_DAEMON")),
            }
            for k, (lbl_t, lbl_d, b_more) in self._binary_labels_map.items():
                if k in binary_titles_map:
                    clean_t = binary_titles_map[k][0].rstrip(":")
                    lbl_t.setText(clean_t)
                    lbl_d.setText(binary_titles_map[k][1])

        if hasattr(self, "btn_save"):
            self.btn_save.setText(c.t("UI_BUTTON_SAVE_SETTINGS"))
        if hasattr(self, "btn_restore"):
            self.btn_restore.setText(c.t("UI_BUTTON_RESTORE_DEFAULTS"))
        for widget, label_key in self._retranslate_labels:
            widget.setText(c.t(label_key))
        if hasattr(self, "modes"):
            for k, btn in self.modes.items():
                btn.setText(c.t("UI_APPEARANCE_MODES").get(k, k))
        if hasattr(self, "lbl_footer_version"):
            self.lbl_footer_version.setText(
                f"{c.t('UI_FOOTER_PROJECT_NAME')} - v{c.VERSION_LAUNCHER}"
            )
            self.lbl_footer_version.setToolTip(c.t("UI_FOOTER_CHANGELOG_TOOLTIP"))
        if hasattr(self, "entry_bin_folder"):
            self.entry_bin_folder.setPlaceholderText(c.t("UI_LABEL_BIN_FOLDER").rstrip(":"))
        if hasattr(self, "entry_mc_libs"):
            self.entry_mc_libs.setPlaceholderText(c.t("UI_LABEL_MC_LIBS_PATH").rstrip(":"))
        if hasattr(self, "comic_color_panel") and self.comic_color_panel:
            self.comic_color_panel.retranslate()

        if hasattr(self, "unsaved_card") and self.unsaved_card:
            self.unsaved_card.retranslate_ui()

        # Appearance - Version Style & Sliders
        if hasattr(self, "lbl_appearance_mode"):
            self.lbl_appearance_mode.setText(c.t("UI_LABEL_APPEARANCE_MODE"))
        if hasattr(self, "lbl_title_list_style"):
            self.lbl_title_list_style.setText(c.t("UI_LABEL_STYLE"))
        if hasattr(self, "lbl_title_icon_size"):
            self.lbl_title_icon_size.setText(c.t("UI_LABEL_ICON_SIZE"))
        if hasattr(self, "lbl_title_title_size"):
            self.lbl_title_title_size.setText(c.t("UI_LABEL_TITLE_SIZE"))
        if hasattr(self, "lbl_title_card_width"):
            self.lbl_title_card_width.setText(c.t("UI_LABEL_CARD_WIDTH"))
        if hasattr(self, "lbl_title_card_height"):
            self.lbl_title_card_height.setText(c.t("UI_LABEL_CARD_HEIGHT"))
        if hasattr(self, "combo_list_style"):
            curr_style = self.combo_list_style.currentData()
            self.combo_list_style.blockSignals(True)
            self.combo_list_style.clear()
            for k, v in c.t("UI_LIST_STYLES").items():
                self.combo_list_style.addItem(v, k)
            idx = self.combo_list_style.findData(curr_style)
            if idx >= 0:
                self.combo_list_style.setCurrentIndex(idx)
            self.combo_list_style.blockSignals(False)

        # Appearance - Background Section
        if hasattr(self, "bg_preview") and self.bg_preview:
            self.bg_preview.set_placeholders(c.t("UI_BG_PREVIEW_TITLE"), c.t("UI_BG_PREVIEW_HINT"))
        if hasattr(self, "lbl_title_bg_path"):
            self.lbl_title_bg_path.setText(c.t("UI_LABEL_BG_PATH"))
        if hasattr(self, "lbl_title_bg_x"):
            self.lbl_title_bg_x.setText(c.t("UI_LABEL_BG_X"))
        if hasattr(self, "lbl_title_bg_y"):
            self.lbl_title_bg_y.setText(c.t("UI_LABEL_BG_Y"))
        if hasattr(self, "lbl_title_bg_opacity"):
            self.lbl_title_bg_opacity.setText(c.t("UI_LABEL_BG_OPACITY"))
        if hasattr(self, "lbl_title_bg_zoom"):
            self.lbl_title_bg_zoom.setText(c.t("UI_LABEL_BG_ZOOM"))
        if hasattr(self, "entry_bg_path"):
            self.entry_bg_path.setPlaceholderText(c.t("UI_BG_PLACEHOLDER_PATH"))
        if hasattr(self, "btn_browse_bg"):
            self.btn_browse_bg.setToolTip(c.t("UI_TOOLTIP_BROWSE_BG"))
        if hasattr(self, "btn_clear_bg"):
            self.btn_clear_bg.setToolTip(c.t("UI_SETTINGS_RESET_BG_TOOLTIP"))

        # Appearance - Sticker Section
        if hasattr(self, "sticker_preview") and self.sticker_preview:
            self.sticker_preview.set_placeholders(c.t("UI_STICKER_PREVIEW_TITLE"), c.t("UI_STICKER_PREVIEW_HINT"))
        if hasattr(self, "lbl_title_sticker_mode"):
            self.lbl_title_sticker_mode.setText(c.t("UI_LABEL_STICKER_MODE"))
        if hasattr(self, "lbl_title_sticker_corner"):
            self.lbl_title_sticker_corner.setText(c.t("UI_LABEL_STICKER_CORNER"))
        if hasattr(self, "lbl_title_sticker_content"):
            self.lbl_title_sticker_content.setText(c.t("UI_LABEL_STICKER_CONTENT"))
        if hasattr(self, "lbl_title_sticker_x"):
            self.lbl_title_sticker_x.setText(c.t("UI_LABEL_STICKER_X"))
        if hasattr(self, "lbl_title_sticker_y"):
            self.lbl_title_sticker_y.setText(c.t("UI_LABEL_STICKER_Y"))
        if hasattr(self, "lbl_title_sticker_zoom"):
            self.lbl_title_sticker_zoom.setText(c.t("UI_LABEL_STICKER_ZOOM"))
        if hasattr(self, "lbl_title_sticker_opacity"):
            self.lbl_title_sticker_opacity.setText(c.t("UI_LABEL_STICKER_OPACITY"))
        if hasattr(self, "combo_sticker_mode"):
            curr_m = self.combo_sticker_mode.currentData()
            self.combo_sticker_mode.blockSignals(True)
            self.combo_sticker_mode.clear()
            for k, v in c.t("UI_STICKER_MODES").items():
                self.combo_sticker_mode.addItem(v, k)
            idx_m = self.combo_sticker_mode.findData(curr_m)
            if idx_m >= 0:
                self.combo_sticker_mode.setCurrentIndex(idx_m)
            self.combo_sticker_mode.blockSignals(False)
        if hasattr(self, "combo_sticker_corner"):
            curr_c = self.combo_sticker_corner.currentData()
            self.combo_sticker_corner.blockSignals(True)
            self.combo_sticker_corner.clear()
            for k, v in c.t("UI_STICKER_CORNERS").items():
                self.combo_sticker_corner.addItem(v, k)
            idx_c = self.combo_sticker_corner.findData(curr_c)
            if idx_c >= 0:
                self.combo_sticker_corner.setCurrentIndex(idx_c)
            self.combo_sticker_corner.blockSignals(False)
        if hasattr(self, "entry_sticker_content"):
            self.entry_sticker_content.setPlaceholderText(c.t("UI_STICKER_PLACEHOLDER_CONTENT"))
        if hasattr(self, "btn_browse_sticker"):
            self.btn_browse_sticker.setToolTip(c.t("UI_TOOLTIP_BROWSE_STICKER"))
        if hasattr(self, "btn_clear_sticker"):
            self.btn_clear_sticker.setToolTip(c.t("UI_TOOLTIP_CLEAR_STICKER"))

    # ── Helpers ──────────────────────────────────────────────────

    def _add_spacer(self):
        self.scroll_layout.addSpacing(8)

    def _get_tinted_icon(self, path, size=16, color=None):
        if not path or not os.path.exists(path):
            return QIcon()
        is_dark = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark") == "Dark"
        orig_pix = QPixmap(path)
        if orig_pix.isNull():
            return QIcon(path)
        tinted = QPixmap(orig_pix.size())
        tinted.fill(Qt.transparent)
        tp = QPainter(tinted)
        tp.drawPixmap(0, 0, orig_pix)
        tp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        fill_color = QColor(color) if color else QColor("#e2e8f0" if is_dark else "#1e293b")
        tp.fillRect(tinted.rect(), fill_color)
        tp.end()
        return QIcon(tinted.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def browse_path(self, key, entry):
        path = ask_open_filename_native(self.app, title=f"{c.t('UI_OPEN_FILE_TITLE')}")
        if path:
            entry.setText(path)

    def browse_libs(self):
        path = ask_directory_native(self.app, title=f"{c.t('UI_OPEN_FILE_TITLE')}")
        if path:
            self.entry_mc_libs.setText(path)

    def browse_bin_folder(self):
        path = ask_directory_native(self.app, title=f"{c.t('UI_LABEL_BIN_FOLDER')}")
        if path:
            self.entry_bin_folder.setText(path)
            self.auto_resolve_binaries()

    BINARY_SLOT_NAMES = {
        c.CONFIG_KEY_CLIENT: ["mcpelauncher-client"],
        c.CONFIG_KEY_EXTRACT: ["mcpelauncher-extract"],
        c.CONFIG_KEY_SIGNIN_UI: ["playdl-signin-ui-qt", "signin-ui-qt"],
        c.CONFIG_KEY_GPLAYDL: ["gplaydl"],
        c.CONFIG_KEY_GPLAYVER: ["gplayver"],
        c.CONFIG_KEY_MSA_DAEMON: ["msa-daemon"],
        c.CONFIG_KEY_WEBVIEW: ["mcpelauncher-webview"],
        c.CONFIG_KEY_ERROR: ["mcpelauncher-error"],
    }

    def auto_resolve_binaries(self):
        """Scan the selected binary folder and fill each slot that has a match."""
        folder = self.entry_bin_folder.text().strip()
        if not folder or not os.path.isdir(folder):
            from src.gui import custom_dialogs as messagebox
            messagebox.showwarning(self, c.t("UI_ERROR_TITLE"), c.t("UI_BIN_FOLDER_INVALID"))
            return
        # Prefer a "bin" subfolder common in mcpelauncher installs.
        candidates = [folder]
        bin_sub = os.path.join(folder, "bin")
        if os.path.isdir(bin_sub):
            candidates.insert(0, bin_sub)

        found = {k: False for k in self.BINARY_SLOT_NAMES}
        for base in candidates:
            if not os.path.isdir(base):
                continue
            for entry in os.listdir(base):
                full = os.path.join(base, entry)
                if not os.path.isfile(full):
                    continue
                base_key = os.path.basename(entry)
                for slot, names in self.BINARY_SLOT_NAMES.items():
                    if base_key in names and not found[slot]:
                        e, b, _ = self.inputs[slot]
                        e.setText(full)
                        found[slot] = True

        if any(found.values()):
            from src.gui import custom_dialogs as messagebox
            resolved = [k for k, v in found.items() if v]
            messagebox.showinfo(
                self, c.t("UI_SUCCESS_TITLE"),
                c.t("UI_BIN_AUTO_RESOLVED", count=len(resolved))
            )
        else:
            from src.gui import custom_dialogs as messagebox
            messagebox.showwarning(self, c.t("UI_ERROR_TITLE"), c.t("UI_BIN_AUTO_NONE"))

    def auto_resolve_libs(self):
        """Auto-detect or validate mcpelauncher library directory."""
        from src.gui import custom_dialogs as messagebox
        current = self.entry_mc_libs.text().strip()
        if current and os.path.isdir(current):
            messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), f"Carpeta de librerías válida:\n{current}")
            return

        bin_folder = self.entry_bin_folder.text().strip()
        candidates = []
        if bin_folder and os.path.isdir(bin_folder):
            candidates.append(bin_folder)
            candidates.append(os.path.join(bin_folder, "bin"))
            candidates.append(os.path.join(bin_folder, "lib"))

        candidates.extend([
            os.path.join(self.app.active_path, "bin"),
            "/usr/local/bin",
            "/usr/bin",
            "/usr/lib/mcpelauncher",
            "/usr/lib64/mcpelauncher",
            os.path.expanduser("~/.local/bin"),
        ])

        found_path = None
        for path in candidates:
            if os.path.isdir(path):
                if (os.path.exists(os.path.join(path, "mcpelauncher-client")) or
                    os.path.exists(os.path.join(path, "msa-daemon"))):
                    found_path = path
                    break

        if not found_path:
            for path in candidates:
                if os.path.isdir(path):
                    found_path = path
                    break

        if found_path:
            self.entry_mc_libs.setText(found_path)
            self.app.config_manager.set(c.CONFIG_KEY_MC_LIBS_PATH, found_path)
            messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), f"Ruta resuelta automáticamente:\n{found_path}")
        else:
            messagebox.showwarning(self, c.t("UI_ERROR_TITLE"), "No se pudo detectar automáticamente la ruta de librerías.")

    def _on_binary_more_clicked(self, key, entry):
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction, QGuiApplication, QDesktopServices, QCursor
        from PySide6.QtCore import QPoint, QUrl
        menu = QMenu(self)
        is_dark = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark") == "Dark"
        menu_bg = "#1e2430" if is_dark else "#ffffff"
        menu_text = "#e2e8f0" if is_dark else "#1e293b"
        menu_border = "#334155" if is_dark else "#cbd5e1"
        menu_hover = "#2a3447" if is_dark else "#f1f5f9"
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {menu_bg};
                color: {menu_text};
                border: 1px solid {menu_border};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 14px;
                border-radius: 6px;
                font-size: 12px;
            }}
            QMenu::item:selected {{
                background-color: {menu_hover};
            }}
        """)

        act_clear = QAction("Limpiar ruta", self)
        act_clear.triggered.connect(lambda: entry.setText(""))
        menu.addAction(act_clear)

        act_copy = QAction("Copiar ruta", self)
        act_copy.triggered.connect(lambda: QGuiApplication.clipboard().setText(entry.text()))
        menu.addAction(act_copy)

        current_path = entry.text().strip()
        if current_path and os.path.exists(current_path):
            act_open_dir = QAction("Abrir carpeta contenedora", self)
            folder = os.path.dirname(current_path) if os.path.isfile(current_path) else current_path
            act_open_dir.triggered.connect(lambda f=folder: open_folder(f))
            menu.addAction(act_open_dir)

        sender = self.sender()
        if sender:
            menu.exec(sender.mapToGlobal(QPoint(0, sender.height() + 2)))
        else:
            menu.exec(QCursor.pos())

    def update_binary_version_info(self):
        if self.lbl_binary_version is None:
            return
        mode = self.app.config.get(c.CONFIG_KEY_MODE, c.t("UI_DEFAULT_MODE"))
        if mode == c.MODE_BIN_FLATPAK or self.app.running_in_flatpak:
            self.lbl_binary_version.setText(c.BINARY_VERSION_INFO)
        else:
            info_path = os.path.join(self.app.compiled_path, "info.txt")
            if os.path.exists(info_path):
                try:
                    with open(info_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        if len(lines) >= 2:
                            self.lbl_binary_version.setText(lines[1].strip())
                        else:
                            self.lbl_binary_version.setText(c.BINARY_VERSION_FALLBACK)
                except (OSError, UnicodeDecodeError) as e:
                    logger.debug(f"Could not read binary info.txt: {e}")
                    self.lbl_binary_version.setText(c.BINARY_VERSION_FALLBACK)
            else:
                self.lbl_binary_version.setText(c.BINARY_VERSION_FALLBACK)

    def on_settings_mode_change(self, display_name):
        mode_key = self.combo_settings_mode.currentData() or c.MODE_BIN_SYSTEM
        is_flatpak = mode_key == c.MODE_BIN_FLATPAK
        is_custom = mode_key == c.MODE_BIN_CUSTOM
        if hasattr(self, "frame_flatpak_id"):
            self.frame_flatpak_id.setVisible(is_flatpak)
        if hasattr(self, "lbl_flatpak_id"):
            self.lbl_flatpak_id.setVisible(is_flatpak)
        if hasattr(self, "card_bin_folder"):
            self.card_bin_folder.setVisible(is_custom)
        elif hasattr(self, "binfolder_group"):
            self.binfolder_group.setVisible(is_custom)
        if hasattr(self, "card_libs"):
            self.card_libs.setVisible(is_custom)
        elif hasattr(self, "libs_group"):
            self.libs_group.setVisible(is_custom)
        if hasattr(self, "binary_rows_container"):
            self.binary_rows_container.setVisible(is_custom)
        if hasattr(self, "lbl_non_custom_mode_info"):
            self.lbl_non_custom_mode_info.setVisible(not is_custom)
        for key, (e, b, parent) in self.inputs.items():
            e.setEnabled(is_custom)
            b.setEnabled(is_custom)
        self.update_binary_version_info()

    def toggle_custom_env(self):
        enabled = self.cb_custom_env.isChecked()
        if c.CONFIG_KEY_NVIDIA_PRIME in self.checks:
            self.checks[c.CONFIG_KEY_NVIDIA_PRIME].setEnabled(not enabled)
        if c.CONFIG_KEY_ZINK_MODE in self.checks:
            self.checks[c.CONFIG_KEY_ZINK_MODE].setEnabled(not enabled)
        self.entry_custom_vars.setEnabled(enabled)
        mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        if enabled:
            text_color = "white" if mode == "Dark" else "#242424"
            self.f_custom_vars.setStyleSheet("")
            self.entry_custom_vars.setStyleSheet(
                f"color: {text_color}; padding: 4px; border: 1px solid {'#444' if mode == 'Dark' else '#ccc'}; border-radius: 6px; background-color: {'#333' if mode == 'Dark' else '#fff'};"
            )
        else:
            disabled_text = "#666" if mode == "Dark" else "#999"
            disabled_bg = "#2a2a2a" if mode == "Dark" else "#f0f0f0"
            self.f_custom_vars.setStyleSheet("")
            self.entry_custom_vars.setStyleSheet(
                f"color: {disabled_text}; background-color: {disabled_bg}; border: 1px dashed {'#555' if mode == 'Dark' else '#bbb'}; border-radius: 6px;"
            )

    # ── Slots ────────────────────────────────────────────────────

    def _on_theme_btn_clicked(self, theme_key):
        if hasattr(self, 'combo_theme'):
            self.combo_theme.deleteLater()
            del self.combo_theme
        self._update_theme_btns(theme_key)
        self.app.change_appearance("color", theme_key)

    def _update_theme_btns(self, selected_key):
        if hasattr(self, "comic_color_panel") and self.comic_color_panel:
            self.comic_color_panel.setSelectedTheme(selected_key)

    def _refresh_per_widget_styles(self):
        mode = self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        theme_color = self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
        accent = c.THEME_COLOR_MAP.get(theme_color, "#1f6aa5")
        text_color = "#DCE4EE" if mode == "Dark" else "#1a1a1a"
        frame_bg = "#3a3a3a" if mode == "Dark" else "#e8e8e8"
        input_bg = "#2a2a2a" if mode == "Dark" else "#ffffff"
        input_text = "#ffffff" if mode == "Dark" else "#1a1a1a"
        input_border = "#555555" if mode == "Dark" else "#c1c9d4"
        slider_groove = "#4a4a4a" if mode == "Dark" else "#c9c9c9"
        combo_qss = f"""
            QComboBox {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 500;
                min-height: 24px;
                min-width: 220px;
                background-clip: padding-box;
            }}
            QComboBox:hover {{
                border: 1px solid {accent};
                background-color: {"rgba(255, 255, 255, 0.08)" if mode == "Dark" else "rgba(0, 0, 0, 0.06)"};
            }}
            QComboBox:focus {{ border: 1px solid {accent}; }}
            QComboBox::drop-down {{
                border: none; width: 28px; background: transparent;
                subcontrol-origin: padding;
                subcontrol-position: top right;
            }}
            QComboBox::down-arrow {{
                width: 10px;
                height: 10px;
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 4px;
                selection-background-color: {accent};
                selection-color: white;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 6px 12px;
                min-height: 28px;
                border-radius: 6px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {"rgba(255, 255, 255, 0.10)" if mode == "Dark" else "rgba(0, 0, 0, 0.08)"};
            }}
        """

        line_qss = f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {accent}; }}
        """

        slider_qss = f"""
            QSlider {{
                min-height: 24px;
            }}
            QSlider::groove:horizontal {{
                background: {slider_groove};
                height: 6px;
                border-radius: 3px;
                border: 1px solid {input_border};
                margin: 2px 0;
            }}
            QSlider::handle:horizontal {{
                background: {accent};
                border: 1px solid {input_border};
                width: 16px;
                height: 16px;
                margin: -3px 0;
                border-radius: 8px;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 3px;
            }}
        """

        for label in self._appearance_labels:
            label.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color};")

        muted_color = "#aaaaaa" if mode == "Dark" else "#555555"
        if hasattr(self, "lbl_binary_version"):
            self.lbl_binary_version.setStyleSheet(f"color: {muted_color}; font-size: 11px;")

        for card_name in ["card_lang", "card_scale", "card_launch_action", "card_profiles", "card_discord",
                          "card_bin_paths", "card_bin_folder", "card_libs", "card_graphics",
                          "card_theme_mode", "card_version_style", "card_section_opacity",
                          "card_background", "card_sticker"]:
            c_widget = getattr(self, card_name, None)
            if c_widget is not None and hasattr(c_widget, "update_styles"):
                c_widget.update_styles()

        is_dark_val = (mode == "Dark")
        if hasattr(self, "lbl_launch_header_title"):
            self.lbl_launch_header_title.setStyleSheet(f"font-size: 17px; font-weight: bold; color: {'#f8fafc' if is_dark_val else '#0f172a'}; background: transparent;")
        if hasattr(self, "lbl_launch_header_sub"):
            self.lbl_launch_header_sub.setStyleSheet(f"font-size: 11px; color: {'#94a3b8' if is_dark_val else '#64748b'}; background: transparent;")
        if hasattr(self, "lbl_launch_slogan") and self.lbl_launch_slogan:
            self.lbl_launch_slogan.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {'#38bdf8' if is_dark_val else '#0284c7'}; background: transparent; letter-spacing: 0.5px;")
        if hasattr(self, "lbl_bin_mode_title") and self.lbl_bin_mode_title:
            self.lbl_bin_mode_title.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {'#cbd5e1' if is_dark_val else '#334155'}; background: transparent;")
        if hasattr(self, "combo_settings_mode") and hasattr(self.combo_settings_mode, "update_styles"):
            self.combo_settings_mode.update_styles()
        if hasattr(self, "lbl_non_custom_mode_info"):
            self.lbl_non_custom_mode_info.setStyleSheet(f"font-size: 11px; color: {'#94a3b8' if is_dark_val else '#64748b'}; padding: 6px 2px; background: transparent;")
        if hasattr(self, "lbl_auto_detect_note"):
            self.lbl_auto_detect_note.setStyleSheet(f"font-size: 10.5px; color: {'#cbd5e1' if is_dark_val else '#334155'}; background: transparent;")
        if hasattr(self, "lbl_custom_vars_title"):
            self.lbl_custom_vars_title.setStyleSheet(f"font-size: 11px; font-weight: 500; color: {'#cbd5e1' if is_dark_val else '#334155'}; background: transparent;")

        browse_btn_qss = f"""
            QPushButton#BinaryBrowseBtn, QPushButton#FolderBrowseBtn {{
                background-color: {'rgba(255, 255, 255, 0.05)' if is_dark_val else 'rgba(0, 0, 0, 0.04)'};
                border: 1px solid {'rgba(255, 255, 255, 0.08)' if is_dark_val else 'rgba(0, 0, 0, 0.10)'};
                border-radius: 6px;
                padding: 2px;
            }}
            QPushButton#BinaryBrowseBtn:hover, QPushButton#FolderBrowseBtn:hover {{
                background-color: {'rgba(255, 255, 255, 0.12)' if is_dark_val else 'rgba(0, 0, 0, 0.08)'};
                border-color: {'rgba(255, 255, 255, 0.20)' if is_dark_val else 'rgba(0, 0, 0, 0.18)'};
            }}
        """

        more_btn_qss = f"""
            QPushButton#BinaryMoreBtn {{
                background-color: {'rgba(255, 255, 255, 0.05)' if is_dark_val else 'rgba(0, 0, 0, 0.04)'};
                border: 1px solid {'rgba(255, 255, 255, 0.08)' if is_dark_val else 'rgba(0, 0, 0, 0.10)'};
                border-radius: 6px;
                padding: 2px;
                color: {'#cbd5e1' if is_dark_val else '#475569'};
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton#BinaryMoreBtn:hover {{
                background-color: {'rgba(255, 255, 255, 0.12)' if is_dark_val else 'rgba(0, 0, 0, 0.08)'};
                border-color: {'rgba(255, 255, 255, 0.20)' if is_dark_val else 'rgba(0, 0, 0, 0.18)'};
                color: {'#ffffff' if is_dark_val else '#0f172a'};
            }}
        """

        ac = QColor(accent)
        ac_r, ac_g, ac_b = ac.red(), ac.green(), ac.blue()

        resolve_btn_qss = f"""
            QPushButton#ResolveButton {{
                background-color: rgba({ac_r}, {ac_g}, {ac_b}, 0.14);
                border: 1px solid rgba({ac_r}, {ac_g}, {ac_b}, 0.38);
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
                color: {accent};
            }}
            QPushButton#ResolveButton:hover {{
                background-color: rgba({ac_r}, {ac_g}, {ac_b}, 0.28);
                border-color: rgba({ac_r}, {ac_g}, {ac_b}, 0.65);
                color: {'#ffffff' if is_dark_val else '#000000'};
            }}
        """

        libs_note_qss = f"""
            QFrame#LibsInfoNote {{
                background-color: rgba({ac_r}, {ac_g}, {ac_b}, 0.08);
                border: 1px solid rgba({ac_r}, {ac_g}, {ac_b}, 0.26);
                border-radius: 8px;
            }}
        """

        divider_qss = f"""
            QFrame#GraphicsDivider {{
                background-color: {'rgba(255, 255, 255, 0.08)' if is_dark_val else 'rgba(0, 0, 0, 0.08)'};
                border: none;
            }}
        """

        checkbox_qss = f"""
            QCheckBox#SettingsCheckbox {{
                font-size: 12px;
                font-weight: 500;
                color: {'#e2e8f0' if is_dark_val else '#1e293b'};
                spacing: 8px;
                background: transparent;
            }}
            QCheckBox#SettingsCheckbox:hover {{
                color: {'#ffffff' if is_dark_val else '#0f172a'};
            }}
        """

        folder_svg = resource_path("assets/media/folder_browse_icon.svg")
        tinted_folder_icon = self._get_tinted_icon(folder_svg, 16)
        if hasattr(self, "_browse_buttons"):
            for btn in self._browse_buttons:
                btn.setIcon(tinted_folder_icon)

        more_svg = resource_path("assets/media/settings_more_dots.svg")
        tinted_more_icon = self._get_tinted_icon(more_svg, 14)
        if hasattr(self, "_more_buttons"):
            for btn in self._more_buttons:
                btn.setIcon(tinted_more_icon)

        if hasattr(self, "_binary_labels_map"):
            for key, (lbl_t, lbl_d, b_more) in self._binary_labels_map.items():
                lbl_t.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {'#f1f5f9' if is_dark_val else '#1e293b'}; background: transparent;")
                lbl_d.setStyleSheet(f"font-size: 10px; color: {'#94a3b8' if is_dark_val else '#64748b'}; background: transparent;")
                b_more.setStyleSheet(more_btn_qss)

        if hasattr(self, "btn_resolve") and self.btn_resolve:
            self.btn_resolve.setStyleSheet(resolve_btn_qss)
        if hasattr(self, "btn_resolve_libs") and self.btn_resolve_libs:
            self.btn_resolve_libs.setStyleSheet(resolve_btn_qss)
        if hasattr(self, "lbl_info_icon") and self.lbl_info_icon:
            self.lbl_info_icon.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {accent};")

        clear_btn_qss = f"""
            QPushButton#FolderClearBtn {{
                background-color: {'rgba(239, 68, 68, 0.10)' if is_dark_val else 'rgba(239, 68, 68, 0.08)'};
                border: 1px solid {'rgba(239, 68, 68, 0.28)' if is_dark_val else 'rgba(239, 68, 68, 0.22)'};
                border-radius: 6px;
                padding: 2px;
            }}
            QPushButton#FolderClearBtn:hover {{
                background-color: {'rgba(239, 68, 68, 0.25)' if is_dark_val else 'rgba(239, 68, 68, 0.18)'};
                border-color: {'rgba(239, 68, 68, 0.60)' if is_dark_val else 'rgba(239, 68, 68, 0.50)'};
            }}
        """

        trash_svg = resource_path("assets/media/trash_delete_icon.svg")
        tinted_trash_icon = self._get_tinted_icon(trash_svg, 14, color="#ef4444")
        if hasattr(self, "_clear_buttons"):
            for btn in self._clear_buttons:
                btn.setIcon(tinted_trash_icon)

        for btn in self.findChildren(QPushButton, "BinaryBrowseBtn"):
            btn.setStyleSheet(browse_btn_qss)
        for btn in self.findChildren(QPushButton, "FolderBrowseBtn"):
            btn.setStyleSheet(browse_btn_qss)
        for btn in self.findChildren(QPushButton, "FolderClearBtn"):
            btn.setStyleSheet(clear_btn_qss)
        for frame in self.findChildren(QFrame, "LibsInfoNote"):
            frame.setStyleSheet(libs_note_qss)
        for frame in self.findChildren(QFrame, "GraphicsDivider"):
            frame.setStyleSheet(divider_qss)
        for cb in self.findChildren(QCheckBox, "SettingsCheckbox"):
            cb.setStyleSheet(checkbox_qss)

        if hasattr(self, "lbl_discord_toggle"):
            self.lbl_discord_toggle.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {'#e2e8f0' if is_dark_val else '#1e293b'}; background: transparent;")
        if hasattr(self, "lbl_discord_cid"):
            self.lbl_discord_cid.setStyleSheet(f"font-size: 13px; color: {'#94a3b8' if is_dark_val else '#64748b'}; font-weight: 500; background: transparent;")
        if hasattr(self, "btn_manage_prof") and self.btn_manage_prof:
            self.btn_manage_prof.setStyleSheet(f"""
                QPushButton#ToolButton {{
                    border-radius: 8px;
                    background-color: {'rgba(255, 255, 255, 0.06)' if is_dark_val else 'rgba(0, 0, 0, 0.05)'};
                    border: 1px solid {'rgba(255, 255, 255, 0.10)' if is_dark_val else 'rgba(0, 0, 0, 0.12)'};
                    color: {'#cbd5e1' if is_dark_val else '#334155'};
                    font-size: 15px;
                }}
                QPushButton#ToolButton:hover {{
                    background-color: {'rgba(255, 255, 255, 0.12)' if is_dark_val else 'rgba(0, 0, 0, 0.10)'};
                    border-color: {'rgba(255, 255, 255, 0.22)' if is_dark_val else 'rgba(0, 0, 0, 0.20)'};
                    color: {'#ffffff' if is_dark_val else '#0f172a'};
                }}
            """)
        if hasattr(self, "btn_discord_info") and self.btn_discord_info:
            if hasattr(self.btn_discord_info, "update_styles"):
                self.btn_discord_info.update_styles()

        if hasattr(self, "comic_color_panel") and self.comic_color_panel:
            self.comic_color_panel.update_styles(is_dark_val)

        for name in ["combo_lang", "combo_scale", "combo_launch_action", "combo_profile", "combo_settings_mode"]:
            widget = getattr(self, name, None)
            if widget is not None and hasattr(widget, "update_styles"):
                widget.update_styles()

        for name in ["combo_list_style", "combo_sticker_mode", "combo_sticker_corner"]:
            widget = getattr(self, name, None)
            if widget is not None and isinstance(widget, QComboBox):
                widget.setStyleSheet(combo_qss)

        for name in ["entry_flatpak_id", "entry_discord_client_id",
                     "entry_bg_path", "entry_sticker_content",
                     "entry_bin_folder", "entry_mc_libs", "entry_custom_vars"]:
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setStyleSheet(line_qss)

        if hasattr(self, "inputs"):
            for key, (e, b, parent) in self.inputs.items():
                e.setStyleSheet(line_qss)

        for name in ["slider_icon", "slider_title", "slider_card_width", "slider_card_height",
                     "slider_section_opacity", "slider_bg_x", "slider_bg_y",
                     "slider_bg_opacity", "slider_bg_zoom", "slider_sticker_x",
                     "slider_sticker_y", "slider_sticker_zoom", "slider_sticker_opacity"]:
            widget = getattr(self, name, None)
            if widget is not None:
                if hasattr(widget, "set_accent_color"):
                    widget.set_accent_color(accent)
                if hasattr(widget, "set_is_dark"):
                    widget.set_is_dark(is_dark_val)
                else:
                    widget.setStyleSheet(slider_qss)

        for lbl in getattr(self, "_version_style_labels", []):
            lbl.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {'#cbd5e1' if is_dark_val else '#334155'}; background: transparent;")
        for lbl in getattr(self, "_version_val_labels", []):
            lbl.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {'#f1f5f9' if is_dark_val else '#0f172a'}; background: transparent;")
        if hasattr(self, "lbl_section_opacity") and self.lbl_section_opacity:
            self.lbl_section_opacity.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {'#f1f5f9' if is_dark_val else '#0f172a'}; background: transparent;")

        for lbl in getattr(self, "_bg_labels", []):
            lbl.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {'#cbd5e1' if is_dark_val else '#334155'}; background: transparent;")
        for lbl in getattr(self, "_bg_val_labels", []):
            lbl.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {'#f1f5f9' if is_dark_val else '#0f172a'}; background: transparent;")
        for lbl in getattr(self, "_sticker_labels", []):
            lbl.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {'#cbd5e1' if is_dark_val else '#334155'}; background: transparent;")
        for lbl in getattr(self, "_sticker_val_labels", []):
            lbl.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {'#f1f5f9' if is_dark_val else '#0f172a'}; background: transparent;")

        if hasattr(self, "bg_preview") and self.bg_preview:
            self.bg_preview.set_is_dark(is_dark_val)
        if hasattr(self, "sticker_preview") and self.sticker_preview:
            self.sticker_preview.set_is_dark(is_dark_val)

        if hasattr(self, 'modes'):
            for k, btn in self.modes.items():
                if hasattr(btn, "set_accent_color"):
                    btn.set_accent_color(accent)
                if hasattr(btn, "set_is_dark"):
                    btn.set_is_dark(is_dark_val)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {frame_bg};
                            color: {text_color};
                            border: 2px solid {input_border};
                            border-radius: 4px;
                            font-weight: bold;
                            font-size: 13px;
                            padding: 6px 20px;
                        }}
                        QPushButton:checked {{
                            background-color: {accent};
                            color: white;
                            border: 2px solid {accent};
                        }}
                        QPushButton:hover:!checked {{
                            border: 2px solid {accent};
                        }}
                    """)

        if hasattr(self, "bottom_menu") and self.bottom_menu:
            self.bottom_menu.update_styles()
        if hasattr(self, "unsaved_card") and self.unsaved_card:
            self.unsaved_card.update_styles()

        self.toggle_custom_env()

    def _on_mode_btn_clicked(self, mode_key):
        for k, btn in self.modes.items():
            btn.setChecked(k == mode_key)
        self.app.config_manager.set(c.CONFIG_KEY_APPEARANCE, mode_key)
        self.app.apply_theme_settings()
        self._refresh_per_widget_styles()

    def on_theme_change(self, display_name):
        theme_key = self.combo_theme.currentData() or "blue"
        self.app.change_appearance("color", theme_key)

    def on_appearance_mode_change(self, display_name):
        mode_key = self.combo_app_mode.currentData() or "Dark"
        self.app.config_manager.set(c.CONFIG_KEY_APPEARANCE, mode_key)
        self.app.apply_theme_settings()
        self._refresh_per_widget_styles()
        if hasattr(self.app, "tools_tab"):
            self.app.tools_tab.refresh_tools_ui()

    def on_language_change(self, display_name):
        lang_code = self.combo_lang.currentData() or "en"
        self.app.config_manager.set(c.CONFIG_KEY_LANGUAGE, lang_code)
        language_manager.load_language(lang_code)
        self.app.retranslate_all()

    def on_scale_change(self, value):
        self.app.config[c.CONFIG_KEY_UI_SCALE] = value
        self.app.config_manager.save_config()

    def on_section_opacity_change(self):
        val = self.slider_section_opacity.value()
        self.lbl_section_opacity.setText(str(val))
        self.app.config_manager.set(c.CONFIG_KEY_SECTION_OPACITY, val)
        if not hasattr(self, '_opacity_debounce'):
            from PySide6.QtCore import QTimer
            self._opacity_debounce = QTimer()
            self._opacity_debounce.setSingleShot(True)
            self._opacity_debounce.timeout.connect(self.app.apply_theme_settings)
        self._opacity_debounce.start(50)

    def on_section_opacity_released(self):
        self.app.config_manager.set(c.CONFIG_KEY_SECTION_OPACITY, self.slider_section_opacity.value())

    def clear_bg(self):
        self.entry_bg_path.setText("")
        self.on_bg_change()
        self.on_bg_released()
        if hasattr(self, "bg_preview") and self.bg_preview:
            self.bg_preview.clear_preview()

    def on_bg_change(self):
        self.lbl_bg_x.setText(str(self.slider_bg_x.value()))
        self.lbl_bg_y.setText(str(self.slider_bg_y.value()))
        self.lbl_bg_opacity.setText(str(self.slider_bg_opacity.value()))
        self.lbl_bg_zoom.setText(str(self.slider_bg_zoom.value()))
        p = self.entry_bg_path.text()
        self.app.config[c.CONFIG_KEY_BG_PATH] = p
        self.app.config[c.CONFIG_KEY_BG_X] = self.slider_bg_x.value()
        self.app.config[c.CONFIG_KEY_BG_Y] = self.slider_bg_y.value()
        self.app.config[c.CONFIG_KEY_BG_OPACITY] = self.slider_bg_opacity.value()
        self.app.config[c.CONFIG_KEY_BG_ZOOM] = self.slider_bg_zoom.value()
        if hasattr(self, "bg_preview") and self.bg_preview:
            self.bg_preview.set_image(p)
        self.app.personalization_timer.start()

    def on_bg_released(self):
        self.app.config_manager.set(c.CONFIG_KEY_BG_PATH, self.entry_bg_path.text())
        self.app.config_manager.set(c.CONFIG_KEY_BG_X, self.slider_bg_x.value())
        self.app.config_manager.set(c.CONFIG_KEY_BG_Y, self.slider_bg_y.value())
        self.app.config_manager.set(c.CONFIG_KEY_BG_OPACITY, self.slider_bg_opacity.value())
        self.app.config_manager.set(c.CONFIG_KEY_BG_ZOOM, self.slider_bg_zoom.value())

    def browse_bg(self):
        p = ask_open_filename_native(self.app, title=c.t("UI_LABEL_BG_PATH"))
        if p:
            self.entry_bg_path.setText(p)

    def clear_sticker(self):
        self.entry_sticker_content.setText("")
        self.on_sticker_change()
        self.on_sticker_released()
        if hasattr(self, "sticker_preview") and self.sticker_preview:
            self.sticker_preview.clear_preview()

    def _update_sticker_preview_display(self):
        if not hasattr(self, "sticker_preview") or not self.sticker_preview:
            return
        mode = self.combo_sticker_mode.currentData() if hasattr(self, "combo_sticker_mode") else "none"
        content = self.entry_sticker_content.text().strip() if hasattr(self, "entry_sticker_content") else ""
        if mode == "image" and content:
            self.sticker_preview.set_image(content)
        elif mode == "text" and content:
            self.sticker_preview.set_text_preview(content)
        else:
            self.sticker_preview.clear_preview()

    def on_sticker_change(self):
        self.lbl_sticker_x.setText(str(self.slider_sticker_x.value()))
        self.lbl_sticker_y.setText(str(self.slider_sticker_y.value()))
        self.lbl_sticker_zoom.setText(str(self.slider_sticker_zoom.value()))
        self.lbl_sticker_opacity.setText(str(self.slider_sticker_opacity.value()))
        mode_key = self.combo_sticker_mode.currentData() or "none"
        corner_key = self.combo_sticker_corner.currentData() or "bottom-right"
        self.app.config[c.CONFIG_KEY_STICKER_MODE] = mode_key
        self.app.config[c.CONFIG_KEY_STICKER_CONTENT] = self.entry_sticker_content.text()
        self.app.config[c.CONFIG_KEY_STICKER_CORNER] = corner_key
        self.app.config[c.CONFIG_KEY_STICKER_X] = self.slider_sticker_x.value()
        self.app.config[c.CONFIG_KEY_STICKER_Y] = self.slider_sticker_y.value()
        self.app.config[c.CONFIG_KEY_STICKER_ZOOM] = self.slider_sticker_zoom.value()
        self.app.config[c.CONFIG_KEY_STICKER_OPACITY] = self.slider_sticker_opacity.value()
        self._update_sticker_preview_display()
        self.app.personalization_timer.start()

    def on_sticker_released(self):
        self.app.config_manager.set(c.CONFIG_KEY_STICKER_MODE, self.app.config.get(c.CONFIG_KEY_STICKER_MODE, "none"))
        self.app.config_manager.set(c.CONFIG_KEY_STICKER_CONTENT, self.entry_sticker_content.text())
        self.app.config_manager.set(c.CONFIG_KEY_STICKER_CORNER, self.app.config.get(c.CONFIG_KEY_STICKER_CORNER, "bottom-right"))
        self.app.config_manager.set(c.CONFIG_KEY_STICKER_X, self.slider_sticker_x.value())
        self.app.config_manager.set(c.CONFIG_KEY_STICKER_Y, self.slider_sticker_y.value())
        self.app.config_manager.set(c.CONFIG_KEY_STICKER_ZOOM, self.slider_sticker_zoom.value())
        self.app.config_manager.set(c.CONFIG_KEY_STICKER_OPACITY, self.slider_sticker_opacity.value())

    def browse_sticker(self):
        p = ask_open_filename_native(self.app, title=c.t("UI_LABEL_STICKER_CONTENT"))
        if p:
            self.entry_sticker_content.setText(p)

    def on_appearance_setting_change(self):
        self.lbl_icon_val.setText(str(self.slider_icon.value()))
        self.lbl_title_val.setText(str(self.slider_title.value()))
        if hasattr(self, 'lbl_card_width_val'):
            self.lbl_card_width_val.setText(str(self.slider_card_width.value()))
        if hasattr(self, 'lbl_card_height_val'):
            self.lbl_card_height_val.setText(str(self.slider_card_height.value()))

    def on_style_combo_changed(self):
        style_key = self.combo_list_style.currentData() or c.STYLE_LIST
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_LIST_STYLE, style_key)
        self.app.logic.refresh_version_list(self.app)

    def on_tools_layout_changed(self):
        style_key = self.combo_tools_layout.currentData() or c.STYLE_COLUMNS
        self.app.config_manager.set(c.CONFIG_KEY_TOOLS_LAYOUT, style_key)
        if hasattr(self.app, "tools_tab"):
            self.app.tools_tab.refresh_tools_ui()

    def on_appearance_released(self):
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_ICON_SIZE, self.slider_icon.value())
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_TITLE_SIZE, self.slider_title.value())
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_CARD_WIDTH, self.slider_card_width.value())
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_CARD_HEIGHT, self.slider_card_height.value())
        self.app.logic.refresh_version_list(self.app)
        if hasattr(self.app, "tools_tab"):
            self.app.tools_tab.refresh_tools_ui()

    def on_profile_change(self, display_text):
        profile_name = self.combo_profile.currentData()
        if profile_name:
            self.app.logic.switch_profile(self.app, profile_name)
            self.refresh_profile_list()

    def open_profile_manager(self):
        from src.gui.profile_manager_dialog import ProfileManagerDialog
        dialog = ProfileManagerDialog(self.app, self.app)
        dialog.exec()
        self.refresh_profile_list()

    def refresh_profile_list(self):
        self.combo_profile.blockSignals(True)
        self._populate_profile_combo()
        self.combo_profile.blockSignals(False)

    def _populate_profile_combo(self):
        self.combo_profile.clear()
        current = self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, "")
        profiles = sorted(self.app.logic.get_profiles(self.app))
        for idx, p in enumerate(profiles):
            icon = profile_icon(idx)
            prefix = "★ " if p == current else ""
            self.combo_profile.addItem(icon, prefix + p, p)
        idx = self.combo_profile.findData(current)
        if idx >= 0:
            self.combo_profile.setCurrentIndex(idx)

    def save_settings(self, silent=False):
        mode_key = self.combo_settings_mode.currentData() or c.MODE_BIN_SYSTEM
        self.app.config_manager.set(c.CONFIG_KEY_MODE, mode_key)
        self.app.config_manager.set(c.CONFIG_KEY_FLATPAK_ID, self.entry_flatpak_id.text())
        for key, cb in self.checks.items():
            self.app.config_manager.set(key, cb.isChecked())
        self.app.config_manager.set(c.CONFIG_KEY_CUSTOM_ENV_VARS, self.entry_custom_vars.text())
        self.app.config_manager.set(c.CONFIG_KEY_DISCORD_RPC_CLIENT_ID, self.entry_discord_client_id.text().strip())
        if mode_key == c.MODE_BIN_CUSTOM:
            for key, (e, b, parent) in self.inputs.items():
                paths = dict(self.app.config.get(c.CONFIG_KEY_BINARY_PATHS, {}))
                paths[key] = e.text()
                self.app.config_manager.set(c.CONFIG_KEY_BINARY_PATHS, paths)
            if hasattr(self, "entry_mc_libs"):
                self.app.config_manager.set(c.CONFIG_KEY_MC_LIBS_PATH, self.entry_mc_libs.text().strip())
            if hasattr(self, "entry_bin_folder"):
                self.app.config_manager.set(c.CONFIG_KEY_BIN_FOLDER, self.entry_bin_folder.text().strip())
        self.app.config_manager.save_config()
        self._saved_snapshot = self._get_current_state()
        self.has_unsaved_changes = False
        if hasattr(self, "unsaved_card") and self.unsaved_card:
            self.unsaved_card.set_visible_animated(False)
        if not silent:
            from src.gui import custom_dialogs as messagebox
            messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), c.t("UI_SAVE_SUCCESS_MSG"))
