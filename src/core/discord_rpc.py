import os
import stat
import time
import threading
from src import constants as c
from src.utils.logger import logger

try:
    from pypresence import Presence
    _HAS_PYPRESENCE = True
except ImportError:
    _HAS_PYPRESENCE = False


_DETAILS_IDLE = "Browsing launcher"
_STATE_TEMPLATE = "{version}"


class DiscordRPC:
    def __init__(self, app):
        self.app = app
        self._thread = None
        self._running = False
        self._rpc = None
        self._lock = threading.Lock()
        self._connected = False
        self._last_presence = None
        self._client_id = None

    @property
    def available(self):
        return _HAS_PYPRESENCE

    def start(self):
        if not self.available:
            return
        if self._running:
            return
        self._client_id = c.DISCORD_DEFAULT_CLIENT_ID
        if not self._client_id:
            logger.debug("Discord RPC: no DISCORD_DEFAULT_CLIENT_ID configured in constants.py")
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        with self._lock:
            if self._rpc:
                try:
                    self._rpc.close()
                except Exception:
                    pass
                self._rpc = None
                self._connected = False
        self._thread = None

    def set_idle(self):
        self._update_presence(details=_DETAILS_IDLE, state=None, start=None)

    def set_playing(self, version, start_time):
        self._update_presence(
            details=_STATE_TEMPLATE.format(version=version),
            state=None,
            start=int(start_time),
        )

    def _update_presence(self, details, state, start):
        with self._lock:
            self._last_presence = (details, state, start)

    def _find_discord_socket(self):
        """Look for Discord's IPC socket in known locations and symlink to standard path."""
        uid = os.getuid()
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{uid}")
        standard = os.path.join(runtime_dir, "discord-ipc-0")

        candidates = [
            standard,
            os.path.join(runtime_dir, "app", "com.discordapp.Discord", "discord-ipc-0"),
            os.path.join(runtime_dir, "app", "com.vesktop.Vesktop", "discord-ipc-0"),
        ]

        for path in candidates:
            try:
                if stat.S_ISSOCK(os.stat(path).st_mode) and path != standard:
                    if os.path.lexists(standard):
                        os.unlink(standard)
                    os.symlink(path, standard)
                    break
            except (OSError, FileNotFoundError):
                continue

    def _connect(self):
        try:
            self._find_discord_socket()
            self._rpc = Presence(self._client_id)
            self._rpc.connect()
            self._connected = True
            logger.info("Discord RPC connected")
            return True
        except Exception as e:
            logger.debug(f"Discord RPC connect failed: {e}")
            self._connected = False
            return False

    def _run(self):
        retry_interval = 30
        last_retry = 0
        sent_idle = False

        while self._running:
            now = time.time()

            if not self._connected:
                if now - last_retry >= retry_interval:
                    last_retry = now
                    self._connect()
                time.sleep(2)
                continue

            with self._lock:
                presence = self._last_presence

            if presence:
                details, state, start = presence
                try:
                    self._rpc.update(
                        details=details,
                        state=state,
                        start=start,
                    )
                    sent_idle = False
                except Exception as e:
                    logger.debug(f"Discord RPC update failed: {e}")
                    self._connected = False
                    try:
                        self._rpc.close()
                    except Exception:
                        pass
                    self._rpc = None
            elif not sent_idle:
                sent_idle = True

            time.sleep(15)

        with self._lock:
            if self._rpc:
                try:
                    self._rpc.clear()
                    self._rpc.close()
                except Exception:
                    pass
                self._rpc = None
                self._connected = False
