"""Unit tests for src.utils.colors — pure color-string helpers."""
import pytest

from src.utils.colors import hex_to_rgba, adjust_color


class TestHexToRgba:
    def test_six_digit_hex(self):
        assert hex_to_rgba("#ff0000", 1.0) == "rgba(255, 0, 0, 255)"

    def test_opacity_half(self):
        assert hex_to_rgba("#000000", 0.5) == "rgba(0, 0, 0, 127)"

    def test_three_digit_shorthand_expands(self):
        # #f00 -> #ff0000
        assert hex_to_rgba("#f00", 1.0) == "rgba(255, 0, 0, 255)"

    def test_zero_opacity(self):
        assert hex_to_rgba("#123456", 0.0) == "rgba(18, 52, 86, 0)"

    def test_non_hex_returned_unchanged(self):
        assert hex_to_rgba("red", 1.0) == "red"

    def test_empty_returned_unchanged(self):
        assert hex_to_rgba("", 1.0) == ""

    def test_none_returned_unchanged(self):
        assert hex_to_rgba(None, 1.0) is None


class TestAdjustColor:
    def test_lighten(self):
        assert adjust_color("#000000", 10) == "#0a0a0a"

    def test_darken(self):
        assert adjust_color("#ffffff", -1) == "#fefefe"

    def test_clamps_upper_bound(self):
        # Adding beyond 255 clamps to ff
        assert adjust_color("#ffffff", 50) == "#ffffff"

    def test_clamps_lower_bound(self):
        # Subtracting below 0 clamps to 00
        assert adjust_color("#000000", -50) == "#000000"

    def test_three_digit_shorthand(self):
        assert adjust_color("#fff", -255) == "#000000"

    def test_no_change_amount_zero(self):
        assert adjust_color("#1a2b3c", 0) == "#1a2b3c"

    def test_non_hex_returned_unchanged(self):
        assert adjust_color("rgb(0,0,0)", 10) == "rgb(0,0,0)"

    def test_none_returned_unchanged(self):
        assert adjust_color(None, 10) is None
