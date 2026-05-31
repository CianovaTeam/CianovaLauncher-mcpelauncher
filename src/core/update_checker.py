from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtCore import QUrl
from src import constants as c
from src.utils.logger import logger
import json
import time


class UpdateChecker(QNetworkAccessManager):
    """Async launcher update checker using GitHub Pages version.json."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._check_callback = None

    def check(self, on_result=None, custom_url=None):
        """Fetch version.json from GitHub Pages and compare versions.

        Args:
            on_result: callable(available: bool, latest_version: str, error: str)
            custom_url: optional override URL (used by test window)
        """
        self._check_callback = on_result
        url = QUrl(custom_url or c.UPDATE_CHECK_URL)
        req = QNetworkRequest(url)
        req.setTransferTimeout(10000)
        reply = self.get(req)
        reply.finished.connect(lambda: self._on_reply(reply))

    def _on_reply(self, reply):
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                err = reply.errorString()
                logger.warning(f"Update check network error: {err}")
                self._call_callback(False, "", f"Network error: {err}")
                return

            data = reply.readAll().data().decode("utf-8")
            info = json.loads(data)

            remote_ver = info.get("latest_version", "")
            is_prerelease = info.get("prerelease", False)

            if not remote_ver:
                self._call_callback(False, "", "Response missing 'latest_version' field")
                return

            if is_prerelease:
                self._call_callback(False, remote_ver, f"Version {remote_ver} is a pre-release, skipped")
                return

            def to_tuple(v):
                parts = v.lstrip("v").split(".")
                return tuple(int(x) for x in (parts + ["0", "0"])[:3])

            remote_tuple = to_tuple(remote_ver)
            local_tuple = to_tuple(c.VERSION_LAUNCHER)

            if remote_tuple > local_tuple:
                self._call_callback(True, remote_ver, "")
            else:
                self._call_callback(False, remote_ver, "")

        except Exception as e:
            logger.error(f"Update check failed: {e}")
            self._call_callback(False, "", f"Parse error: {e}")

    def _call_callback(self, *args):
        if self._check_callback:
            self._check_callback(*args)
