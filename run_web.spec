# -*- mode: python ; coding: utf-8 -*-
# Web 版单文件 exe 打包配置。在项目根目录执行: pyinstaller run_web.spec

# 静态资源：解压到 _MEIPASS 后与 _web_base 拼接得到 frontend-v2/dist、frontend
block_cipher = None
app_dir = 'app'
datas = [
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
    name='B站评论助手_Web',
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
