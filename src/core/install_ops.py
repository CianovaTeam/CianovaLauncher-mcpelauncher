import os
from PySide6.QtCore import Qt, QPoint, QSize, QMimeData, QEvent
from PySide6.QtWidgets import (
    QLabel, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
    QCheckBox, QPushButton, QWidget, QApplication
)
from PySide6.QtGui import QDrag, QPainter, QColor, QPen

from src import constants as c
from src.utils.image_manager import ImageManager
from src.utils.logger import logger
from src.utils.colors import hex_to_rgba


class DragHandleGrip(QLabel):
    """Dedicated grip handle widget that handles drag initiation."""
    def __init__(self, card, parent=None):
        super().__init__(parent)
        self.card = card
        self._drag_start_pos = None
        self.setFixedSize(20, 36)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip("Arrastrar para reordenar")
        self.setStyleSheet("background: transparent; border: none;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and self._drag_start_pos:
            dist = (event.pos() - self._drag_start_pos).manhattanLength()
            if dist >= QApplication.startDragDistance():
                drag = QDrag(self.card)
                mime = QMimeData()
                mime.setText(f"cianova_version:{self.card.version_name}")
                drag.setMimeData(mime)

                pix = self.card.grab()
                drag.setPixmap(pix)
                drag.setHotSpot(self.mapTo(self.card, event.pos()))

                drag.exec(Qt.MoveAction)
                self._drag_start_pos = None
                self.setCursor(Qt.OpenHandCursor)
                return
        super().mouseMoveEvent(event)


class SleekVersionCard(QFrame):
    """
    Version Card supporting click-to-select and interactive Drag-and-Drop
    reordering via DragHandleGrip when in mass edit mode.
    """
    def __init__(self, app, version_name, parent=None):
        super().__init__(parent)
        self.app = app
        self.version_name = version_name
        self.setObjectName("VersionCard")
        self.setProperty("selected", False)
        self.setAcceptDrops(True)
        self.drag_grip = None

    def register_child(self, widget):
        """Install event filter on child so drop events on children bubble to card."""
        if widget:
            widget.setAcceptDrops(True)
            widget.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.DragEnter, QEvent.DragMove, QEvent.DragLeave, QEvent.Drop):
            if event.type() == QEvent.DragEnter:
                self.dragEnterEvent(event)
            elif event.type() == QEvent.DragMove:
                self.dragMoveEvent(event)
            elif event.type() == QEvent.DragLeave:
                self.dragLeaveEvent(event)
            elif event.type() == QEvent.Drop:
                self.dropEvent(event)
            return True
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "lbl_sub") and hasattr(self, "_raw_sub") and self.lbl_sub:
            avail_w = self.lbl_sub.width()
            if avail_w > 20:
                fm = self.lbl_sub.fontMetrics()
                self.lbl_sub.setText(fm.elidedText(self._raw_sub, Qt.ElideRight, avail_w))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not getattr(self.app.play_tab, "_is_edit_mode", False):
                select_version(self.app, self.version_name)
        super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        if getattr(self.app.play_tab, "_is_edit_mode", False):
            if event.mimeData().hasText() and event.mimeData().text().startswith("cianova_version:"):
                event.acceptProposedAction()
                self._set_drop_highlight(True)
                return
        event.ignore()

    def dragMoveEvent(self, event):
        if getattr(self.app.play_tab, "_is_edit_mode", False):
            if event.mimeData().hasText() and event.mimeData().text().startswith("cianova_version:"):
                event.acceptProposedAction()
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._set_drop_highlight(False)
        event.accept()

    def dropEvent(self, event):
        self._set_drop_highlight(False)
        if not getattr(self.app.play_tab, "_is_edit_mode", False):
            event.ignore()
            return

        text = event.mimeData().text()
        if text.startswith("cianova_version:"):
            src_ver = text.split(":", 1)[1]
            tgt_ver = self.version_name
            if src_ver and tgt_ver and src_ver != tgt_ver:
                vers = self.app.logic.get_installed_versions(self.app)
                if src_ver in vers and tgt_ver in vers:
                    cur_order = list(vers)
                    src_idx = cur_order.index(src_ver)
                    tgt_idx = cur_order.index(tgt_ver)
                    cur_order.pop(src_idx)
                    new_tgt_idx = cur_order.index(tgt_ver)
                    if src_idx < tgt_idx:
                        cur_order.insert(new_tgt_idx + 1, src_ver)
                    else:
                        cur_order.insert(new_tgt_idx, src_ver)
                    self.app.config_manager.set("versions_order", cur_order)
                    self.app.config["versions_order"] = cur_order
                    self.app.config_manager.flush()
                    if hasattr(self.app.logic, "refresh_version_list"):
                        self.app.logic.refresh_version_list(self.app)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _set_drop_highlight(self, active: bool):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        if active:
            self.setStyleSheet(f"QFrame#VersionCard {{ border: 2px dashed {accent}; background: rgba(31, 106, 165, 0.15); }}")
        else:
            self.setStyleSheet("")


