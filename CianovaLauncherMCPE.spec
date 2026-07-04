# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

# ── Solo los módulos PySide6 que USAMOS ──
# Nada de collect_submodules/collect_dynamic_libs/collect_data_files
# porque traen todo Qt3D/QtWebEngine/QtQuick/QtQml/FFmpeg/QML tooling
NEEDED_PYSIDE_MODULES = [
    'PySide6',  # ← el package __init__.py
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtNetwork',
    'PySide6.QtUiTools',
    'PySide6.QtDBus',
    'PySide6.QtSvg',
    'PySide6.QtSvgWidgets',
    'PySide6.QtXml',
    'PySide6.QtPrintSupport',
    'PySide6.QtOpenGL',
    'PySide6.QtOpenGLWidgets',
]

# ── La única data que necesitamos de PySide6 (además de lo que los hooks
#    recolectan automáticamente) es el __init__.py del package.
#    Los Qt .so, plugins, y traducciones los colectan los hooks individuales.
PYSIDE_INIT = [
    ('/home/willyos/.local/lib/python3.12/site-packages/PySide6/__init__.py', 'PySide6'),
]

# ── Pillow ──
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

pil_imports = collect_submodules('Pillow')
pil_data = collect_data_files('Pillow')
pil_bin = collect_dynamic_libs('Pillow')

# ── pypresence ──
pp_imports = collect_submodules('pypresence')
pp_data = collect_data_files('pypresence')
pp_bin = collect_dynamic_libs('pypresence')

# ── Datos del proyecto ──
my_datas = [
    ('icon.png', '.'),
    ('src/langs', 'src/langs'),
    ('src/themes', 'src/themes'),
    ('Docs', 'Docs'),
]

datas = my_datas + PYSIDE_INIT + pil_data + pp_data
binaries = pil_bin + pp_bin
hiddenimports = (NEEDED_PYSIDE_MODULES
                 + ['PIL._tkinter_finder', 'pypresence']
                 + pil_imports + pp_imports)

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CianovaLauncherMCPE',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.png'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=False,
    upx_exclude=[],
    name='CianovaLauncherMCPE',
)
