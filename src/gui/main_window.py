from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QTabWidget, QTabBar, QPushButton, QFrame, QScrollArea,
                             QComboBox, QApplication, QSystemTrayIcon, QMenu,
                             QGraphicsDropShadowEffect, QGraphicsOpacityEffect)
from PySide6.QtCore import (Qt, QTimer, QPropertyAnimation, QParallelAnimationGroup,
                            QEasingCurve, Property, QRectF, QRect, QSize, QPoint, QThread)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPainterPath, QAction, QPen, QFontMetrics, QFont, QPalette
import os
import re
import sys
import time



from src import constants as c
from src.utils.resource_path import resource_path
from src.utils.image_manager import ImageManager
from src.utils.colors import hex_to_rgba, adjust_color, blend_colors
from src.core.config_manager import ConfigManager
from src.core import language_manager
from src.gui import custom_dialogs as messagebox
from src.gui.install_dialog import InstallDialog
from src.gui.skin_pack_tool import SkinPackTool
from src.gui.addon_manager_dialog import AddonManagerDialog
from src.gui.migration_wizard import MigrationWizard
from src.gui.game_config_dialog import GameConfigDialog
from src.core import app_logic
from src.core.discord_rpc import DiscordRPC
from src.core.update_checker import UpdateChecker
from src.gui.tabs.play_tab import PlayTab
from src.gui.tabs.tools_tab import ToolsTab
from src.gui.tabs.settings_tab import SettingsTab
from src.gui.tabs.about_tab import AboutTab
from src.gui.tabs.logs_tab import LogsTab
from src.utils.logger import logger

