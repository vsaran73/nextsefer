# -*- mode: python ; coding: utf-8 -*-
"""
NextSefer Starter için özel PyInstaller spec dosyası.
Bu dosya, Tkinter bağımlılıklarını tamamen kaldırır.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files

# Dinamik yollar
current_dir = os.path.abspath('.')
django_app_path = os.path.join(current_dir, 'sefer_app')
django_project_path = os.path.join(current_dir, 'nextsefer')

# Django için gerekli veri dosyalarını otomatik topla
django_datas = collect_data_files('django')

# Özel runtime hook oluştur
runtime_hooks = [os.path.join(current_dir, 'custom_hook.py')]

block_cipher = None

a = Analysis(
    ['NextSefer_starter.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        ('bypass_tkinter.py', '.'),
        ('version_info.txt', '.'),
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
        'bypass_tkinter',  # Tkinter devre dışı bırakmak için özel modül
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=[
        'tkinter', '_tkinter', 'Tkinter', 'tk', 'tcl', 'Tcl', 'Tk',
        '_imagingtk', 'PIL._tkinter_finder', 'PIL.ImageTk', 'FixTk'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Tcl/Tk ile ilgili dosyaları manuel olarak çıkar
a.binaries = [x for x in a.binaries if not any(tk in x[0].lower() for tk in ['tcl', '_tkinter', 'tk'])]
a.datas = [x for x in a.datas if not any(tk in x[0].lower() for tk in ['tcl', '_tkinter', 'tk'])]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NextSefer_starter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Konsol gösterme (Windows uygulaması)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/images/favicon.ico'  # İkon ekle (varsa)
) 
 
 
 