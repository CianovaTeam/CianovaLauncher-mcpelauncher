"""Unit tests for ConfigManager — no Qt dependency."""
import json
import os
import tempfile

import pytest

from src.core.config_manager import ConfigManager
from src import constants as c


@pytest.fixture
def tmp_config():
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
    json.dump({}, tmp)
    tmp.close()
    cm = ConfigManager(config_file=tmp.name)
    yield cm, tmp.name
    os.unlink(tmp.name)


class TestDefaults:
    def test_default_config_keys(self, tmp_config):
        cm, _ = tmp_config
        assert "data_path" in cm.default_config
        assert cm.default_config["data_path"] != ""

    def test_default_language_is_en(self, tmp_config):
        cm, _ = tmp_config
        assert cm.get(c.CONFIG_KEY_LANGUAGE) == "en"

    def test_default_appearance_is_dark(self, tmp_config):
        cm, _ = tmp_config
        assert cm.get(c.CONFIG_KEY_APPEARANCE) == "Dark"


class TestSetGet:
    def test_set_and_get(self, tmp_config):
        cm, _ = tmp_config
        cm.set(c.CONFIG_KEY_LANGUAGE, "es")
        assert cm.get(c.CONFIG_KEY_LANGUAGE) == "es"

    def test_get_default_when_missing(self, tmp_config):
        cm, _ = tmp_config
        assert cm.get("nonexistent_key", "fallback") == "fallback"

    def test_get_none_when_missing_no_default(self, tmp_config):
        cm, _ = tmp_config
        assert cm.get("nonexistent_key") is None


class TestSaveLoad:
    def test_save_and_load_preserves_values(self, tmp_config):
        cm, path = tmp_config
        cm.set(c.CONFIG_KEY_LANGUAGE, "fr")
        cm.save_config()

        cm2 = ConfigManager(config_file=path)
        assert cm2.get(c.CONFIG_KEY_LANGUAGE) == "fr"

    def test_save_is_valid_json(self, tmp_config):
        cm, path = tmp_config
        cm.save_config()
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert c.CONFIG_KEY_LANGUAGE in data


class TestDeepMerge:
    def test_merge_adds_new_keys(self, tmp_config):
        cm, _ = tmp_config
        merged = cm._deep_merge({"a": 1, "b": 2}, {"c": 3})
        assert merged == {"a": 1, "b": 2, "c": 3}

    def test_merge_overwrites_existing(self, tmp_config):
        cm, _ = tmp_config
        merged = cm._deep_merge({"a": 1}, {"a": 99})
        assert merged["a"] == 99

    def test_merge_nested(self, tmp_config):
        cm, _ = tmp_config
        defaults = {"outer": {"inner_a": 1, "inner_b": 2}}
        loaded = {"outer": {"inner_a": 99}}
        merged = cm._deep_merge(defaults, loaded)
        assert merged["outer"]["inner_a"] == 99
        assert merged["outer"]["inner_b"] == 2

    def test_merge_preserves_unrelated_nested(self, tmp_config):
        cm, _ = tmp_config
        defaults = {"a": {"x": 1}, "b": 2}
        loaded = {"a": {"y": 3}}
        merged = cm._deep_merge(defaults, loaded)
        assert merged["a"]["x"] == 1
        assert merged["a"]["y"] == 3


class TestRestoreDefaults:
    def test_restore_defaults(self, tmp_config):
        cm, _ = tmp_config
        cm.set(c.CONFIG_KEY_LANGUAGE, "de")
        cm.restore_defaults()
        assert cm.get(c.CONFIG_KEY_LANGUAGE) == "en"

    def test_restore_persists_to_disk(self, tmp_config):
        cm, path = tmp_config
        cm.set(c.CONFIG_KEY_LANGUAGE, "de")
        cm.restore_defaults()

        cm2 = ConfigManager(config_file=path)
        assert cm2.get(c.CONFIG_KEY_LANGUAGE) == "en"


class TestMigration:
    def test_migrate_launch_action(self, tmp_config):
        cm, _ = tmp_config
        config = {"close_on_launch": False}
        changed = cm._migrate_config(config)
        assert changed
        assert c.CONFIG_KEY_LAUNCH_ACTION in config

    def test_migrate_flatpak_id(self, tmp_config):
        cm, _ = tmp_config
        config = {c.CONFIG_KEY_FLATPAK_ID: c.MCPELAUNCHER_FLATPAK_ID}
        changed = cm._migrate_config(config)
        assert changed
        assert config[c.CONFIG_KEY_FLATPAK_ID] == c.DEFAULT_FLATPAK_ID


class TestCriticalFixes:
    def test_restore_defaults_uses_deepcopy(self, tmp_config):
        """C1: restore_defaults mutating config must not affect default_config."""
        cm, _ = tmp_config
        binary_paths_key = c.CONFIG_KEY_BINARY_PATHS
        original_default = cm.default_config[binary_paths_key][c.CONFIG_KEY_CLIENT]

        cm.config[binary_paths_key][c.CONFIG_KEY_CLIENT] = "MUTATED"
        cm.restore_defaults()

        assert cm.default_config[binary_paths_key][c.CONFIG_KEY_CLIENT] == original_default

    def test_deep_merge_does_not_share_nested_dicts(self, tmp_config):
        """C2: _deep_merge must deep-copy defaults to avoid shared mutation."""
        cm, _ = tmp_config
        bp_key = c.CONFIG_KEY_BINARY_PATHS

        loaded = {bp_key: {"client": "/custom"}}
        merged = cm._deep_merge(cm.default_config, loaded)

        merged[bp_key]["extract"] = "MUTATED"
        assert cm.default_config[bp_key]["extract"] != "MUTATED"