class HamburgerNavMenu(QWidget):
    """Floating popup drawer menu showing navigation tabs when header is in compact/narrow mode."""
    def __init__(self, tab_widget, main_window, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.tab_widget = tab_widget
        self.main_window = main_window

        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(10, 10, 10, 10)
        self._main_layout.setSpacing(6)
        self.setFixedWidth(210)

    def _rebuild_items(self):
        while self._main_layout.count():
            item = self._main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        accent = getattr(self.main_window, "current_accent_color", "#1f6aa5")
        is_dark = getattr(self.main_window, "is_dark_mode", True)
        curr_idx = self.tab_widget.currentIndex()

        # 1. Profile item at top of drawer
        current_profile = str(getattr(self.main_window, "config", {}).get(c.CONFIG_KEY_CURRENT_PROFILE, c.t("UI_PROFILE_DEFAULT")) if hasattr(self.main_window, "config") else "default").upper()
        prof_btn = QPushButton(f"  {current_profile}")
        user_icon = ImageManager.get_icon("steve.png")
        if user_icon and not user_icon.isNull():
            prof_btn.setIcon(user_icon)
            prof_btn.setIconSize(QSize(22, 22))
        prof_btn.setFixedHeight(38)
        prof_btn.setCursor(Qt.PointingHandCursor)
        prof_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {hex_to_rgba(accent, 0.15) if is_dark else hex_to_rgba(accent, 0.10)};
                color: {accent};
                border: 1px solid {hex_to_rgba(accent, 0.45)};
                border-radius: 19px;
                font-weight: bold;
                font-size: 13px;
                text-align: left;
                padding-left: 14px;
            }}
            QPushButton:hover {{
                background-color: {hex_to_rgba(accent, 0.30) if is_dark else hex_to_rgba(accent, 0.22)};
                border: 1px solid {accent};
            }}
        """)
        prof_btn.clicked.connect(self._open_profile_from_menu)
        self._main_layout.addWidget(prof_btn)

        # Separator line
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {'rgba(255,255,255,0.12)' if is_dark else 'rgba(0,0,0,0.10)'}; border: none;")
        self._main_layout.addWidget(divider)

        for i in range(self.tab_widget.count()):
            text = self.tab_widget.tabText(i)
            icon = self.tab_widget.tabIcon(i)
            btn = QPushButton(text)
            if not icon.isNull():
                btn.setIcon(icon)
                btn.setIconSize(QSize(18, 18))
            btn.setFixedHeight(36)
            btn.setCursor(Qt.PointingHandCursor)

            is_selected = (i == curr_idx)
            if is_selected:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {accent};
                        color: #ffffff;
                        border-radius: 18px;
                        font-weight: bold;
                        font-size: 13px;
                        text-align: left;
                        padding-left: 16px;
                        border: none;
                    }}
                """)
            else:
                hover_bg = "rgba(255, 255, 255, 0.09)" if is_dark else "rgba(0, 0, 0, 0.07)"
                txt_col = "#e6e8ee" if is_dark else "#1c1e22"
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {txt_col};
                        border-radius: 18px;
                        font-weight: bold;
                        font-size: 13px;
                        text-align: left;
                        padding-left: 16px;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {hover_bg};
                    }}
                """)

            btn.clicked.connect(lambda checked=False, idx=i: self._select_tab(idx))
            self._main_layout.addWidget(btn)

        self.adjustSize()

    def _open_profile_from_menu(self):
        self.close()
        if hasattr(self.main_window, "open_profile_manager"):
            self.main_window.open_profile_manager()

    def _select_tab(self, index):
        win = self.main_window
        if hasattr(win, "settings_tab") and win.tab_widget.currentIndex() == 2 and index != 2:
            if getattr(win.settings_tab, "has_unsaved_changes", False):
                win.settings_tab.trigger_unsaved_shake()
                self.close()
                return
        self.tab_widget.setCurrentIndex(index)
        self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_dark = getattr(self.main_window, "is_dark_mode", True)
        accent = getattr(self.main_window, "current_accent_color", "#1f6aa5")
        bg_col = QColor(blend_colors("#171717", accent, 0.09) if is_dark else blend_colors("#ffffff", accent, 0.05))
        border_col = QColor(255, 255, 255, 24) if is_dark else QColor(0, 0, 0, 24)

        card_rect = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        shadow_rect = card_rect.adjusted(0, 3, 2, 5)
        painter.setBrush(QColor(0, 0, 0, 45 if is_dark else 30))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(shadow_rect, 16, 16)

        painter.setBrush(bg_col)
        painter.setPen(QPen(border_col, 1))
        painter.drawRoundedRect(card_rect, 16, 16)
        painter.end()

    def show_animated(self, target_pos):
        self._rebuild_items()
        start_pos = QPoint(target_pos.x(), target_pos.y() - 10)
        self.move(start_pos)
        self.show()
        self._anim.stop()
        self._anim.setStartValue(start_pos)
        self._anim.setEndValue(target_pos)
        self._anim.start()

class AnimatedTabBar(QTabBar):
    """QTabBar with smooth sliding indicator, fluid hover, and responsive collapsible hamburger menu."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._indicator_rect = QRectF()
        self._sink_factor = 0.0
        self._hover_index = -1
        self._hover_opacity = 0.0

        self._is_compact = False
        self._compact_opacity = 0.0
        self._hover_hamburger = False
        self._hover_profile = False
        self._nav_menu = None

        self.setMouseTracking(True)
        self.setDrawBase(False)
        self.setUsesScrollButtons(False)
        self.setElideMode(Qt.ElideNone)

        # Sliding position animation
        self._slide_anim = QPropertyAnimation(self, b"indicatorRect", self)
        self._slide_anim.setDuration(240)
        self._slide_anim.setEasingCurve(QEasingCurve.OutCubic)

        # Button press / sink tactile animation
        self._sink_anim = QPropertyAnimation(self, b"sinkFactor", self)
        self._sink_anim.setDuration(180)
        self._sink_anim.setEasingCurve(QEasingCurve.InOutQuad)

        # Fluid hover fade animation
        self._hover_anim = QPropertyAnimation(self, b"hoverOpacity", self)
        self._hover_anim.setDuration(140)
        self._hover_anim.setEasingCurve(QEasingCurve.OutQuad)

        # Compact / Hamburger mode transition animation
        self._compact_anim = QPropertyAnimation(self, b"compactOpacity", self)
        self._compact_anim.setDuration(200)
        self._compact_anim.setEasingCurve(QEasingCurve.OutCubic)

        # Profile button press animation
        self._profile_sink_factor = 0.0
        self._profile_sink_anim = QPropertyAnimation(self, b"profileSinkFactor", self)
        self._profile_sink_anim.setDuration(180)
        self._profile_sink_anim.setEasingCurve(QEasingCurve.InOutQuad)

        # Profile hover animation
        self._profile_hover_opacity = 0.0
        self._profile_hover_anim = QPropertyAnimation(self, b"profileHoverOpacity", self)
        self._profile_hover_anim.setDuration(140)
        self._profile_hover_anim.setEasingCurve(QEasingCurve.OutQuad)

        self.currentChanged.connect(self._on_current_changed)

    def _get_profile_rect(self):
        win = self.window()
        current_profile = str(getattr(win, "config", {}).get(c.CONFIG_KEY_CURRENT_PROFILE, c.t("UI_PROFILE_DEFAULT")) if hasattr(win, "config") else "default").upper()
        font = self.font()
        font.setBold(True)
        font.setPointSize(10)
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(current_profile)
        icon_size = 24
        spacing = 10
        btn_w = max(text_w + icon_size + spacing + 22, 96)
        btn_h = 38.0
        y = (self.height() - btn_h) / 2.0
        right_offset = 12.0
        x = self.width() - btn_w - right_offset
        return QRectF(x, y, btn_w, btn_h)

    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        return QSize(max(size.width() + 14, 100), 52)

    def _get_button_rect(self, index):
        if index < 0 or index >= self.count():
            return QRectF()
        rect = self.tabRect(index)
        btn_height = 38.0
        v_offset = (rect.height() - btn_height) / 2.0
        return QRectF(rect.x() + 4, rect.y() + v_offset, rect.width() - 8, btn_height)

    # ── Properties ──
    def _get_indicator_rect(self):
        return self._indicator_rect

    def _set_indicator_rect(self, rect):
        self._indicator_rect = rect
        self.update()

    indicatorRect = Property(QRectF, _get_indicator_rect, _set_indicator_rect)

    def _get_sink_factor(self):
        return self._sink_factor

    def _set_sink_factor(self, val):
        self._sink_factor = val
        self.update()

    sinkFactor = Property(float, _get_sink_factor, _set_sink_factor)

    def _get_profile_sink_factor(self):
        return self._profile_sink_factor

    def _set_profile_sink_factor(self, val):
        self._profile_sink_factor = val
        self.update()

    profileSinkFactor = Property(float, _get_profile_sink_factor, _set_profile_sink_factor)

    def _get_hover_opacity(self):
        return self._hover_opacity

    def _set_hover_opacity(self, val):
        self._hover_opacity = val
        self.update()

    hoverOpacity = Property(float, _get_hover_opacity, _set_hover_opacity)

    def _get_profile_hover_opacity(self):
        return self._profile_hover_opacity

    def _set_profile_hover_opacity(self, val):
        self._profile_hover_opacity = val
        self.update()

    profileHoverOpacity = Property(float, _get_profile_hover_opacity, _set_profile_hover_opacity)

    def _get_compact_opacity(self):
        return self._compact_opacity

    def _set_compact_opacity(self, val):
        self._compact_opacity = val
        self.update()

    compactOpacity = Property(float, _get_compact_opacity, _set_compact_opacity)

    def _check_compact_mode(self):
        first_tab_left = self.tabRect(0).left() if self.count() > 0 else 999
        should_compact = (self.width() < 590 or first_tab_left < 54)
        if should_compact != self._is_compact:
            self._is_compact = should_compact
            self._compact_anim.stop()
            self._compact_anim.setStartValue(self._compact_opacity)
            self._compact_anim.setEndValue(1.0 if should_compact else 0.0)
            self._compact_anim.start()

    def _trigger_sink_animation(self):
        self._sink_anim.stop()
        self._sink_anim.setKeyValueAt(0.0, 0.0)
        self._sink_anim.setKeyValueAt(0.5, 1.0)
        self._sink_anim.setKeyValueAt(1.0, 0.0)
        self._sink_anim.start()

    def _trigger_profile_sink_animation(self):
        self._profile_sink_anim.stop()
        self._profile_sink_anim.setKeyValueAt(0.0, 0.0)
        self._profile_sink_anim.setKeyValueAt(0.5, 1.0)
        self._profile_sink_anim.setKeyValueAt(1.0, 0.0)
        self._profile_sink_anim.start()

    def _on_current_changed(self, index):
        if index < 0 or index >= self.count():
            return
        target_rect = self._get_button_rect(index)
        self._trigger_sink_animation()
        if self._indicator_rect.isNull() or not self.isVisible():
            self._indicator_rect = target_rect
            self.update()
        else:
            self._slide_anim.stop()
            self._slide_anim.setStartValue(self._indicator_rect)
            self._slide_anim.setEndValue(target_rect)
            self._slide_anim.start()

    def mousePressEvent(self, event):
        # 1. Profile button click with tactile feedback
        prof_rect = self._get_profile_rect()
        if (not self._is_compact or self._compact_opacity < 0.5) and prof_rect.contains(event.position()):
            self._trigger_profile_sink_animation()
            win = self.window()
            if hasattr(win, "open_profile_manager"):
                win.open_profile_manager()
            return

        self._check_compact_mode()
        if self._is_compact and self._compact_opacity > 0.4:
            h_size = 34.0
            h_x = self.width() - h_size - 10.0
            h_y = (self.height() - h_size) / 2.0
            h_rect = QRectF(h_x, h_y, h_size, h_size)
            if h_rect.contains(event.position()):
                parent_tab_widget = self.parentWidget()
                if not self._nav_menu:
                    self._nav_menu = HamburgerNavMenu(parent_tab_widget, self.window(), self.window())
                menu_pos = self.mapToGlobal(QPoint(int(self.width() - 215), int(self.height() + 4)))
                self._nav_menu.show_animated(menu_pos)
                return

        idx = self.tabAt(event.pos())
        if idx >= 0:
            win = self.window()
            if hasattr(win, "settings_tab") and self.currentIndex() == 2 and idx != 2:
                if getattr(win.settings_tab, "has_unsaved_changes", False):
                    win.settings_tab.trigger_unsaved_shake()
                    return
            self._trigger_sink_animation()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        win = self.window()
        if hasattr(win, "settings_tab") and self.currentIndex() == 2:
            if getattr(win.settings_tab, "has_unsaved_changes", False):
                win.settings_tab.trigger_unsaved_shake()
                return
        super().keyPressEvent(event)

    def mouseMoveEvent(self, event):
        prof_rect = self._get_profile_rect()
        is_prof_hover = (not self._is_compact or self._compact_opacity < 0.5) and prof_rect.contains(event.position())
        if is_prof_hover != self._hover_profile:
            self._hover_profile = is_prof_hover
            self._profile_hover_anim.stop()
            self._profile_hover_anim.setStartValue(self._profile_hover_opacity)
            self._profile_hover_anim.setEndValue(1.0 if is_prof_hover else 0.0)
            self._profile_hover_anim.start()

        if self._is_compact:
            h_size = 34.0
            h_x = self.width() - h_size - 10.0
            h_y = (self.height() - h_size) / 2.0
            h_rect = QRectF(h_x, h_y, h_size, h_size)
            is_hover = h_rect.contains(event.position())
            if is_hover != self._hover_hamburger:
                self._hover_hamburger = is_hover
                self.update()
        else:
            idx = self.tabAt(event.pos())
            if idx != self._hover_index:
                self._hover_index = idx
                if idx >= 0 and idx != self.currentIndex():
                    self._hover_anim.stop()
                    self._hover_anim.setStartValue(self._hover_opacity)
                    self._hover_anim.setEndValue(1.0)
                    self._hover_anim.start()
                else:
                    self._hover_anim.stop()
                    self._hover_anim.setStartValue(self._hover_opacity)
                    self._hover_anim.setEndValue(0.0)
                    self._hover_anim.start()

        if is_prof_hover or self._hover_hamburger:
            self.setCursor(Qt.PointingHandCursor)
        elif self.cursor().shape() == Qt.PointingHandCursor:
            self.setCursor(Qt.ArrowCursor)

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_index = -1
        self._hover_hamburger = False
        if self._hover_profile:
            self._hover_profile = False
            self._profile_hover_anim.stop()
            self._profile_hover_anim.setStartValue(self._profile_hover_opacity)
            self._profile_hover_anim.setEndValue(0.0)
            self._profile_hover_anim.start()
        self.setCursor(Qt.ArrowCursor)
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_opacity)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        self.update()
        super().leaveEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self._check_compact_mode()
        idx = self.currentIndex()
        if idx >= 0 and idx < self.count():
            self._indicator_rect = self._get_button_rect(idx)
            self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._check_compact_mode()
        idx = self.currentIndex()
        if idx >= 0 and idx < self.count():
            self._indicator_rect = self._get_button_rect(idx)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        win = self.window()
        accent = getattr(win, "current_accent_color", "#1f6aa5")
        is_dark = getattr(win, "is_dark_mode", True)
        accent_qcolor = QColor(accent)

        # 0. Draw launcher brand logo and responsive title in top-left corner
        logo_size = 34
        logo_x = 10.0
        logo_y = (self.height() - logo_size) / 2.0
        logo_rect = QRectF(logo_x, logo_y, logo_size, logo_size)

        if is_dark:
            logo_steps = 10
            logo_max_expand = 6.5
            logo_max_alpha = 34
            for i in range(logo_steps, 0, -1):
                t = i / logo_steps
                alpha = int(logo_max_alpha * ((1.0 - t) ** 1.7))
                if alpha <= 0:
                    continue
                exp = logo_max_expand * t
                g_rect = logo_rect.adjusted(-exp, -exp, exp, exp)
                g_radius = g_rect.height() / 2.0
                g_color = QColor(accent_qcolor)
                g_color.setAlpha(alpha)
                painter.setBrush(g_color)
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(g_rect, g_radius, g_radius)
        else:
            shadow_steps = 8
            shadow_max_expand = 6.0
            shadow_max_alpha = 18
            for i in range(shadow_steps, 0, -1):
                t = i / shadow_steps
                alpha = int(shadow_max_alpha * ((1.0 - t) ** 1.6))
                if alpha <= 0:
                    continue
                s_rect = logo_rect.adjusted(0.6 * t, 1.0 * t, shadow_max_expand * t, shadow_max_expand * t)
                s_radius = s_rect.height() / 2.0
                painter.setBrush(QColor(0, 0, 0, alpha))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(s_rect, s_radius, s_radius)

        # Draw logo icon
        logo_pixmap = ImageManager.get_image("icon.png", size=(logo_size, logo_size))
        if logo_pixmap and not logo_pixmap.isNull():
            painter.drawPixmap(int(logo_x), int(logo_y), logo_pixmap)

        # Draw brand text "Cianova Launcher" only if not in compact mode and space is ample
        first_tab_left = self.tabRect(0).left() if self.count() > 0 else 999
        text_x = int(logo_x + logo_size + 9)
        required_space = text_x + 135
        if not self._is_compact and first_tab_left > required_space:
            brand_font = self.font()
            brand_font.setBold(True)
            brand_font.setPointSize(11)
            painter.setFont(brand_font)
            brand_text_color = QColor("#ffffff" if is_dark else "#1c1e22")
            painter.setPen(brand_text_color)
            text_rect = QRect(text_x, 0, 150, self.height())
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, "Cianova Launcher")

        # ── 1. Draw Horizontal Tabs when expanded ──
        if self._compact_opacity < 1.0:
            painter.setOpacity(1.0 - self._compact_opacity)

            # Unselected hover pills
            if self._hover_index >= 0 and self._hover_index != self.currentIndex() and self._hover_opacity > 0:
                h_rect = self._get_button_rect(self._hover_index)
                h_radius = h_rect.height() / 2.0
                h_color = QColor(255, 255, 255, int(26 * self._hover_opacity)) if is_dark else QColor(0, 0, 0, int(18 * self._hover_opacity))
                painter.setBrush(h_color)
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(h_rect, h_radius, h_radius)

            # Sliding indicator with sink compression & glow / shadow
            if not self._indicator_rect.isNull():
                sink_inset = self._sink_factor * 1.8
                draw_rect = self._indicator_rect.adjusted(sink_inset, sink_inset, -sink_inset, -sink_inset)
                radius = draw_rect.height() / 2.0

                if is_dark:
                    steps = 12
                    max_expand = 8.0
                    max_alpha = 36
                    for i in range(steps, 0, -1):
                        t = i / steps
                        alpha = int(max_alpha * ((1.0 - t) ** 1.7))
                        if alpha <= 0:
                            continue
                        exp = max_expand * t
                        glow_rect = draw_rect.adjusted(-exp, -exp, exp, exp)
                        glow_radius = glow_rect.height() / 2.0
                        glow_color = QColor(accent_qcolor)
                        glow_color.setAlpha(alpha)
                        painter.setBrush(glow_color)
                        painter.setPen(Qt.NoPen)
                        painter.drawRoundedRect(glow_rect, glow_radius, glow_radius)

                    painter.setBrush(accent_qcolor)
                    painter.setPen(Qt.NoPen)
                    painter.drawRoundedRect(draw_rect, radius, radius)
                else:
                    shadow_steps = 10
                    shadow_max_expand_x = 7.0
                    shadow_max_expand_y = 7.5
                    shadow_max_alpha = 24
                    for i in range(shadow_steps, 0, -1):
                        t = i / shadow_steps
                        alpha = int(shadow_max_alpha * ((1.0 - t) ** 1.6))
                        if alpha <= 0:
                            continue
                        s_rect = draw_rect.adjusted(0.8 * t, 1.2 * t, shadow_max_expand_x * t, shadow_max_expand_y * t)
                        s_radius = s_rect.height() / 2.0
                        painter.setBrush(QColor(0, 0, 0, alpha))
                        painter.setPen(Qt.NoPen)
                        painter.drawRoundedRect(s_rect, s_radius, s_radius)

                    painter.setBrush(accent_qcolor)
                    painter.setPen(Qt.NoPen)
                    painter.drawRoundedRect(draw_rect, radius, radius)

            # Tab text and icons
            for i in range(self.count()):
                rect = self.tabRect(i)
                text = self.tabText(i)
                icon = self.tabIcon(i)
                is_selected = (i == self.currentIndex())

                if is_selected:
                    text_color = QColor("#ffffff")
                else:
                    text_color = QColor("#e6e8ee" if is_dark else "#22252a")

                painter.setPen(text_color)
                font = self.font()
                font.setBold(True)
                font.setPointSize(10)
                painter.setFont(font)

                if not icon.isNull():
                    icon_size = 18
                    icon_rect = QRect(rect.left() + 12, rect.center().y() - icon_size // 2, icon_size, icon_size)
                    icon.paint(painter, icon_rect)
                    text_rect = QRect(rect.left() + 12 + icon_size + 6, rect.top(), rect.width() - (12 + icon_size + 6), rect.height())
                    painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)
                else:
                    painter.drawText(rect, Qt.AlignCenter, text)

            painter.setOpacity(1.0)

        # ── 2. Draw Hamburger Button on Right when compact ──
        if self._compact_opacity > 0.0:
            painter.setOpacity(self._compact_opacity)
            h_size = 34.0
            h_x = self.width() - h_size - 10.0
            h_y = (self.height() - h_size) / 2.0
            h_rect = QRectF(h_x, h_y, h_size, h_size)
            h_radius = h_size / 2.0

            # Hover pill
            if self._hover_hamburger:
                h_bg = QColor(255, 255, 255, 30) if is_dark else QColor(0, 0, 0, 20)
                painter.setBrush(h_bg)
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(h_rect, h_radius, h_radius)

            # Draw 3 rounded hamburger bars
            bar_w = 16.0
            bar_h = 2.4
            bar_r = 1.2
            bar_x = h_x + (h_size - bar_w) / 2.0
            bar_color = QColor(accent if self._hover_hamburger else ("#ffffff" if is_dark else "#1c1e22"))
            painter.setBrush(bar_color)
            painter.setPen(Qt.NoPen)

            for offset_y in [-5.5, 0.0, 5.5]:
                bar_y = h_y + (h_size - bar_h) / 2.0 + offset_y
                painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), bar_r, bar_r)

            painter.setOpacity(1.0)

        # ── 3. Draw Profile Button inside Top Bar (when not in compact mode) ──
        if not self._is_compact or self._compact_opacity < 0.6:
            prof_opacity = max(0.0, 1.0 - self._compact_opacity)
            painter.setOpacity(prof_opacity)

            prof_rect = self._get_profile_rect()
            current_profile = str(getattr(win, "config", {}).get(c.CONFIG_KEY_CURRENT_PROFILE, c.t("UI_PROFILE_DEFAULT")) if hasattr(win, "config") else "default").upper()

            # Tactile press scale transformation
            if self._profile_sink_factor > 0.001:
                scale = 1.0 - (0.04 * self._profile_sink_factor)
                c_point = prof_rect.center()
                prof_rect = QRectF(
                    c_point.x() - (prof_rect.width() * scale) / 2.0,
                    c_point.y() - (prof_rect.height() * scale) / 2.0,
                    prof_rect.width() * scale,
                    prof_rect.height() * scale
                )

            prof_radius = prof_rect.height() / 2.0

            # Smooth hover pill effect with animation opacity
            if self._profile_hover_opacity > 0.01:
                hover_alpha = int(45 * self._profile_hover_opacity) if is_dark else int(30 * self._profile_hover_opacity)
                hover_bg = QColor(accent_qcolor)
                hover_bg.setAlpha(hover_alpha)
                painter.setBrush(hover_bg)
                border_alpha = int(180 * self._profile_hover_opacity)
                border_col = QColor(accent_qcolor)
                border_col.setAlpha(border_alpha)
                painter.setPen(QPen(border_col, 1.0))
                painter.drawRoundedRect(prof_rect, prof_radius, prof_radius)

            icon_size = 24
            spacing = 10
            icon_x = int(prof_rect.right() - icon_size - 8)
            icon_y = int(prof_rect.top() + (prof_rect.height() - icon_size) / 2.0)
            avatar_rect = QRectF(icon_x, icon_y, icon_size, icon_size)

            # Draw Profile text in UPPERCASE on left (separated from icon)
            font = self.font()
            font.setBold(True)
            font.setPointSize(10)
            painter.setFont(font)
            painter.setPen(QColor(accent))
            text_w = prof_rect.width() - (icon_size + spacing + 14.0)
            text_rect = QRectF(prof_rect.left() + 6, prof_rect.top(), text_w, prof_rect.height())
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignRight, current_profile)

            # Glowing border effect in dark mode / soft shadow in light mode for Steve avatar (matching logo in top-left)
            if is_dark:
                avatar_steps = 8
                avatar_max_expand = 4.5
                avatar_max_alpha = 32
                for i in range(avatar_steps, 0, -1):
                    t = i / avatar_steps
                    alpha = int(avatar_max_alpha * ((1.0 - t) ** 1.7))
                    if alpha <= 0:
                        continue
                    exp = avatar_max_expand * t
                    g_rect = avatar_rect.adjusted(-exp, -exp, exp, exp)
                    g_radius = 4.0 + exp
                    g_color = QColor(accent_qcolor)
                    g_color.setAlpha(alpha)
                    painter.setBrush(g_color)
                    painter.setPen(Qt.NoPen)
                    painter.drawRoundedRect(g_rect, g_radius, g_radius)
            else:
                shadow_steps = 6
                shadow_max_expand = 4.0
                shadow_max_alpha = 18
                for i in range(shadow_steps, 0, -1):
                    t = i / shadow_steps
                    alpha = int(shadow_max_alpha * ((1.0 - t) ** 1.6))
                    if alpha <= 0:
                        continue
                    s_rect = avatar_rect.adjusted(0.4 * t, 0.8 * t, shadow_max_expand * t, shadow_max_expand * t)
                    s_radius = 4.0
                    painter.setBrush(QColor(0, 0, 0, alpha))
                    painter.setPen(Qt.NoPen)
                    painter.drawRoundedRect(s_rect, s_radius, s_radius)

            # Draw Steve face avatar (steve.png)
            pix = ImageManager.get_image("steve.png", size=(icon_size, icon_size))
            if pix and not pix.isNull():
                painter.drawPixmap(icon_x, icon_y, pix)

            # Subtle accent border around Steve avatar in dark mode
            if is_dark:
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor(accent_qcolor), 1.0))
                painter.drawRoundedRect(avatar_rect, 4.0, 4.0)

            painter.setOpacity(1.0)

        painter.end()

