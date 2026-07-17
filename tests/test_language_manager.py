"""Unit tests for src.core.language_manager — translation loading/lookup."""
import pytest

from src.core import language_manager as lm
from src import constants as c


class TestProcessValue:
    def test_replaces_placeholder_in_string(self):
        out = lm._process_value("Hello {APP_NAME}", {"APP_NAME": "Cianova"})
        assert out == "Hello Cianova"

    def test_leaves_string_without_placeholder(self):
        assert lm._process_value("plain", {"APP_NAME": "Cianova"}) == "plain"

    def test_processes_nested_dict(self):
        out = lm._process_value({"a": "{X}"}, {"X": "1"})
        assert out == {"a": "1"}

    def test_processes_list(self):
        out = lm._process_value(["{X}", "y"], {"X": "1"})
        assert out == ["1", "y"]

    def test_non_string_returned_as_is(self):
        assert lm._process_value(42, {"X": "1"}) == 42


class TestGetAvailableLanguages:
    def test_contains_expected_codes(self):
        langs = lm.get_available_languages()
        for code in ("en", "es", "fr", "de", "it", "pt", "ca"):
            assert code in langs
        assert langs["en"] == "English"


class TestLoadLanguage:
    def test_load_missing_returns_false(self):
        assert lm.load_language("zz_nonexistent") is False

    def test_load_english_registers_translator(self):
        assert lm.load_language("en") is True
        # c.t is now the language_manager translator
        assert callable(c.t)

    def test_translate_known_key_after_load(self):
        lm.load_language("en")
        # UI_BUTTON_CLOSE exists in the en translations / constants
        val = c.t("UI_BUTTON_CLOSE")
        assert isinstance(val, str)
        assert val and not val.startswith("!")

    def test_translate_unknown_key_returns_marker(self):
        lm.load_language("en")
        assert c.t("THIS_KEY_DEFINITELY_DOES_NOT_EXIST") == "!THIS_KEY_DEFINITELY_DOES_NOT_EXIST!"


class TestTranslateFormatting:
    def test_translate_formats_kwargs(self):
        lm._translations.clear()
        lm._translations["GREETING"] = "Hi {name}"
        assert lm._translate("GREETING", name="Bob") == "Hi Bob"

    def test_translate_ignores_missing_kwargs(self):
        lm._translations.clear()
        lm._translations["GREETING"] = "Hi {name}"
        # Missing kwarg -> KeyError swallowed, original returned
        assert lm._translate("GREETING") == "Hi {name}"
