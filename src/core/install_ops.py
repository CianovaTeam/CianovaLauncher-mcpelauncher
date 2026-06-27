import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout

from src import constants as c
from src.utils.image_manager import ImageManager
from src.utils.logger import logger


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
    isize = app.config.get(c.CONFIG_KEY_VERSION_ICON_SIZE, 32)
    tsize = app.config.get(c.CONFIG_KEY_VERSION_TITLE_SIZE, 13)
    cwidth = app.config.get(c.CONFIG_KEY_VERSION_CARD_WIDTH, 180)
    cheight = app.config.get(c.CONFIG_KEY_VERSION_CARD_HEIGHT, 145)
    default_pix = ImageManager.get_image("icon.png", size=(isize, isize))

    zooms = app.config.get(c.CONFIG_KEY_VERSION_ICON_ZOOM, {})
    xs = app.config.get(c.CONFIG_KEY_VERSION_ICON_X, {})
    ys = app.config.get(c.CONFIG_KEY_VERSION_ICON_Y, {})

    try:
        vers = sorted(
            [d for d in os.listdir(vdir) if os.path.isdir(os.path.join(vdir, d))]
        )
        if not vers:
            app.play_tab.version_list_layout.addWidget(QLabel(c.t("UI_NO_VERSIONS_INSTALLED")))
            return

        for v in vers:
            vpath = os.path.join(vdir, v)
            v_pix = default_pix
            for ext in [".png", ".jpg", ".jpeg", ".webp"]:
                icon_p = os.path.join(vpath, "icon" + ext)
                if os.path.exists(icon_p):
                    zoom = zooms.get(v, 100) / 100.0
                    v_pix = ImageManager.get_image(
                        icon_p, size=(int(isize * zoom), int(isize * zoom))
                    )
                    if not v_pix:
                        v_pix = default_pix
                    break

            card = QFrame()
            card.setObjectName("VersionCard")
            if style == c.STYLE_GRID:
                card.setFixedSize(cwidth, cheight)
                cl = QVBoxLayout(card)
                cl.setAlignment(Qt.AlignCenter)

                icon_container = QFrame()
                icon_container.setFixedSize(isize + 10, isize + 10)
                icon_container.setStyleSheet(
                    "background: transparent; border: none;"
                )
                icon_lbl = QLabel(icon_container)
                icon_lbl.setPixmap(v_pix)
                icon_lbl.setFixedSize(v_pix.size())
                icon_lbl.setStyleSheet("background: transparent;")

                off_x = xs.get(v, 0)
                off_y = ys.get(v, 0)
                icon_lbl.move(
                    (isize + 10 - v_pix.width()) // 2 + off_x,
                    (isize + 10 - v_pix.height()) // 2 + off_y,
                )

                cl.addWidget(icon_container, 0, Qt.AlignCenter)

                name = v
                if v == "current":
                    rv = _resolve_ver(os.path.join(vdir, v))
                    if rv:
                        name = f"current ({rv})"
                lbl = QLabel(name)
                lbl.setStyleSheet(
                    f"font-size: {tsize}px; font-weight: bold; background: transparent;"
                )
                lbl.setAlignment(Qt.AlignCenter)
                cl.addWidget(lbl)
            else:
                cl = QHBoxLayout(card)
                icon_container = QFrame()
                icon_container.setFixedSize(isize + 10, isize + 10)
                icon_container.setStyleSheet(
                    "background: transparent; border: none;"
                )
                icon_lbl = QLabel(icon_container)
                icon_lbl.setPixmap(v_pix)
                icon_lbl.setFixedSize(v_pix.size())
                icon_lbl.setStyleSheet("background: transparent;")

                off_x = xs.get(v, 0)
                off_y = ys.get(v, 0)
                icon_lbl.move(
                    (isize + 10 - v_pix.width()) // 2 + off_x,
                    (isize + 10 - v_pix.height()) // 2 + off_y,
                )

                cl.addWidget(icon_container)

                name = v
                if v == "current":
                    rv = _resolve_ver(os.path.join(vdir, v))
                    if rv:
                        name = f"current ({rv})"
                lbl = QLabel(name)
                lbl.setStyleSheet(
                    f"font-size: {tsize}px; font-weight: bold; background: transparent;"
                )
                cl.addWidget(lbl, 1)

            card.mousePressEvent = lambda e, ver=v: (select_version(app, ver), QFrame.mousePressEvent(card, e))
            app.version_cards[v] = card

            if style != c.STYLE_GRID:
                app.play_tab.version_list_layout.addWidget(card)

        if style == c.STYLE_GRID:
            grid = QGridLayout()
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
    theme_color = app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue")
    accent = c.THEME_COLOR_MAP.get(theme_color, "#1f6aa5")
    mode = app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")
    unselected_bg = "#3a3a3a" if mode == "Dark" else "#e0e0e0"

    for v, card in app.version_cards.items():
        if v == version:
            card.setStyleSheet(f"background-color: {accent};")
        else:
            card.setStyleSheet(f"background-color: {unselected_bg};")
