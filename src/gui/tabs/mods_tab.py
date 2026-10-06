"""
MCPELauncher Native Mods (.so) Tab for Cianova Launcher.
Features a segmented top selector (Instalados / Descargar),
smooth sliding animations, permanent slim DRM status strip,
isolated view logics, auto-hiding right-spaced scrollbars,
real physical icons (icon.png, google_favicon.svg, github_icon.svg),
and complete Google Play session enforcement.
"""

import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QScrollArea, QLineEdit,
                             QSizePolicy, QCheckBox, QStackedWidget,
                             QGraphicsOpacityEffect)
from PySide6.QtCore import (Qt, QSize, QPoint, QRectF, QPropertyAnimation,
                            QParallelAnimationGroup, QEasingCurve,
                            Property, Signal, QThread, QUrl)
from PySide6.QtGui import (QPainter, QColor, QFont, QPen, QPixmap,
                           QDesktopServices, QDragEnterEvent, QDropEvent)
from src import constants as c
from src.core.ui_utils import FlowLayout, clear_layout, ResponsiveGridLayout, CreeperWatermarkWidget
from src.core import addon_manager
from src.core.moddb_service import (
    ModDBFetchWorker, get_cached_moddb, is_mod_installed,
    detect_architecture, find_asset_for_arch
)
from src.core.google_integration import check_google_session
from src.utils.resource_path import resource_path
from src.utils.image_manager import ImageManager
from src.utils.colors import adjust_color, hex_to_rgba
from src.utils.logger import logger
from src.utils.process_utils import open_folder
from src.utils.dialogs import ask_open_filename_native
from src.gui import custom_dialogs as messagebox


class ModActionWorker(QThread):
    """Background worker for mod installation or file ops."""
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, action_func, *args):
        super().__init__()
        self.action_func = action_func
        self.args = args

    def run(self):
        try:
            res = self.action_func(*self.args)
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))


class ModsSegmentedTabBar(QWidget):
    """
    Animated segmented pill selector for Mods (Instalados / Descargar).
    Matches the installer tab bar with smooth sliding pill, tactile press sink,
    hover glow, and theme integration.
    """
    tabChanged = Signal(int)

    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.setFixedHeight(38)
        self.setFixedWidth(400)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._tabs = [c.t("UI_MODS_TAB_INSTALLED"), c.t("UI_MODS_TAB_DOWNLOAD")]
        self._current_index = 0
        self._indicator_x = 4.0
        self._hover_index = -1
        self._hover_opacity = 0.0
        self._sink_factor = 0.0
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        self._anim_pos = QPropertyAnimation(self, b"indicatorX", self)
        self._anim_pos.setDuration(200)
        self._anim_pos.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_hover = QPropertyAnimation(self, b"hoverOpacity", self)
        self._anim_hover.setDuration(120)

        self._anim_sink = QPropertyAnimation(self, b"sinkFactor", self)
        self._anim_sink.setDuration(90)

    def retranslate_ui(self):
        self._tabs = [c.t("UI_MODS_TAB_INSTALLED"), c.t("UI_MODS_TAB_DOWNLOAD")]
        self.update()

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

    def currentIndex(self):
        return self._current_index

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
        track_color = QColor(255, 255, 255, 12) if is_dark else QColor(0, 0, 0, 10)
        painter.setBrush(track_color)
        painter.setPen(QPen(QColor(255, 255, 255, 18) if is_dark else QColor(0, 0, 0, 15), 1))
        painter.drawRoundedRect(bg_rect, 9.0, 9.0)

        if self._hover_index >= 0 and self._hover_index != self._current_index and self._hover_opacity > 0:
            h_rect = self._get_tab_rect(self._hover_index)
            h_color = QColor(255, 255, 255, int(20 * self._hover_opacity)) if is_dark else QColor(0, 0, 0, int(14 * self._hover_opacity))
            painter.setBrush(h_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(h_rect, 7.0, 7.0)

        w_tab = (self.width() - 8) / len(self._tabs)
        sink_inset = self._sink_factor * 1.5
        draw_rect = QRectF(self._indicator_x + sink_inset, 4 + sink_inset, w_tab - (sink_inset * 2), self.height() - 8 - (sink_inset * 2))
        radius = 7.0

        if is_dark:
            steps = 8
            max_expand = 5.0
            max_alpha = 28
            for i in range(steps, 0, -1):
                t = i / steps
                alpha = int(max_alpha * ((1.0 - t) ** 1.6))
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
            shadow_steps = 6
            for i in range(shadow_steps, 0, -1):
                t = i / shadow_steps
                alpha = int(20 * ((1.0 - t) ** 1.5))
                if alpha <= 0:
                    continue
                s_rect = draw_rect.adjusted(0, 1.0 * t, 0, 3.0 * t)
                painter.setBrush(QColor(0, 0, 0, alpha))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(s_rect, radius, radius)

            painter.setBrush(accent_qcolor)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(draw_rect, radius, radius)

        # Tab text
        font = QFont(self.font())
        font.setPointSize(10)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)

        for i, tab_title in enumerate(self._tabs):
            rect = self._get_tab_rect(i)
            if i == self._current_index:
                painter.setPen(QColor("#ffffff"))
            else:
                painter.setPen(QColor("#94a3b8" if is_dark else "#475569"))
            painter.drawText(rect, Qt.AlignCenter, tab_title)


