"""Unit tests for src.core.profiles — profile CRUD and symlink logic."""
import os
from types import SimpleNamespace

import pytest

from src.core import profiles as p
from src import constants as c


class FakeConfigManager:
    """Minimal ConfigManager stand-in backed by a plain dict."""

    def __init__(self, config):
        self.config = config

    def set(self, key, value):
        self.config[key] = value

    def save_config(self):
        pass


def make_app(tmp_path, config=None):
    config = config if config is not None else {}
    cm = FakeConfigManager(config)
    return SimpleNamespace(
        active_path=str(tmp_path),
        config=config,
        config_manager=cm,
        profiles_supported=None,
        home=str(tmp_path),
    )


class TestGetProfiles:
    def test_default_when_absent(self, tmp_path):
        app = make_app(tmp_path)
        assert p.get_profiles(app) == [c.t("UI_PROFILE_DEFAULT")]

    def test_returns_config_list(self, tmp_path):
        app = make_app(tmp_path, {c.CONFIG_KEY_PROFILES: ["default", "dev"]})
        assert p.get_profiles(app) == ["default", "dev"]


class TestApplyProfileSymlink:
    def test_creates_symlink(self, tmp_path):
        app = make_app(tmp_path)
        assert p.apply_profile_symlink(app, "default") is True
        link = os.path.join(str(tmp_path), "games")
        assert os.path.islink(link)
        target = os.path.join(c.PROFILES_DIR, "default", "games")
        assert os.readlink(link) == target

    def test_no_active_path_returns_false(self):
        app = SimpleNamespace(active_path=None)
        assert p.apply_profile_symlink(app, "default") is False

    def test_replaces_existing_symlink(self, tmp_path):
        app = make_app(tmp_path)
        p.apply_profile_symlink(app, "default")
        assert p.apply_profile_symlink(app, "dev") is True
        link = os.path.join(str(tmp_path), "games")
        assert os.readlink(link) == os.path.join(c.PROFILES_DIR, "dev", "games")


class TestCreateProfile:
    def test_create_new(self, tmp_path, monkeypatch):
        app = make_app(tmp_path, {c.CONFIG_KEY_PROFILES: ["default"]})
        monkeypatch.setattr("src.core.install_ops.switch_profile", lambda a, n: None)
        result = p.create_profile_pyside(app, "MyProfile")
        assert result == "MyProfile"
        assert "MyProfile" in app.config[c.CONFIG_KEY_PROFILES]
        assert os.path.isdir(os.path.join(str(tmp_path), c.PROFILES_DIR, "MyProfile", "games"))

    def test_sanitizes_name(self, tmp_path, monkeypatch):
        app = make_app(tmp_path, {c.CONFIG_KEY_PROFILES: ["default"]})
        monkeypatch.setattr("src.core.install_ops.switch_profile", lambda a, n: None)
        result = p.create_profile_pyside(app, "My/Profile!!")
        assert result == "MyProfile"

    def test_empty_name_returns_none(self, tmp_path):
        app = make_app(tmp_path, {c.CONFIG_KEY_PROFILES: ["default"]})
        assert p.create_profile_pyside(app, "") is None

    def test_only_invalid_chars_returns_none(self, tmp_path):
        app = make_app(tmp_path, {c.CONFIG_KEY_PROFILES: ["default"]})
        assert p.create_profile_pyside(app, "///") is None

    def test_duplicate_not_added_twice(self, tmp_path, monkeypatch):
        app = make_app(tmp_path, {c.CONFIG_KEY_PROFILES: ["default", "dev"]})
        monkeypatch.setattr("src.core.install_ops.switch_profile", lambda a, n: None)
        p.create_profile_pyside(app, "dev")
        assert app.config[c.CONFIG_KEY_PROFILES].count("dev") == 1


