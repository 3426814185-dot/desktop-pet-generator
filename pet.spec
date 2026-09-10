# -*- mode: python ; coding: utf-8 -*-
# 文件夹模式（onedir）：启动快，不每次解压 263MB 单文件
import os

from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata

datas = []
binaries = []
hiddenimports = []

# rembg 及其依赖
for pkg in ["rembg"]:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# pymatting 的 __init__.py 用 importlib.metadata 查自身版本，
# 必须打包其 dist-info 元数据，否则运行时报 "No package metadata was found"
datas += copy_metadata("pymatting")

# onnxruntime 需要其 DLL
for pkg in ["onnxruntime", "numba", "scikit_image", "skimage", "cv2"]:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# 图标文件打包进去
datas += [("cat_paw.ico", ".")]

a = Analysis(
    ["run.py"],
    pathex=[os.path.abspath(".")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "pytest", "IPython", "notebook"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="桌宠生成器",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="cat_paw.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="桌宠生成器",
)