def ensure_profile_system(app):
    """Delegate to profiles module to ensure the profile system is initialized."""
    from .profiles import ensure_profile_system as _eps
    _eps(app)


def apply_profile_symlink(app, name):
    """Delegate to profiles module to apply a profile symlink."""
    from .profiles import apply_profile_symlink as _aps
    _aps(app, name)


def get_installed_versions(app):
    """Delegate to version_ops module to list installed versions."""
    from .version_ops import get_installed_versions as _giv
    return _giv(app)


def resolve_version(vpath):
    """Delegate to version_ops module to resolve a version path."""
    from .version_ops import resolve_version as _rv
    return _rv(vpath)


def detect_installation(app):
    """Detect and set the active installation path based on the configured install mode."""
    from .profiles import ensure_profile_system as _eps
    imode = app.config.get(c.CONFIG_KEY_INSTALL_MODE, c.MODE_INSTALL_LOCAL)
    fid = app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.DEFAULT_FLATPAK_ID)
    std_shared = os.path.join(app.home, c.LOCAL_SHARE_DIR)
    app.is_flatpak = False

    if app.running_in_flatpak and imode in [c.MODE_INSTALL_OWN, c.MODE_INSTALL_SHARED]:
        if os.path.exists(os.path.join(app.our_data_path, c.VERSIONS_DIR)):
            imode, app.active_path = c.MODE_INSTALL_OWN, app.our_data_path
        elif os.path.exists(os.path.join(std_shared, c.VERSIONS_DIR)):
            imode, app.active_path = c.MODE_INSTALL_SHARED, std_shared
        else:
            imode, app.active_path = c.MODE_INSTALL_OWN, app.our_data_path
        app.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, imode)
    else:
        if imode == c.MODE_INSTALL_OWN:
            app.active_path = app.our_data_path if app.running_in_flatpak else app.compiled_path
        elif imode == c.MODE_INSTALL_SHARED:
            app.active_path = std_shared
        elif imode == c.MODE_INSTALL_LOCAL:
            app.active_path = app.compiled_path
        elif imode == c.MODE_INSTALL_FLATPAK:
            app.is_flatpak = True
            app.active_path = os.path.join(
                app.home, f"{c.FLATPAK_DATA_DIR}/{fid}/{c.MCPELAUNCHER_DATA_SUBDIR}"
            )

    if app.active_path:
        _eps(app)

    status_text = f"● Mode: {imode}"
    if imode == c.MODE_INSTALL_OWN:
        status_text = c.t("UI_STATUS_LOCAL_OWN")
    elif imode == c.MODE_INSTALL_SHARED:
        status_text = c.t("UI_STATUS_LOCAL_SHARED")
    elif imode == c.MODE_INSTALL_LOCAL:
        status_text = c.t("UI_STATUS_LOCAL")
    elif imode == c.MODE_INSTALL_FLATPAK:
        status_text = c.t("UI_STATUS_FLATPAK_CUSTOM", flatpak_id=fid)

    app.play_tab.lbl_status.setText(status_text)
    app.update_floating_labels()
    app.play_tab.update_profile_indicator()

    refresh_version_list(app)
    check_shader_status(app)

    try:
        disp = c.t("UI_INSTALL_MODES").get(imode, "Unknown")
        app.play_tab.combo_mode.setCurrentText(disp)
        if getattr(app.tools_tab, "lbl_tools_status", None) is not None:
            app.tools_tab.lbl_tools_status.setText(status_text)
        app.update_floating_labels()
    except Exception as e:
        logger.warning("Failed to update install UI: %s", e)


def change_mode_ui(app, disp):
    """Change the install mode and optionally configure a custom Flatpak ID."""
    key = next((k for k, v in c.t("UI_INSTALL_MODES").items() if v == disp),
               c.MODE_INSTALL_LOCAL)
    app.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, key)
    if key == c.MODE_INSTALL_FLATPAK:
        from PySide6.QtWidgets import QInputDialog
        _id, ok = QInputDialog.getText(
            app, c.t("UI_CONFIG_FLATPAK_CUSTOM_TITLE"), c.t("UI_FLATPAK_ID_LABEL"),
            text=app.config.get(c.CONFIG_KEY_FLATPAK_ID, ""),
        )
        if ok and _id:
            app.config_manager.set(c.CONFIG_KEY_FLATPAK_ID, _id)
            detect_installation(app)
    else:
        detect_installation(app)


