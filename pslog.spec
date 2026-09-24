# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/pslog_icon.png', 'assets'), ('config/db/locations.json', 'config/db'), ('config/db/aja_locations.json', 'config/db'), ('config/db/club_db.csv', 'config/db'), ('config/db/club_db_meta.json', 'config/db'), ('config/db/cty.dat', 'config/db'), ('config/db/cty_meta.json', 'config/db'), ('config/db/cty_LICENSE.txt', 'config/db'), ('config/templates/pdf', 'config/templates/pdf'), ('config/rules', 'config/rules'), ('config/db/contest', 'config/db/contest'), ('config/templates/cabrillo', 'config/templates/cabrillo')],
    hiddenimports=['xlrd'],
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
    [],
    exclude_binaries=True,
    name='pslog',
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
    icon=['assets\\pslog.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pslog',
)
