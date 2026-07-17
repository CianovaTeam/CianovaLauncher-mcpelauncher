import os
import json
import shutil
import zipfile
import tempfile
import time
import re
from src import constants as c
from src.utils.logger import logger
from src.utils.safe_archive import safe_extractall


def _mods_config_path(active_path):
    return os.path.join(active_path, c.MODS_DIR, "mods_config.json")

def load_mods_config(app):
    """Carga la config de mods (qué mods se lanzan al iniciar el juego)."""
    if not app.active_path:
        return {}
    cfg_path = _mods_config_path(app.active_path)
    config = {}
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            config = {}
    return config

def save_mods_config(app, config):
    """Guarda la config de mods."""
    if not app.active_path:
        logger.warning("save_mods_config: no active_path")
        return
    cfg_path = _mods_config_path(app.active_path)
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    tmp_path = cfg_path + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(config, f, indent=2)
        os.replace(tmp_path, cfg_path)
        logger.debug(f"mods config saved: {cfg_path}")
    except OSError as e:
        logger.warning(f"Failed to save mods config: {e}")

def _mod_stable_key(mod_path):
    """Return a stable identifier for a mod using its .so filename only."""
    base = os.path.basename(mod_path)
    if base.lower().endswith(".disabled"):
        base = base[:-9]
    if base.lower().endswith(".so"):
        base = base[:-3]
    return base


def get_mod_launch_state(app, mod_path):
    """Retorna si un mod debe cargarse al lanzar el juego."""
    config = load_mods_config(app)
    mod_key = _mod_stable_key(mod_path)
    if mod_key in config:
        val = config[mod_key].get("launch", True)
        logger.debug(f"get_mod_launch_state: {mod_key} -> {val} (from {mod_path})")
        return val
    logger.debug(f"get_mod_launch_state: {mod_key} not in config, default True")
    return True


def set_mod_launch_state(app, mod_path, launch_enabled):
    """Establece si un mod debe cargarse al lanzar el juego."""
    config = load_mods_config(app)
    mod_key = _mod_stable_key(mod_path)
    if mod_key not in config:
        config[mod_key] = {}
    config[mod_key]["launch"] = launch_enabled
    logger.debug(f"set_mod_launch_state: {mod_key} -> {launch_enabled} (path={mod_path})")
    save_mods_config(app, config)

def get_com_mojang_path(active_path):
    """Retorna la ruta a games/com.mojang"""
    if not active_path:
        return None
    # Try standard path first
    p = os.path.join(active_path, "games", "com.mojang")
    if os.path.exists(p): return p
    # Try alternate if games/ is missing but active_path is the base
    alt = os.path.join(active_path, "com.mojang")
    if os.path.exists(alt): return alt
    # Default to standard
    return p

def get_disabled_packs_path(app):
    """Retorna la ruta a disabled_packs dentro del perfil actual"""
    if not app.active_path:
        return None
    current_profile = app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.t("UI_PROFILE_DEFAULT"))
    return os.path.join(app.active_path, c.PROFILES_DIR, current_profile, c.DISABLED_PACKS_DIR)

def strip_mc_codes(text):
    """Elimina códigos de color de Minecraft (§a, §l, etc.)"""
    if not text: return ""
    return re.sub(r'§[0-9a-gk-or]', '', text)

