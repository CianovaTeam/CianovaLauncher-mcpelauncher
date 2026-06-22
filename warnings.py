"""Manage version-warnings.json for CianovaLauncher.

Usage:
  python warnings.py list
  python warnings.py add <version> <reason>
  python warnings.py remove <version>
  python warnings.py versions [filter]

- list:        show current warnings
- add:         add/update a warning (validates against versiondb)
- remove:      remove a warning
- versions:    list versions from versiondb (optional filter)

  sync:       git pull && git push gh-pages (from CianovaLaunREPO)

Versiondb source: PlaGaPlusDev/mcpelauncher-versiondb
"""
import json
import os
import subprocess as sp
import sys
import urllib.request
import urllib.error

WARN_FILE = os.path.join(os.path.dirname(__file__), "version-warnings.json")
VERSIONDB_URL = "https://raw.githubusercontent.com/PlaGaPlusDev/mcpelauncher-versiondb/master/versions.x86_64.json.min"

if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
    _R = _G = _Y = _X = ""
else:
    _R = "\033[31m"    # red
    _G = "\033[32m"    # green
    _Y = "\033[93m"    # bright yellow
    _X = "\033[0m"     # reset


def _load_json(path):
    with open(path) as f:
        return json.load(f)


def _save_json(data, path):
    data["updated"] = __import__("datetime").date.today().isoformat()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _natural_key(v: str):
    return [int(p) if p.isdigit() else p for p in v.split(".")]


def _fetch_versiondb() -> dict[str, int]:
    """Returns {version: is_beta} where is_beta=0 release, 1 beta."""
    req = urllib.request.Request(
        VERSIONDB_URL,
        headers={"User-Agent": "warnings-script/1.0",
                 "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return {e[1]: e[2] for e in json.loads(raw)}
    except Exception as e:
        print(f"warning: couldn't fetch versiondb ({e}), skipping validation")
        return {}


def cmd_list():
    data = _load_json(WARN_FILE)
    ws = data.get("warnings", [])
    if not ws:
        print("No warnings.")
        return
    print(f"Warnings (updated: {data.get('updated', '?')}):")
    for w in ws:
        print(f"  {w['version']}  —  {w['reason']}")


def cmd_add(version: str, reason: str):
    db = _fetch_versiondb()
    if db and version not in db:
        print(f"error: '{version}' not found in versiondb")
        close = [v for v in sorted(db) if version in v]
        if close:
            print("Did you mean?")
            for v in close:
                print(f"  {v}")
        sys.exit(1)

    data = _load_json(WARN_FILE)
    for w in data["warnings"]:
        if w["version"] == version:
            print(f"warning: '{version}' already exists, updating reason")
            w["reason"] = reason
            break
    else:
        data["warnings"].append({"version": version, "reason": reason})
    _save_json(data, WARN_FILE)
    print(f"ok: '{version}' added/updated")


def cmd_versions(filtro: str | None):
    db = _fetch_versiondb()
    if not db:
        print("Could not fetch versiondb.")
        return
    data = _load_json(WARN_FILE)
    warned = {w["version"] for w in data.get("warnings", [])}
    sorted_ = sorted(db, key=_natural_key)
    if filtro:
        sorted_ = [v for v in sorted_ if filtro in v]
    print(f"Versions ({len(sorted_)} shown / {len(db)} total)  [R]=Release [B]=Beta [*]=warning:")
    for v in sorted_:
        tag = f"{_G}R{_X}" if db[v] == 0 else f"{_R}B{_X}"
        warn = f"{_Y}*{_X}" if v in warned else " "
        print(f" [{tag}]{warn} {v}")


def cmd_sync():
    repo = os.path.dirname(os.path.abspath(__file__))
    branch = sp.run(["git", "branch", "--show-current"], capture_output=True, text=True, cwd=repo).stdout.strip()
    if branch != "gh-pages":
        print(f"warning: current branch is '{branch}' not 'gh-pages', pushing anyway")

    print("=> git pull origin gh-pages...")
    r = sp.run(["git", "pull", "origin", "gh-pages"], cwd=repo)
    if r.returncode != 0:
        print("warning: pull failed (no upstream?), continuing...")

    print("=> git push origin gh-pages...")
    r = sp.run(["git", "push", "origin", "gh-pages"], cwd=repo)
    if r.returncode != 0:
        print("error: git push failed")
        sys.exit(1)

    print("ok: synced gh-pages")


def cmd_remove(version: str):
    data = _load_json(WARN_FILE)
    before = len(data["warnings"])
    data["warnings"] = [w for w in data["warnings"] if w["version"] != version]
    if len(data["warnings"]) == before:
        print(f"warning: '{version}' not found in warnings")
        return
    _save_json(data, WARN_FILE)
    print(f"ok: '{version}' removed")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "list":
        cmd_list()
    elif cmd == "add":
        if len(sys.argv) < 4:
            print("usage: warnings.py add <version> <reason>")
            sys.exit(1)
        cmd_add(sys.argv[2], " ".join(sys.argv[3:]))
    elif cmd == "remove":
        if len(sys.argv) < 3:
            print("usage: warnings.py remove <version>")
            sys.exit(1)
        cmd_remove(sys.argv[2])
    elif cmd == "versions":
        filtro = sys.argv[2] if len(sys.argv) >= 3 else None
        cmd_versions(filtro)
    elif cmd == "sync":
        cmd_sync()
    else:
        print(f"unknown command: {cmd}")
        sys.exit(1)