class SlideAnimatedStackedWidget(QStackedWidget):
    """
    QStackedWidget with smooth horizontal slide and cross-fade transition
    between views (Instalados <-> Descargar).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._prev_index = 0
        self._anim_group = None
        self._anim_effect = None
        self._anim_target = None
        self.currentChanged.connect(self._on_index_changed)

    def _on_index_changed(self, index):
        if index < 0 or index == self._prev_index:
            return

        direction = 1 if index > self._prev_index else -1
        self._prev_index = index

        current_widget = self.widget(index)
        if not current_widget or not self.isVisible():
            return

        if self._anim_group and self._anim_group.state() == QParallelAnimationGroup.Running:
            self._anim_group.stop()

        effect = QGraphicsOpacityEffect(current_widget)
        current_widget.setGraphicsEffect(effect)
        self._anim_effect = effect
        self._anim_target = current_widget

        anim_fade = QPropertyAnimation(effect, b"opacity", self)
        anim_fade.setDuration(190)
        anim_fade.setStartValue(0.0)
        anim_fade.setEndValue(1.0)
        anim_fade.setEasingCurve(QEasingCurve.OutCubic)

        anim_slide = QPropertyAnimation(current_widget, b"pos", self)
        anim_slide.setDuration(190)
        start_x = current_widget.x() + (35 * direction)
        anim_slide.setStartValue(QPoint(start_x, current_widget.y()))
        anim_slide.setEndValue(QPoint(current_widget.x(), current_widget.y()))
        anim_slide.setEasingCurve(QEasingCurve.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(anim_fade)
        group.addAnimation(anim_slide)

        def _cleanup():
            if current_widget == self._anim_target:
                current_widget.setGraphicsEffect(None)
                self._anim_effect = None
                self._anim_target = None

        group.finished.connect(_cleanup)
        self._anim_group = group
        group.start()


class ModCardWidget(QFrame):
    """Clean, compact card displaying a single installed MCPELauncher mod."""

    def __init__(self, mod_info: dict, app=None, parent_tab=None):
        super().__init__()
        self.mod_info = mod_info
        self.app = app
        self.parent_tab = parent_tab
        self.setObjectName("ModCard")
        self.setFixedHeight(168)
        self.setMinimumWidth(240)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 10)
        self._layout.setSpacing(6)

        # 1. Top Header: Physical icon + Name + Version/Type
        row_head = QHBoxLayout()
        row_head.setContentsMargins(0, 0, 0, 0)
        row_head.setSpacing(10)

        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(36, 36)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setStyleSheet("background-color: rgba(0, 0, 0, 0.20); border-radius: 8px;")
        row_head.addWidget(self.lbl_icon, 0, Qt.AlignTop)

        col_text = QVBoxLayout()
        col_text.setContentsMargins(0, 0, 0, 0)
        col_text.setSpacing(1)

        self.lbl_name = QLabel()
        self.lbl_name.setStyleSheet("font-size: 13px; font-weight: 600;")
        col_text.addWidget(self.lbl_name)

        self.lbl_meta = QLabel()
        self.lbl_meta.setStyleSheet("font-size: 10px; color: #94a3b8; font-weight: 500;")
        col_text.addWidget(self.lbl_meta)

        row_head.addLayout(col_text, 1)
        self._layout.addLayout(row_head)

        # 2. Checkbox: Launch with game
        self.cb_launch = QCheckBox(c.t("UI_MODS_LOAD_ON_STARTUP"))
        self.cb_launch.setCursor(Qt.PointingHandCursor)
        self.cb_launch.setStyleSheet("font-size: 11px;")
        is_launch = self.mod_info.get("launch", True)
        self.cb_launch.setChecked(is_launch)
        self.cb_launch.clicked.connect(self._on_launch_toggled)
        self._layout.addWidget(self.cb_launch)

        self._layout.addStretch(1)

        # 3. Action bar: status pill on left, folder/delete buttons on right
        row_actions = QHBoxLayout()
        row_actions.setContentsMargins(0, 0, 0, 0)
        row_actions.setSpacing(6)

        self.lbl_status_pill = QLabel()
        self.lbl_status_pill.setStyleSheet("font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 4px;")
        self._update_status_pill(is_launch)
        row_actions.addWidget(self.lbl_status_pill)

        row_actions.addStretch(1)

        self.btn_open_folder = QPushButton()
        self.btn_open_folder.setToolTip(c.t("UI_MODS_TOOLTIP_OPEN"))
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_folder.setFixedSize(28, 26)
        self.btn_open_folder.clicked.connect(self._open_folder)
        row_actions.addWidget(self.btn_open_folder)

        self.btn_delete = QPushButton()
        self.btn_delete.setToolTip(c.t("UI_MODS_TOOLTIP_DELETE"))
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setFixedSize(28, 26)
        self.btn_delete.clicked.connect(self._delete_mod)
        row_actions.addWidget(self.btn_delete)

        self._layout.addLayout(row_actions)

        self._load_data()
        self.update_theme_styles()

    def retranslate_ui(self):
        self.cb_launch.setText(c.t("UI_MODS_LOAD_ON_STARTUP"))
        self.btn_open_folder.setToolTip(c.t("UI_MODS_TOOLTIP_OPEN"))
        self.btn_delete.setToolTip(c.t("UI_MODS_TOOLTIP_DELETE"))
        self._update_status_pill(self.cb_launch.isChecked())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided_name()

    def _update_elided_name(self):
        name = self.mod_info.get("name", os.path.basename(self.mod_info.get("path", "Mod")))
        avail = max(130, self.width() - 80)
        fm = self.lbl_name.fontMetrics()
        self.lbl_name.setText(fm.elidedText(name, Qt.ElideMiddle, avail))
        self.lbl_name.setToolTip(name)

    def _update_status_pill(self, enabled: bool):
        if enabled:
            self.lbl_status_pill.setText(c.t("UI_MODS_STATUS_ACTIVE_PILL"))
            self.lbl_status_pill.setStyleSheet("""
                background: rgba(16, 185, 129, 0.15);
                color: #10b981;
                border: 1px solid rgba(16, 185, 129, 0.30);
                font-size: 10px;
                font-weight: 600;
                padding: 2px 7px;
                border-radius: 4px;
            """)
        else:
            self.lbl_status_pill.setText(c.t("UI_MODS_STATUS_INACTIVE_PILL"))
            self.lbl_status_pill.setStyleSheet("""
                background: rgba(148, 163, 184, 0.12);
                color: #94a3b8;
                border: 1px solid rgba(148, 163, 184, 0.25);
                font-size: 10px;
                font-weight: 600;
                padding: 2px 7px;
                border-radius: 4px;
            """)

    def _load_data(self):
        self._update_elided_name()

        path = self.mod_info.get("path", "")
        size_str = "0 KB"
        if path and os.path.exists(path):
            try:
                sz = os.path.getsize(path)
                if sz >= 1024 * 1024:
                    size_str = f"{sz / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{sz / 1024:.1f} KB"
            except OSError:
                pass
        self.lbl_meta.setText(f"Mod nativo  •  {size_str}")

        icon_path = resource_path("icon.png")
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(26, 26, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_icon.setPixmap(pix)

    def _on_launch_toggled(self):
        enabled = self.cb_launch.isChecked()
        addon_manager.set_mod_launch_state(self.app, self.mod_info.get("path", ""), enabled)
        self.mod_info["launch"] = enabled
        self._update_status_pill(enabled)
        if self.parent_tab:
            self.parent_tab.update_stats()

    def _open_folder(self):
        path = self.mod_info.get("path", "")
        if path and os.path.exists(path):
            folder = os.path.dirname(path)
            open_folder(folder)

    def _delete_mod(self):
        name = self.mod_info.get("name", "este mod")
        if messagebox.askyesno(
            self.parent_tab or self,
            c.t("UI_MODS_DELETE_TITLE"),
            c.t("UI_MODS_DELETE_CONFIRM", name=name)
        ):
            path = self.mod_info.get("path", "")
            try:
                addon_manager.delete_mod(path)
                if self.parent_tab:
                    self.parent_tab.load_mods()
            except Exception as e:
                logger.error(f"Error deleting mod {path}: {e}")
                messagebox.showerror(self.parent_tab or self, c.t("UI_MODS_DELETE_TITLE"), c.t("UI_MODS_DELETE_ERROR", e=str(e)))

    def update_theme_styles(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        self.setStyleSheet(f"""
            QFrame#ModCard {{
                background-color: {"rgba(255, 255, 255, 0.04)" if is_dark else "rgba(0, 0, 0, 0.03)"};
                border: 1px solid {"rgba(255, 255, 255, 0.07)" if is_dark else "rgba(0, 0, 0, 0.08)"};
                border-radius: 10px;
            }}
            QFrame#ModCard:hover {{
                background-color: {"rgba(255, 255, 255, 0.07)" if is_dark else "rgba(0, 0, 0, 0.05)"};
                border: 1px solid {hex_to_rgba(accent, 0.6)};
            }}
        """)

        self.lbl_name.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {'#ffffff' if is_dark else '#0f172a'}; background: transparent;")
        self.lbl_meta.setStyleSheet(f"font-size: 10px; color: {'#94a3b8' if is_dark else '#64748b'}; background: transparent;")
        self.cb_launch.setStyleSheet(f"font-size: 11px; color: {'#cbd5e1' if is_dark else '#334155'}; background: transparent;")

        icon_color = "#94a3b8" if is_dark else "#64748b"
        icon_folder = ImageManager.get_tinted_icon(resource_path("folder_browse_icon.svg"), icon_color, 13)
        icon_trash = ImageManager.get_tinted_icon(resource_path("trash_delete_icon.svg"), "#ef4444", 13)

        if icon_folder:
            self.btn_open_folder.setIcon(icon_folder)
        if icon_trash:
            self.btn_delete.setIcon(icon_trash)

        btn_card_style = f"""
            QPushButton {{
                background: {"rgba(255, 255, 255, 0.06)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                border: 1px solid {"rgba(255, 255, 255, 0.09)" if is_dark else "rgba(0, 0, 0, 0.07)"};
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background: {hex_to_rgba(accent, 0.25)};
                border: 1px solid {accent};
            }}
        """
        self.btn_open_folder.setStyleSheet(btn_card_style)
        self.btn_delete.setStyleSheet(f"""
            QPushButton {{
                background: {"rgba(255, 255, 255, 0.06)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                border: 1px solid {"rgba(255, 255, 255, 0.09)" if is_dark else "rgba(0, 0, 0, 0.07)"};
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background: rgba(239, 68, 68, 0.25);
                border: 1px solid #ef4444;
            }}
        """)


class ModDBCardWidget(QFrame):
    """Clean, compact card displaying a downloadable mod from the ModDB repository."""

    def __init__(self, mod_entry: dict, app=None, parent_tab=None, is_drm_card: bool = False):
        super().__init__()
        self.mod_entry = mod_entry
        self.app = app
        self.parent_tab = parent_tab
        self.is_drm_card = is_drm_card
        self.setObjectName("ModDBCard")
        self.setFixedHeight(168)
        self.setMinimumWidth(240)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 10)
        self._layout.setSpacing(6)

        # 1. Top Header: Physical icon + Name + Version tag
        row_head = QHBoxLayout()
        row_head.setContentsMargins(0, 0, 0, 0)
        row_head.setSpacing(10)

        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(36, 36)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setStyleSheet("background-color: rgba(0, 0, 0, 0.20); border-radius: 8px;")
        row_head.addWidget(self.lbl_icon, 0, Qt.AlignTop)

        col_text = QVBoxLayout()
        col_text.setContentsMargins(0, 0, 0, 0)
        col_text.setSpacing(1)

        self.lbl_name = QLabel()
        self.lbl_name.setStyleSheet("font-size: 13px; font-weight: 600;")
        col_text.addWidget(self.lbl_name)

        self.lbl_version = QLabel()
        self.lbl_version.setStyleSheet("font-size: 10px; color: #94a3b8; font-weight: 500;")
        col_text.addWidget(self.lbl_version)

        row_head.addLayout(col_text, 1)
        self._layout.addLayout(row_head)

        # 2. Description (2 lines, compact)
        self.lbl_desc = QLabel()
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setFixedHeight(34)
        self.lbl_desc.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._layout.addWidget(self.lbl_desc)

        self._layout.addStretch(1)

        # 3. Action Row: Download Button + GitHub Icon Button
        row_actions = QHBoxLayout()
        row_actions.setContentsMargins(0, 0, 0, 0)
        row_actions.setSpacing(6)

        self.btn_download = QPushButton(c.t("UI_MODS_BTN_DOWNLOAD"))
        self.btn_download.setCursor(Qt.PointingHandCursor)
        self.btn_download.setFixedHeight(28)
        self.btn_download.clicked.connect(self._download_mod)
        row_actions.addWidget(self.btn_download, 1)

        self.btn_github = QPushButton()
        self.btn_github.setToolTip(c.t("UI_MODS_TOOLTIP_GITHUB"))
        self.btn_github.setCursor(Qt.PointingHandCursor)
        self.btn_github.setFixedSize(28, 28)
        self.btn_github.clicked.connect(self._open_github)
        row_actions.addWidget(self.btn_github)

        self._layout.addLayout(row_actions)

        self._load_data()
        self.update_theme_styles()

    def retranslate_ui(self):
        self.btn_download.setText(c.t("UI_MODS_BTN_DOWNLOAD"))
        self.btn_github.setToolTip(c.t("UI_MODS_TOOLTIP_GITHUB"))
        self._load_data()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided_name()

    def _update_elided_name(self):
        name = self.mod_entry.get("name", "Mod")
        avail = max(130, self.width() - 80)
        fm = self.lbl_name.fontMetrics()
        self.lbl_name.setText(fm.elidedText(name, Qt.ElideMiddle, avail))
        self.lbl_name.setToolTip(name)

    def _load_data(self):
        self._update_elided_name()

        desc = self.mod_entry.get("description", "Mod comunitario de mcpelauncher-moddb.")
        self.lbl_desc.setText(desc)
        self.lbl_desc.setToolTip(desc)

        if self.is_drm_card:
            self.lbl_version.setText(c.t("UI_MODS_OFFICIAL_GPLAY"))
            icon_path = resource_path("google_favicon.svg")
            if os.path.exists(icon_path):
                pix = QPixmap(icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.lbl_icon.setPixmap(pix)
        else:
            versions = self.mod_entry.get("versions", [])
            latest_ver = versions[-1].get("version", "") if versions else ""
            arch = detect_architecture()
            download_url, _ = find_asset_for_arch(self.mod_entry, arch) if arch else (None, None)

            ver_str = f"v{latest_ver}" if latest_ver else "v1.0"
            arch_str = f"•  {arch}" if arch else ""
            self.lbl_version.setText(f"{ver_str}  {arch_str}")

            if not download_url:
                self.btn_download.setEnabled(False)
                self.btn_download.setText(c.t("UI_MODS_NOT_COMPATIBLE"))
                self.btn_download.setToolTip(c.t("UI_MODS_NO_PKG_CPU"))

            icon_path = resource_path("icon.png")
            if os.path.exists(icon_path):
                pix = QPixmap(icon_path).scaled(26, 26, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.lbl_icon.setPixmap(pix)

    def _download_mod(self):
        if self.is_drm_card:
            if self.parent_tab:
                self.parent_tab._install_drm_mod_flow()
            return
        mod_name = self.mod_entry.get("name")
        if mod_name and self.parent_tab:
            self.parent_tab.install_moddb_mod(mod_name)

    def _open_github(self):
        url = self.mod_entry.get("url", "https://github.com/Leimsoto/mcpelauncher-updates" if self.is_drm_card else "")
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def update_theme_styles(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        self.setStyleSheet(f"""
            QFrame#ModDBCard {{
                background-color: {"rgba(255, 255, 255, 0.04)" if is_dark else "rgba(0, 0, 0, 0.03)"};
                border: 1px solid {"rgba(255, 255, 255, 0.07)" if is_dark else "rgba(0, 0, 0, 0.08)"};
                border-radius: 10px;
            }}
            QFrame#ModDBCard:hover {{
                background-color: {"rgba(255, 255, 255, 0.07)" if is_dark else "rgba(0, 0, 0, 0.05)"};
                border: 1px solid {hex_to_rgba(accent, 0.6)};
            }}
        """)

        self.lbl_name.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {'#ffffff' if is_dark else '#0f172a'}; background: transparent;")
        self.lbl_version.setStyleSheet(f"font-size: 10px; color: {'#94a3b8' if is_dark else '#64748b'}; background: transparent;")
        self.lbl_desc.setStyleSheet(f"font-size: 11px; color: {'#94a3b8' if is_dark else '#64748b'}; line-height: 1.3; background: transparent;")

        self.btn_download.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 5px;
                font-size: 11px;
                font-weight: 600;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                background-color: {adjust_color(accent, 1.15)};
            }}
            QPushButton:disabled {{
                background-color: {"rgba(255, 255, 255, 0.06)" if is_dark else "rgba(0, 0, 0, 0.05)"};
                color: {"#64748b" if is_dark else "#94a3b8"};
            }}
        """)

        icon_color = "#94a3b8" if is_dark else "#64748b"
        icon_git = ImageManager.get_tinted_icon(resource_path("github_icon.svg"), icon_color, 14)
        if icon_git:
            self.btn_github.setIcon(icon_git)

        self.btn_github.setStyleSheet(f"""
            QPushButton {{
                background: {"rgba(255, 255, 255, 0.06)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                border: 1px solid {"rgba(255, 255, 255, 0.09)" if is_dark else "rgba(0, 0, 0, 0.07)"};
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background: {hex_to_rgba(accent, 0.25)};
                border: 1px solid {accent};
            }}
        """)


