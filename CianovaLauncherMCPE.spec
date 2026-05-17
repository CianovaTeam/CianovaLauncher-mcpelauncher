# CianovaLauncherMCPE.spec corregido
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# IMPORTANTE: Asegúrate de que la ruta a main.py sea correcta
# Si main.py está en la carpeta 'src'
block_cipher = None

# Recolectamos todo lo necesario
from PyInstaller.utils.hooks import collect_all

block_cipher = None

tmp_ret_pyside = collect_all('PySide6')
tmp_ret_pil = collect_all('Pillow')
tmp_ret_pypresence = collect_all('pypresence')

# Definimos los datos manuales: ('origen', 'destino')
my_datas = [
    ('icon.png', '.'),
    ('src/langs', 'src/langs'),
    ('src/themes', 'src/themes'),
    ('Docs', 'Docs')
]

# Sumamos los datos de las librerías a los nuestros
datas = my_datas + tmp_ret_pyside[0] + tmp_ret_pil[0] + tmp_ret_pypresence[0]
binaries = tmp_ret_pyside[1] + tmp_ret_pil[1] + tmp_ret_pypresence[1]
hiddenimports = ['PySide6', 'PySide6.QtCore', 'PySide6.QtWidgets', 'PySide6.QtGui', 'PIL._tkinter_finder', 'pypresence'] + tmp_ret_pyside[2] + tmp_ret_pil[2] + tmp_ret_pypresence[2]

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
    strip=False,
    upx=True,
    console=False, # Pon True si quieres ver errores en terminal al probar
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.png'], # Este es el icono del .exe en el explorador
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CianovaLauncherMCPE',
)
