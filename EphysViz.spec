# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['EphysViz.py'],
    pathex=[],
    binaries=[],
    datas=[('*.otf', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EphysViz',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['/Users/domenick_mifsud/Documents/NAY/icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EphysViz',
)
app = BUNDLE(
    coll,
    name='EphysViz.app',
    icon='/Users/domenick_mifsud/Documents/NAY/icon.ico',
    bundle_identifier=None,
)
