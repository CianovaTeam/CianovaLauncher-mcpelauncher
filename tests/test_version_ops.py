"""Unit tests for src.core.version_ops — install-source metadata and version helpers."""
import json
import os
from types import SimpleNamespace

import pytest

from src.core import version_ops as vo
from src import constants as c


@pytest.fixture
def version_dir(tmp_path):
    d = tmp_path / "ver"
    d.mkdir()
    return str(d)


class TestInstallSource:
    def test_write_then_read(self, version_dir):
        vo._write_install_source(version_dir, "apk")
        assert vo.read_install_source(version_dir) == "apk"

    def test_write_records_timestamp(self, version_dir):
        vo._write_install_source(version_dir, "google_play")
        with open(os.path.join(version_dir, ".install_source")) as f:
            meta = json.load(f)
        assert meta["source"] == "google_play"
        assert "installed_at" in meta

    def test_read_missing_returns_none(self, version_dir):
        assert vo.read_install_source(version_dir) is None

    def test_read_corrupt_returns_none(self, version_dir):
        with open(os.path.join(version_dir, ".install_source"), "w") as f:
            f.write("{bad json")
        assert vo.read_install_source(version_dir) is None

    def test_read_missing_source_key(self, version_dir):
        with open(os.path.join(version_dir, ".install_source"), "w") as f:
            json.dump({"installed_at": "2020"}, f)
        assert vo.read_install_source(version_dir) is None


class TestResolveVersion:
    def test_from_version_name_txt(self, version_dir):
        with open(os.path.join(version_dir, "version_name.txt"), "w") as f:
            f.write("1.20.10\n")
        assert vo.resolve_version(version_dir) == "1.20.10"

    def test_from_manifest(self, version_dir):
        manifest_dir = os.path.join(version_dir, "assets/packs/vanilla")
        os.makedirs(manifest_dir)
        with open(os.path.join(manifest_dir, "manifest.json"), "w") as f:
            json.dump({"header": {"version": [1, 21, 2]}}, f)
        assert vo.resolve_version(version_dir) == "1.21.2"

    def test_version_name_txt_takes_priority(self, version_dir):
        with open(os.path.join(version_dir, "version_name.txt"), "w") as f:
            f.write("9.9.9")
        manifest_dir = os.path.join(version_dir, "assets/packs/vanilla")
        os.makedirs(manifest_dir)
        with open(os.path.join(manifest_dir, "manifest.json"), "w") as f:
            json.dump({"header": {"version": [1, 0, 0]}}, f)
        assert vo.resolve_version(version_dir) == "9.9.9"

    def test_none_when_nothing_present(self, version_dir):
        assert vo.resolve_version(version_dir) is None

    def test_none_when_manifest_has_no_version(self, version_dir):
        manifest_dir = os.path.join(version_dir, "assets/packs/vanilla")
        os.makedirs(manifest_dir)
        with open(os.path.join(manifest_dir, "manifest.json"), "w") as f:
            json.dump({"header": {}}, f)
        assert vo.resolve_version(version_dir) is None


class TestGetInstalledVersions:
    def _make_app(self, active_path):
        return SimpleNamespace(active_path=active_path)

    def test_lists_version_dirs_sorted_desc(self, tmp_path):
        vdir = tmp_path / c.VERSIONS_DIR
        vdir.mkdir()
        (vdir / "1.20.0").mkdir()
        (vdir / "1.21.0").mkdir()
        (vdir / "afile.txt").write_text("x")
        app = self._make_app(str(tmp_path))
        assert vo.get_installed_versions(app) == ["1.21.0", "1.20.0"]

    def test_no_versions_dir_returns_empty(self, tmp_path):
        app = self._make_app(str(tmp_path))
        assert vo.get_installed_versions(app) == []


class TestRenameVersion:
    def _make_app(self, tmp_path):
        cfg = {c.CONFIG_KEY_VERSION_ICON_ZOOM: {}, c.CONFIG_KEY_LAST_VERSION: None}
        app = SimpleNamespace(
            active_path=str(tmp_path),
            config=cfg,
            config_manager=SimpleNamespace(save_config=lambda: None),
            play_tab=None,
        )
        return app

    def test_rename_success(self, tmp_path, monkeypatch):
        vdir = tmp_path / c.VERSIONS_DIR
        vdir.mkdir()
        (vdir / "old").mkdir()
        app = self._make_app(tmp_path)
        monkeypatch.setattr("src.core.install_ops.refresh_version_list", lambda a: None)
        assert vo.rename_version(app, "old", "new") is True
        assert (vdir / "new").is_dir()
        assert not (vdir / "old").exists()

    def test_rename_updates_last_version(self, tmp_path, monkeypatch):
        vdir = tmp_path / c.VERSIONS_DIR
        vdir.mkdir()
        (vdir / "old").mkdir()
        app = self._make_app(tmp_path)
        app.config[c.CONFIG_KEY_LAST_VERSION] = "old"
        monkeypatch.setattr("src.core.install_ops.refresh_version_list", lambda a: None)
        vo.rename_version(app, "old", "new")
        assert app.config[c.CONFIG_KEY_LAST_VERSION] == "new"

    def test_rename_migrates_icon_zoom(self, tmp_path, monkeypatch):
        vdir = tmp_path / c.VERSIONS_DIR
        vdir.mkdir()
        (vdir / "old").mkdir()
        app = self._make_app(tmp_path)
        app.config[c.CONFIG_KEY_VERSION_ICON_ZOOM] = {"old": 1.5}
        monkeypatch.setattr("src.core.install_ops.refresh_version_list", lambda a: None)
        vo.rename_version(app, "old", "new")
        zooms = app.config[c.CONFIG_KEY_VERSION_ICON_ZOOM]
        assert "old" not in zooms and zooms["new"] == 1.5

    def test_rename_fails_when_target_exists(self, tmp_path, monkeypatch):
        vdir = tmp_path / c.VERSIONS_DIR
        vdir.mkdir()
        (vdir / "old").mkdir()
        (vdir / "new").mkdir()
        app = self._make_app(tmp_path)
        # Suppress the Qt error dialog
        monkeypatch.setattr(vo.messagebox, "showerror", lambda *a, **k: None)
        assert vo.rename_version(app, "old", "new") is False
