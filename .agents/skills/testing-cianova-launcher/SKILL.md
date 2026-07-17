---
name: testing-cianova-launcher
description: Smoke-test the CianovaLauncher PySide6 GUI end-to-end on a Linux desktop. Use when verifying launcher startup, theming, Flatpak/subprocess helpers, or GPU/hardware detection changes.
---

# Testing CianovaLauncher (PySide6 GUI)

CianovaLauncher is a PySide6/Qt6 GUI for Minecraft Bedrock on Linux. Most changes
can be validated by launching the GUI and confirming it renders + navigates.

## Environment
- **Python 3.12** is the intended runtime (release CI uses 3.12; the code relies on
  3.12-only f-string syntax, so 3.10 fails with `SyntaxError: f-string ... backslash`).
  Use a 3.12 venv: `python3.12 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt pytest`.
- Deps: `PySide6`, `Pillow`, `pypresence`.
- Unit tests: `QT_QPA_PLATFORM=offscreen python -m pytest -q` (expect ~87 passed, 1 pre-existing
  `TestWindow` collection warning).

## Launching the GUI for a smoke test
- Entrypoint: `PYTHONPATH=$(pwd) python src/main.py` (run.sh expects a `venv/` + `bin/` dir; you
  can launch directly instead). Launch on the real display (`DISPLAY=:0`), not offscreen, to see UI.
- **Skip the 7-step first-run SetupWizard** by pre-seeding the config so the main window opens directly:
  - Non-Flatpak config path: `~/.local/share/mcpelauncher/cianovalauncher-config.json`
  - Minimal contents: `{"accepted_terms": true, "initial_setup_complete": true, "language": "en", "appearance_mode": "Dark"}`
  - Keys live in `src/core/config_keys.py` (`accepted_terms`, `initial_setup_complete`).
- Maximize the window for recording: `wmctrl -r "CianovaLauncher" -b add,maximized_vert,maximized_horz`.

## What launching exercises (useful for refactors touching utils)
- `is_running_in_flatpak()` / `get_flatpak_app_id()` — main window opening via the non-Flatpak
  config path proves these resolved correctly.
- `colors._hex_to_rgb` / `adjust_color` — themed UI (blue buttons/sliders) proves these ran.
- `query_glxinfo(...)` — **Tools tab → "Verify Requirements (Hardware)"** opens a dialog that
  displays the GPU OpenGL / OpenGL ES lines. Install `mesa-utils` first (`sudo apt-get install -y mesa-utils`)
  so `glxinfo` exists and the dialog shows a **real** value (e.g. `OpenGL ES 3.2 Mesa ...`) instead of
  the silent `"Unknown"` fallback — this is what distinguishes a working helper from a broken one.
- Startup log (stdout, also under `logs/`) prints `GPU OpenGL:` / `GPU OpenGL ES:` lines; grep for them
  and for `Traceback`.

## Notes / gotchas
- This host is NOT a Flatpak sandbox, so only the non-Flatpak code paths run at runtime. The Flatpak
  branches (`host_prefix`/`host_command` with `flatpak-spawn`, Flatpak config/log paths, the
  `query_glxinfo` host fallback) are covered by `tests/test_process_utils.py`, not runtime — call this out
  in reports rather than claiming they were runtime-verified.
- "Could not find 'versions' folder" on the PLAY tab is expected with no installed versions.
- The repo's only workflow is a manual release build, so PRs have no automatic CI checks.

## Devin Secrets Needed
None. All testing is local; no external services or credentials required.
