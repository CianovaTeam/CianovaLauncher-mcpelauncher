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


_APP_NAME = "CianovaLauncher"
_DETAILS_IDLE = _APP_NAME
_STATE_IDLE = "Browsing launcher"
_DETAILS_PLAYING = _APP_NAME
_STATE_PLAYING_TEMPLATE = "Playing {version}"
_LARGE_IMAGE = "logo"
_LARGE_TEXT = _APP_NAME
_SMALL_IMAGE_PLAYING = "play"
_SMALL_TEXT_PLAYING = "In-Game"


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
        custom_id = self.app.config.get(c.CONFIG_KEY_DISCORD_RPC_CLIENT_ID, "").strip()
        self._client_id = custom_id or c.DISCORD_DEFAULT_CLIENT_ID
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
        self._update_presence(
            details=_DETAILS_IDLE,
            state=_STATE_IDLE,
            start=None,
            large_image=None,
            large_text=None,
            small_image=None,
            small_text=None,
        )

    def set_playing(self, version, start_time):
        self._update_presence(
            details=_DETAILS_PLAYING,
            state=_STATE_PLAYING_TEMPLATE.format(version=version),
            start=int(start_time),
            large_image=_LARGE_IMAGE,
            large_text=_LARGE_TEXT,
            small_image=_SMALL_IMAGE_PLAYING,
            small_text=_SMALL_TEXT_PLAYING,
        )

    def _update_presence(self, details, state, start, large_image, large_text, small_image, small_text):
        with self._lock:
            self._last_presence = (details, state, start, large_image, large_text, small_image, small_text)

    def _find_discord_socket(self):
        """Look for Discord's IPC socket in known locations and symlink to standard path."""
        uid = os.getuid()
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{uid}")
        standard = os.path.join(runtime_dir, "discord-ipc-0")

        candidates = [
            standard,
            os.path.join(runtime_dir, "app", "com.discordapp.Discord", "discord-ipc-0"),
            os.path.join(runtime_dir, "app", "com.vesktop.Vesktop", "discord-ipc-0"),
            os.path.join(runtime_dir, "app", "com.github.TheWisker.WebCord", "discord-ipc-0"),
            os.path.join(runtime_dir, "app", "com.armcord.ArmCord", "discord-ipc-0"),
        ]

        for path in candidates:
            try:
                mode = os.stat(path).st_mode
                if stat.S_ISSOCK(mode):
                    if path == standard:
                        break
                    if os.path.lexists(standard):
                        os.unlink(standard)
                    os.symlink(path, standard)
                    break
            except (OSError, FileNotFoundError):
                continue
        else:
            if os.path.lexists(standard):
                try:
                    if not stat.S_ISSOCK(os.stat(standard).st_mode):
                        os.unlink(standard)
                except OSError:
                    os.unlink(standard)

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
                details, state, start, large_image, large_text, small_image, small_text = presence
                try:
                    kwargs = dict(details=details)
                    if state is not None:
                        kwargs["state"] = state
                    if start is not None:
                        kwargs["start"] = start
                    if large_image is not None:
                        kwargs["large_image"] = large_image
                    if large_text is not None:
                        kwargs["large_text"] = large_text
                    if small_image is not None:
                        kwargs["small_image"] = small_image
                    if small_text is not None:
                        kwargs["small_text"] = small_text
                    self._rpc.update(**kwargs)
                except Exception as e:
                    logger.debug(f"Discord RPC update failed: {e}")
                    self._connected = False
                    try:
                        self._rpc.close()
                    except Exception:
                        pass
                    self._rpc = None

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
