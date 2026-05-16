# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build spec for PhysioSkeptic
# Run: pyinstaller build.spec

import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# Collect PySide6 data and binaries
pyside6_datas, pyside6_binaries, pyside6_hidden = collect_all('PySide6')
pyqtgraph_datas, pyqtgraph_binaries, pyqtgraph_hidden = collect_all('pyqtgraph')

datas = pyside6_datas + pyqtgraph_datas + [
    ('ui', 'ui'),
    ('core', 'core'),
]

binaries = pyside6_binaries + pyqtgraph_binaries

hidden_imports = (
    pyside6_hidden + pyqtgraph_hidden + [
        # PySide6 modules
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtPrintSupport',
        'PySide6.QtSvg',
        'PySide6.QtOpenGL',
        # pyqtgraph
        'pyqtgraph',
        'pyqtgraph.graphicsItems',
        'pyqtgraph.Qt',
        # numpy / scipy
        'numpy',
        'numpy.core',
        'scipy',
        'scipy.signal',
        'scipy.interpolate',
        # stdlib
        'sqlite3',
        'json',
        'csv',
        'dataclasses',
        # optional
        'pandas',
        'requests',
        'openai',
        'anthropic',
    ]
)

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'PyQt5', 'PyQt6'],
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
    name='PhysioSkeptic',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,        # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',  # Uncomment if you add an icon
    version_file=None,
    uac_admin=False,
    uac_uiaccess=False,
)