def parse_lang_file(lang_path):
    """Parsea un archivo .lang de Minecraft Bedrock"""
    translations = {}
    if os.path.exists(lang_path):
        try:
            with open(lang_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line and not line.startswith("#"):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            translations[parts[0].strip()] = strip_mc_codes(parts[1].strip())
        except (OSError, UnicodeDecodeError) as e:
            logger.debug(f"Could not parse lang file {lang_path}: {e}")
    return translations

def scan_all_addons(app):
    """Escanea todas las carpetas de addons y retorna una lista de diccionarios"""
    active_path = app.active_path
    com_mojang = get_com_mojang_path(active_path)
    if not com_mojang:
        return []

    addon_list = []

    # Carpetas a escanear (Activadas)
    folders = {
        "resource_packs": c.t("UI_TYPE_RESOURCE"),
        "behavior_packs": c.t("UI_TYPE_BEHAVIOR"),
        "minecraftWorlds": c.t("UI_TYPE_WORLD"),
        "skin_packs": c.t("UI_TYPE_SKIN"),
        "custom_skins": c.t("UI_TYPE_SKIN"),
    }

    # Escanear packs activos
    for folder, type_label in folders.items():
        path = os.path.join(com_mojang, folder)
        if os.path.exists(path):
            try:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    # Support both directories and individual files (e.g. .mcpack, .mcworld)
                    if not os.path.exists(item_path):
                        continue
                    if os.path.isdir(item_path) or (os.path.isfile(item_path) and item.lower().endswith(('.mcpack', '.mcworld', '.mcaddon', '.mcworldtemplate', '.mctemplate', '.zip'))):
                        info = get_addon_info(item_path, folder)
                        if not info.get("is_valid", True): continue
                        addon_list.append({
                            **info,
                            "type_label": c.t("UI_TYPE_SKINPACK") if info.get("real_type") == "skin_packs" else type_label,
                            "folder": folder,
                            "enabled": True,
                            "path": item_path
                        })
            except OSError as e:
                logger.debug(f"Could not scan addon folder {path}: {e}")

    # Escanear packs desactivados
    disabled_root = get_disabled_packs_path(app)
    if disabled_root and os.path.exists(disabled_root):
        for folder in folders.keys():
            path = os.path.join(disabled_root, folder)
            if os.path.exists(path):
                try:
                    for item in os.listdir(path):
                        item_path = os.path.join(path, item)
                        if not os.path.exists(item_path):
                            continue
                        if os.path.isdir(item_path) or (os.path.isfile(item_path) and item.lower().endswith(('.mcpack', '.mcworld', '.mcaddon', '.mcworldtemplate', '.mctemplate'))):
                            info = get_addon_info(item_path, folder)
                            if not info.get("is_valid", True): continue
                            addon_list.append({
                                **info,
                                "type_label": c.t("UI_TYPE_SKINPACK") if info.get("real_type") == "skin_packs" else folders.get(folder, c.t("UI_TYPE_RESOURCE")),
                                "folder": folder,
                                "enabled": False,
                                "path": item_path
                            })
                except OSError as e:
                    logger.debug(f"Could not scan disabled addon folder {path}: {e}")

    return addon_list

def _peek_packed_info(path):
    """Lee el manifest.json dentro de un .mcpack/.mcaddon/.zip sin extraer todo"""
    try:
        with zipfile.ZipFile(path, 'r') as z:
            candidates = [n for n in z.namelist() if n.replace("\\", "/").endswith("manifest.json")]
            if not candidates:
                return None
            manifest_path = min(candidates, key=len)
            with z.open(manifest_path) as f:
                content = f.read().decode("utf-8", errors="replace")
                if content.startswith('\ufeff'):
                    content = content[1:]
                data = json.loads(content)
                header = data.get("header", {})
                name = header.get("name", "")
                desc = header.get("description", "")
                ver = header.get("version", [])
                min_ver = header.get("min_engine_version", [])
                modules = data.get("modules", [])
                real_type = None
                for mod in modules:
                    if mod.get("type") == "skin_pack":
                        real_type = "skin_packs"
                        break
                result = {
                    "name": strip_mc_codes(str(name)) if name else None,
                    "description": strip_mc_codes(str(desc)) if desc else None,
                }
                if isinstance(ver, list):
                    result["version"] = ".".join(map(str, ver))
                if isinstance(min_ver, list):
                    result["min_engine"] = ".".join(map(str, min_ver))
                if real_type:
                    result["real_type"] = real_type
                return result
    except Exception as e:
        logger.warning("Failed to peek packed info in %s: %s", path, e)
        return None

def get_addon_info(path, folder_type=None):
    """Extrae información del manifest.json o levelname.txt"""
    info = {
        "name": os.path.basename(path),
        "description": "",
        "version": "",
        "min_engine": "",
        "icon_path": None,
        "is_valid": True,
        "real_type": folder_type
    }

    # Handle packed files (.mcpack, .mcworld)
    if os.path.isfile(path) and path.lower().endswith(('.mcpack', '.mcworld', '.mcaddon', '.mcworldtemplate', '.mctemplate', '.zip')):
        packed = _peek_packed_info(path)
        if packed:
            info["name"] = packed.get("name", info["name"])
            info["description"] = packed.get("description", info["description"])
            info["version"] = packed.get("version", info["version"])
            info["min_engine"] = packed.get("min_engine", info["min_engine"])
            if packed.get("real_type"):
                info["real_type"] = packed["real_type"]
        return info

    if folder_type == "minecraftWorlds":
        levelname_path = os.path.join(path, "levelname.txt")
        if os.path.exists(levelname_path):
            try:
                with open(levelname_path, "r", errors="replace") as f:
                    info["name"] = f.read().strip()
            except (OSError, UnicodeDecodeError) as e:
                logger.debug(f"Could not read levelname.txt at {levelname_path}: {e}")
        else:
            if os.path.basename(path) == "Texture":
                info["is_valid"] = False
                return info

        icon_path = os.path.join(path, "world_icon.jpeg")
        if os.path.exists(icon_path):
            info["icon_path"] = icon_path
        return info

    manifest_path = os.path.join(path, "manifest.json")
    if not os.path.exists(manifest_path):
        try:
            for sub in os.listdir(path):
                sub_path = os.path.join(path, sub)
                if os.path.isdir(sub_path):
                    m = os.path.join(sub_path, "manifest.json")
                    if os.path.exists(m):
                        manifest_path = m
                        break
        except OSError:
            pass

    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
                if content.startswith('\ufeff'): content = content[1:]
                data = json.loads(content)
                header = data.get("header", {})

                name = header.get("name")
                desc = header.get("description")

                if name:
                    info["name"] = strip_mc_codes(str(name))
                if desc:
                    info["description"] = strip_mc_codes(str(desc))

                # Soporte para traducciones (.lang)
                texts_dir = os.path.join(os.path.dirname(manifest_path), "texts")
                if os.path.exists(texts_dir):
                    all_translations = {}
                    # Cargar traducciones (Inglés y Español)
                    for lang_file in ["en_US.lang", "es_ES.lang", "es_MX.lang"]:
                        all_translations.update(parse_lang_file(os.path.join(texts_dir, lang_file)))

                    # Resolver claves de traducción si los valores originales eran keys
                    name_key = str(name) if name else ""
                    desc_key = str(desc) if desc else ""

                    if name_key in all_translations:
                        info["name"] = all_translations[name_key]
                    if desc_key in all_translations:
                        info["description"] = all_translations[desc_key]

                modules = data.get("modules", [])
                for mod in modules:
                    if mod.get("type") == "skin_pack":
                        info["real_type"] = "skin_packs"
                        break

                ver = header.get("version", [])
                if isinstance(ver, list):
                    info["version"] = ".".join(map(str, ver))

                min_ver = header.get("min_engine_version", [])
                if isinstance(min_ver, list):
                    info["min_engine"] = ".".join(map(str, min_ver))
        except (json.JSONDecodeError, KeyError, OSError, UnicodeDecodeError) as e:
            logger.warning("Failed to parse manifest at %s: %s", manifest_path, e)
    else:
        if folder_type in ["resource_packs", "behavior_packs"]:
             info["is_valid"] = False

    icon_path = os.path.join(os.path.dirname(manifest_path) if os.path.exists(manifest_path) else path, "pack_icon.png")
    if os.path.exists(icon_path):
        info["icon_path"] = icon_path
    elif os.path.exists(os.path.join(path, "pack_icon.png")):
        info["icon_path"] = os.path.join(path, "pack_icon.png")

    return info

def find_file_recursive(base_path, filename, max_depth=2, current_depth=0):
    if current_depth > max_depth:
        return None
    target = os.path.join(base_path, filename)
    if os.path.exists(target): return target
    try:
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path):
                found = find_file_recursive(item_path, filename, max_depth, current_depth + 1)
                if found: return found
    except OSError:
        pass
    return None

