"""Unit tests for color helpers — no Qt dependency."""
from src.utils.colors import hex_to_rgba, adjust_color, _hex_to_rgb


class TestHexToRgb:
    def test_full_form(self):
        assert _hex_to_rgb("#102030") == (16, 32, 48)

    def test_short_form_expands(self):
        assert _hex_to_rgb("#abc") == (0xaa, 0xbb, 0xcc)


class TestHexToRgba:
    def test_basic(self):
        assert hex_to_rgba("#ffffff", 0.5) == "rgba(255, 255, 255, 127)"

    def test_short_form(self):
        assert hex_to_rgba("#fff", 1.0) == "rgba(255, 255, 255, 255)"

    def test_passthrough_non_hex(self):
        assert hex_to_rgba("red", 0.5) == "red"
        assert hex_to_rgba("", 0.5) == ""


class TestAdjustColor:
    def test_lighten(self):
        assert adjust_color("#102030", 16) == "#203040"

    def test_clamped_at_max(self):
        assert adjust_color("#ffffff", 50) == "#ffffff"

    def test_clamped_at_min(self):
        assert adjust_color("#000000", -50) == "#000000"

    def test_passthrough_non_hex(self):
        assert adjust_color("blue", 10) == "blue"