class TestDeleteProfile:
    def test_cannot_delete_default(self, tmp_path):
        app = make_app(tmp_path)
        assert p.delete_profile(app, c.t("UI_PROFILE_DEFAULT")) is False

    def test_cannot_delete_current(self, tmp_path):
        app = make_app(tmp_path, {c.CONFIG_KEY_CURRENT_PROFILE: "dev"})
        assert p.delete_profile(app, "dev") is False

    def test_delete_removes_dir_and_config(self, tmp_path, monkeypatch):
        config = {
            c.CONFIG_KEY_PROFILES: ["default", "dev"],
            c.CONFIG_KEY_CURRENT_PROFILE: "default",
        }
        app = make_app(tmp_path, config)
        prof_dir = os.path.join(str(tmp_path), c.PROFILES_DIR, "dev")
        os.makedirs(prof_dir)
        monkeypatch.setattr(p.messagebox, "askyesno", lambda *a, **k: True)
        assert p.delete_profile(app, "dev") is True
        assert "dev" not in app.config[c.CONFIG_KEY_PROFILES]
        assert not os.path.exists(prof_dir)

    def test_delete_cancelled_returns_false(self, tmp_path, monkeypatch):
        config = {c.CONFIG_KEY_PROFILES: ["default", "dev"], c.CONFIG_KEY_CURRENT_PROFILE: "default"}
        app = make_app(tmp_path, config)
        monkeypatch.setattr(p.messagebox, "askyesno", lambda *a, **k: False)
        assert p.delete_profile(app, "dev") is False


class TestRenameProfile:
    def test_cannot_rename_default(self, tmp_path):
        app = make_app(tmp_path)
        assert p.rename_profile(app, c.t("UI_PROFILE_DEFAULT"), "new") is False

    def test_empty_new_name_returns_false(self, tmp_path):
        app = make_app(tmp_path, {c.CONFIG_KEY_PROFILES: ["default", "dev"]})
        assert p.rename_profile(app, "dev", "") is False

    def test_duplicate_new_name_returns_false(self, tmp_path):
        app = make_app(tmp_path, {c.CONFIG_KEY_PROFILES: ["default", "dev", "prod"]})
        assert p.rename_profile(app, "dev", "prod") is False

    def test_rename_success(self, tmp_path):
        config = {c.CONFIG_KEY_PROFILES: ["default", "dev"], c.CONFIG_KEY_CURRENT_PROFILE: "default"}
        app = make_app(tmp_path, config)
        os.makedirs(os.path.join(str(tmp_path), c.PROFILES_DIR, "dev"))
        assert p.rename_profile(app, "dev", "staging") is True
        assert "staging" in app.config[c.CONFIG_KEY_PROFILES]
        assert "dev" not in app.config[c.CONFIG_KEY_PROFILES]

    def test_rename_current_updates_symlink(self, tmp_path):
        config = {c.CONFIG_KEY_PROFILES: ["default", "dev"], c.CONFIG_KEY_CURRENT_PROFILE: "dev"}
        app = make_app(tmp_path, config)
        os.makedirs(os.path.join(str(tmp_path), c.PROFILES_DIR, "dev"))
        assert p.rename_profile(app, "dev", "staging") is True
        assert app.config[c.CONFIG_KEY_CURRENT_PROFILE] == "staging"
        link = os.path.join(str(tmp_path), "games")
        assert os.readlink(link) == os.path.join(c.PROFILES_DIR, "staging", "games")


class TestEnsureProfileSystem:
    def test_no_active_path_is_noop(self):
        app = SimpleNamespace(active_path=None)
        p.ensure_profile_system(app)  # should not raise

    def test_bootstraps_profile_dir(self, tmp_path, monkeypatch):
        config = {}
        app = make_app(tmp_path, config)
        monkeypatch.setattr(p.messagebox, "showinfo", lambda *a, **k: None)
        p.ensure_profile_system(app)
        assert app.profiles_supported is True
        assert os.path.isdir(os.path.join(str(tmp_path), c.PROFILES_DIR, c.t("UI_PROFILE_DEFAULT")))
        assert app.config[c.CONFIG_KEY_PROFILES] == [c.t("UI_PROFILE_DEFAULT")]
