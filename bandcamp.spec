# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

curl_cffi_datas, curl_cffi_binaries, curl_cffi_hidden = collect_all('curl_cffi')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=curl_cffi_binaries,
    datas=[
        ('assets', 'assets'),
        *curl_cffi_datas,
    ],
    hiddenimports=[
        'PySide6.QtSvg',
        'PySide6.QtNetwork',
        *curl_cffi_hidden,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

_STRIP_BINARIES = (
    'libvlc',
    'libvlccore',
    'libavcodec',
    'libavformat',
    'libavutil',
    'libswresample',
    'libswscale',
    'libfontconfig',
)
a.binaries = [b for b in a.binaries if not b[0].startswith(_STRIP_BINARIES)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='bandcamp-player',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.png',
)