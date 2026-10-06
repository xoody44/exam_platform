# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

a = Analysis(
    ['client_entry.py'],
    pathex=[str(Path(SPECPATH))],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtNetwork',
        'PyQt6.QtSvg',
        'psutil',
        'psutil._pswindows',
        'requests',
        'urllib3',
        'urllib3.contrib.pyopenssl',
        'certifi',
        'charset_normalizer',
        'idna',
        'encodings.idna',
        'email.mime.text',
        'email.mime.multipart',
        'anyio._backends._asyncio',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy',
        'PIL', 'pytest', 'IPython', 'jupyter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ExamClient',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)