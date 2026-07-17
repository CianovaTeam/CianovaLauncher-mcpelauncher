"""Unit tests for src.core.moddb_service — pure/disk helpers (no network)."""
import json
import os

import pytest

from src.core import moddb_service as m
from src import constants as c


@pytest.fixture
def active_path(tmp_path):
    return str(tmp_path)


class TestCachePath:
    def test_cache_path_layout(self, active_path):
        path = m._moddb_cache_path(active_path)
        assert path == os.path.join(active_path, c.MODS_DIR, m.MODDB_CACHE_FILE)


class TestCacheRoundTrip:
    def test_cache_then_read(self, active_path):
        data = [{"name": "zoom"}, {"name": "fullbright"}]
        m.cache_moddb(active_path, data)
        assert m.get_cached_moddb(active_path) == data

    def test_cache_creates_mods_dir(self, active_path):
        m.cache_moddb(active_path, {"a": 1})
        assert os.path.isdir(os.path.join(active_path, c.MODS_DIR))

    def test_get_cached_missing_returns_none(self, active_path):
        assert m.get_cached_moddb(active_path) is None

    def test_get_cached_no_active_path(self):
        assert m.get_cached_moddb(None) is None

    def test_cache_no_active_path_is_noop(self):
        # Should not raise
        m.cache_moddb(None, {"a": 1})

    def test_get_cached_corrupt_json_returns_none(self, active_path):
        path = m._moddb_cache_path(active_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("{not valid json")
        assert m.get_cached_moddb(active_path) is None


class TestGetModInfo:
    def test_find_existing(self):
        db = [{"name": "zoom"}, {"name": "legacy"}]
        assert m.get_mod_info(db, "legacy") == {"name": "legacy"}

    def test_missing_returns_none(self):
        assert m.get_mod_info([{"name": "zoom"}], "nope") is None

    def test_non_list_returns_none(self):
        assert m.get_mod_info({"name": "zoom"}, "zoom") is None

    def test_empty_list(self):
        assert m.get_mod_info([], "zoom") is None


class TestFindAssetForArch:
    def test_exact_arch_match(self):
        entry = {
            "versions": [
                {"version": "1.2", "assets": {"x86_64": "u64", "arm64-v8a": "uarm"}},
            ]
        }
        assert m.find_asset_for_arch(entry, "x86_64") == ("u64", "1.2")

    def test_arch_match_in_second_version(self):
        entry = {
            "versions": [
                {"version": "1.0", "assets": {"arm64-v8a": "uarm"}},
                {"version": "2.0", "assets": {"x86_64": "u64"}},
            ]
        }
        assert m.find_asset_for_arch(entry, "x86_64") == ("u64", "2.0")

    def test_fallback_to_first_asset(self):
        entry = {"versions": [{"version": "1.0", "assets": {"arm64-v8a": "uarm"}}]}
        url, ver = m.find_asset_for_arch(entry, "x86_64")
        assert url == "uarm"
        assert ver == "1.0"

    def test_no_versions(self):
        assert m.find_asset_for_arch({"versions": []}, "x86_64") == (None, None)

    def test_missing_versions_key(self):
        assert m.find_asset_for_arch({}, "x86_64") == (None, None)

    def test_version_without_assets_falls_through(self):
        entry = {"versions": [{"version": "1.0", "assets": {}}]}
        assert m.find_asset_for_arch(entry, "x86_64") == (None, None)


class TestIsModInstalled:
    def test_installed(self, active_path):
        os.makedirs(os.path.join(active_path, c.MODS_DIR, "zoom"))
        assert m.is_mod_installed(active_path, "zoom") is True

    def test_not_installed(self, active_path):
        assert m.is_mod_installed(active_path, "zoom") is False

    def test_no_active_path(self):
        assert m.is_mod_installed(None, "zoom") is False


class TestGetInstalledModDirs:
    def test_lists_dirs_only(self, active_path):
        mods = os.path.join(active_path, c.MODS_DIR)
        os.makedirs(os.path.join(mods, "zoom"))
        os.makedirs(os.path.join(mods, "legacy"))
        with open(os.path.join(mods, "moddb_cache.json"), "w") as f:
            f.write("{}")
        assert m.get_installed_mod_dirs(active_path) == {"zoom", "legacy"}

    def test_excludes_pycache(self, active_path):
        mods = os.path.join(active_path, c.MODS_DIR)
        os.makedirs(os.path.join(mods, "zoom"))
        os.makedirs(os.path.join(mods, "__pycache__"))
        assert m.get_installed_mod_dirs(active_path) == {"zoom"}

    def test_missing_mods_dir_returns_empty(self, active_path):
        assert m.get_installed_mod_dirs(active_path) == set()

    def test_no_active_path(self):
        assert m.get_installed_mod_dirs(None) == set()


class TestDetectArchitecture:
    @pytest.mark.parametrize("machine,expected", [
        ("x86_64", "x86_64"),
        ("amd64", "x86_64"),
        ("aarch64", "arm64-v8a"),
        ("arm64", "arm64-v8a"),
        ("i386", "x86"),
        ("i686", "x86"),
        ("x86", "x86"),
        ("armv7l", "armeabi-v7a"),
        ("armv6l", "armeabi-v7a"),
    ])
    def test_arch_mapping(self, monkeypatch, machine, expected):
        monkeypatch.setattr("platform.machine", lambda: machine)
        assert m.detect_architecture() == expected

    def test_unknown_arch(self, monkeypatch):
        monkeypatch.setattr("platform.machine", lambda: "riscv64")
        assert m.detect_architecture() is None
