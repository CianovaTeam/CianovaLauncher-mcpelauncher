import os
import shutil
import time
from src import constants as c
from src.gui import custom_dialogs as messagebox
from src.utils.logger import logger


def ensure_profile_system(app):
    """Create the profiles directory and default profile if they do not exist."""
    if not app.active_path:
        return
    app.profiles_supported = True
    pdir = os.path.join(app.active_path, c.PROFILES_DIR)
    gdir = os.path.join(app.active_path, "games")
    def_path = os.path.join(pdir, c.t("UI_PROFILE_DEFAULT"))
    if not os.path.exists(app.active_path):
        os.makedirs(app.active_path, exist_ok=True)
    if not os.path.exists(pdir):
        try:
            os.makedirs(def_path, exist_ok=True)
            if os.path.exists(gdir) and not os.path.islink(gdir):
                shutil.move(gdir, def_path)
                messagebox.showinfo(app, c.t("UI_INFO_TITLE"), c.t("UI_PROFILE_MIGRATION_NOTICE"))
            os.makedirs(os.path.join(def_path, "games"), exist_ok=True)
            if c.CONFIG_KEY_PROFILES not in app.config:
                app.config[c.CONFIG_KEY_PROFILES] = [c.t("UI_PROFILE_DEFAULT")]
            if c.CONFIG_KEY_CURRENT_PROFILE not in app.config:
                app.config[c.CONFIG_KEY_CURRENT_PROFILE] = c.t("UI_PROFILE_DEFAULT")
            app.config_manager.save_config()
            if not apply_profile_symlink(app, app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.t("UI_PROFILE_DEFAULT"))):
                app.profiles_supported = False
        except Exception as e:
            logger.error(f"Profile migration error: {e}")
            app.profiles_supported = False
    else:
        if not apply_profile_symlink(app, app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.t("UI_PROFILE_DEFAULT"))):
            app.profiles_supported = False


def apply_profile_symlink(app, profile):
    """Create or update the games symlink pointing to the given profile."""
    if not app.active_path:
        return False
    link = os.path.join(app.active_path, "games")
    target_rel = os.path.join(c.PROFILES_DIR, profile, "games")
    target_abs = os.path.join(app.active_path, target_rel)

    os.makedirs(target_abs, exist_ok=True)
    try:
        if os.path.islink(link):
            os.unlink(link)
        elif os.path.exists(link):
            if os.path.isdir(link):
                os.rename(link, link + "_bak_" + str(int(time.time())))
            else:
                os.remove(link)

        os.symlink(target_rel, link)
        return True
    except Exception as e:
        logger.error(f"Symlink error: {e}")
        try:
            if os.path.exists(link) and not os.path.islink(link):
                os.rename(link, link + "_bak_" + str(int(time.time())))

            if not os.path.exists(link):
                os.makedirs(link, exist_ok=True)

            messagebox.showwarning(app, c.t("UI_SYMLINK_NOT_SUPPORTED_TITLE"), c.t("UI_SYMLINK_NOT_SUPPORTED_MSG"))
            app.profiles_supported = False
        except Exception as e2:
            logger.error(f"Symlink fallback also failed: {e2}")
        return False


def get_profiles(app):
    """Return the list of profile names from config."""
    return app.config.get(c.CONFIG_KEY_PROFILES, [c.t("UI_PROFILE_DEFAULT")])


def create_profile_pyside(app, name):
    """Create a new profile directory and switch to it."""
    if name:
        name = "".join(x for x in name if x.isalnum() or x in " -_").strip()
        if name:
            profiles = get_profiles(app)
            if name not in profiles:
                profiles.append(name)
                app.config_manager.set(c.CONFIG_KEY_PROFILES, profiles)
                os.makedirs(os.path.join(app.active_path, c.PROFILES_DIR, name, "games"), exist_ok=True)
                from src.core.install_ops import switch_profile
                switch_profile(app, name)
            return name
    return None


def delete_profile(app, name):
    """Remove a profile from config and delete its directory."""
    if name == c.t("UI_PROFILE_DEFAULT") or name == app.config.get(c.CONFIG_KEY_CURRENT_PROFILE):
        return False
    if messagebox.askyesno(app, c.t("UI_CONFIRM_DELETE_TITLE"), c.t("UI_CONFIRM_DELETE_PROFILE", name=name)):
        try:
            p = get_profiles(app)
            if name in p:
                p.remove(name)
                app.config_manager.set(c.CONFIG_KEY_PROFILES, p)
                path = os.path.join(app.active_path, c.PROFILES_DIR, name)
                if os.path.exists(path):
                    shutil.rmtree(path)
                return True
        except Exception as e:
            messagebox.showerror(app, c.t("UI_ERROR_TITLE"), str(e))
    return False


def rename_profile(app, old, new):
    """Rename a profile folder and update config references."""
    if old == c.t("UI_PROFILE_DEFAULT") or not new:
        return False
    new = "".join(x for x in new if x.isalnum() or x in " -_").strip()
    p = get_profiles(app)
    if not new or new in p:
        return False
    try:
        os.rename(os.path.join(app.active_path, c.PROFILES_DIR, old),
                  os.path.join(app.active_path, c.PROFILES_DIR, new))
        p[p.index(old)] = new
        app.config_manager.set(c.CONFIG_KEY_PROFILES, p)
        if app.config.get(c.CONFIG_KEY_CURRENT_PROFILE) == old:
            app.config_manager.set(c.CONFIG_KEY_CURRENT_PROFILE, new)
            apply_profile_symlink(app, new)
        return True
    except Exception as e:
        messagebox.showerror(app, c.t("UI_ERROR_TITLE"), str(e))
        return False