class AnimatedTabWidget(QTabWidget):
    """QTabWidget with smooth slide and cross-fade transition between tab pages."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setUsesScrollButtons(False)
        self.setTabBar(AnimatedTabBar(self))
        self._prev_index = -1
        self._anim_group = None
        self._anim_effect = None
        self._anim_target = None
        self.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index):
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

        # Clean up any existing running animation
        if self._anim_group and self._anim_group.state() == QParallelAnimationGroup.Running:
            self._anim_group.stop()
        if self._anim_target and self._anim_effect:
            try:
                self._anim_target.setGraphicsEffect(None)
            except RuntimeError:
                pass

        # Setup opacity effect
        effect = QGraphicsOpacityEffect(current_widget)
        current_widget.setGraphicsEffect(effect)
        self._anim_effect = effect
        self._anim_target = current_widget

        # Fade in: 0.0 -> 1.0
        anim_fade = QPropertyAnimation(effect, b"opacity", self)
        anim_fade.setDuration(220)
        anim_fade.setStartValue(0.0)
        anim_fade.setEndValue(1.0)
        anim_fade.setEasingCurve(QEasingCurve.OutCubic)

        # Slide offset: 24px in the direction of movement -> 0
        offset = 24 * direction
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
                current_widget.setGraphicsEffect(None)
                self._anim_effect = None
                self._anim_target = None

        self._anim_group.finished.connect(_cleanup)
        self._anim_group.start()

class VisualLabel(QLabel):
    """A transparent overlay label used for background and sticker display."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent; border: none;")

