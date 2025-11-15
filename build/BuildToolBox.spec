# BuildToolBox.spec
# PyInstaller specification file for building the project
from PyInstaller.building.api import PYZ, EXE
from PyInstaller.building.build_main import Analysis

block_cipher = None

a = Analysis(
    ['../src/main.py'],      # Entry point of your application
    pathex=['../src'],       # Add 'src' folder to sys.path
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    exclude_binaries=False,   # important for one-file build with _internal
    name='main',              # executable name
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,             # False -> windowed app without console (GUI)
)
