"""Unit tests for src.core.update_checker — version comparison / reply parsing.

These exercise UpdateChecker._on_reply with a stub reply object, avoiding any
real network access.
"""
import json

import pytest

from PySide6.QtNetwork import QNetworkReply

from src.core.update_checker import UpdateChecker
from src import constants as c


class FakeData:
    def __init__(self, payload):
        self._payload = payload

    def data(self):
        return self._payload.encode("utf-8")


class FakeReply:
    """Minimal stand-in for QNetworkReply used by UpdateChecker._on_reply."""

    def __init__(self, payload="", error=QNetworkReply.NetworkError.NoError,
                 error_string="boom"):
        self._payload = payload
        self._error = error
        self._error_string = error_string

    def error(self):
        return self._error

    def errorString(self):
        return self._error_string

    def readAll(self):
        return FakeData(self._payload)


@pytest.fixture
def checker(qapp):
    return UpdateChecker()


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    return app


def _run(checker, reply):
    results = {}

    def cb(available, latest, error):
        results["available"] = available
        results["latest"] = latest
        results["error"] = error

    checker._check_callback = cb
    checker._on_reply(reply)
    return results


class TestOnReply:
    def test_network_error_reports_failure(self, checker):
        reply = FakeReply(error=QNetworkReply.NetworkError.HostNotFoundError,
                          error_string="host not found")
        res = _run(checker, reply)
        assert res["available"] is False
        assert "host not found" in res["error"]

    def test_newer_version_available(self, checker):
        payload = json.dumps({"latest_version": "999.0.0"})
        res = _run(checker, FakeReply(payload=payload))
        assert res["available"] is True
        assert res["latest"] == "999.0.0"
        assert res["error"] == ""

    def test_same_version_not_available(self, checker):
        payload = json.dumps({"latest_version": c.VERSION_LAUNCHER})
        res = _run(checker, FakeReply(payload=payload))
        assert res["available"] is False

    def test_older_version_not_available(self, checker):
        payload = json.dumps({"latest_version": "0.0.1"})
        res = _run(checker, FakeReply(payload=payload))
        assert res["available"] is False

    def test_version_with_v_prefix(self, checker):
        payload = json.dumps({"latest_version": "v999.0.0"})
        res = _run(checker, FakeReply(payload=payload))
        assert res["available"] is True

    def test_prerelease_skipped(self, checker):
        payload = json.dumps({"latest_version": "999.0.0", "prerelease": True})
        res = _run(checker, FakeReply(payload=payload))
        assert res["available"] is False
        assert "pre-release" in res["error"]

    def test_missing_latest_version_field(self, checker):
        payload = json.dumps({"foo": "bar"})
        res = _run(checker, FakeReply(payload=payload))
        assert res["available"] is False
        assert "latest_version" in res["error"]

    def test_invalid_json_reports_parse_error(self, checker):
        res = _run(checker, FakeReply(payload="{not json"))
        assert res["available"] is False
        assert "Parse error" in res["error"]


class TestCallback:
    def test_no_callback_is_noop(self, checker):
        checker._check_callback = None
        # Should not raise
        checker._call_callback(True, "1.0", "")
