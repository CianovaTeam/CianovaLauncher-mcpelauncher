import os
import shutil
import subprocess
import threading
import tempfile
import time
import re
import glob
import urllib.request
import urllib.parse
import urllib.error
from PySide6.QtCore import QTimer, QProcess, QProcessEnvironment, QObject, Signal
from src import constants as c
from src.gui import custom_dialogs as messagebox
from src.core.version_ops import resolve_version
from src.utils.logger import logger


class InstallSignals(QObject):
    """Qt signals for reporting Google download/install progress and completion."""
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(bool, str)


def get_signin_workdir(app):
    """
    Root directory for Google Play session files (playdl.conf, device.conf).
    Uses active_path inside Flatpak sandbox or CWD as fallback.
    """
    d = app.active_path if app.active_path else os.getcwd()
    try:
        os.makedirs(d, exist_ok=True)
    except Exception as e:
        logger.error(f"Could not create signin workdir: {e}")
    return d


def check_google_session(app):
    """
    Checks if there is an active Google Play session.
    Looks for playdl.conf / token_cache.conf in the root data path
    (active_path or CWD), plus legacy paths for backward compatibility.
    Falls back to gplayver binary verification if no file is found.
    """
    workdir = get_signin_workdir(app)
    search_paths = [
        workdir,
        os.getcwd(),
        os.path.join(app.home, ".config", "mcpelauncher"),
    ]

    seen = set()
    for p in search_paths:
        if not p or p in seen:
            continue
        seen.add(p)
        for fname in ("playdl.conf", "token_cache.conf"):
            full = os.path.join(p, fname)
            try:
                if os.path.exists(full) and os.path.getsize(full) > 0:
                    return True
            except OSError:
                continue

    # Fallback: verify via gplayver binary
    try:
        bin_path = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_GPLAYVER, "gplayver")
        cmd = [bin_path, "-nv", "-a", "com.mojang.minecraftpe", "--accept-tos"]
        gv_env = os.environ.copy()
        if app.running_in_flatpak:
            gv_env.pop("LD_LIBRARY_PATH", None)
        res = subprocess.run(cmd, capture_output=True, timeout=3, env=gv_env)
        return res.returncode == 0
    except Exception:
        pass

    return False


GOOGLE_AUTH_URL = "https://android.clients.google.com/auth"