def switch_profile(app, name):
    """Switch the active profile and re-detect the installation."""
    from .profiles import apply_profile_symlink as _aps
    if app.active_path:
        _aps(app, name)
        app.config_manager.set(c.CONFIG_KEY_CURRENT_PROFILE, name)
        detect_installation(app)


def check_shader_status(app):
    """Read the current shader/graphics mode from options.txt and update the UI."""
    if not app.active_path:
        return
    op = os.path.join(app.active_path, c.MINECRAFT_PE_DIR_ALT, c.OPTIONS_FILE)
    status = "Unknown"
    if os.path.exists(op):
        try:
            with open(op, "r") as f:
                for line in f:
                    if "graphics_mode:" in line:
                        val = line.strip().split(":")[1]
                        if val == "0":
                            status = "Simple"
                        elif val == "1":
                            status = "Fancy"
                        elif val == "2":
                            status = "Vibrant"
                        break
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("Failed to read options.txt for shader status: %s", e)
    if hasattr(app.tools_tab, "lbl_shader_status") and app.tools_tab.lbl_shader_status:
        app.tools_tab.lbl_shader_status.setText(f"Shaders: {status}")


def update_shader_status_label(app):
    """Refresh the shader status label in the tools tab."""
    check_shader_status(app)


def clear_layout(layout):
    """Delegate to ui_utils module to clear all widgets from a layout."""
    from .ui_utils import clear_layout as _cl
    _cl(layout)


