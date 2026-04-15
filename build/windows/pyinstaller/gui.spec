# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_root = Path.cwd()
bundled_dir = project_root / "qltoq3" / "bundled"
datas = collect_data_files("customtkinter")
if bundled_dir.is_dir():
    datas.append((str(bundled_dir), "qltoq3/bundled"))

hiddenimports = collect_submodules("customtkinter")
icon_path = bundled_dir / "logo.ico"
icon = str(icon_path) if icon_path.is_file() else None

a = Analysis(
    [str(project_root / "qltoq3" / "gui.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="qltoq3-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