class ModsTab(QWidget):
    """
    MCPELauncher Native Mods (.so) Tab with segmented top bar (Instalados / Descargar),
    permanent slim DRM strip, animated views, and separated logics.
    """

    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.setAcceptDrops(True)

        self._all_mods = []
        self._mods_scan_worker = None
        self._mods_scan_pending = False
        self._moddb_data = None
        self._moddb_worker = None
        self._moddb_loading = False

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(28, 20, 28, 16)
        self._main_layout.setSpacing(12)

        # 1. Header Row (Brand Title & Subtitle)
        header_widget = QWidget()
        row_header = QHBoxLayout(header_widget)
        row_header.setContentsMargins(0, 0, 0, 0)
        row_header.setSpacing(12)

        col_titles = QVBoxLayout()
        col_titles.setContentsMargins(0, 0, 0, 0)
        col_titles.setSpacing(2)

        self.lbl_brand_title = QLabel(c.t("UI_MODS_HEADER_TITLE"))
        self.lbl_brand_sub = QLabel(c.t("UI_MODS_SUBTITLE"))
        col_titles.addWidget(self.lbl_brand_title)
        col_titles.addWidget(self.lbl_brand_sub)
        row_header.addLayout(col_titles, 1)

        header_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._main_layout.addWidget(header_widget, 0)

        # 2. Permanent Slim DRM Mod Status Strip (Always above both options)
        self.strip_drm = QFrame()
        self.strip_drm.setObjectName("DRMStrip")
        self.strip_drm.setFixedHeight(40)
        layout_drm = QHBoxLayout(self.strip_drm)
        layout_drm.setContentsMargins(12, 0, 12, 0)
        layout_drm.setSpacing(10)

        self.lbl_drm_icon = QLabel()
        self.lbl_drm_icon.setFixedSize(18, 18)
        self.lbl_drm_icon.setAlignment(Qt.AlignCenter)
        layout_drm.addWidget(self.lbl_drm_icon)

        self.lbl_drm_text = QLabel()
        self.lbl_drm_text.setStyleSheet("font-size: 11px; font-weight: 500;")
        layout_drm.addWidget(self.lbl_drm_text, 1)

        self.btn_drm_action = QPushButton()
        self.btn_drm_action.setCursor(Qt.PointingHandCursor)
        self.btn_drm_action.setFixedHeight(26)
        self.btn_drm_action.clicked.connect(self._on_drm_action_clicked)
        layout_drm.addWidget(self.btn_drm_action, 0)

        self._main_layout.addWidget(self.strip_drm, 0)

        # 3. Custom Animated Segmented Tab Bar (Instalados / Descargar) Centered
        row_segmented = QHBoxLayout()
        row_segmented.setContentsMargins(0, 4, 0, 4)
        row_segmented.setAlignment(Qt.AlignCenter)

        self.tab_bar = ModsSegmentedTabBar(self, app=self.app)
        self.tab_bar.tabChanged.connect(self._on_tab_changed)
        row_segmented.addWidget(self.tab_bar)
        self._main_layout.addLayout(row_segmented)

        # 4. Animated Stacked Widget for the two views
        self.tab_stack = SlideAnimatedStackedWidget(self)

        # ─── VIEW 0: INSTALADOS ───
        self.view_installed = QWidget()
        layout_v_inst = QVBoxLayout(self.view_installed)
        layout_v_inst.setContentsMargins(0, 0, 0, 0)
        layout_v_inst.setSpacing(10)

        # Toolbar Instalados: Search, Count, Open folder, Refresh
        row_inst_bar = QHBoxLayout()
        row_inst_bar.setContentsMargins(0, 0, 0, 0)
        row_inst_bar.setSpacing(10)

        self.entry_search_inst = QLineEdit()
        self.entry_search_inst.setPlaceholderText(c.t("UI_MODS_SEARCH_INSTALLED"))
        self.entry_search_inst.setFixedWidth(220)
        self.entry_search_inst.setFixedHeight(30)
        self.entry_search_inst.textChanged.connect(self.render_installed_cards)
        row_inst_bar.addWidget(self.entry_search_inst)

        self.lbl_installed_count = QLabel()
        self.lbl_installed_count.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        row_inst_bar.addWidget(self.lbl_installed_count)

        row_inst_bar.addStretch(1)

        self.btn_open_folder = QPushButton(c.t("UI_MODS_BTN_OPEN_FOLDER"))
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_folder.setFixedHeight(30)
        self.btn_open_folder.clicked.connect(self._open_mods_folder)
        row_inst_bar.addWidget(self.btn_open_folder)

        self.btn_refresh_inst = QPushButton(c.t("UI_MODS_BTN_REFRESH"))
        self.btn_refresh_inst.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_inst.setFixedHeight(30)
        self.btn_refresh_inst.clicked.connect(self.load_mods)
        row_inst_bar.addWidget(self.btn_refresh_inst)

        layout_v_inst.addLayout(row_inst_bar)

        # Scroll area for installed mods
        self.scroll_installed = QScrollArea()
        self.scroll_installed.setWidgetResizable(True)
        self.scroll_installed.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_installed.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_installed.setStyleSheet("background: transparent; border: none;")

        self.content_installed = QWidget()
        self.layout_content_inst = QVBoxLayout(self.content_installed)
        self.layout_content_inst.setContentsMargins(0, 4, 0, 16)
        self.layout_content_inst.setSpacing(10)

        self.container_installed = QWidget()
        self.grid_installed = ResponsiveGridLayout(self.container_installed, margin=0, h_spacing=12, v_spacing=12, min_item_width=250, item_height=168)
        self.layout_content_inst.addWidget(self.container_installed)
        self.layout_content_inst.addStretch(1)

        self.scroll_installed.setWidget(self.content_installed)
        layout_v_inst.addWidget(self.scroll_installed, 1)

        # ─── VIEW 1: DESCARGAR ───
        self.view_download = QWidget()
        layout_v_down = QVBoxLayout(self.view_download)
        layout_v_down.setContentsMargins(0, 0, 0, 0)
        layout_v_down.setSpacing(10)

        # Toolbar Descargar: Search, Count, Import Button, Refresh Catálogo
        row_down_bar = QHBoxLayout()
        row_down_bar.setContentsMargins(0, 0, 0, 0)
        row_down_bar.setSpacing(10)

        self.entry_search_down = QLineEdit()
        self.entry_search_down.setPlaceholderText(c.t("UI_MODS_SEARCH_DOWNLOAD"))
        self.entry_search_down.setFixedWidth(220)
        self.entry_search_down.setFixedHeight(30)
        self.entry_search_down.textChanged.connect(self.render_moddb_cards)
        row_down_bar.addWidget(self.entry_search_down)

        self.lbl_moddb_count = QLabel()
        self.lbl_moddb_count.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        row_down_bar.addWidget(self.lbl_moddb_count)

        row_down_bar.addStretch(1)

        self.btn_import = QPushButton(c.t("UI_MODS_BTN_IMPORT"))
        self.btn_import.setCursor(Qt.PointingHandCursor)
        self.btn_import.setFixedHeight(30)
        self.btn_import.clicked.connect(self._import_mod)
        row_down_bar.addWidget(self.btn_import)

        self.btn_fetch_moddb = QPushButton(c.t("UI_MODS_BTN_FETCH"))
        self.btn_fetch_moddb.setCursor(Qt.PointingHandCursor)
        self.btn_fetch_moddb.setFixedHeight(30)
        self.btn_fetch_moddb.clicked.connect(self._fetch_moddb_online)
        row_down_bar.addWidget(self.btn_fetch_moddb)

        layout_v_down.addLayout(row_down_bar)

        self.lbl_moddb_status = QLabel()
        self.lbl_moddb_status.setStyleSheet("font-size: 11px; color: #94a3b8; padding: 2px 0;")
        layout_v_down.addWidget(self.lbl_moddb_status)

        # Scroll area for downloadable mods
        self.scroll_download = QScrollArea()
        self.scroll_download.setWidgetResizable(True)
        self.scroll_download.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_download.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_download.setStyleSheet("background: transparent; border: none;")

        self.content_download = QWidget()
        self.layout_content_down = QVBoxLayout(self.content_download)
        self.layout_content_down.setContentsMargins(0, 4, 0, 16)
        self.layout_content_down.setSpacing(10)

        self.container_moddb = QWidget()
        self.grid_moddb = ResponsiveGridLayout(self.container_moddb, margin=0, h_spacing=12, v_spacing=12, min_item_width=250, item_height=168)
        self.layout_content_down.addWidget(self.container_moddb)
        self.layout_content_down.addStretch(1)

        self.scroll_download.setWidget(self.content_download)
        layout_v_down.addWidget(self.scroll_download, 1)

        # Add both views to the animated stack
        self.tab_stack.addWidget(self.view_installed)
        self.tab_stack.addWidget(self.view_download)
        self._main_layout.addWidget(self.tab_stack, 1)

        # 5. Background Creeper Watermark (positioned bottom-right with soft opacity)
        self.watermark = CreeperWatermarkWidget(self)
        self.watermark.lower()

        self.update_theme_styles()

    def _on_tab_changed(self, index):
        self.tab_stack.setCurrentIndex(index)

    def _on_drm_action_clicked(self):
        """Handle DRM strip button click."""
        drm_status = self.app.logic.get_drm_mod_status(self.app) if hasattr(self.app, "logic") else "missing"

        if drm_status == "missing":
            self._install_drm_mod_flow()

        elif drm_status == "disabled":
            drm_dir = os.path.join(self.app.active_path, c.MODS_DIR, "mcpelauncher-updates")
            if os.path.isdir(drm_dir):
                found = False
                for root, dirs, files in os.walk(drm_dir):
                    if "libmcpelauncher-updates.so.disabled" in files:
                        src = os.path.join(root, "libmcpelauncher-updates.so.disabled")
                        dst = os.path.join(root, "libmcpelauncher-updates.so")
                        try:
                            os.rename(src, dst)
                            found = True
                        except Exception as e:
                            logger.error(f"Error enabling DRM mod: {e}")
                if found:
                    messagebox.showinfo(self, "Mod DRM Activado", "El mod DRM ha sido reactivado correctamente.")
                    self.load_mods()

    def _install_drm_mod_flow(self):
        """Enforce active Google Play session before downloading DRM mod."""
        if not check_google_session(self.app):
            messagebox.showwarning(
                self,
                "Cuenta de Google Play Requerida",
                "Para descargar e instalar el mod DRM (mcpelauncher-updates) es necesario tener una cuenta de Google Play activa.\n\n"
                "Inicia sesión en Google Play desde la pestaña 'Instalación'."
            )
            return

        if messagebox.askyesno(
            self,
            "Instalar Mod DRM",
            "¿Deseas descargar e instalar el mod DRM oficial (mcpelauncher-updates)?\n\n"
            "Parche obligatorio para versiones de Google Play (≥ 1.21.30)."
        ):
            self.app.logic.install_drm_mod(self.app, on_done=self.load_mods)

    def install_moddb_mod(self, mod_name: str):
        if hasattr(self.app, "logic") and hasattr(self.app.logic, "install_mod_from_moddb"):
            self.app.logic.install_mod_from_moddb(self.app, mod_name, on_done=self.load_mods)

    def _open_mods_folder(self):
        active_path = getattr(self.app, "active_path", None)
        if active_path:
            mods_path = os.path.join(active_path, c.MODS_DIR)
            os.makedirs(mods_path, exist_ok=True)
            open_folder(mods_path)

    def _import_mod(self):
        file_path = ask_open_filename_native(
            self,
            title="Importar Mod de MCPELauncher",
            filetypes=[("Mods de MCPELauncher", "*.so *.zip"), ("Librerías dinámicas", "*.so"), ("Archivos ZIP", "*.zip")],
            initial_dir=os.path.expanduser("~/Descargas")
        )
        if not file_path or not os.path.isfile(file_path):
            return
        self._install_file(file_path)

    def _install_file(self, file_path: str):
        active_path = getattr(self.app, "active_path", None)
        if not active_path:
            return

        def worker():
            return addon_manager.install_mod_file(active_path, file_path)

        self._import_worker = ModActionWorker(worker)
        def on_done(results):
            bname = os.path.basename(file_path)
            errors = [msg for status, msg in results if status == "ERROR"]
            if errors:
                messagebox.showerror(self, "Error al importar mod", "\n".join(errors))
            else:
                messagebox.showinfo(self, "Mod Importado", f"El mod '{bname}' ha sido instalado.")
            self.load_mods()
        def on_err(err):
            logger.error(f"Error installing mod {file_path}: {err}")
            messagebox.showerror(self, "Error de Instalación", f"No se pudo instalar el mod:\n{err}")

        self._import_worker.finished.connect(on_done)
        self._import_worker.error.connect(on_err)
        self._import_worker.start()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                ext = os.path.splitext(url.toLocalFile())[1].lower()
                if ext in (".so", ".zip"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                fp = url.toLocalFile()
                ext = os.path.splitext(fp)[1].lower()
                if ext in (".so", ".zip"):
                    self._install_file(fp)
            event.acceptProposedAction()

    def load_mods(self):
        """Scan the mod tree without making tab navigation block."""
        if self._mods_scan_worker and self._mods_scan_worker.isRunning():
            self._mods_scan_pending = True
            return

        self._mods_scan_worker = ModActionWorker(addon_manager.scan_mods, self.app)
        self._mods_scan_worker.finished.connect(self._on_mods_loaded)
        self._mods_scan_worker.error.connect(self._on_mods_load_error)
        self._mods_scan_worker.start()

    def _on_mods_loaded(self, mods):
        self._all_mods = mods
        self._mods_scan_worker = None

        if self._moddb_data is None:
            active_path = getattr(self.app, "active_path", None)
            if active_path:
                self._moddb_data = get_cached_moddb(active_path)

        if self._moddb_data is None and not self._moddb_loading:
            self._fetch_moddb_online()

        self.render_all()

        if self._mods_scan_pending:
            self._mods_scan_pending = False
            self.load_mods()

    def _on_mods_load_error(self, error):
        logger.error("Error scanning mods: %s", error)
        self._all_mods = []
        self._mods_scan_worker = None
        self.render_all()
        if self._mods_scan_pending:
            self._mods_scan_pending = False
            self.load_mods()

    def _fetch_moddb_online(self):
        active_path = getattr(self.app, "active_path", None)
        if not active_path:
            return

        self._moddb_loading = True
        self.lbl_moddb_status.setText("Consultando catálogo ModDB en línea...")
        self.lbl_moddb_status.show()

        self._moddb_worker = ModDBFetchWorker(active_path)
        def on_fetched(data):
            self._moddb_loading = False
            self._moddb_data = data
            self.lbl_moddb_status.hide()
            self.render_moddb_cards()
        def on_fetch_error(err):
            self._moddb_loading = False
            logger.warning(f"Failed to fetch moddb: {err}")
            self.lbl_moddb_status.setText(f"No se pudo conectar con el catálogo ({err}).")
            self.lbl_moddb_status.show()

        self._moddb_worker.finished.connect(on_fetched)
        self._moddb_worker.error.connect(on_fetch_error)
        self._moddb_worker.start()

    def update_stats(self):
        total_cnt = len(self._all_mods)
        active_cnt = sum(1 for m in self._all_mods if m.get("launch", True))
        self.lbl_installed_count.setText(
            c.t("UI_MODS_COUNT_LABEL",
                total_cnt=total_cnt,
                plural_total="s" if total_cnt != 1 else "",
                active_cnt=active_cnt,
                plural_active="s" if active_cnt != 1 else "")
        )

    def update_drm_card(self):
        """Update simplified slim DRM strip."""
        drm_status = self.app.logic.get_drm_mod_status(self.app) if hasattr(self.app, "logic") else "missing"
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        g_icon_path = resource_path("google_favicon.svg")
        if os.path.exists(g_icon_path):
            pix = QPixmap(g_icon_path).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_drm_icon.setPixmap(pix)

        if drm_status == "installed":
            self.strip_drm.setStyleSheet(f"""
                QFrame#DRMStrip {{
                    background-color: rgba(16, 185, 129, 0.08);
                    border: 1px solid rgba(16, 185, 129, 0.20);
                    border-radius: 8px;
                }}
            """)
            self.lbl_drm_text.setText(c.t("UI_MODS_DRM_ACTIVE_TEXT"))
            self.lbl_drm_text.setStyleSheet(f"font-size: 11px; color: {'#10b981' if is_dark else '#059669'};")
            self.btn_drm_action.setText(c.t("UI_MODS_STATUS_ACTIVE"))
            self.btn_drm_action.setEnabled(False)
            self.btn_drm_action.setStyleSheet("""
                QPushButton {
                    background: rgba(16, 185, 129, 0.15);
                    color: #10b981;
                    border: 1px solid rgba(16, 185, 129, 0.30);
                    border-radius: 5px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 0 10px;
                }
            """)
        elif drm_status == "disabled":
            self.strip_drm.setStyleSheet(f"""
                QFrame#DRMStrip {{
                    background-color: rgba(245, 158, 11, 0.08);
                    border: 1px solid rgba(245, 158, 11, 0.25);
                    border-radius: 8px;
                }}
            """)
            self.lbl_drm_text.setText(c.t("UI_MODS_DRM_DISABLED_TEXT"))
            self.lbl_drm_text.setStyleSheet(f"font-size: 11px; color: {'#f59e0b' if is_dark else '#d97706'};")
            self.btn_drm_action.setText(c.t("UI_MODS_DRM_ACTIVATE_BTN"))
            self.btn_drm_action.setEnabled(True)
            self.btn_drm_action.setStyleSheet("""
                QPushButton {{
                    background-color: #f59e0b;
                    color: #ffffff;
                    border: none;
                    border-radius: 5px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 0 10px;
                }}
                QPushButton:hover {{
                    background-color: #d97706;
                }}
            """)
        else:
            self.strip_drm.setStyleSheet(f"""
                QFrame#DRMStrip {{
                    background-color: rgba(239, 68, 68, 0.06);
                    border: 1px solid rgba(239, 68, 68, 0.20);
                    border-radius: 8px;
                }}
            """)
            self.lbl_drm_text.setText(c.t("UI_MODS_DRM_MISSING_TEXT"))
            self.lbl_drm_text.setStyleSheet(f"font-size: 11px; color: {'#f87171' if is_dark else '#dc2626'};")
            self.btn_drm_action.setText(c.t("UI_MODS_DRM_INSTALL_BTN"))
            self.btn_drm_action.setEnabled(True)
            self.btn_drm_action.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent};
                    color: #ffffff;
                    border: none;
                    border-radius: 5px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 0 10px;
                }}
                QPushButton:hover {{
                    background-color: {adjust_color(accent, 1.15)};
                }}
            """)

    def render_installed_cards(self):
        clear_layout(self.grid_installed)
        query = self.entry_search_inst.text().strip().lower()

        filtered = []
        for m in self._all_mods:
            name = m.get("name", "").lower()
            if query and query not in name:
                continue
            filtered.append(m)

        self.update_stats()

        # "en instalados si no hay nada instalado no muestres nada"
        if not filtered:
            self.container_installed.hide()
        else:
            self.container_installed.show()
            for m in filtered:
                card = ModCardWidget(m, app=self.app, parent_tab=self)
                self.grid_installed.addWidget(card)

    def render_moddb_cards(self):
        clear_layout(self.grid_moddb)

        query = self.entry_search_down.text().strip().lower()
        active_path = getattr(self.app, "active_path", None)
        drm_status = self.app.logic.get_drm_mod_status(self.app) if hasattr(self.app, "logic") else "missing"

        # "que lo de isntalar mod drm si no está instalado aparezca en el lado de descargar"
        if drm_status == "missing":
            drm_entry = {
                "name": "mcpelauncher-updates",
                "description": c.t("UI_MODS_DRM_DESC"),
                "url": "https://github.com/Leimsoto/mcpelauncher-updates"
            }
            if not query or query in "mcpelauncher-updates" or query in "drm":
                drm_card = ModDBCardWidget(drm_entry, app=self.app, parent_tab=self, is_drm_card=True)
                self.grid_moddb.addWidget(drm_card)

        if not self._moddb_data:
            return

        available_entries = []
        for entry in self._moddb_data:
            mname = entry.get("name", "")
            if mname == "mcpelauncher-updates":
                continue
            if is_mod_installed(active_path, mname):
                continue
            if any(mname.lower() in m.get("name", "").lower() for m in self._all_mods):
                continue

            name = entry.get("name", "").lower()
            desc = entry.get("description", "").lower()
            if query and query not in name and query not in desc:
                continue
            available_entries.append(entry)

        cnt = len(available_entries) + (1 if drm_status == "missing" else 0)
        self.lbl_moddb_count.setText(c.t("UI_MODS_MODDB_AVAILABLE_COUNT", cnt=cnt, plural="s" if cnt != 1 else ""))

        if not available_entries and drm_status != "missing":
            if not self._moddb_loading:
                self.lbl_moddb_status.setText(c.t("UI_MODS_EMPTY_SEARCH"))
                self.lbl_moddb_status.show()
        else:
            self.lbl_moddb_status.hide()
            for entry in available_entries:
                card = ModDBCardWidget(entry, app=self.app, parent_tab=self)
                self.grid_moddb.addWidget(card)

    def render_all(self):
        self.update_drm_card()
        self.render_installed_cards()
        self.render_moddb_cards()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "watermark") and self.watermark:
            self.watermark.update_position()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_mods()
        if hasattr(self, "watermark") and self.watermark:
            self.watermark.update_position()

    def update_theme_styles(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        # Header Titles
        self.lbl_brand_title.setStyleSheet(
            f"font-size: 15px; font-weight: 800; letter-spacing: 0.5px; color: {'#ffffff' if is_dark else '#0f172a'}; background: transparent;"
        )
        self.lbl_brand_sub.setStyleSheet(
            f"font-size: 12px; color: {'#94a3b8' if is_dark else '#64748b'}; background: transparent;"
        )

        # Search Inputs
        search_style = f"""
            QLineEdit {{
                background-color: {"rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                color: {'#ffffff' if is_dark else '#0f172a'};
                border: 1px solid {"rgba(255, 255, 255, 0.10)" if is_dark else "rgba(0, 0, 0, 0.10)"};
                border-radius: 6px;
                padding: 0 8px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border: 1px solid {accent};
            }}
        """
        self.entry_search_inst.setStyleSheet(search_style)
        self.entry_search_down.setStyleSheet(search_style)

        # Action Buttons
        self.btn_import.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {adjust_color(accent, 1.12)};
            }}
        """)

        btn_top_style = f"""
            QPushButton {{
                background: {"rgba(255, 255, 255, 0.06)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                color: {'#ffffff' if is_dark else '#0f172a'};
                border: 1px solid {"rgba(255, 255, 255, 0.09)" if is_dark else "rgba(0, 0, 0, 0.08)"};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {hex_to_rgba(accent, 0.20)};
                border: 1px solid {accent};
            }}
        """
        self.btn_open_folder.setStyleSheet(btn_top_style)
        self.btn_refresh_inst.setStyleSheet(btn_top_style)
        self.btn_fetch_moddb.setStyleSheet(btn_top_style)

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
        self.scroll_installed.verticalScrollBar().setStyleSheet(scrollbar_style)
        self.scroll_download.verticalScrollBar().setStyleSheet(scrollbar_style)

        self.update_drm_card()
        if hasattr(self, "tab_bar"):
            self.tab_bar.update()

        # Update cards
        for layout in (self.grid_installed, self.grid_moddb):
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget() and hasattr(item.widget(), "update_theme_styles"):
                    item.widget().update_theme_styles()

    def retranslate_ui(self):
        self.lbl_brand_title.setText(c.t("UI_MODS_HEADER_TITLE"))
        self.lbl_brand_sub.setText(c.t("UI_MODS_SUBTITLE"))
        if hasattr(self, "tab_bar") and hasattr(self.tab_bar, "retranslate_ui"):
            self.tab_bar.retranslate_ui()
        self.entry_search_inst.setPlaceholderText(c.t("UI_MODS_SEARCH_INSTALLED"))
        self.btn_open_folder.setText(c.t("UI_MODS_BTN_OPEN_FOLDER"))
        self.btn_refresh_inst.setText(c.t("UI_MODS_BTN_REFRESH"))
        self.entry_search_down.setPlaceholderText(c.t("UI_MODS_SEARCH_DOWNLOAD"))
        self.btn_import.setText(c.t("UI_MODS_BTN_IMPORT"))
        self.btn_fetch_moddb.setText(c.t("UI_MODS_BTN_FETCH"))
        self.update_drm_card()
        self.update_stats()

        for layout in (self.grid_installed, self.grid_moddb):
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget() and hasattr(item.widget(), "retranslate_ui"):
                    item.widget().retranslate_ui()