def _exchange_access_token(email, access_token):
    """
    Convierte el access_token (oauth_token de un solo uso) entregado por
    playdl-signin-ui-qt en un master Token reutilizable via /auth con
    ACCESS_TOKEN=1. Equivale a playapi::login_api::perform_with_access_token.
    Devuelve dict parseado de la respuesta (al menos 'Token') o None.
    """
    body = {
        "accountType": "HOSTED_OR_GOOGLE",
        "Token": access_token,
        "ACCESS_TOKEN": "1",
        "Email": email or "",
        "add_account": "1",
        "has_permission": "1",
        "service": "ac2dm",
        "source": "android",
        "app": "com.google.android.gsf",
        "device_country": "us",
        "lang": "en_US",
        "sdk_version": "36",
        "client_sig": "38918a453d07199354f8b19af05ec6562ced5788",
        "system_partition": "1",
        "droidguard_results": "null",
    }
    if not email:
        body.pop("Email", None)
        body.pop("add_account", None)

    data = urllib.parse.urlencode(body).encode("utf-8")
    req = urllib.request.Request(
        GOOGLE_AUTH_URL,
        data=data,
        headers={
            "User-Agent": "GoogleAuth/1.4 (desktop DSKTOP); gzip",
            "Content-Type": "application/x-www-form-urlencoded",
            "app": "com.google.android.gsf",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        try:
            text = e.read().decode("utf-8", errors="replace")
        except Exception:
            text = ""
        logger.error(f"OAuth exchange HTTP {e.code}: {text[:300]}")
    except Exception as e:
        logger.error(f"OAuth exchange request failed: {e}")
        return None

    parsed = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            parsed[k.strip()] = v.strip()

    if "Error" in parsed:
        logger.error(f"OAuth exchange error: {parsed.get('Error')} (full: {parsed})")
        return None
    if "Token" not in parsed:
        logger.error(f"OAuth exchange: no Token in response: {parsed}")
        return None
    return parsed


def _parse_signin_output(text):
    """
    Extrae user_email / user_id / user_token de la salida stdout del binario
    playdl-signin-ui-qt. El binario imprime líneas con formato 'clave = valor'.
    Devuelve dict con las claves encontradas (token, id, email).
    """
    fields = {}
    for line in text.splitlines():
        for key in ("user_token", "user_id", "user_email"):
            prefix = key + " = "
            if line.startswith(prefix):
                fields[key] = line[len(prefix):].strip()
    return fields


def _write_playdl_conf(workdir, fields):
    """
    Escribe playdl.conf en workdir con los campos obtenidos.
    Formato compatible con playapi::file_login_cache (clave = valor).
    Devuelve True si se escribió un token no vacío.
    """
    token = fields.get("user_token", "").strip()
    if not token:
        return False
    conf_path = os.path.join(workdir, "playdl.conf")
    lines = []
    for key in ("user_email", "user_id", "user_token"):
        val = fields.get(key, "").strip()
        if val:
            lines.append(f"{key} = {val}")
    try:
        with open(conf_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        os.chmod(conf_path, 0o600)
        return True
    except Exception as e:
        logger.error(f"Error escribiendo playdl.conf: {e}")
        return False


def launch_google_login(app, on_finished=None):
    """
    Lanza playdl-signin-ui-qt como QProcess capturando stdout.
    - Fija cwd al workdir compartido.
    - Al terminar, parsea stdout (user_email/user_id/user_token) y escribe
      playdl.conf en el workdir para que gplaydl lo consuma.
    - Invoca on_finished(exit_code) si se proporciona.
    Devuelve el QProcess (None si falla el lanzamiento).
    """
    bin_path = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_SIGNIN_UI, "playdl-signin-ui-qt")
    if not bin_path:
        logger.error("launch_google_login: signin_ui binary path is empty")
        if on_finished:
            on_finished(-1)
        return None

    if not os.path.isfile(bin_path) and not shutil.which(bin_path):
        logger.error("launch_google_login: binary not found: %s", bin_path)
        try:
            messagebox.showerror(app, c.t("UI_ERROR_TITLE"),
                                 c.t("UI_GOOGLE_SIGNIN_LAUNCH_FAILED", bin_path=bin_path))
        except Exception:
            pass
        if on_finished:
            on_finished(-1)
        return None

    workdir = get_signin_workdir(app)
    logger.debug("launch_google_login: bin=%s workdir=%s flatpak=%s", bin_path, workdir, app.running_in_flatpak)

    proc = QProcess(app)
    proc.setWorkingDirectory(workdir)
    proc.setProcessChannelMode(QProcess.SeparateChannels)

    # Run inside the sandbox — playdl-signin-ui-qt has X11/Wayland access
    # via finish-args and lives at /app/bin/ inside the Flatpak.
    proc.setProgram(bin_path)

    if app.running_in_flatpak:
        # Clear LD_LIBRARY_PATH so the linker does NOT see the PyInstaller
        # bundle at /app/lib/cianova (which bundles an older Qt6). The
        # signin binary must resolve Qt6 exclusively from the KDE runtime
        # at /usr/lib/x86_64-linux-gnu/ where 6.10.3 lives.
        env = QProcessEnvironment.systemEnvironment()
        env.remove("LD_LIBRARY_PATH")
        # Clear QT_STYLE_OVERRIDE — kvantum is not available inside the sandbox
        # and can cause crashes in the Qt style resolution on some systems.
        env.remove("QT_STYLE_OVERRIDE")
        # Ensure QT_PLUGIN_PATH includes the KDE runtime's plugin directory
        # (/usr/lib/plugins). The flatpak runtime sets QT_PLUGIN_PATH to
        # /app/lib/plugins:/usr/share/runtime/lib/plugins by default, which
        # does NOT include /usr/lib/plugins — where the xcb/wayland platform
        # plugins live. Without it, playdl-signin-ui-qt fails with
        # "Could not find the Qt platform plugin".
        pp = env.value("QT_PLUGIN_PATH", "")
        if "/usr/lib/plugins" not in pp:
            env.insert("QT_PLUGIN_PATH", (pp + ":" if pp else "") + "/usr/lib/plugins")
        proc.setProcessEnvironment(env)

    state = {"stdout": b"", "stderr": b""}

    def _drain():
        try:
            data = bytes(proc.readAllStandardOutput())
            if data:
                state["stdout"] += data
        except Exception as e:
            logger.error(f"Signin stdout read error: {e}")
        try:
            data = bytes(proc.readAllStandardError())
            if data:
                state["stderr"] += data
        except Exception as e:
            logger.error(f"Signin stderr read error: {e}")

    proc.readyReadStandardOutput.connect(_drain)
    proc.readyReadStandardError.connect(_drain)

    def _on_done(code, _status):
        _drain()
        try:
            text = state["stdout"].decode("utf-8", errors="replace")
        except Exception:
            text = ""
        try:
            err_text = state["stderr"].decode("utf-8", errors="replace")
        except Exception:
            err_text = ""
        fields = _parse_signin_output(text)
        logger.debug("signin-ui finished code=%s stdout_len=%d stderr_len=%d fields=%s",
            code, len(text), len(err_text),
            {k: (len(v) if v else 0) for k, v in fields.items()})
        if err_text.strip():
            logger.debug("signin-ui stderr:\n%s", err_text.strip())

        access_token = fields.get("user_token", "").strip()
        email = fields.get("user_email", "").strip()
        wrote = False
        if access_token:
            logger.debug("exchanging access_token (len=%d) email=%s", len(access_token), email)
            exchanged = _exchange_access_token(email, access_token)
            logger.debug("exchange result: %s", "OK" if exchanged else "FAIL")
            if exchanged:
                master_fields = {
                    "user_email": exchanged.get("Email") or email,
                    "user_id": fields.get("user_id", ""),
                    "user_token": exchanged["Token"],
                }
                wrote = _write_playdl_conf(workdir, master_fields)
                logger.debug("playdl.conf written=%s path=%s", wrote, os.path.join(workdir, "playdl.conf"))
            else:
                try:
                    messagebox.showerror(app, c.t("UI_ERROR_TITLE"), c.t("UI_GOOGLE_TOKEN_EXCHANGE_FAILED"))
                except Exception:
                    pass

        if not wrote and code == 0 and not access_token:
            try:
                messagebox.showwarning(app, c.t("UI_ERROR_TITLE"), c.t("UI_GOOGLE_SIGNIN_NO_TOKEN"))
            except Exception:
                pass

        if not wrote and code != 0 and not access_token:
            # Binary exited with error — show the exit code and stderr
            tail = err_text.strip()[-300:] if err_text.strip() else "(no stderr output)"
            msg = c.t("UI_GOOGLE_SIGNIN_LAUNCH_FAILED", bin_path=bin_path)
            msg += f"\n\nExit code: {code}\n\n{tail}"
            try:
                messagebox.showerror(app, c.t("UI_ERROR_TITLE"), msg)
            except Exception:
                logger.error(f"Signin exit code={code} stderr={err_text}")

        if on_finished is not None:
            on_finished(code)

    proc.finished.connect(_on_done)

    def _on_error(err):
        try:
            messagebox.showerror(app, c.t("UI_ERROR_TITLE"), c.t("UI_GOOGLE_LOGIN_LAUNCH_ERROR", error=err))
        except Exception:
            logger.error(f"Signin launch error: {err}")

    proc.errorOccurred.connect(_on_error)
    app._signin_proc = proc
    proc.start()
    if not proc.waitForStarted(3000):
        messagebox.showerror(app, c.t("UI_ERROR_TITLE"),
                             c.t("UI_GOOGLE_SIGNIN_LAUNCH_FAILED", bin_path=bin_path))
        return None
    return proc


ABI_PROFILES = {
    "x86_64": ["x86_64", "x86"],
    "x86": ["x86"],
    "arm64-v8a": ["arm64-v8a", "armeabi-v7a"],
    "armeabi-v7a": ["armeabi-v7a"],
}


def _detect_country_locale():
    """Detecta country/locale del entorno. Cae a us/en_US si no se puede."""
    import locale as _l
    try:
        loc, _enc = _l.getdefaultlocale()
        if loc and "_" in loc:
            lang, region = loc.split("_", 1)
            region = region.split(".")[0].lower()
            return region, loc
    except Exception:
        pass
    return "us", "en_US"


def _write_device_conf(workdir, arch):
    """
    Genera un device.conf que sobrescribe los campos críticos del device_info
    interno de gplaydl. El default trae un typo ('armeabi-x7a'), solo x86 y
    country=us, locale=en_US → Google rechaza descargas de apps pagadas
    cuando la cuenta es de otra región. Aquí declaramos las ABIs reales y
    derivamos country/locale del entorno del usuario.
    """
    abis = ABI_PROFILES.get(arch, ["x86_64", "x86"])
    array_lines = ",\n".join(f'    "{a}"' for a in abis)
    country, locale_id = _detect_country_locale()
    body = (
        f"config.native_platforms = [\n{array_lines}\n]\n"
        "build.sdk_version = 36\n"
        f"country = {country}\n"
        f"locale = {locale_id}\n"
    )
    path = os.path.join(workdir, "device.conf")
    try:
        with open(path, "w") as f:
            f.write(body)
    except Exception as e:
        logger.error(f"device.conf write error: {e}")
        return None
    return path


_DELIVERY_STATUS_MESSAGES = {
    "2": c.t("UI_GOOGLE_DELIVERY_STATUS_2"),
    "3": c.t("UI_GOOGLE_DELIVERY_STATUS_3"),
    "5": c.t("UI_GOOGLE_DELIVERY_STATUS_5"),
}


def _map_gplaydl_error(returncode, tail_text):
    """
    Translates gplaydl output into a human-friendly message.
    Detects structured errors emitted by our patches (status, no-cookie).
    """
    m = re.search(r"delivery status=(\d+)", tail_text)
    if m:
        msg = _DELIVERY_STATUS_MESSAGES.get(m.group(1))
        if msg:
            return msg
        return c.t("UI_GOOGLE_DELIVERY_STATUS_UNKNOWN", status=m.group(1))

    if "no downloadauthcookie" in tail_text:
        return _DELIVERY_STATUS_MESSAGES["2"]
    if "bad token" in tail_text or "BadAuthentication" in tail_text:
        return c.t("UI_GOOGLE_SESSION_EXPIRED")
    if "MissingDroidguard" in tail_text:
        return c.t("UI_GOOGLE_DROIDGUARD_REQUIRED")

    return c.t("UI_GOOGLE_DOWNLOAD_ERROR", code=returncode, tail=tail_text[-600:] or "(empty)"
    )


def download_and_install_google(app, vcode, vname, arch, target_root, is_target_flatpak, flatpak_id,
                                progress_callback, status_callback, finished_callback):
    """
    Inicia el proceso de descarga con gplaydl y luego extrae usando el método actual.
    """
    logger.debug("download_and_install_google: vcode=%s vname=%s arch=%s target_root=%s flatpak=%s id=%s",
        vcode, vname, arch, target_root, is_target_flatpak, flatpak_id)

    signals = InstallSignals()
    signals.progress.connect(progress_callback)
    signals.status.connect(status_callback)
    signals.finished.connect(finished_callback)

    def run_flow():
        signin_cwd = get_signin_workdir(app)
        # Write APK to signin_cwd (inside home, accessible from any sandbox via
        # --filesystem=home) instead of /tmp/ which is sandbox-private.
        temp_apk = os.path.join(signin_cwd, f"minecraft_{vcode}.apk")
        logger.debug("run_flow: temp_apk=%s", temp_apk)
        device_conf = os.path.join(target_root, "device.conf")
        try:
            # 0. Prepare device.conf
            with open(device_conf, "w") as f:
                f.write(f"config.native_platforms = [\n    {arch}\n]\n")

            # 1. Download
            signals.status.emit(c.t("UI_STATUS_DOWNLOADING"))

            bin_path = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_GPLAYDL, "gplaydl")

            token = ""
            user_email = ""
            try:
                with open(os.path.join(signin_cwd, "playdl.conf"), "r") as f:
                    for line in f:
                        if line.startswith("user_token = "):
                            token = line[len("user_token = "):].strip()
                        elif line.startswith("user_email = "):
                            user_email = line[len("user_email = "):].strip()
            except FileNotFoundError:
                pass

            dev_conf = _write_device_conf(signin_cwd, arch)

            cmd = [bin_path, "-sa", "-tos"]
            if user_email:
                cmd += ["-u", user_email]
            if token:
                cmd += ["-t", token]
            if dev_conf:
                cmd += ["-d", dev_conf]
            cmd += ["-a", "com.mojang.minecraftpe"]
            try:
                vcode_int = int(vcode)
            except (TypeError, ValueError):
                vcode_int = 0
            if vcode_int > 0:
                cmd += ["-v", str(vcode_int)]
            cmd += ["-o", temp_apk]

            # gplaydl runs inside the sandbox — it has network access via
            # --share=network and writes to signin_cwd in the home directory
            # (accessible from any flatpak sandbox via --filesystem=home).
            logger.debug("gplaydl cwd=%s", signin_cwd)
            logger.debug("gplaydl cmd=%s", " ".join(cmd))
            logger.debug("device.conf=%s exists=%s", dev_conf, os.path.exists(dev_conf) if dev_conf else False)
            logger.debug("playdl.conf exists=%s token_len=%d email=%s",
                os.path.exists(os.path.join(signin_cwd, "playdl.conf")), len(token), user_email)

            gplay_env = None
            if app.running_in_flatpak:
                gplay_env = os.environ.copy()
                gplay_env.pop("LD_LIBRARY_PATH", None)
            process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       bufsize=0, cwd=signin_cwd, env=gplay_env)
            logger.debug("gplaydl pid=%s", process.pid)

            stdout_tail = []
            stderr_tail = []

            def drain_stderr():
                try:
                    while True:
                        chunk = process.stderr.read(4096)
                        if not chunk:
                            break
                        text = chunk.decode("utf-8", errors="replace")
                        for line in text.splitlines(keepends=True):
                            stderr_tail.append(line)
                            if len(stderr_tail) > 40:
                                stderr_tail.pop(0)
                except Exception:
                    pass

            t_err = threading.Thread(target=drain_stderr, daemon=True)
            t_err.start()

            buf = ""
            last_pct = -1
            while True:
                raw = process.stdout.read(4096)
                if not raw:
                    break
                buf += raw.decode("utf-8", errors="replace")
                parts = re.split(r"[\r\n]", buf)
                buf = parts[-1]
                for line in parts[:-1]:
                    if not line:
                        continue
                    stdout_tail.append(line + "\n")
                    if len(stdout_tail) > 40:
                        stdout_tail.pop(0)
                    m = re.search(r"Downloaded (\d+)%", line)
                    if m:
                        p_val = int(m.group(1))
                        if p_val != last_pct:
                            last_pct = p_val
                            logger.debug("progress %d%%", p_val)
                            signals.progress.emit(p_val)
                m = re.search(r"Downloaded (\d+)%", buf)
                if m:
                    p_val = int(m.group(1))
                    if p_val != last_pct:
                        last_pct = p_val
                        logger.debug("progress %d%%", p_val)
                        signals.progress.emit(p_val)

            process.wait()
            t_err.join(timeout=2)
            logger.debug("gplaydl exit=%s temp_apk_exists=%s",
                process.returncode, os.path.exists(temp_apk))
            if stderr_tail:
                logger.debug("gplaydl stderr tail:\n%s", "".join(stderr_tail).strip())
            if stdout_tail:
                logger.debug("gplaydl stdout last 5 lines:\n%s",
                    "".join(stdout_tail[-5:]).strip())

            if process.returncode != 0 or not os.path.exists(temp_apk):
                combined = "".join(stderr_tail) + "\n" + "".join(stdout_tail)
                err_msg = _map_gplaydl_error(process.returncode, combined)
                logger.debug("download FAILED → mapped msg:\n%s", err_msg)
                signals.finished.emit(False, err_msg)
                return

            # 2. Extract
            signals.status.emit(c.t("UI_STATUS_EXTRACTING"))

            target_dir = os.path.join(target_root, c.VERSIONS_DIR, vname)
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            os.makedirs(target_dir, exist_ok=True)

            base_no_ext = temp_apk[:-len(".apk")] if temp_apk.endswith(".apk") else temp_apk
            apk_inputs = [temp_apk]
            for split_path in sorted(glob.glob(base_no_ext + ".*.apk")):
                if split_path != temp_apk:
                    apk_inputs.append(split_path)
            logger.debug("extract inputs (%d): %s",
                len(apk_inputs),
                ", ".join(f"{os.path.basename(p)}({os.path.getsize(p)//1024}K)"
                          for p in apk_inputs if os.path.exists(p)))

            use_flatpak_logic = is_target_flatpak
            extract_cmd = []
            custom_extract = app.config[c.CONFIG_KEY_BINARY_PATHS].get(c.CONFIG_KEY_EXTRACT)

            if custom_extract and os.path.exists(custom_extract):
                extract_cmd = [custom_extract, *apk_inputs, target_dir]
            elif use_flatpak_logic:
                app_id = flatpak_id if flatpak_id else app.config.get(c.CONFIG_KEY_FLATPAK_ID, c.MCPELAUNCHER_FLATPAK_ID)
                base_cmd = ["flatpak", "run", "--command=mcpelauncher-extract", app_id, *apk_inputs, target_dir]
                if app.running_in_flatpak:
                    fs = shutil.which("flatpak-spawn")
                    extract_cmd = [fs, "--host"] + base_cmd if fs else ["mcpelauncher-extract", *apk_inputs, target_dir]
                else:
                    extract_cmd = base_cmd
            else:
                extract_cmd = ["mcpelauncher-extract", *apk_inputs, target_dir]

            extract_env = os.environ.copy()
            bundled_lib = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "..", "..", "bin", "lib")
            bundled_lib = os.path.normpath(bundled_lib)
            if os.path.isdir(bundled_lib):
                extract_env["LD_LIBRARY_PATH"] = (
                    bundled_lib + os.pathsep + extract_env.get("LD_LIBRARY_PATH", "")
                )

            logger.debug("extract cmd=%s", " ".join(extract_cmd))
            logger.debug("extract LD_LIBRARY_PATH=%s", extract_env.get("LD_LIBRARY_PATH", ""))
            extract_proc = subprocess.run(extract_cmd, capture_output=True, text=True,
                                          env=extract_env)
            logger.debug("extract exit=%s stdout_tail=%r stderr_tail=%r",
                extract_proc.returncode,
                extract_proc.stdout[-300:] if extract_proc.stdout else "",
                extract_proc.stderr[-300:] if extract_proc.stderr else "")

            for p in apk_inputs:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except OSError:
                    pass

            final_vname = vname
            if extract_proc.returncode == 0 and vname == "latest":
                real = resolve_version(target_dir)
                if real:
                    new_target = os.path.join(target_root, c.VERSIONS_DIR, real)
                    if not os.path.exists(new_target):
                        try:
                            os.rename(target_dir, new_target)
                            target_dir = new_target
                            final_vname = real
                        except OSError as e:
                            logger.error(f"Rename latest→{real} failed: {e}")

            if extract_proc.returncode == 0:
                if target_root == app.active_path:
                    from src.core.install_ops import refresh_version_list
                    QTimer.singleShot(0, app, lambda: refresh_version_list(app))
                signals.finished.emit(True, c.t("UI_EXTRACTION_SUCCESS_MSG", ver_name=final_vname))
            else:
                signals.finished.emit(False, c.t("UI_EXTRACTION_ERROR_MSG", err_msg=extract_proc.stderr))

        except Exception as e:
            import traceback as _tb
            tb_text = _tb.format_exc()
            logger.debug("run_flow EXCEPTION:\n%s", tb_text)
            if os.path.exists(temp_apk):
                try:
                    os.remove(temp_apk)
                except OSError:
                    pass
            err_msg = f"{type(e).__name__}: {e}"
            signals.finished.emit(False, err_msg)

    threading.Thread(target=run_flow, daemon=True).start()
