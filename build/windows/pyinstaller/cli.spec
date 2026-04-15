# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

project_root = Path.cwd()
bundled_dir = project_root / "qltoq3" / "bundled"
datas = []
if bundled_dir.is_dir():
    datas.append((str(bundled_dir), "qltoq3/bundled"))
icon_path = os.environ.get("QLTOQ3_ICON_PATH") or str(bundled_dir / "logo.ico")
icon = icon_path if Path(icon_path).is_file() else None

a = Analysis(
    [str(project_root / "build" / "windows" / "pyinstaller" / "run_cli.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="qltoq3-cli",
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
    icon=icon,
)
