"""Unit tests for the shared process/Flatpak helpers — no Qt dependency."""
import subprocess

import pytest

from src.utils import process_utils as pu
from src import constants as c


class TestFlatpakDetection:
    def test_is_running_in_flatpak_false(self, monkeypatch):
        monkeypatch.setattr(pu.os.path, "exists", lambda p: False)
        assert pu.is_running_in_flatpak() is False

    def test_is_running_in_flatpak_true(self, monkeypatch):
        monkeypatch.setattr(pu.os.path, "exists",
                            lambda p: p == c.FLATPAK_INFO_FILE)
        assert pu.is_running_in_flatpak() is True

    def test_get_flatpak_app_id_none_outside_sandbox(self, monkeypatch):
        monkeypatch.setattr(pu, "is_running_in_flatpak", lambda: False)
        assert pu.get_flatpak_app_id() is None

    def test_get_flatpak_app_id_parses_app_line(self, monkeypatch, tmp_path):
        info = tmp_path / "flatpak-info"
        info.write_text("[Application]\napp=org.example.App\n")
        monkeypatch.setattr(pu, "is_running_in_flatpak", lambda: True)
        monkeypatch.setattr(c, "FLATPAK_INFO_FILE", str(info))
        assert pu.get_flatpak_app_id() == "org.example.App"


class TestHostCommand:
    def test_host_prefix_none_without_flatpak_spawn(self, monkeypatch):
        monkeypatch.setattr(pu.shutil, "which", lambda name: None)
        assert pu.host_prefix() is None

    def test_host_prefix_present(self, monkeypatch):
        monkeypatch.setattr(pu.shutil, "which", lambda name: "/usr/bin/flatpak-spawn")
        assert pu.host_prefix() == ["/usr/bin/flatpak-spawn", "--host"]

    def test_host_command_unwrapped_without_flatpak_spawn(self, monkeypatch):
        monkeypatch.setattr(pu.shutil, "which", lambda name: None)
        assert pu.host_command(["flatpak", "list"]) == ["flatpak", "list"]

    def test_host_command_wrapped(self, monkeypatch):
        monkeypatch.setattr(pu.shutil, "which", lambda name: "/usr/bin/flatpak-spawn")
        assert pu.host_command(["flatpak", "list"]) == [
            "/usr/bin/flatpak-spawn", "--host", "flatpak", "list",
        ]

    def test_host_command_copies_input(self, monkeypatch):
        monkeypatch.setattr(pu.shutil, "which", lambda name: None)
        original = ["a", "b"]
        result = pu.host_command(original)
        result.append("c")
        assert original == ["a", "b"]


class TestQueryGlxinfo:
    def test_returns_local_output(self, monkeypatch):
        monkeypatch.setattr(pu.subprocess, "check_output",
                            lambda *a, **k: "OpenGL ES 3.2\n")
        assert pu.query_glxinfo("OpenGL ES profile version") == "OpenGL ES 3.2"

    def test_returns_unknown_when_not_in_flatpak(self, monkeypatch):
        def boom(*a, **k):
            raise subprocess.SubprocessError()
        monkeypatch.setattr(pu.subprocess, "check_output", boom)
        assert pu.query_glxinfo("x", running_in_flatpak=False) == "Unknown"

    def test_falls_back_to_host_in_flatpak(self, monkeypatch):
        calls = []

        def fake_check_output(cmd, *a, **k):
            calls.append(cmd)
            if len(calls) == 1:
                raise subprocess.SubprocessError()
            return "OpenGL ES 3.1\n"

        monkeypatch.setattr(pu.subprocess, "check_output", fake_check_output)
        monkeypatch.setattr(pu, "host_prefix",
                            lambda: ["flatpak-spawn", "--host"])
        result = pu.query_glxinfo("x", running_in_flatpak=True)
        assert result == "OpenGL ES 3.1"
        assert calls[1][:2] == ["flatpak-spawn", "--host"]