class CianovaLauncherApp(QMainWindow):
    """Main application window managing tabs, theming, and top-level logic."""
    def __init__(self, launcher_path=".", force_flatpak_ui=False, force_nvidia_ui=False):
        super().__init__()

        logger.info("Initializing Main Window...")
        self.logic = app_logic
        self.launcher_path = launcher_path
        self.home = c.HOME_DIR
        self.force_flatpak_ui = force_flatpak_ui
        self.force_nvidia_ui = force_nvidia_ui

        self.running_in_flatpak = self.logic.is_running_in_flatpak() or self.force_flatpak_ui

        self.our_flatpak_id = self.logic.get_flatpak_app_id() if self.running_in_flatpak else None

        if self.running_in_flatpak:
            app_id = self.our_flatpak_id if self.our_flatpak_id else c.DEFAULT_FLATPAK_ID
            self.our_data_path = os.path.join(self.home, f"{c.FLATPAK_DATA_DIR}/{app_id}/{c.MCPELAUNCHER_DATA_SUBDIR}")
            self.compiled_path = self.our_data_path
            self.flatpak_path = os.path.join(self.home, f"{c.FLATPAK_DATA_DIR}/{c.MCPELAUNCHER_FLATPAK_ID}/{c.MCPELAUNCHER_DATA_SUBDIR}")
        else:
            self.flatpak_path = os.path.join(self.home, f"{c.FLATPAK_DATA_DIR}/{c.MCPELAUNCHER_FLATPAK_ID}/{c.MCPELAUNCHER_DATA_SUBDIR}")
            self.compiled_path = os.path.join(self.home, c.LOCAL_SHARE_DIR)

        self.active_path = None
        self.is_flatpak = False
        self.version_cards = {}
        self._bg_cache = {"path": None, "pixmap": None}
        self._sticker_cache = {"path": None, "pixmap": None, "zoom": None}
        self._last_qss_params = None

        # Config
        if self.running_in_flatpak:
            app_id = self.our_flatpak_id if self.our_flatpak_id else c.DEFAULT_FLATPAK_ID
            data_dir = os.path.join(self.home, f"{c.FLATPAK_DATA_DIR}/{app_id}/data")
            config_path = os.path.join(data_dir, c.CONFIG_FILE_NAME)
            old_config_path = os.path.join(self.compiled_path, c.OLD_CONFIG_FILE_NAME)
        else:
            config_path = os.path.join(self.compiled_path, c.CONFIG_FILE_NAME)
            old_config_path = os.path.join(self.compiled_path, c.OLD_CONFIG_FILE_NAME)

        self.config_manager = ConfigManager(config_path, old_config_file=old_config_path)
        self.config = self.config_manager.config

        # Lang
        lang = self.config.get(c.CONFIG_KEY_LANGUAGE, "en")
        language_manager.load_language(lang)

        # UI Setup
        self.setWindowTitle(c.t("UI_TITLE_VERSION"))
        size_str = self.config.get(c.CONFIG_KEY_WINDOW_SIZE, "700x550")
        try:
            w, h = map(int, size_str.split('x'))
            self.resize(w, h)
        except (ValueError, AttributeError) as e:
            logger.debug(f"Invalid window size '{size_str}', using default: {e}")
            self.resize(700, 550)
        self.setMinimumSize(600, 450)

        self.setWindowIcon(ImageManager.get_icon("icon.png"))

        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 18, 10, 16)
        self.main_layout.setSpacing(12)

        self.tab_widget = AnimatedTabWidget()
        self.tab_widget.setObjectName("MainTabs")
        self.tab_widget.setDocumentMode(True)
        # Native drawBase line renders as a dark horizontal line above the
        # tab bar in light mode; the QSS already styles the tabs, so disable it.
        self.tab_widget.tabBar().setDrawBase(False)
        self.main_layout.addWidget(self.tab_widget)

        self.play_tab = PlayTab(self.tab_widget, self)
        self.play_tab.setObjectName("PlayTab")
        self.tools_tab = ToolsTab(self.tab_widget, self)
        self.tools_tab.setObjectName("ToolsTab")
        self.settings_tab = SettingsTab(self.tab_widget, self)
        self.settings_tab.setObjectName("SettingsTab")
        self.about_tab = AboutTab(self.tab_widget, self)
        self.about_tab.setObjectName("AboutTab")
        self.logs_tab = LogsTab(self.tab_widget, self)
        self.logs_tab.setObjectName("LogsTab")

        self.tab_widget.addTab(self.play_tab, c.t("UI_TAB_PLAY"))
        self.tab_widget.addTab(self.tools_tab, c.t("UI_TAB_TOOLS"))
        self.tab_widget.addTab(self.settings_tab, c.t("UI_TAB_SETTINGS"))
        self.tab_widget.addTab(self.about_tab, c.t("UI_TAB_ABOUT"))
        self.tab_widget.addTab(self.logs_tab, c.t("UI_TAB_LOGS"))

        # Visuals (BG and Sticker)
        self.bg_label = VisualLabel(self.central_widget)
        self.bg_label.setScaledContents(True)
        self.sticker_label = VisualLabel(self.central_widget)
        self.game_status_label = VisualLabel(self.central_widget)
        self.game_status_label.setStyleSheet(
            "background-color: rgba(0,0,0,0.75); color: #4CAF50; "
            "font-size: 12px; font-weight: bold; padding: 4px 10px; "
            "border-radius: 10px;"
        )
        self.game_status_label.hide()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # Debounce timer for personalization and resizing
        self.personalization_timer = QTimer()
        self.personalization_timer.setSingleShot(True)
        self.personalization_timer.setInterval(50) # 50ms debounce
        self.personalization_timer.timeout.connect(self._apply_debounced_personalization)

        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(50) # 50ms for resize debounce (smoother tracking)
        self.resize_timer.timeout.connect(self._handle_resize_finished)

        # Logic init
        self.logic.detect_installation(self)
        if self.running_in_flatpak:
            self.logic.setup_flatpak_environment(self)
            self.logic.check_migration_needed(self)

        # Discord Rich Presence (lazy start on first show)
        self._discord_rpc = DiscordRPC(self)
        if self.config.get(c.CONFIG_KEY_DISCORD_RPC_ENABLED, False):
            self._discord_rpc.start()
            self._discord_rpc.set_idle()

        # Game process monitoring
        self._game_process = None
        self._game_monitor = QTimer()
        self._game_monitor.setInterval(500)
        self._game_monitor.timeout.connect(self._check_game_process)

        # System Tray
        self._tray_icon = None
        self._setup_tray_icon()

        # Apply initial theme settings
        self.apply_theme_settings()
        self.update_floating_labels()

        # Process args
        if "--version" in sys.argv:
            try:
                idx = sys.argv.index("--version")
                if idx + 1 < len(sys.argv):
                    target_version = sys.argv[idx + 1]
                    QTimer.singleShot(500, lambda: self.logic.launch_from_args(self, target_version))
            except Exception as e:
                logger.warning(f"Failed to handle --version argument: {e}")

    def resizeEvent(self, event):
        self.resize_timer.start()
        super().resizeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._handle_first_show_layout)

    def _handle_first_show_layout(self):
        """Recompute the tab bar alignment once the window is laid out on first show."""
        self._update_tab_bar_qss()
        self.update_background()
        self.update_sticker()
        self.update_floating_labels()

    def _handle_resize_finished(self):
        size = f"{self.width()}x{self.height()}"
        self.config_manager.set(c.CONFIG_KEY_WINDOW_SIZE, size)
        self.update_background()
        self.update_sticker()
        self.update_floating_labels()
        self._update_tab_bar_qss()
        if self.game_status_label.isVisible():
            w = self.width() - self.game_status_label.width() - 20
            y = self.tab_widget.tabBar().height() + 14
            self.game_status_label.move(w, y)

    def _update_tab_bar_qss(self):
        """Recompute the tab bar width so it stays aligned after a resize."""
        inset = c.SECTION_PADDING
        width = max(120, self.tab_widget.width() - 2 * inset)
        block = (
            f"QTabWidget#MainTabs::tab-bar {{\n"
            f"                top: 0px;\n"
            f"                left: {inset}px;\n"
            f"                width: {width}px;\n"
            f"                border: none;\n"
            f"            }}"
        )
        app = QApplication.instance()
        ss = app.styleSheet()
        new_ss, n = re.subn(r"QTabWidget#MainTabs::tab-bar\s*\{[^}]*\}", lambda m: block, ss, count=1)
        if n and new_ss != ss:
            app.setStyleSheet(new_ss)

    def update_sticker_visibility(self, index):
        """Show or hide the sticker based on the current tab index."""
        # Sticker visible in Play (0) and Tools (1)
        self.sticker_label.setVisible(index in [0, 1])

    def on_tab_changed(self, index):
        """Handle tab change - update sticker visibility"""
        self.update_sticker_visibility(index)

        # Clear some caches to save RAM when not in specific tabs
        if index != 0: # Not in Play tab
            # We don't clear version_cards yet as they are recreated on refresh anyway,
            # but we could potentially hide them or clear their pixmaps if RAM is critical.
            pass

    def update_background(self):
        """Update the background image position, zoom, and opacity from config."""
        bg_path = self.config.get(c.CONFIG_KEY_BG_PATH)
        if not bg_path or not os.path.exists(bg_path):
            self.bg_label.clear()
            self.bg_label.hide()
            return

        try:
            if self._bg_cache["path"] == bg_path:
                pix = self._bg_cache["pixmap"]
            else:
                pix = QPixmap(bg_path)
                if pix.isNull(): return
                self._bg_cache["path"] = bg_path
                self._bg_cache["pixmap"] = pix

            zoom = self.config.get(c.CONFIG_KEY_BG_ZOOM, 100) / 100.0
            opacity = self.config.get(c.CONFIG_KEY_BG_OPACITY, 100) / 100.0
            x_off = self.config.get(c.CONFIG_KEY_BG_X, 0)
            y_off = self.config.get(c.CONFIG_KEY_BG_Y, 0)

            w, h = int(pix.width() * zoom), int(pix.height() * zoom)
            if self.bg_label.pixmap() != pix:
                self.bg_label.setPixmap(pix)

            if self.bg_label.width() != w or self.bg_label.height() != h:
                self.bg_label.setFixedSize(w, h)

            self.bg_label.move(x_off, y_off)
            if self.bg_label.isHidden():
                self.bg_label.show()

            # Opacity - avoid creating new effect if possible
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            effect = self.bg_label.graphicsEffect()
            if not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(self.bg_label)
                self.bg_label.setGraphicsEffect(effect)

            if effect.opacity() != opacity:
                effect.setOpacity(opacity)

            self.bg_label.lower()
        except Exception as e:
            logger.debug(f"Failed to apply background opacity effect: {e}")

    def update_sticker(self):
        """Update the sticker (image or text) based on current configuration."""
        mode = self.config.get(c.CONFIG_KEY_STICKER_MODE, "none")
        if mode == "none":
            self.sticker_label.clear()
            self.sticker_label.hide()
            return

        content = self.config.get(c.CONFIG_KEY_STICKER_CONTENT, "")
        opacity = self.config.get(c.CONFIG_KEY_STICKER_OPACITY, 100) / 100.0
        corner = self.config.get(c.CONFIG_KEY_STICKER_CORNER, "bottom-right")
        x_dist = self.config.get(c.CONFIG_KEY_STICKER_X, 10)
        y_dist = self.config.get(c.CONFIG_KEY_STICKER_Y, 10)
        zoom = self.config.get(c.CONFIG_KEY_STICKER_ZOOM, 100) / 100.0

        if mode == "image":
            if not os.path.exists(content):
                self.sticker_label.clear()
                self.sticker_label.hide()
                return

            if (self._sticker_cache["path"] == content and
                self._sticker_cache["zoom"] == zoom and
                self._sticker_cache["pixmap"] is not None):
                pix = self._sticker_cache["pixmap"]
            else:
                pix = QPixmap(content)
                if not pix.isNull():
                    if zoom != 1.0:
                        pix = pix.scaled(int(pix.width() * zoom), int(pix.height() * zoom),
                                        Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self._sticker_cache["path"] = content
                    self._sticker_cache["zoom"] = zoom
                    self._sticker_cache["pixmap"] = pix

            if pix and not pix.isNull():
                if self.sticker_label.pixmap() != pix:
                    self.sticker_label.setPixmap(pix)
                if self.sticker_label.size() != pix.size():
                    self.sticker_label.setFixedSize(pix.size())
                self.sticker_label.show()
            else:
                self.sticker_label.hide()
                return
        elif mode == "text":
            self.sticker_label.clear()
            self.sticker_label.setText(content)
            self.sticker_label.setStyleSheet(f"color: white; font-weight: bold; font-size: {int(16 * zoom)}px; background: transparent; border: none;")
            self.sticker_label.adjustSize()
            self.sticker_label.show()
        else:
            self.sticker_label.hide()
            return

        self.update_sticker_visibility(self.tab_widget.currentIndex())

        # Position based on corner
        w, h = self.width(), self.height()
        sw, sh = self.sticker_label.width(), self.sticker_label.height()

        if corner == "top-left": self.sticker_label.move(x_dist, y_dist)
        elif corner == "top-right": self.sticker_label.move(w - sw - x_dist, y_dist)
        elif corner == "bottom-left": self.sticker_label.move(x_dist, h - sh - y_dist)
        else: self.sticker_label.move(w - sw - x_dist, h - sh - y_dist)

        # Opacity - reuse effect
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        effect = self.sticker_label.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(self.sticker_label)
            self.sticker_label.setGraphicsEffect(effect)

        if effect.opacity() != opacity:
            effect.setOpacity(opacity)

        self.sticker_label.raise_()

    def restore_default_settings(self):
        """Restore all settings to factory defaults after user confirmation."""
        if messagebox.askyesno(self, c.t("UI_CONFIRM_TITLE"), c.t("UI_RESTORE_DEFAULTS_CONFIRM")):
            self.config_manager.restore_defaults()
            messagebox.showinfo(self, c.t("UI_RESTORE_DEFAULTS_SUCCESS_TITLE"), c.t("UI_RESTORE_DEFAULTS_SUCCESS_MSG"))
            self.close()

    def change_appearance(self, type_change, value):
        """Change a visual setting (e.g. color theme) and update the UI."""
        if type_change == "color":
            self.config_manager.set(c.CONFIG_KEY_COLOR_THEME, value)
            self.config_manager.save_config()
            self.apply_theme_settings()
            if hasattr(self, "settings_tab"):
                self.settings_tab._refresh_per_widget_styles()
            return
        self.config_manager.save_config()
        self.apply_theme_settings()

    def apply_theme_settings(self):
        """Apply global theme settings using selectors to avoid re-applying QSS on tab change."""
        mode = self.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
        theme_color = self.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
        accent = c.THEME_COLOR_MAP.get(theme_color, "#1f6aa5")
        section_opacity_val = self.config.get(c.CONFIG_KEY_SECTION_OPACITY, 100)
        bg_path = self.config.get(c.CONFIG_KEY_BG_PATH)
        has_bg = bool(bg_path and os.path.exists(bg_path))

        # Update visuals regardless of QSS cache
        self.update_background()
        self.update_sticker()

        # Save theme state for custom painted animated widgets
        self.current_accent_color = accent
        self.is_dark_mode = (mode == "Dark")
        if hasattr(self, "tab_widget") and self.tab_widget.tabBar():
            self.tab_widget.tabBar().update()

        # Optimization: skip reapplying the exact same QSS
        params = (mode, theme_color, section_opacity_val, has_bg)
        if self._last_qss_params == params:
            return
        self._last_qss_params = params

        if mode == "Dark":
            bg = blend_colors("#0e0e0e", accent, 0.035)
            frame_bg_base = blend_colors("#171717", accent, 0.065)
            tab_bg = blend_colors("#141414", accent, 0.050)
            input_bg = blend_colors("#1f1f1f", accent, 0.085)
            input_border = blend_colors("#303030", accent, 0.12)
            text = "#dedede"
            input_text = "#ffffff"
        else:
            bg = blend_colors("#f5f6f8", accent, 0.02)
            frame_bg_base = blend_colors("#ffffff", accent, 0.04)
            tab_bg = blend_colors("#e9ecf0", accent, 0.04)
            input_bg = blend_colors("#ffffff", accent, 0.04)
            input_border = blend_colors("#d5d9e0", accent, 0.10)
            text = "#212121"
            input_text = "#212121"

        # Tab bar inset to match the content panels below (SECTION_PADDING each side)
        tab_inset = c.SECTION_PADDING
        tab_bar_width = max(120, self.tab_widget.width() - 2 * tab_inset)

        section_opacity = section_opacity_val / 100.0
        frame_bg_opaque = hex_to_rgba(frame_bg_base, 1.0)
        
        # Section opacity should only affect Settings and Tools tabs
        frame_bg_transparent = hex_to_rgba(frame_bg_base, section_opacity)

        # Tool cards get a more solid background so they read as buttons even
        # when section opacity is low, plus an accent-tinted hover "illumination"
        # in both themes so the accent color clearly shows on mouse over.
        tool_card_bg = hex_to_rgba(frame_bg_base, max(section_opacity, 0.94))
        _base = QColor(frame_bg_base)
        _acc = QColor(accent)
        if mode == "Dark":
            # Dark: keep most of the base but add a clear accent glow.
            _hr = int(_base.red() * 0.80 + _acc.red() * 0.20)
            _hg = int(_base.green() * 0.80 + _acc.green() * 0.20)
            _hb = int(_base.blue() * 0.80 + _acc.blue() * 0.20)
        else:
            # Light: a softer accent tint so it reads as a warm highlight.
            _hr = int(_base.red() * 0.88 + _acc.red() * 0.12)
            _hg = int(_base.green() * 0.88 + _acc.green() * 0.12)
            _hb = int(_base.blue() * 0.88 + _acc.blue() * 0.12)
        tool_card_hover_bg = QColor(_hr, _hg, _hb).name()
        tool_card_hover_border = hex_to_rgba(accent, 0.85)

        if has_bg:
            bg_qss = f"background: transparent;"
        else:
            bg_qss = f"background-color: {bg};"

        # The configured background is rendered once by `bg_label` (behind
        # every widget). Play/Tools scroll content must stay transparent so
        # that single image shows through, without re-painting a duplicate.
        if has_bg:
            scroll_content_bg = "background: transparent;"
        else:
            scroll_content_bg = f"background-color: {bg};"

        # Generate down-arrow pixmap for QComboBox (stylesheets suppress native arrow)
        arrow_size = 12
        arrow_path = os.path.join(c.HOME_DIR, ".local", "share", "cianovalauncher", "combo_arrow.png")
        os.makedirs(os.path.dirname(arrow_path), exist_ok=True)
        arrow_pixmap = QPixmap(arrow_size, arrow_size)
        arrow_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(arrow_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.moveTo(arrow_size // 2, arrow_size - 1)
        path.lineTo(1, 2)
        path.lineTo(arrow_size - 1, 2)
        path.closeSubpath()
        painter.fillPath(path, QColor(input_text))
        painter.end()
        arrow_pixmap.save(arrow_path)

        # Fixed semi-transparent background for floating labels
        floating_label_bg = hex_to_rgba("#353542" if mode == "Dark" else "#e2e6ed", 0.85)
        floating_label_border = f"1px solid {hex_to_rgba('#ffffff' if mode == 'Dark' else '#000000', 0.15)}"

        # Accent-tinted "pill" style for header indicators (status, profile,
        # installation, mode, section titles). Reads clearly in both themes.
        pill_bg = hex_to_rgba(accent, 0.18) if mode == "Dark" else hex_to_rgba(accent, 0.12)
        pill_border = f"1px solid {hex_to_rgba(accent, 0.50)}"
        pill_text = text if mode == "Dark" else "#1a1a1a"

        qss = f"""
            QMainWindow, QWidget#centralWidget {{
                {bg_qss}
                color: {text};
                font-family: 'Segoe UI', 'Roboto', -apple-system, sans-serif;
            }}
            QLabel {{
                color: {text};
            }}
            QDialog {{
                background-color: {bg};
                color: {text};
            }}
            #VersionManagerDialog, #InstallDialog, #AddonManagerDialog, #MigrationDialog, #GameConfigDialog {{
                background-color: {bg};
            }}
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar {{
                alignment: center;
                background: transparent;
                border: none;
                min-height: 52px;
                padding: 0px;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {text};
                padding: 0px 18px;
                min-height: 38px;
                border-radius: 19px;
                font-weight: bold;
                font-size: 13px;
                margin: 2px 6px;
                border: none;
                outline: none;
            }}
            QTabBar::tab:selected {{
                background: transparent;
                color: #ffffff;
            }}
            QTabBar::tab:hover:!selected {{
                background: transparent;
            }}
            QTabBar QToolButton, QTabBar::scroller {{
                width: 0px;
                height: 0px;
                border: none;
                background: transparent;
                padding: 0px;
                margin: 0px;
                qproperty-icon: none;
            }}
            QTabWidget#MainTabs::tab-bar {{
                top: 0px;
                left: {tab_inset}px;
                width: {tab_bar_width}px;
                border: none;
            }}
            QToolTip {{
                background-color: {"#181a1f" if mode == "Dark" else "#ffffff"};
                color: {"#ffffff" if mode == "Dark" else "#18191c"};
                border: 1px solid {"rgba(255, 255, 255, 0.18)" if mode == "Dark" else "rgba(0, 0, 0, 0.16)"};
                border-radius: 6px;
                padding: 5px 9px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: 1px solid {accent};
                border-radius: {c.RADIUS_BUTTON}px;
                padding: 7px 16px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {adjust_color(accent, 20)};
                border: 1px solid {adjust_color(accent, 20)};
            }}
            QPushButton:pressed {{
                background-color: {adjust_color(accent, -18)};
                border: 1px solid {adjust_color(accent, -18)};
            }}
            QPushButton:disabled {{
                background-color: {"#363640" if mode == "Dark" else "#e2e5ea"};
                color: {"#6c6c78" if mode == "Dark" else "#989ea8"};
                border: 1px solid {"#363640" if mode == "Dark" else "#d0d5dd"};
            }}
            QPushButton:flat {{
                background-color: {accent};
                color: white;
                border: none;
            }}
            QPushButton:flat:disabled {{
                background-color: {"#363640" if mode == "Dark" else "#e2e5ea"};
                color: {"#6c6c78" if mode == "Dark" else "#989ea8"};
                border: none;
            }}
            QLineEdit, QComboBox, QSpinBox, QTextEdit {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: {c.RADIUS_INPUT}px;
                padding: 6px 10px;
                font-size: 13px;
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {{
                border: 1px solid {accent};
            }}
            QComboBox::drop-down {{ 
                border: none; 
                width: 26px; 
                border-top-right-radius: {c.RADIUS_INPUT}px;
                border-bottom-right-radius: {c.RADIUS_INPUT}px;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: url("{arrow_path}");
                width: {arrow_size}px;
                height: {arrow_size}px;
                margin-right: 6px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                selection-background-color: {accent};
                selection-color: white;
                border-radius: {c.RADIUS_INPUT}px;
                padding: 4px;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 30px;
                padding: 5px 10px;
                border-radius: {c.RADIUS_TINY}px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {hex_to_rgba(accent, 0.25)};
            }}
            QCheckBox, QRadioButton {{
                color: {text};
                spacing: 8px;
                font-size: 13px;
            }}
            QCheckBox::indicator, QRadioButton::indicator {{
                width: 18px; height: 18px; border-radius: {c.RADIUS_TINY}px;
                border: 2px solid {accent}; background: {input_bg};
            }}
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
                background: {accent};
            }}
            QPushButton#PlayButton, QPushButton#SaveButton, QPushButton#ActionButton {{
                background-color: {accent};
                color: #ffffff;
                border-radius: {c.CORNER_RADIUS}px;
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 0.5px;
                border: 1px solid rgba(255, 255, 255, 0.25);
                padding: 8px 16px;
            }}
            QPushButton#PlayButton:hover, QPushButton#SaveButton:hover, QPushButton#ActionButton:hover {{
                background-color: {adjust_color(accent, 22)};
                border: 1px solid rgba(255, 255, 255, 0.4);
            }}
            QPushButton#PlayButton:pressed, QPushButton#SaveButton:pressed, QPushButton#ActionButton:pressed {{
                background-color: {adjust_color(accent, -18)};
            }}
            QPushButton#PlayButton:disabled, QPushButton#SaveButton:disabled, QPushButton#ActionButton:disabled {{
                background-color: {"#363640" if mode == "Dark" else "#e2e5ea"};
                color: {"#6c6c78" if mode == "Dark" else "#989ea8"};
                border: 1px solid {"#363640" if mode == "Dark" else "#d0d5dd"};
            }}
            QPushButton#ToolButton {{
                background-color: {accent};
                color: white;
                border: none;
                border-radius: {c.RADIUS_BUTTON}px;
                font-weight: bold;
                min-width: 24px;
                min-height: 24px;
            }}
            QPushButton#ToolButton:hover {{
                background-color: {adjust_color(accent, 20)};
            }}
            QPushButton#ToolButton:disabled {{
                background-color: {"#363640" if mode == "Dark" else "#e2e5ea"};
                color: {"#6c6c78" if mode == "Dark" else "#989ea8"};
            }}
            QFrame#ToolCard, QFrame#GroupFrame, QFrame#VersionCard, QFrame#VersionContainerCard, QFrame#LaunchControlCard, QFrame#RightTopCard, QFrame#RightBottomCard {{
                border-radius: {c.CORNER_RADIUS}px;
                border: 1px solid {hex_to_rgba(input_border, 0.45)};
                background-color: {frame_bg_opaque};
            }}

            /* Version Container Card & Launch Control Card & Right Panel Cards Styling */
            QFrame#VersionContainerCard, QFrame#LaunchControlCard, QFrame#RightTopCard, QFrame#RightBottomCard {{
                border-radius: {c.CORNER_RADIUS}px;
                border: 1px solid {hex_to_rgba(input_border, 0.45)};
                background-color: {frame_bg_opaque};
            }}
            QWidget#RightPanelContainer {{
                background: transparent;
                border: none;
            }}
            QFrame#VersionCard {{
                border: 1px solid {hex_to_rgba(input_border, 0.45)};
                background-color: {frame_bg_opaque};
            }}
            QFrame#VersionCard:hover {{
                border: 1px solid {hex_to_rgba(accent, 0.75)};
                background-color: {hex_to_rgba(accent, 0.08) if mode == "Dark" else hex_to_rgba(accent, 0.05)};
            }}
            QFrame#VersionCard[selected="true"] {{
                border: 2px solid {accent};
                background-color: {hex_to_rgba(accent, 0.22) if mode == "Dark" else hex_to_rgba(accent, 0.14)};
            }}

            /* Wireframe Mockup Panels */
            QFrame#WireframePanel {{
                border-radius: {c.CORNER_RADIUS}px;
                border: 1.5px dashed {hex_to_rgba(input_border, 0.65)};
                background-color: {hex_to_rgba(frame_bg_base, 0.40)};
            }}
            QFrame#WireframeBox {{
                border-radius: 10px;
                border: 1px dashed {hex_to_rgba(input_border, 0.50)};
                background-color: {hex_to_rgba(input_bg, 0.45)};
            }}
            #PlayTab QFrame#DualStatusCard, QFrame#DualStatusCard {{
                border-radius: 12px;
                border: 1.5px solid {hex_to_rgba(input_border, 0.65)};
                background-color: transparent;
                background: transparent;
            }}
            QFrame#DualCardDivider {{
                background-color: {hex_to_rgba(input_border, 0.40)};
                border: none;
                max-height: 1px;
            }}
            QFrame#QuickSubCard {{
                background-color: {"rgba(255, 255, 255, 0.04)" if mode == "Dark" else "rgba(0, 0, 0, 0.03)"};
                border: 1px solid {"rgba(255, 255, 255, 0.08)" if mode == "Dark" else "rgba(0, 0, 0, 0.08)"};
                border-radius: 10px;
            }}
            QFrame#QuickSubCard:hover {{
                background-color: {"rgba(255, 255, 255, 0.075)" if mode == "Dark" else "rgba(0, 0, 0, 0.055)"};
                border: 1px solid {"rgba(255, 255, 255, 0.16)" if mode == "Dark" else "rgba(0, 0, 0, 0.15)"};
            }}
            QFrame#QuickSubCardIcon {{
                background-color: {"rgba(255, 255, 255, 0.06)" if mode == "Dark" else "rgba(0, 0, 0, 0.04)"};
                border: 1px solid {"rgba(255, 255, 255, 0.08)" if mode == "Dark" else "rgba(0, 0, 0, 0.08)"};
                border-radius: 8px;
            }}
            QPushButton#QuickActionBtn {{
                background-color: {"rgba(255, 255, 255, 0.08)" if mode == "Dark" else "rgba(0, 0, 0, 0.05)"};
                color: {"#ffffff" if mode == "Dark" else "#1a1c22"};
                border: 1px solid {"rgba(255, 255, 255, 0.14)" if mode == "Dark" else "rgba(0, 0, 0, 0.12)"};
                border-radius: 7px;
                padding: 5px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#QuickActionBtn:hover {{
                background-color: {hex_to_rgba(accent, 0.25) if mode == "Dark" else hex_to_rgba(accent, 0.15)};
                color: {"#ffffff" if mode == "Dark" else accent};
                border: 1px solid {accent};
            }}
            QPushButton#QuickActionBtn:pressed {{
                background-color: {accent};
                color: #ffffff;
            }}
            QPushButton#SidebarHomeButton {{
                background-color: {hex_to_rgba(accent, 0.22) if mode == "Dark" else hex_to_rgba(accent, 0.14)};
                color: {"#ffffff" if mode == "Dark" else "#111111"};
                border: 1.5px solid {hex_to_rgba(accent, 0.50)};
                border-radius: 10px;
                padding-left: 14px;
                text-align: left;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton#SidebarHomeButton:hover {{
                background-color: {hex_to_rgba(accent, 0.35) if mode == "Dark" else hex_to_rgba(accent, 0.24)};
                border: 1.5px solid {accent};
            }}
            QPushButton#SidebarHomeButton:pressed {{
                background-color: {hex_to_rgba(accent, 0.48) if mode == "Dark" else hex_to_rgba(accent, 0.38)};
            }}
            QLabel#ModeValueLabel {{
                color: {accent};
                font-weight: bold;
                font-size: 12px;
                background: transparent;
                border: none;
            }}
            QComboBox#CleanModeCombo {{
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
                font-size: 13px;
                font-weight: bold;
                color: {accent};
            }}
            QComboBox#CleanModeCombo::drop-down {{
                border: none;
                width: 14px;
                background: transparent;
            }}
            QComboBox#CleanModeCombo::down-arrow {{
                image: url("{arrow_path}");
                width: 10px;
                height: 10px;
            }}
            QComboBox#CleanModeCombo QAbstractItemView {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                selection-background-color: {accent};
                selection-color: white;
                border-radius: {c.RADIUS_INPUT}px;
                padding: 4px;
                outline: none;
            }}

            /* Floating-style Launch Action Dropdown Card */
            QFrame#LaunchComboCard {{
                border-radius: 10px;
                border: 1px solid {hex_to_rgba(input_border, 0.55)};
                background-color: {hex_to_rgba(input_bg, 0.70)};
            }}
            QFrame#LaunchComboCard:hover {{
                border: 1px solid {hex_to_rgba(accent, 0.85)};
                background-color: {hex_to_rgba(input_bg, 0.95)};
            }}
            QComboBox#LaunchSubCombo {{
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
                font-size: 13px;
                font-weight: bold;
                color: {text};
            }}
            QComboBox#LaunchSubCombo::drop-down {{
                border: none;
                width: 14px;
                background: transparent;
            }}
            QComboBox#LaunchSubCombo::down-arrow {{
                image: url("{arrow_path}");
                width: 10px;
                height: 10px;
            }}
            QComboBox#LaunchSubCombo QAbstractItemView {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                selection-background-color: {accent};
                selection-color: white;
                border-radius: {c.RADIUS_INPUT}px;
                padding: 4px;
                outline: none;
            }}

            #PlayTab QFrame#GroupFrame, #PlayTab QFrame#VersionCard, #PlayTab QFrame#VersionContainerCard, #PlayTab QFrame#LaunchControlCard, #PlayTab QFrame#RightTopCard, #PlayTab QFrame#RightBottomCard, #AboutTab QFrame#GroupFrame {{
                background-color: {frame_bg_opaque};
            }}

            #SettingsTab, #LogsTab {{
                background-color: {bg};
            }}
            #PlayTab, #ToolsTab, #AboutTab {{
                background-color: transparent;
            }}
            #SettingsTab QStackedWidget, #SettingsTab QStackedWidget > QWidget {{
                background-color: {bg};
            }}

            #ToolsTab QFrame#GroupFrame, #ToolsTab QFrame#ToolCard,
            #SettingsTab QFrame#GroupFrame {{
                background-color: {frame_bg_transparent};
            }}

            #ToolsTab QFrame#ToolCard {{
                background-color: {tool_card_bg};
            }}

            QScrollArea#GroupFrame {{
                background-color: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget#SettingsPageContent {{
                background-color: {bg};
            }}
            #PlayTab QScrollArea > QWidget > QWidget#VersionList,
            #ToolsTab QScrollArea > QWidget > QWidget#ScrollContent {{
                {scroll_content_bg}
            }}
            #AboutTab QScrollArea {{
                background-color: transparent;
            }}
            #AboutTab QScrollArea > QWidget > QWidget#ScrollContent {{
                background-color: transparent;
            }}
            #SettingsTab QScrollArea {{
                background-color: {bg};
            }}
            #ToolsTab QFrame#ToolCard:hover,
            #ToolsTab QFrame#GroupFrame:hover {{
                border: 1px solid {tool_card_hover_border};
            }}
            #ToolsTab QFrame#ToolCard:hover {{
                background-color: {tool_card_hover_bg};
                border: 1px solid {accent};
            }}
            QLabel#HeaderLabel {{
                color: {accent};
                font-size: 18px;
                font-weight: bold;
                background: transparent;
                margin-bottom: 5px;
            }}
            QLabel#FloatingLabel {{
                background-color: {floating_label_bg};
                color: {text};
                padding: 5px 15px;
                border-radius: 6px;
                border: {floating_label_border};
                qproperty-alignment: 'AlignCenter';
            }}
            QLabel#IndicatorPill {{
                background-color: {pill_bg};
                color: {pill_text};
                padding: 5px 14px;
                border-radius: 14px;
                border: {pill_border};
                font-weight: bold;
                font-size: 12px;
                qproperty-alignment: 'AlignCenter';
            }}
            QSlider:horizontal {{
                min-height: 24px;
            }}
            QSlider::groove:horizontal {{
                background: {"#3e3e4c" if mode == "Dark" else "#d0d5dd"};
                height: 6px;
                border-radius: 3px;
                margin: 2px 0;
            }}
            QSlider::handle:horizontal {{
                background: {accent};
                border: 2px solid {"#ffffff" if mode == "Dark" else "#ffffff"};
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {adjust_color(accent, 25)};
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 3px;
            }}
            QComboBox::item:selected {{
                background-color: {accent};
                color: white;
            }}
            /* Sleek modern scrollbars */
            QScrollBar:vertical {{
                background: transparent;
                width: 11px;
                margin: 2px 0px 2px 0px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {hex_to_rgba(accent, 0.65)};
                min-height: 28px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {accent};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::horizontal {{
                background: transparent;
                height: 8px;
                margin: 0px 2px 0px 2px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {hex_to_rgba(accent, 0.65)};
                min-width: 24px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {accent};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            /* ── Settings sidebar ── */
            QFrame#SettingsSidebar {{
                background-color: {hex_to_rgba(frame_bg_base, 0.55)};
                border-right: 1px solid {hex_to_rgba(input_border, 0.35)};
                border-top-left-radius: {c.CORNER_RADIUS}px;
                border-bottom-left-radius: {c.CORNER_RADIUS}px;
            }}
            QPushButton#SidebarButton {{
                background: transparent;
                color: {"#333333" if mode == "Light" else "#cccccc"};
                border: none;
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: bold;
                text-align: left;
                min-width: 35px;
                min-height: 42px;
                margin: 2px 4px;
            }}
            QPushButton#SidebarButton:hover {{
                background: {hex_to_rgba(accent, 0.12)};
                color: {"#000000" if mode == "Light" else "white"};
            }}
            QPushButton#SidebarButton:disabled {{
                background: transparent;
                color: {"#9a9aa0" if mode == "Light" else "#666666"};
            }}
            QPushButton#SidebarButton[active="true"] {{
                background: {hex_to_rgba(accent, 0.20)};
                color: {accent};
                border-left: 4px solid {accent};
                border-radius: 4px;
            }}
            QPushButton#SidebarToggle {{
                background: transparent;
                color: {"#333333" if mode == "Light" else "#cccccc"};
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                min-height: 38px;
                margin: 2px 4px;
            }}
            QPushButton#SidebarToggle:hover {{
                background: {hex_to_rgba(accent, 0.12)};
                color: {"#000000" if mode == "Light" else "white"};
            }}
            QPushButton#SidebarToggle:disabled {{
                background: transparent;
                color: {"#9a9aa0" if mode == "Light" else "#666666"};
            }}
            /* ── QGroupBox in Settings ── */
            #SettingsTab QGroupBox {{
                border: 1px solid {hex_to_rgba(input_border, 0.35)};
                border-radius: 8px;
                margin-top: 1.5ex;
                padding: 18px 12px 12px 12px;
                background-color: {frame_bg_transparent};
            }}
            #SettingsTab QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: {text};
                font-weight: bold;
            }}
            #SettingsTab QGroupBox:hover {{
                border: 1px solid {accent};
            }}
            /* ── Settings footer bar ── */
            QFrame#SettingsFooterBar {{
                background-color: {frame_bg_opaque};
                border-top: 1px solid {hex_to_rgba(input_border, 0.4)};
            }}
            /* Generic scroll areas remain transparent */
            QScrollArea, QScrollArea > QWidget {{
                background: transparent;
                border: none;
            }}
            /* ── Modern Fallback QFileDialog Styling ── */
            QFileDialog {{
                background-color: {bg};
                color: {text};
            }}
            QFileDialog QTreeView, QFileDialog QListView, QFileDialog QTableView {{
                background-color: {input_bg};
                color: {text};
                border: 1px solid {hex_to_rgba(input_border, 0.5)};
                border-radius: 8px;
                padding: 4px;
                outline: none;
            }}
            QFileDialog QTreeView::item, QFileDialog QListView::item {{
                padding: 4px 6px;
                border-radius: 4px;
            }}
            QFileDialog QTreeView::item:hover, QFileDialog QListView::item:hover {{
                background-color: {hex_to_rgba(accent, 0.20)};
            }}
            QFileDialog QTreeView::item:selected, QFileDialog QListView::item:selected {{
                background-color: {accent};
                color: #ffffff;
            }}
            QFileDialog QHeaderView, QFileDialog QHeaderView::section, QFileDialog QTableCornerButton::section {{
                background-color: {frame_bg_opaque};
                color: {text};
                padding: 5px 8px;
                border: none;
                border-right: 1px solid {hex_to_rgba(input_border, 0.3)};
                border-bottom: 1px solid {hex_to_rgba(input_border, 0.3)};
                font-weight: bold;
                font-size: 11px;
            }}
            QFileDialog QToolButton {{
                background-color: {hex_to_rgba(frame_bg_base, 0.6)};
                color: {text};
                border: 1px solid {hex_to_rgba(input_border, 0.4)};
                border-radius: 6px;
                padding: 4px;
                margin: 2px;
            }}
            QFileDialog QToolButton:hover {{
                background-color: {hex_to_rgba(accent, 0.3)};
                border: 1px solid {accent};
            }}
            QFileDialog QToolButton:pressed {{
                background-color: {hex_to_rgba(accent, 0.5)};
            }}
            QFileDialog QSplitter::handle {{
                background-color: {hex_to_rgba(input_border, 0.3)};
            }}
        """
        try:
            QApplication.instance().setStyleSheet(qss)
            palette = QApplication.instance().palette()
            if mode == "Dark":
                palette.setColor(QPalette.ToolTipBase, QColor("#181a1f"))
                palette.setColor(QPalette.ToolTipText, QColor("#ffffff"))
            else:
                palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
                palette.setColor(QPalette.ToolTipText, QColor("#18191c"))
            QApplication.instance().setPalette(palette)
        except Exception as e:
            logger.warning(f"Failed to apply global stylesheet: {e}")

        if hasattr(self, "settings_tab"):
            self.settings_tab._refresh_per_widget_styles()

        if hasattr(self, "play_tab") and hasattr(self.play_tab, "update_theme_styles"):
            self.play_tab.update_theme_styles()
        if hasattr(self, "tools_tab") and hasattr(self.tools_tab, "update_theme_styles"):
            self.tools_tab.update_theme_styles()
        if hasattr(self, "about_tab") and hasattr(self.about_tab, "update_theme_styles"):
            self.about_tab.update_theme_styles()

        from src.core.install_ops import refresh_version_cards_theme
        try:
            refresh_version_cards_theme(self)
        except Exception:
            pass

        # Apply drop shadow to all card-type frames
        shadow_color = QColor(0, 0, 0, 60) if mode == "Dark" else QColor(0, 0, 0, 30)
        for frame in self.findChildren(QFrame):
            if frame.objectName() in ("GroupFrame", "ToolCard", "VersionCard", "VersionContainerCard", "LaunchControlCard", "RightTopCard", "RightBottomCard"):
                existing = frame.graphicsEffect()
                if existing is None:
                    shadow = QGraphicsDropShadowEffect()
                    shadow.setBlurRadius(12)
                    shadow.setOffset(0, 2)
                    shadow.setColor(shadow_color)
                    frame.setGraphicsEffect(shadow)

        self.update_top_profile_badge()

    def open_profile_manager(self):
        """Open the profile manager dialog."""
        from src.gui.profile_manager_dialog import ProfileManagerDialog
        dialog = ProfileManagerDialog(self, self)
        dialog.exec()

    def update_top_profile_badge(self):
        """Trigger repaint of AnimatedTabBar to update profile indicator."""
        if hasattr(self, "tab_widget") and self.tab_widget and self.tab_widget.tabBar():
            self.tab_widget.tabBar().update()

    def _apply_debounced_personalization(self):
        self.apply_theme_settings()

    def update_floating_labels(self):
        """Hide or show floating status labels based on their text content."""
        # In PySide6, we can iterate over widgets to hide empty FloatingLabels
        for widget in self.findChildren(QLabel, "FloatingLabel") + self.findChildren(QLabel, "IndicatorPill"):
            text = widget.text().strip()
            # If it's a profile or install label, it might have icons/prefixes
            if not text or text in ["●", "👤", "● Searching...", "● Buscando..."]:
                if "Searching" not in text and "Buscando" not in text:
                    widget.hide()
                else:
                    widget.show()
            else:
                widget.show()

    def retranslate_all(self):
        self.setWindowTitle(c.t("UI_TITLE_VERSION"))
        self.tab_widget.setTabText(0, c.t("UI_TAB_PLAY"))
        self.tab_widget.setTabText(1, c.t("UI_TAB_TOOLS"))
        self.tab_widget.setTabText(2, c.t("UI_TAB_SETTINGS"))
        self.tab_widget.setTabText(3, c.t("UI_TAB_ABOUT"))
        self.tab_widget.setTabText(4, c.t("UI_TAB_LOGS"))
        for tab in (self.play_tab, self.tools_tab, self.settings_tab, self.about_tab, self.logs_tab):
            if hasattr(tab, "retranslate_ui"):
                tab.retranslate_ui()
        self.update_floating_labels()
        self.update_top_profile_badge()

    def show_info(self, title, msg):
        """Show an information dialog with the given title and message."""
        messagebox.showinfo(self, title, msg)

    # Tool openers
    def install_apk_dialog(self):
        """Switch to the embedded installation view in the play tab sidebar."""
        self.tab_widget.setCurrentIndex(0)
        self.play_tab.show_install_view()
    def open_skin_tool(self):
        """Open the skin pack creator tool."""
        SkinPackTool(self).exec()
    def open_migration_tool(self):
        """Open the data migration tool dialog."""
        try: MigrationWizard(self).exec()
        except Exception as e: messagebox.showerror(self, c.t("UI_ERROR_TITLE"), f"Error: {e}")
    def open_game_config_tool(self):
        """Open the Minecraft game options editor dialog."""
        try: GameConfigDialog(self).exec()
        except Exception as e: messagebox.showerror(self, c.t("UI_ERROR_TITLE"), f"Error: {e}")
    def open_addon_manager(self):
        """Open the addon (worlds, resource packs, behavior packs) manager dialog."""
        try: AddonManagerDialog(self).exec()
        except Exception as e: messagebox.showerror(self, c.t("UI_ERROR_TITLE"), f"Error: {e}")

    def open_version_manager(self, version=None):
        """Open the version manager dialog for renaming, customizing, and shortcuts."""
        from src.gui.version_manager_dialog import SleekVersionEditDialog
        try:
            SleekVersionEditDialog(self, target_version=version).exec()
        except Exception as e:
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), f"Error: {e}")

    def sync_gamemode_ui(self, value):
        """Synchronize the gamemode toggle between Play and Settings tabs."""
        self.config_manager.set(c.CONFIG_KEY_GAMEMODE_ENABLED, value)
        if hasattr(self.play_tab, "check_gamemode"):
            self.play_tab.check_gamemode.blockSignals(True)
            self.play_tab.check_gamemode.setChecked(value)
            self.play_tab.check_gamemode.blockSignals(False)
        if hasattr(self.settings_tab, "checks"):
            cb = self.settings_tab.checks.get(c.CONFIG_KEY_GAMEMODE_ENABLED)
            if cb:
                cb.blockSignals(True)
                cb.setChecked(value)
                cb.blockSignals(False)

    def sync_discord_rpc_ui(self, value):
        """Synchronize the Discord RPC toggle between Play and Settings tabs."""
        self.config_manager.set(c.CONFIG_KEY_DISCORD_RPC_ENABLED, value)
        self._sync_discord_play(value)
        self._sync_discord_settings(value)
        if value:
            self._discord_rpc.start()
            self._discord_rpc.set_idle()
        else:
            self._discord_rpc.stop()

    def _sync_discord_play(self, value):
        if hasattr(self.play_tab, "check_discord"):
            blocked = self.play_tab.check_discord.blockSignals(True)
            self.play_tab.check_discord.setChecked(value)
            self.play_tab.check_discord.blockSignals(blocked)

    def _sync_discord_settings(self, value):
        if hasattr(self.settings_tab, "check_discord_rpc"):
            blocked = self.settings_tab.check_discord_rpc.blockSignals(True)
            self.settings_tab.check_discord_rpc.setChecked(value)
            self.settings_tab.check_discord_rpc.blockSignals(blocked)

    def sync_launch_action_ui(self, action_key):
        """Synchronize the launch-action combo between Play and Settings tabs."""
        self.config_manager.set(c.CONFIG_KEY_LAUNCH_ACTION, action_key)
        for tab in (self.play_tab, self.settings_tab):
            if tab is None:
                continue
            if hasattr(tab, "box_launch_action") and hasattr(tab.box_launch_action, "setCurrentAction"):
                tab.box_launch_action.setCurrentAction(action_key)
            elif hasattr(tab, "combo_launch_action"):
                blocked = tab.combo_launch_action.blockSignals(True)
                if hasattr(tab.combo_launch_action, "setCurrentAction"):
                    tab.combo_launch_action.setCurrentAction(action_key)
                elif hasattr(tab.combo_launch_action, "findData"):
                    idx = tab.combo_launch_action.findData(action_key)
                    if idx >= 0:
                        tab.combo_launch_action.setCurrentIndex(idx)
                tab.combo_launch_action.blockSignals(blocked)

    def _setup_tray_icon(self):
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setIcon(self.windowIcon())
        self._tray_icon.setToolTip(c.t("UI_TITLE_VERSION"))
        tray_menu = QMenu()
        show_act = QAction(c.t("UI_TRAY_SHOW"), self)
        show_act.triggered.connect(self.show)
        quit_act = QAction(c.t("UI_TRAY_QUIT"), self)
        quit_act.triggered.connect(self.close)
        tray_menu.addAction(show_act)
        tray_menu.addAction(quit_act)
        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()
            self.raise_()

    def hide_to_tray(self):
        self._tray_icon.show()
        self.hide()
        self._game_monitor.start()

    def on_game_launched(self):
        self._game_monitor.start()
        self._set_persistent_game_indicator(True)
        if hasattr(self.play_tab, "set_game_status"):
            self.play_tab.set_game_status(True)

    def _set_persistent_game_indicator(self, running):
        """Global badge suppressed in favor of dedicated PlayTab status card."""
        if hasattr(self, "game_status_label") and self.game_status_label:
            self.game_status_label.hide()

    def _check_game_process(self):
        if self._game_process is None:
            self._game_monitor.stop()
            return
        rc = self._game_process.poll()
        if rc is not None:
            self._game_process = None
            self._game_monitor.stop()
            if hasattr(self, '_tray_icon') and self._tray_icon and self.isHidden():
                self._tray_icon.hide()
                self.show()
                self.activateWindow()
                self.raise_()
            if hasattr(self.play_tab, "set_game_status"):
                self.play_tab.set_game_status(False)
            self._set_persistent_game_indicator(False)

    def manage_desktop_shortcut(self):
        """Open the version manager to manage desktop shortcuts."""
        self.open_version_manager()

    def closeEvent(self, event):
        self._game_monitor.stop()
        self.config_manager.flush()
        if self._tray_icon:
            self._tray_icon.hide()
        if hasattr(self, '_discord_rpc') and self._discord_rpc:
            self._discord_rpc.stop()

        # Stop background worker threads cleanly
        workers = []
        if hasattr(self, '_update_checker') and self._update_checker:
            t = getattr(self._update_checker, '_thread', None)
            if t and isinstance(t, QThread) and t.isRunning():
                workers.append(t)
        if hasattr(self, 'play_tab') and self.play_tab:
            for subview_name in ['view_screenshots', 'view_worlds', 'view_packs', 'view_mods']:
                subview = getattr(self.play_tab, subview_name, None)
                if subview:
                    for attr in ['_scan_worker', '_world_scan_worker', '_pack_scan_worker', '_worker']:
                        w = getattr(subview, attr, None)
                        if w and isinstance(w, QThread) and w.isRunning():
                            workers.append(w)
        for w in workers:
            try:
                w.requestInterruption()
                w.quit()
                w.wait(200)
            except Exception:
                pass

        super().closeEvent(event)

    def check_version_update(self):
        """Compare stored version with current launcher version and show changelog on update.
        Also schedules a remote update check if enough time has passed."""
        config_ver = self.config.get(c.CONFIG_KEY_VERSION, "0.0.0")
        current_ver = c.VERSION_LAUNCHER

        try:
            def ver_to_tuple(v): return tuple(map(int, (v.split('.') + ['0','0'])[:3]))
            cv_tuple = ver_to_tuple(config_ver)
            rv_tuple = ver_to_tuple(current_ver)

            if rv_tuple > cv_tuple:
                logger.info(f"Update detected: {config_ver} -> {current_ver}")
                self.show_update_changelog(current_ver)
            elif rv_tuple < cv_tuple:
                logger.warning(f"Downgrade detected: {config_ver} -> {current_ver}")
                messagebox.showwarning(self, c.t("UI_DOWNGRADE_WARNING_TITLE"),
                                     c.t("UI_DOWNGRADE_WARNING_MSG", old=config_ver))

            self.config_manager.set(c.CONFIG_KEY_VERSION, current_ver)
        except Exception as e:
            logger.error(f"Error comparing versions: {e}")

        QTimer.singleShot(3000, self._check_remote_update)

    def _check_remote_update(self):
        """Fetch version.json from GitHub Pages and notify if a newer version exists."""
        last_check = self.config.get(c.CONFIG_KEY_UPDATE_LAST_CHECK, 0)
        ignored = self.config.get(c.CONFIG_KEY_UPDATE_IGNORE, "")
        now = int(time.time())

        if now - last_check < c.UPDATE_CHECK_INTERVAL:
            return

        self._update_checker = UpdateChecker(self)
        self._update_checker.check(on_result=lambda ok, ver, hf, err: self._on_remote_check(ok, ver, hf, ignored))

        self.config_manager.set(c.CONFIG_KEY_UPDATE_LAST_CHECK, now)

    def _on_remote_check(self, available, remote_ver, hotfix, ignored):
        """Handle the remote check result. Show the update and/or hotfix dialog.

        A hotfix is a re-release of the same version (same version string) that
        must reach users even though their version number already matches.
        """
        if hotfix:
            self._handle_hotfix(hotfix)

        if available and remote_ver != ignored:
            messagebox.showinfo(self, c.t("UI_INFO_TITLE"),
                              c.t("UI_UPDATE_AVAILABLE", version=remote_ver))

    def _handle_hotfix(self, hotfix):
        """Show the hotfix dialog unless its id was already acknowledged/ignored."""
        if not isinstance(hotfix, dict):
            return
        hf_id = hotfix.get("id", "")
        if not hf_id:
            return
        ignored_hf = self.config.get(c.CONFIG_KEY_UPDATE_IGNORE_HOTFIX, "")
        if hf_id == ignored_hf:
            return

        title = hotfix.get("title") or c.t("UI_HOTFIX_TITLE")
        body = hotfix.get("body") or ""
        force = bool(hotfix.get("force", False))
        msg = c.t("UI_HOTFIX_MSG", body=body) if body else c.t("UI_HOTFIX_MSG")

        if force:
            # Mandatory hotfix: only an acknowledgement button, cannot be ignored.
            messagebox.showwarning(self, title, msg)
            return

        dialog = messagebox.CustomDialog(
            self, title, msg, icon_type="warning",
            options=[c.t("UI_HOTFIX_UPDATE"), c.t("UI_HOTFIX_IGNORE")])
        dialog.exec()
        if dialog.result_value == c.t("UI_HOTFIX_IGNORE"):
            self.config_manager.set(c.CONFIG_KEY_UPDATE_IGNORE_HOTFIX, hf_id)

    def show_update_changelog(self, version):
        """Display the changelog dialog for the given version."""
        from src.gui.changelog_dialog import ChangelogDialog
        dialog = ChangelogDialog(self, version)
        dialog.exec()

    def check_drm_alert(self):
        """Warn the user if the latest installed version needs the DRM mod and it's missing."""
        if not self.active_path:
            return
        latest = self.logic.get_latest_version_needs_drm(self)
        if latest and not self.logic.check_drm_mod_installed(self):
            messagebox.showwarning(self, c.t("UI_DRM_ALERT_TITLE"),
                                  c.t("UI_DRM_ALERT_MSG", version=latest))