def toggle_addon(app, addon_info):
    """Activa o desactiva un addon moviéndolo de carpeta"""
    current_path = addon_info["path"]
    folder_name = addon_info["folder"]
    item_name = os.path.basename(current_path)

    if addon_info["enabled"]:
        target_dir = os.path.join(get_disabled_packs_path(app), folder_name)
    else:
        target_dir = os.path.join(get_com_mojang_path(app.active_path), folder_name)

    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, item_name)

    if os.path.abspath(current_path) == os.path.abspath(target_path):
        return target_path

    if os.path.exists(target_path):
        if os.path.isdir(target_path): shutil.rmtree(target_path)
        else: os.remove(target_path)

    shutil.move(current_path, target_path)
    return target_path

def delete_addon(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return True
    return False

def export_world(world_path, dest_dir):
    """Exporta un mundo a formato .mcworld"""
    try:
        name = os.path.basename(world_path)
        levelname_path = os.path.join(world_path, "levelname.txt")
        if os.path.exists(levelname_path):
            try:
                with open(levelname_path, "r", errors="replace") as f:
                    raw = f.read().strip()
                    safe = re.sub(r'[<>:"/\\|?*]', '', raw).strip()[:200]
                    name = safe if safe else name
            except (OSError, UnicodeDecodeError):
                pass

        save_path = os.path.join(dest_dir, f"{name}.mcworld")
        temp_base = os.path.join(tempfile.gettempdir(), f"{name}_{int(time.time())}")

        created_zip = shutil.make_archive(temp_base, "zip", world_path)
        shutil.move(created_zip, save_path)
        return True, save_path
    except Exception as e:
        return False, str(e)

def install_addon_file(active_path, file_path, manual_type=None):
    """Instala un archivo .mcpack, .mcworld, .mcaddon"""
    com_mojang = get_com_mojang_path(active_path)
    ext = os.path.splitext(file_path)[1].lower()
    results = []
    if ext in (".mcworld", ".mcworldtemplate", ".mctemplate"):
        if not validate_zip(file_path):
            results.append(("ERROR", f"Corrupted file: {os.path.basename(file_path)}"))
        else:
            results.append(extract_to(file_path, os.path.join(com_mojang, "minecraftWorlds")))
    elif ext == ".mcpack":
        results.append(install_single_pack(file_path, com_mojang, manual_type))
    elif ext == ".mcaddon":
        results.extend(install_mcaddon(file_path, com_mojang))
    else:
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                safe_extractall(zip_ref, temp_dir)
            pack_dirs = []
            if os.path.exists(os.path.join(temp_dir, "manifest.json")):
                pack_dirs.append(temp_dir)
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "manifest.json")):
                    pack_dirs.append(item_path)
            if len(pack_dirs) == 0:
                shutil.rmtree(temp_dir)
                results.append(install_single_pack(file_path, com_mojang, manual_type))
            elif len(pack_dirs) == 1:
                shutil.rmtree(temp_dir)
                results.append(install_single_pack(file_path, com_mojang, manual_type))
            else:
                for pack_dir in pack_dirs:
                    manifest_path = os.path.join(pack_dir, "manifest.json")
                    item_name = os.path.basename(pack_dir)
                    p_type = detect_pack_type(manifest_path)
                    if p_type:
                        dest_folder = PACK_TYPE_FOLDER_MAP.get(p_type, "resource_packs")
                        target = os.path.join(com_mojang, dest_folder, item_name)
                        if os.path.exists(target):
                            if os.path.isdir(target): shutil.rmtree(target)
                            else: os.remove(target)
                        shutil.move(pack_dir, target)
                        results.append(("SUCCESS", target))
                    else:
                        results.append(("SKIPPED", item_name))
                shutil.rmtree(temp_dir)
        except zipfile.BadZipFile:
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
            results.append(install_single_pack(file_path, com_mojang, manual_type))
        except Exception as e:
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
            results.append(("ERROR", str(e)))
    return results