def refresh_version_list(app):
    """Rebuild the version card list in the play tab from the installed versions."""
    from .version_ops import resolve_version as _resolve_ver
    clear_layout(app.play_tab.version_list_layout)

    app.version_cards = {}
    if not app.active_path:
        return
    vdir = os.path.join(app.active_path, c.VERSIONS_DIR)
    if not os.path.exists(vdir):
        app.play_tab.version_list_layout.addWidget(QLabel(c.t("UI_NO_VERSIONS_FOLDER_MSG")))
        return

    style = app.config.get(c.CONFIG_KEY_VERSION_LIST_STYLE, c.STYLE_LIST)
    isize = app.config.get(c.CONFIG_KEY_VERSION_ICON_SIZE, 96)
    tsize = max(app.config.get(c.CONFIG_KEY_VERSION_TITLE_SIZE, 17), 17)
    cwidth = max(app.config.get(c.CONFIG_KEY_VERSION_CARD_WIDTH, 220), 220)
    cheight = max(app.config.get(c.CONFIG_KEY_VERSION_CARD_HEIGHT, 220), 220)

    # In list mode, use a prominent 70px icon (or full isize in grid mode)
    card_icon_size = max(70, isize if style == c.STYLE_GRID else 70)
    default_pix = (
        ImageManager.get_image("assets/minecraft_logo.svg", size=(card_icon_size, card_icon_size))
        or ImageManager.get_image("minecraft_logo.svg", size=(card_icon_size, card_icon_size))
        or ImageManager.get_image("minecraft_logo.png", size=(card_icon_size, card_icon_size))
        or ImageManager.get_image("icon.png", size=(card_icon_size, card_icon_size))
    )

    zooms = app.config.get(c.CONFIG_KEY_VERSION_ICON_ZOOM, {})
    xs = app.config.get(c.CONFIG_KEY_VERSION_ICON_X, {})
    ys = app.config.get(c.CONFIG_KEY_VERSION_ICON_Y, {})

    try:
        raw_vers = [d for d in os.listdir(vdir) if os.path.isdir(os.path.join(vdir, d))]
        saved_order = app.config.get("versions_order", [])
        if saved_order:
            ordered = [v for v in saved_order if v in raw_vers]
            for v in raw_vers:
                if v not in ordered:
                    ordered.append(v)
            vers = ordered
        else:
            vers = sorted(raw_vers, reverse=True)

        if not vers:
            app.play_tab.version_list_layout.addWidget(QLabel(c.t("UI_NO_VERSIONS_INSTALLED")))
            return

        is_edit_mode = getattr(app.play_tab, "_is_edit_mode", False)
        accent = getattr(app, "current_accent_color", "#1f6aa5") if app else "#1f6aa5"
        is_dark = getattr(app, "is_dark_mode", True) if app else True

        for idx, v in enumerate(vers):
            vpath = os.path.join(vdir, v)
            v_pix = default_pix
            for ext in [".svg", ".png", ".jpg", ".jpeg", ".webp"]:
                icon_p = os.path.join(vpath, "icon" + ext)
                if os.path.exists(icon_p):
                    zoom = zooms.get(v, 100) / 100.0
                    v_pix = ImageManager.get_image(
                        icon_p, size=(int(card_icon_size * zoom), int(card_icon_size * zoom))
                    )
                    if not v_pix:
                        v_pix = default_pix
                    break

            card = SleekVersionCard(app, v)

            if style == c.STYLE_GRID:
                card.setFixedSize(cwidth, cheight)
                cl = QVBoxLayout(card)
                cl.setContentsMargins(16, 16, 16, 16)
                cl.setSpacing(10)
                cl.setAlignment(Qt.AlignCenter)

                icon_container = QFrame()
                icon_container.setFixedSize(card_icon_size + 14, card_icon_size + 14)
                icon_container.setStyleSheet("background: transparent; border: none;")
                icon_lbl = QLabel(icon_container)
                icon_lbl.setPixmap(v_pix)
                icon_lbl.setFixedSize(v_pix.size())
                icon_lbl.setStyleSheet("background: transparent; border: none;")

                off_x = xs.get(v, 0)
                off_y = ys.get(v, 0)
                icon_lbl.move(
                    (card_icon_size + 14 - v_pix.width()) // 2 + off_x,
                    (card_icon_size + 14 - v_pix.height()) // 2 + off_y,
                )
                cl.addWidget(icon_container, 0, Qt.AlignCenter)

                name = v
                if v == "current":
                    rv = _resolve_ver(os.path.join(vdir, v))
                    if rv:
                        name = f"current ({rv})"
                lbl = QLabel(name)
                lbl.setStyleSheet(f"font-size: {tsize}px; font-weight: bold; background: transparent; border: none;")
                lbl.setAlignment(Qt.AlignCenter)
                cl.addWidget(lbl)
            else:
                card.setMinimumHeight(96)
                cl = QHBoxLayout(card)
                cl.setContentsMargins(14, 14, 18, 14)
                cl.setSpacing(12)

                # Drag grip handle (visible in mass edit mode)
                card.drag_grip = DragHandleGrip(card)
                grip_icon = ImageManager.get_tinted_icon("drag_handle_dots_icon.svg", "#4b5563" if not is_dark else "#8ea3b0", (18, 18))
                if not grip_icon.isNull():
                    card.drag_grip.setPixmap(grip_icon.pixmap(18, 18))
                card.drag_grip.setVisible(is_edit_mode)
                cl.addWidget(card.drag_grip, 0, Qt.AlignVCenter)

                icon_container = QFrame()
                icon_container.setFixedSize(card_icon_size + 14, card_icon_size + 14)
                icon_container.setStyleSheet("background: transparent; border: none;")
                icon_lbl = QLabel(icon_container)
                icon_lbl.setPixmap(v_pix)
                icon_lbl.setFixedSize(v_pix.size())
                icon_lbl.setStyleSheet("background: transparent; border: none;")

                off_x = xs.get(v, 0)
                off_y = ys.get(v, 0)
                icon_lbl.move(
                    (card_icon_size + 14 - v_pix.width()) // 2 + off_x,
                    (card_icon_size + 14 - v_pix.height()) // 2 + off_y,
                )
                cl.addWidget(icon_container, 0, Qt.AlignVCenter)

                text_layout = QVBoxLayout()
                text_layout.setContentsMargins(0, 0, 0, 0)
                text_layout.setSpacing(4)
                text_layout.setAlignment(Qt.AlignVCenter)

                name = v
                if v == "current":
                    rv = _resolve_ver(os.path.join(vdir, v))
                    if rv:
                        name = f"current ({rv})"
                lbl = QLabel(name)
                lbl.setMinimumWidth(0)
                lbl.setStyleSheet(f"font-size: {tsize}px; font-weight: bold; background: transparent; border: none;")
                text_layout.addWidget(lbl)

                # Dynamic Minecraft Bedrock v... subtitle
                rv_sub = _resolve_ver(vpath)
                if rv_sub:
                    sub_text = f"Minecraft Bedrock v{rv_sub}"
                elif v.replace(".", "").isdigit():
                    sub_text = f"Minecraft Bedrock v{v}"
                else:
                    sub_text = f"Minecraft Bedrock"

                sub_lbl = QLabel(sub_text)
                sub_lbl.setMinimumWidth(0)
                sub_lbl.setStyleSheet(f"font-size: 13px; color: {'#8ea3b0' if is_dark else '#4b5563'}; background: transparent; border: none;")
                text_layout.addWidget(sub_lbl)

                card.lbl_title = lbl
                card.lbl_sub = sub_lbl
                card._raw_sub = sub_text

                cl.addLayout(text_layout, 1)

                # Checkbox for mass edit mode (on the right side)
                card.cb_select = QCheckBox()
                card.cb_select.setFixedSize(24, 24)
                card.cb_select.setCursor(Qt.PointingHandCursor)
                card.cb_select.setVisible(is_edit_mode)
                card.cb_select.setStyleSheet(f"""
                    QCheckBox {{
                        background: transparent;
                        border: none;
                    }}
                    QCheckBox::indicator {{
                        width: 18px;
                        height: 18px;
                        border-radius: 5px;
                        border: 1.5px solid {hex_to_rgba(accent, 0.55)};
                        background-color: {"rgba(0, 0, 0, 0.35)" if is_dark else "rgba(0, 0, 0, 0.06)"};
                    }}
                    QCheckBox::indicator:hover {{
                        border-color: {accent};
                    }}
                    QCheckBox::indicator:checked {{
                        background-color: {accent};
                        border-color: {accent};
                    }}
                """)
                cl.addWidget(card.cb_select, 0, Qt.AlignVCenter)

                # 3-dots Context Menu Button (on the right side)
                card.btn_more = QPushButton()
                card.btn_more.setFixedSize(32, 32)
                card.btn_more.setCursor(Qt.PointingHandCursor)
                more_icon = ImageManager.get_tinted_icon("more_vertical_icon.svg", "#18191c" if not is_dark else "#ffffff", (18, 18))
                if not more_icon.isNull():
                    card.btn_more.setIcon(more_icon)
                    card.btn_more.setIconSize(QSize(18, 18))
                card.btn_more.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        border: none;
                        border-radius: 6px;
                    }}
                    QPushButton:hover {{
                        background: {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.08)"};
                    }}
                """)

                card.register_child(icon_container)
                card.register_child(icon_lbl)
                card.register_child(lbl)
                card.register_child(sub_lbl)
                card.register_child(card.cb_select)
                card.register_child(card.btn_more)

                def _open_card_menu(ver_name=v, b=card.btn_more):
                    from src.gui.version_manager_dialog import SleekVersionContextMenu
                    menu = SleekVersionContextMenu(app, ver_name, parent=b)
                    pos = b.mapToGlobal(QPoint(b.width() - 180, b.height() + 4))
                    menu.show_at(pos)

                card.btn_more.clicked.connect(lambda _, ver_n=v, b=card.btn_more: _open_card_menu(ver_n, b))
                cl.addWidget(card.btn_more, 0, Qt.AlignVCenter)

            app.version_cards[v] = card

            if style != c.STYLE_GRID:
                app.play_tab.version_list_layout.addWidget(card)

        if style == c.STYLE_GRID:
            grid = QGridLayout()
            grid.setSpacing(10)
            app.play_tab.version_list_layout.addLayout(grid)
            for i, v in enumerate(vers):
                grid.addWidget(app.version_cards[v], i // 3, i % 3)

        last = app.config.get(c.CONFIG_KEY_LAST_VERSION)
        if last in vers:
            select_version(app, last)
        elif vers:
            select_version(app, vers[0])
    except Exception as e:
        logger.warning("Failed to populate version grid: %s", e)


def select_version(app, version):
    """Select a version card and update the play tab state."""
    app.play_tab.set(version)
    for v, card in app.version_cards.items():
        is_selected = (v == version)
        card.setProperty("selected", is_selected)
        card.style().unpolish(card)
        card.style().polish(card)


def refresh_version_cards_theme(app):
    """Reapply the selected/unselected card colors and icon tints for the current theme."""
    if not app.version_cards:
        return
    selected = app.play_tab.get()
    is_dark = getattr(app, "is_dark_mode", True)
    for v, card in app.version_cards.items():
        card.setProperty("selected", v == selected)
        card.style().unpolish(card)
        card.style().polish(card)
        if hasattr(card, "btn_more") and card.btn_more:
            more_icon = ImageManager.get_tinted_icon("more_vertical_icon.svg", "#18191c" if not is_dark else "#ffffff", (18, 18))
            if not more_icon.isNull():
                card.btn_more.setIcon(more_icon)
        if hasattr(card, "drag_grip") and card.drag_grip:
            grip_icon = ImageManager.get_tinted_icon("drag_handle_dots_icon.svg", "#4b5563" if not is_dark else "#8ea3b0", (18, 18))
            if not grip_icon.isNull():
                card.drag_grip.setPixmap(grip_icon.pixmap(18, 18))
