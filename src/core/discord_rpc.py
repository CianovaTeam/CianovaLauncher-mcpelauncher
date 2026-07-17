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
    """Discord Rich Presence controller.

    Thread model: the pypresence ``Presence`` object owns an asyncio event loop
    bound to the worker thread that created it, so it is NOT safe to touch from
    other threads.  All ``_rpc`` access (connect/update/clear/close) therefore
    happens exclusively inside ``_run``.  Other threads only publish the desired
    presence via ``set_idle``/``set_playing`` (guarded by ``_lock``) and wake the
    worker through ``_wake``.
    """

    def __init__(self, app):
        self.app = app
        self._thread = None
        self._running = False
        self._rpc = None
        self._lock = threading.Lock()
        self._connected = False
        self._last_presence = None
        self._client_id = None
        self._wake = threading.Event()

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
        self._wake.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Signal the worker to disconnect and wait for it to clean up.

        Cleanup (clear/close) is performed by the worker thread itself so that
        the pypresence object is never used from a foreign thread.
        """
        if not self._running:
            return
        self._running = False
        self._wake.set()
        t = self._thread
        self._thread = None
        if t and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=5)

    def _build_presence_kwargs(self, details, state, start, large_image, large_text, small_image, small_text):
        kwargs = dict(details=details)
        if state is not None: kwargs["state"] = state
        if start is not None: kwargs["start"] = start
        if large_image is not None: kwargs["large_image"] = large_image
        if large_text is not None: kwargs["large_text"] = large_text
        if small_image is not None: kwargs["small_image"] = small_image
        if small_text is not None: kwargs["small_text"] = small_text
        return kwargs

    def set_idle(self):
        kwargs = self._build_presence_kwargs(
            details=_DETAILS_IDLE, state=_STATE_IDLE, start=None,
            large_image=None, large_text=None, small_image=None, small_text=None,
        )
        self._queue_presence(kwargs)

    def set_playing(self, version, start_time):
        kwargs = self._build_presence_kwargs(
            details=_DETAILS_PLAYING, state=_STATE_PLAYING_TEMPLATE.format(version=version),
            start=int(start_time), large_image=_LARGE_IMAGE, large_text=_LARGE_TEXT,
            small_image=_SMALL_IMAGE_PLAYING, small_text=_SMALL_TEXT_PLAYING,
        )
        self._queue_presence(kwargs)

    def _queue_presence(self, kwargs):
        """Publish the desired presence for the worker thread to send."""
        with self._lock:
            self._last_presence = dict(kwargs)
        self._wake.set()

    def _find_discord_socket(self):
        """Look for Discord's IPC socket in known locations and symlink to standard path."""
        uid = os.getuid()
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{uid}")
        standard = os.path.join(runtime_dir, "discord-ipc-0")

        candidates = [
            standard,
            os.path.join(runtime_dir, "app", "com.discordapp.Discord", "discord-ipc-0"),
            os.path.join(runtime_dir, "app", "com.discordapp.DiscordCanary", "discord-ipc-0"),
            os.path.join(runtime_dir, "app", "com.discordapp.DiscordPTB", "discord-ipc-0"),
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
        """Worker loop: owns the pypresence object exclusively.

        Wakes on demand via ``_wake`` (when a new presence is published or on
        stop) and otherwise re-asserts presence periodically. Only sends when
        the desired presence actually changed to avoid redundant IPC traffic.
        """
        retry_interval = 30
        last_retry = 0.0
        last_sent = None

        while self._running:
            if not self._connected:
                now = time.time()
                if now - last_retry >= retry_interval:
                    last_retry = now
                    if self._connect():
                        last_sent = None  # force a resend after reconnect
                self._wake.wait(timeout=2)
                self._wake.clear()
                continue

            with self._lock:
                presence = self._last_presence

            if presence and presence != last_sent:
                try:
                    self._rpc.update(**presence)
                    last_sent = presence
                except Exception as e:
                    logger.debug(f"Discord RPC update failed: {e}")
                    self._connected = False
                    last_sent = None
                    try:
                        self._rpc.close()
                    except Exception:
                        pass
                    self._rpc = None
                    continue

            self._wake.wait(timeout=15)
            self._wake.clear()

        if self._rpc:
            try:
                self._rpc.clear()
                self._rpc.close()
            except Exception:
                pass
            self._rpc = None
            self._connected = False
