import os
import json
import shutil
import zipfile
import tempfile
import time
import re
from src import constants as c

def get_com_mojang_path(active_path):
    """Retorna la ruta a games/com.mojang"""
    if not active_path:
        return None
    return os.path.join(active_path, "games", "com.mojang")

def get_disabled_packs_path(app):
    """Retorna la ruta a disabled_packs dentro del perfil actual"""
    if not app.active_path:
        return None
    current_profile = app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.UI_PROFILE_DEFAULT)
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
        except: pass
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
        "resource_packs": c.UI_TYPE_RESOURCE,
        "behavior_packs": c.UI_TYPE_BEHAVIOR,
        "minecraftWorlds": c.UI_TYPE_WORLD,
        "skin_packs": c.UI_TYPE_SKIN,
        "custom_skins": c.UI_TYPE_SKIN,
    }

    # Escanear packs activos
    for folder, type_label in folders.items():
        path = os.path.join(com_mojang, folder)
        if os.path.exists(path):
            try:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        info = get_addon_info(item_path, folder)
                        if not info.get("is_valid", True): continue
                        addon_list.append({
                            **info,
                            "type_label": c.UI_TYPE_SKINPACK if info.get("real_type") == "skin_packs" else type_label,
                            "folder": folder,
                            "enabled": True,
                            "path": item_path
                        })
            except: pass

    # Escanear packs desactivados
    disabled_root = get_disabled_packs_path(app)
    if disabled_root and os.path.exists(disabled_root):
        for folder in folders.keys():
            path = os.path.join(disabled_root, folder)
            if os.path.exists(path):
                try:
                    for item in os.listdir(path):
                        item_path = os.path.join(path, item)
                        if os.path.isdir(item_path):
                            info = get_addon_info(item_path, folder)
                            if not info.get("is_valid", True): continue
                            addon_list.append({
                                **info,
                                "type_label": c.UI_TYPE_SKINPACK if info.get("real_type") == "skin_packs" else folders.get(folder, c.UI_TYPE_RESOURCE),
                                "folder": folder,
                                "enabled": False,
                                "path": item_path
                            })
                except: pass

    return addon_list

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

    if folder_type == "minecraftWorlds":
        levelname_path = os.path.join(path, "levelname.txt")
        if os.path.exists(levelname_path):
            try:
                with open(levelname_path, "r", errors="replace") as f:
                    info["name"] = f.read().strip()
            except: pass
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
        except: pass

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
        except: pass
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
    except: pass
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

    if os.path.exists(target_path):
        shutil.rmtree(target_path)

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
                    name = "".join(x for x in f.read().strip() if x.isalnum() or x in " -_")
            except: pass

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
    if ext == ".mcworld" or ext == ".mcworldtemplate":
        results.append(extract_to(file_path, os.path.join(com_mojang, "minecraftWorlds")))
    elif ext == ".mcpack":
        results.append(install_single_pack(file_path, com_mojang, manual_type))
    elif ext == ".mcaddon":
        results.extend(install_mcaddon(file_path, com_mojang))
    else:
        results.append(install_single_pack(file_path, com_mojang, manual_type))
    return results

def extract_to(zip_path, target_dir):
    os.makedirs(target_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        folder_name = os.path.splitext(os.path.basename(zip_path))[0]
        top_level = {os.path.split(n)[0] for n in zip_ref.namelist() if n}
        if len(top_level) == 1 and list(top_level)[0] != "":
            zip_ref.extractall(target_dir)
            return os.path.join(target_dir, list(top_level)[0])
        else:
            dest = os.path.join(target_dir, folder_name)
            os.makedirs(dest, exist_ok=True)
            zip_ref.extractall(dest)
            return dest

def install_single_pack(file_path, com_mojang, manual_type=None):
    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        manifest_path = find_file_recursive(temp_dir, "manifest.json")
        pack_type = manual_type
        if not pack_type and manifest_path:
            pack_type = detect_pack_type(manifest_path)
        if not pack_type:
            shutil.rmtree(temp_dir)
            return ("NEED_TYPE", file_path)
        dest_folder = {
            c.UI_TYPE_RESOURCE: "resource_packs",
            c.UI_TYPE_BEHAVIOR: "behavior_packs",
            c.UI_TYPE_SKIN: "skin_packs",
            c.UI_TYPE_WORLD: "minecraftWorlds"
        }.get(pack_type, "resource_packs")
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

def detect_pack_type(manifest_path):
    try:
        with open(manifest_path, "r") as f:
            data = json.load(f)
            modules = data.get("modules", [])
            for mod in modules:
                m_type = mod.get("type")
                if m_type == "resources": return c.UI_TYPE_RESOURCE
                if m_type == "data": return c.UI_TYPE_BEHAVIOR
                if m_type == "skin_pack": return c.UI_TYPE_SKIN
                if m_type == "world_template": return c.UI_TYPE_WORLD
    except: pass
    return None

def install_mcaddon(file_path, com_mojang):
    temp_dir = tempfile.mkdtemp()
    results = []
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            if item.endswith(".mcpack"):
                results.append(install_single_pack(item_path, com_mojang))
            elif os.path.isdir(item_path):
                manifest = os.path.join(item_path, "manifest.json")
                if os.path.exists(manifest):
                    p_type = detect_pack_type(manifest)
                    if p_type:
                        dest_folder = {
                            c.UI_TYPE_RESOURCE: "resource_packs",
                            c.UI_TYPE_BEHAVIOR: "behavior_packs",
                            c.UI_TYPE_SKIN: "skin_packs"
                        }.get(p_type, "resource_packs")
                        target = os.path.join(com_mojang, dest_folder, item)
                        if os.path.exists(target): shutil.rmtree(target)
                        shutil.move(item_path, target)
                        results.append(("SUCCESS", target))
        shutil.rmtree(temp_dir)
    except Exception as e:
        results.append(("ERROR", str(e)))
    return results