def extract_to(zip_path, target_dir):
    os.makedirs(target_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        folder_name = os.path.splitext(os.path.basename(zip_path))[0]
        top_level = {os.path.split(n)[0] for n in zip_ref.namelist() if n}
        if len(top_level) == 1 and list(top_level)[0] != "":
            safe_extractall(zip_ref, target_dir)
            return os.path.join(target_dir, list(top_level)[0])
        else:
            dest = os.path.join(target_dir, folder_name)
            os.makedirs(dest, exist_ok=True)
            safe_extractall(zip_ref, dest)
            return dest

def validate_zip(file_path):
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            bad = z.testzip()
            return bad is None
    except Exception as e:
        logger.warning("validate_zip failed for %s: %s", file_path, e)
        return False

def install_single_pack(file_path, com_mojang, manual_type=None):
    if not validate_zip(file_path):
        return ("ERROR", "Corrupted ZIP file")
    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            safe_extractall(zip_ref, temp_dir)
        manifest_path = find_file_recursive(temp_dir, "manifest.json")
        pack_type = manual_type
        if not pack_type and manifest_path:
            pack_type = detect_pack_type(manifest_path)
        if not pack_type:
            shutil.rmtree(temp_dir)
            return ("NEED_TYPE", file_path)
        dest_folder = PACK_TYPE_FOLDER_MAP.get(pack_type, "resource_packs")
        final_dest = os.path.join(com_mojang, dest_folder)
        os.makedirs(final_dest, exist_ok=True)
        item_name = os.path.splitext(os.path.basename(file_path))[0]
        target_path = os.path.join(final_dest, item_name)
        if os.path.exists(target_path): shutil.rmtree(target_path)
        shutil.move(temp_dir, target_path)
        return ("SUCCESS", target_path)
    except Exception as e:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        return ("ERROR", str(e))

PACK_TYPE_FOLDER_MAP = {
    "resources": "resource_packs",
    "data": "behavior_packs",
    "skin_pack": "skin_packs",
    "world_template": "minecraftWorlds",
}


def detect_pack_type(manifest_path):
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            modules = data.get("modules", [])
            for mod in modules:
                m_type = mod.get("type")
                if m_type in PACK_TYPE_FOLDER_MAP:
                    return m_type
    except Exception:
        return None
    return None

def install_mcaddon(file_path, com_mojang):
    if not validate_zip(file_path):
        return [("ERROR", f"Corrupted .mcaddon file: {os.path.basename(file_path)}")]
    temp_dir = tempfile.mkdtemp()
    results = []
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            safe_extractall(zip_ref, temp_dir)
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            if item.endswith(".mcpack"):
                results.append(install_single_pack(item_path, com_mojang))
            elif os.path.isdir(item_path):
                manifest = os.path.join(item_path, "manifest.json")
                if os.path.exists(manifest):
                    p_type = detect_pack_type(manifest)
                    if p_type:
                        dest_folder = PACK_TYPE_FOLDER_MAP.get(p_type, "resource_packs")
                        target = os.path.join(com_mojang, dest_folder, item)
                        if os.path.exists(target):
                            base, ext = os.path.splitext(item)
                            suffix = 1
                            while os.path.exists(os.path.join(com_mojang, dest_folder, f"{base}_{suffix}{ext}")):
                                suffix += 1
                            target = os.path.join(com_mojang, dest_folder, f"{base}_{suffix}{ext}")
                        shutil.move(item_path, target)
                        results.append(("SUCCESS", target))
        shutil.rmtree(temp_dir)
    except Exception as e:
        results.append(("ERROR", str(e)))
    return results

def _collect_mods_recursive(search_path, app=None):
    mods = []
    try:
        for item in os.listdir(search_path):
            item_path = os.path.join(search_path, item)
            if os.path.isdir(item_path):
                mods.extend(_collect_mods_recursive(item_path, app))
            elif os.path.isfile(item_path):
                is_disabled = item.lower().endswith(".disabled")
                base_name = item[:-9] if is_disabled else item
                if not base_name.lower().endswith(".so"):
                    continue
                try:
                    size = os.path.getsize(item_path)
                except OSError:
                    size = 0
                launch = get_mod_launch_state(app, item_path) if app else True

                # Detect DRM mod (mcpelauncher-updates)
                desc = ""
                if "mcpelauncher-updates" in search_path and base_name == "libmcpelauncher-updates.so":
                    desc = "Parchea Pairip Core DRM para ejecutar Minecraft Bedrock ≥ 1.21.30 en Linux. Solo necesario para versiones instaladas desde Google Play."

                mods.append({
                    "name": base_name,
                    "description": desc,
                    "version": "",
                    "min_engine": "",
                    "icon_path": None,
                    "is_valid": True,
                    "real_type": "mod",
                    "type_label": "Mod MCPELauncher",
                    "folder": "mods",
                    "enabled": not is_disabled,
                    "launch": launch,
                    "path": item_path,
                    "size": size
                })
    except OSError as e:
        logger.debug(f"Could not scan mods directory: {e}")
    return mods

def scan_mods(app):
    active_path = app.active_path
    if not active_path:
        return []
    mods_path = os.path.join(active_path, c.MODS_DIR)
    if not os.path.exists(mods_path):
        return []
    return _collect_mods_recursive(mods_path, app)

def toggle_mod(app, mod_info):
    current_path = mod_info["path"]
    mods_dir = os.path.dirname(current_path)
    base_name = mod_info["name"]
    if mod_info["enabled"]:
        new_name = base_name + ".disabled"
    else:
        new_name = base_name
    new_path = os.path.join(mods_dir, new_name)
    os.rename(current_path, new_path)
    return new_path

def delete_mod(path):
    if os.path.exists(path):
        os.remove(path)
        return True
    return False

def install_mod_file(active_path, file_path):
    mods_path = os.path.join(active_path, c.MODS_DIR)
    os.makedirs(mods_path, exist_ok=True)
    ext = os.path.splitext(file_path)[1].lower()
    results = []
    if ext == ".zip":
        if not validate_zip(file_path):
            return [("ERROR", f"Corrupted .zip file: {os.path.basename(file_path)}")]
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                safe_extractall(zip_ref, temp_dir)
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    if f.lower().endswith(".so"):
                        src = os.path.join(root, f)
                        dst = os.path.join(mods_path, f)
                        if os.path.exists(dst):
                            os.remove(dst)
                        shutil.copy2(src, dst)
                        results.append(("SUCCESS", dst))
            shutil.rmtree(temp_dir)
        except Exception as e:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            results.append(("ERROR", str(e)))
    elif ext == ".so":
        dst = os.path.join(mods_path, os.path.basename(file_path))
        if os.path.exists(dst):
            os.remove(dst)
        shutil.copy2(file_path, dst)
        results.append(("SUCCESS", dst))
    else:
        results.append(("ERROR", f"Unsupported format: {ext}"))
    return results
