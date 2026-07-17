import os
import sys
import platform
import re
import subprocess
import logging
from datetime import datetime
from src import constants as c

class Logger:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def init(self, log_dir=None):
        if self._initialized:
            return
        
        if log_dir is None:
            # Try standard location
            log_dir = os.path.join(os.path.expanduser("~"), ".local/share/mcpelauncher/logs")
            # If we are in Flatpak, this might be trapped in sandbox or mapped. 
            # Better to use a relative path to the app data if possible.
        
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception:
                log_dir = "." # Fallback

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        log_file = os.path.join(log_dir, f"cianovalauncher-{timestamp}.log")
        
        self.logger = logging.getLogger("CianovaLauncher")
        self.logger.setLevel(logging.DEBUG)
        
        # File handler (UTF-8 to support all chars)
        try:
            fh = logging.FileHandler(log_file, encoding='utf-8')
            fh.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
        except Exception as e:
            print(f"Error creating log file: {e}")
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter_ch = logging.Formatter('%(levelname)s: %(message)s')
        ch.setFormatter(formatter_ch)
        self.logger.addHandler(ch)
        
        self._log_file = log_file
        self._initialized = True
        self.log_system_info()

    def log_system_info(self):
        self.info(f"=== CIANOVALAUNCHER v{c.VERSION_LAUNCHER} SESSION START ===")
        self.info(f"OS: {platform.system()} {platform.release()} ({platform.version()})")
        
        # Distro info if on Linux
        if platform.system() == "Linux":
            try:
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            self.info(f"Distro: {line.split('=')[1].strip().strip('\"')}")
            except Exception:
                self.debug("Could not read distro info from /etc/os-release", exc_info=True)

        self.info(f"Architecture: {platform.machine()}")
        
        cpu = "Unknown"
        ram = "Unknown"
        cpu_flags = []
        try:
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo") as f:
                    content = f.read()
                    m_model = re.search(r"model name\s*:\s*(.*)", content)
                    if m_model: cpu = m_model.group(1).strip()
                    m_flags = re.search(r"flags\s*:\s*(.*)", content)
                    if m_flags: cpu_flags = m_flags.group(1).split()
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo") as f:
                    m_mem = re.search(r"MemTotal:\s*(\d+)\s*kB", f.read())
                    if m_mem: ram = f"{int(m_mem.group(1))/1024/1024:.2f} GB"
        except Exception:
            self.debug("Could not read CPU/RAM info from /proc", exc_info=True)
        
        self.info(f"CPU: {cpu}")
        self.info(f"RAM: {ram}")
        
        # Filter interesting instructions
        important_flags = ["sse", "sse2", "ssse3", "sse4_1", "sse4_2", "popcnt", "avx", "avx2", "aes"]
        found_flags = [f.upper() for f in cpu_flags if f.lower() in important_flags]
        self.info(f"CPU Instructions: {', '.join(found_flags)}")

        # Motherboard Info
        board_vendor = "Unknown"
        board_name = "Unknown"
        try:
            if os.path.exists("/sys/class/dmi/id/board_vendor"):
                with open("/sys/class/dmi/id/board_vendor") as f: board_vendor = f.read().strip()
            if os.path.exists("/sys/class/dmi/id/board_name"):
                with open("/sys/class/dmi/id/board_name") as f: board_name = f.read().strip()
        except Exception:
            self.debug("Could not read motherboard info from /sys/class/dmi", exc_info=True)
        self.info(f"Motherboard: {board_vendor} {board_name}")

        # OpenGL detection
        gl_ver = "Unknown"
        gles_ver = "Unknown"
        try:
            # Full OpenGL
            cmd_gl = ["sh", "-c", "glxinfo | grep 'OpenGL version string'"]
            gl_ver = subprocess.check_output(cmd_gl, text=True, stderr=subprocess.DEVNULL).strip()
            # OpenGL ES
            cmd_gles = ["sh", "-c", "glxinfo | grep 'OpenGL ES profile version'"]
            gles_ver = subprocess.check_output(cmd_gles, text=True, stderr=subprocess.DEVNULL).strip()
        except Exception:
            # Try flatpak-spawn if we are in sandbox
            if os.path.exists("/.flatpak-info"):
                try:
                    cmd_gl = ["flatpak-spawn", "--host", "sh", "-c", "glxinfo | grep 'OpenGL version string'"]
                    gl_ver = subprocess.check_output(cmd_gl, text=True, stderr=subprocess.DEVNULL).strip()
                    cmd_gles = ["flatpak-spawn", "--host", "sh", "-c", "glxinfo | grep 'OpenGL ES profile version'"]
                    gles_ver = subprocess.check_output(cmd_gles, text=True, stderr=subprocess.DEVNULL).strip()
                except Exception:
                    self.debug("glxinfo via flatpak-spawn failed", exc_info=True)
        
        self.info(f"GPU OpenGL: {gl_ver}")
        self.info(f"GPU OpenGL ES: {gles_ver}")
        self.info("==========================================")

    @property
    def log_file(self):
        return getattr(self, '_log_file', None)

    def open_game_output(self, mode="a"):
        if self._log_file:
            return open(self._log_file, mode, encoding="utf-8", errors="replace")
        return None

    def info(self, msg, *args, **kwargs): self.logger.info(msg, *args, **kwargs)
    def error(self, msg, *args, **kwargs): self.logger.error(msg, *args, **kwargs)
    def warning(self, msg, *args, **kwargs): self.logger.warning(msg, *args, **kwargs)
    def debug(self, msg, *args, **kwargs): self.logger.debug(msg, *args, **kwargs)

# Global instance
logger = Logger()
