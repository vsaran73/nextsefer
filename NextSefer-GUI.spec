# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
import os
import sys

# Dinamik yollar
current_dir = os.path.abspath('.')
django_app_path = os.path.join(current_dir, 'sefer_app')
django_project_path = os.path.join(current_dir, 'nextsefer')

# Django için gerekli veri dosyalarını otomatik topla
django_datas = collect_data_files('django')

# Tkinter bağımlılıklarını tamamen devre dışı bırak
block_cipher = None

a = Analysis(
    ['app_launcher.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        ('manage.py', '.'),
        ('db.sqlite3', '.'),
        ('nextsefer', 'nextsefer'),
        ('sefer_app', 'sefer_app'),
        ('static', 'static'),
        ('staticfiles', 'staticfiles'),
        ('fonts', 'fonts'),
    ] + django_datas,
    hiddenimports=[
        'django',
        'django.template.defaulttags',
        'django.template.defaultfilters',
        'django.template.loader_tags',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'sefer_app',
        'sefer_app.models',
        'sefer_app.views',
        'sefer_app.urls',
        'pwa',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', '_tkinter', 'Tkinter', 'tk', 'tcl', 'Tcl', 'Tk'],  # Tüm Tkinter bağımlılıklarını dışla
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Tcl/Tk ile ilgili dosyaları manuel olarak çıkar
a.binaries = [x for x in a.binaries if not x[0].startswith("tcl")]
a.binaries = [x for x in a.binaries if not x[0].startswith("_tkinter")]
a.binaries = [x for x in a.binaries if not x[0].startswith("tk")]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NextSefer-GUI',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NextSefer-GUI',
)
