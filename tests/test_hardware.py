"""Unit tests for src.core.hardware — pure detection/compat logic."""
from types import SimpleNamespace
from unittest import mock

import pytest

from src.core import hardware as hw
from src import constants as c


X86_FLAGS = ["fpu", "ssse3", "sse4_1", "sse4_2", "popcnt"]


def incompat():
    """Evaluated at call time so it matches whichever translator is active."""
    return c.t("UI_INCOMPATIBLE_TEXT")


class TestParseEsMajorMinor:
    def test_parses_version(self):
        assert hw._parse_es_major_minor("OpenGL ES 3.2 Mesa 23.0") == (3, 2)

    def test_parses_es_30(self):
        assert hw._parse_es_major_minor("OpenGL ES 3.0") == (3, 0)

    def test_unknown_returns_none(self):
        assert hw._parse_es_major_minor("Unknown") is None

    def test_no_match_returns_none(self):
        assert hw._parse_es_major_minor("some random text") is None


class TestComputeCompatibilityX8664:
    def test_full_range_es32(self):
        assert hw._compute_compatibility("x86_64", X86_FLAGS, "OpenGL ES 3.2") == "1.13.0 - 1.26.0+"

    def test_es31(self):
        assert hw._compute_compatibility("x86_64", X86_FLAGS, "OpenGL ES 3.1") == "1.13.0 - 1.21.132"

    def test_es30(self):
        assert hw._compute_compatibility("x86_64", X86_FLAGS, "OpenGL ES 3.0") == "1.13.0 - 1.21.124"

    def test_es20(self):
        assert hw._compute_compatibility("x86_64", X86_FLAGS, "OpenGL ES 2.0") == "1.13.0 - 1.20.20"

    def test_missing_sse_incompatible(self):
        assert hw._compute_compatibility("x86_64", ["fpu"], "OpenGL ES 3.2") == incompat()

    def test_unknown_gl_defaults_to_es30(self):
        # Unknown GL -> assume ES 3.0 range
        assert hw._compute_compatibility("x86_64", X86_FLAGS, "Unknown") == "1.13.0 - 1.21.124"


class TestComputeCompatibilityX86:
    def test_ssse3_present(self):
        assert hw._compute_compatibility("i686", ["ssse3"], "OpenGL ES 3.2") == "1.13.0 - 1.26.0+"

    def test_ssse3_missing_incompatible(self):
        assert hw._compute_compatibility("i686", ["fpu"], "OpenGL ES 3.2") == incompat()


class TestComputeCompatibilityArm:
    def test_aarch64_neon(self):
        assert hw._compute_compatibility("aarch64", ["neon"], "OpenGL ES 3.2") == "1.13.0 - 1.26.0+"

    def test_armv7l_capped(self):
        assert hw._compute_compatibility("armv7l", ["neon"], "OpenGL ES 3.2") == "1.13.0 - 1.18.10"

    def test_arm_missing_neon_incompatible(self):
        assert hw._compute_compatibility("aarch64", [], "OpenGL ES 3.2") == incompat()


class TestComputeCompatibilityUnknownArch:
    def test_unknown_arch_incompatible(self):
        assert hw._compute_compatibility("riscv64", [], "OpenGL ES 3.2") == incompat()


class TestDetectCpuFlags:
    def test_reads_flags_from_cpuinfo(self, monkeypatch):
        cpuinfo = "processor : 0\nflags : fpu vme ssse3 sse4_1\n"
        monkeypatch.setattr(hw.os.path, "exists", lambda p: p == "/proc/cpuinfo")
        monkeypatch.setattr(hw.platform, "machine", lambda: "x86_64")
        with mock.patch("builtins.open", mock.mock_open(read_data=cpuinfo)):
            arch, flags = hw._detect_cpu_flags()
        assert arch == "x86_64"
        assert "ssse3" in flags and "sse4_1" in flags

    def test_reads_arm_features(self, monkeypatch):
        cpuinfo = "processor : 0\nFeatures : fp asimd neon\n"
        monkeypatch.setattr(hw.os.path, "exists", lambda p: p == "/proc/cpuinfo")
        monkeypatch.setattr(hw.platform, "machine", lambda: "aarch64")
        with mock.patch("builtins.open", mock.mock_open(read_data=cpuinfo)):
            arch, flags = hw._detect_cpu_flags()
        assert arch == "aarch64"
        assert "neon" in flags

    def test_no_cpuinfo_returns_empty_flags(self, monkeypatch):
        monkeypatch.setattr(hw.os.path, "exists", lambda p: False)
        monkeypatch.setattr(hw.platform, "machine", lambda: "x86_64")
        arch, flags = hw._detect_cpu_flags()
        assert arch == "x86_64"
        assert flags == []


class TestGetCompatibilityRange:
    def test_combines_detectors(self, monkeypatch):
        monkeypatch.setattr(hw, "_detect_cpu_flags", lambda: ("x86_64", X86_FLAGS))
        monkeypatch.setattr(hw, "_detect_gl_version", lambda app: "OpenGL ES 3.2")
        app = SimpleNamespace(running_in_flatpak=False)
        assert hw.get_compatibility_range(app) == "1.13.0 - 1.26.0+"
