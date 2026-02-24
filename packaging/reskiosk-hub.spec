# -*- mode: python ; coding: utf-8 -*-
# Run from repo root: pyinstaller packaging/reskiosk-hub.spec
# pathex so the tracer finds the hub package (avoids ModuleNotFoundError: No module named 'hub' when frozen)
import os
_specdir = os.path.dirname(os.path.abspath(__file__))
_reskiosk_root = os.path.normpath(os.path.join(_specdir, '..'))

block_cipher = None

a = Analysis(
    ['../hub/launcher.py'],
    pathex=[_reskiosk_root],
    binaries=[],
    datas=[
        ('ollama_portable', 'ollama_portable'),
        ('hub_models', 'hub_models'),
        ('../console/dist', 'console_static'), # Phase 3: Bundled Console
    ],
    hiddenimports=['uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'fastapi', 'huggingface_hub', 'sentence_transformers'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'test', 'unittest', 'ipython', 'notebook'],
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
    name='ResKiosk-Hub',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Keep console for debugging in Phase 0
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ResKiosk-Hub',
)
