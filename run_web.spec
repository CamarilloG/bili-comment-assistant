# -*- mode: python ; coding: utf-8 -*-
# Web ???? exe ?????????????? pyinstaller run_web.spec

# ?????????_MEIPASS ?? _web_base ???? frontend-v2/dist?frontend
block_cipher = None
app_dir = 'app'
datas = [
    # ??? app ???????????frozen ?? sys._MEIPASS/app ?? Python ?
    (app_dir, 'app'),
    (f'{app_dir}/web/frontend-v2/dist', 'frontend-v2/dist'),
    (f'{app_dir}/web/frontend', 'frontend'),
    (f'{app_dir}/server/static', 'server/static'),
]

a = Analysis(
    [f'{app_dir}/run_web.py'],
    pathex=[app_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'main',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'core.config',
        'winotify',
        'web',
        'web.app',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
    ],
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
    name='BiliBot_Web_v3.11',
    icon=f'{app_dir}/pmkix-xoym4-001.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
