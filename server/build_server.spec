# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

web_dist = Path(SPECPATH).parent / 'web' / 'dist'

if not web_dist.exists():
    raise SystemExit(
        f'web/dist не найден: {web_dist}\n'
        f'Сначала выполни `npm run build` в папке {web_dist.parent}'
    )

datas = [
    (str(web_dist), 'web/dist'),
]

a = Analysis(
    ['exe_entry.py'],
    pathex=[str(Path(SPECPATH))],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'httptools',
        'h11',
        'websockets',
        'multipart',
        'anyio._backends._asyncio',
        'sqlalchemy.dialects.sqlite',
        'argon2',
        'argon2.low_level',
        'argon2._ffi',
        'fastapi',
        'fastapi.applications',
        'fastapi.routing',
        'starlette.applications',
        'starlette.routing',
        'starlette.middleware',
        'starlette.middleware.cors',
        'starlette.middleware.exceptions',
        'starlette.responses',
        'starlette.staticfiles',
        'pydantic',
        'pydantic.networks',
        'pydantic.validators',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'pytest',
        'IPython',
        'jupyter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ExamServer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)