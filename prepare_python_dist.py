#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NextSefer için Python dağıtımını hazırlama scripti.
Bu script, Electron ile birlikte dağıtılmak üzere Python uygulamasını hazırlar.
"""

import os
import sys
import shutil
import subprocess
import platform
import glob
import site
from distutils.sysconfig import get_python_lib

# Virtualenv paketi yüklü değilse otomatik yükle
try:
    import virtualenv
except ImportError:
    print("Virtualenv paketi bulunamadı. Yükleniyor...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "virtualenv"])
    import virtualenv

# Python'un venv modülünü de import et (yedek yöntem için)
try:
    import venv
except ImportError:
    pass

# Yapılandırma
PROJ_DIR = os.path.abspath(os.path.dirname(__file__))
VENV_DIR = os.path.join(PROJ_DIR, 'venv')
DIST_DIR = os.path.join(PROJ_DIR, 'python_dist')
REQUIREMENTS = [
    'django',
    'requests',
    'reportlab',
    'openpyxl',
    'Pillow',
    'xlwt'
]

def cleanup():
    """Önceki dağıtımı temizle"""
    print("Daha önce oluşturulmuş dağıtım dizini temizleniyor...")
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR, exist_ok=True)

def create_virtual_env():
    """Sanal ortam oluştur"""
    print("Sanal ortam oluşturuluyor...")
    if os.path.exists(VENV_DIR):
        print(f"Mevcut sanal ortam ({VENV_DIR}) siliniyor...")
        shutil.rmtree(VENV_DIR)
    
    # Güncel virtualenv API'sini kullan
    try:
        # Modern virtualenv sürümleri için
        import virtualenv
        from virtualenv.cli_run import cli_run
        cli_run([VENV_DIR])
    except (ImportError, AttributeError):
        # Alternatif yöntem - subprocess ile venv modülü
        print("Virtualenv API kullanılamadı, subprocess ile venv oluşturuluyor...")
        subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])

def install_requirements():
    """Gereksinimleri yükle"""
    print("Gereksinimler yükleniyor...")
    
    # Sanal ortamdaki pip yolunu belirle
    if platform.system() == "Windows":
        pip_path = os.path.join(VENV_DIR, 'Scripts', 'pip.exe')
        python_path = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
    else:
        pip_path = os.path.join(VENV_DIR, 'bin', 'pip')
        python_path = os.path.join(VENV_DIR, 'bin', 'python')
    
    # pip.exe dosyasının varlığını kontrol et
    if not os.path.exists(pip_path):
        print(f"Pip bulunamadı: {pip_path}")
        print("Python ile pip modülünü kullanmaya çalışılıyor...")
        # Python ile pip modülünü kullan
        for req in REQUIREMENTS:
            print(f"Yükleniyor: {req}")
            subprocess.check_call([python_path, '-m', 'pip', 'install', req])
        return
        
    # Gereksinimleri yükle
    for req in REQUIREMENTS:
        print(f"Yükleniyor: {req}")
        try:
            subprocess.check_call([pip_path, 'install', req])
        except subprocess.CalledProcessError:
            print(f"Pip ile kurulum başarısız oldu, python -m pip kullanılıyor...")
            subprocess.check_call([python_path, '-m', 'pip', 'install', req])

def copy_django_app():
    """Django uygulamasını dağıtım dizinine kopyala"""
    print("Django uygulaması kopyalanıyor...")
    
    # Django projesindeki önemli dosya ve dizinleri kopyala
    django_files = [
        'manage.py', 
        'run_app.py',
        'db.sqlite3', 
        'nextsefer',
        'sefer_app',
        'templates',
        'static',
        'staticfiles',
    ]
    
    for item in django_files:
        src = os.path.join(PROJ_DIR, item)
        dst = os.path.join(DIST_DIR, item)
        
        if not os.path.exists(src):
            print(f"UYARI: {src} bulunamadı, atlanıyor...")
            continue
            
        print(f"Kopyalanıyor: {item}")
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

def copy_python_libs():
    """Python kütüphanelerini dağıtım dizinine kopyala"""
    print("Python kütüphaneleri kopyalanıyor...")
    
    # Sanal ortamdaki site-packages dizinini belirle
    if platform.system() == "Windows":
        python_exe = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
    else:
        python_exe = os.path.join(VENV_DIR, 'bin', 'python')
    
    # Site packages dizinini al
    cmd = [
        python_exe, 
        '-c', 
        'import site; print(site.getsitepackages()[0])'
    ]
    site_packages = subprocess.check_output(cmd).decode('utf-8').strip()
    
    # Hedef dizini oluştur
    target_lib_dir = os.path.join(DIST_DIR, 'lib', 'site-packages')
    os.makedirs(target_lib_dir, exist_ok=True)
    
    # Tüm site-packages içeriğini kopyala
    print(f"Site packages kopyalanıyor: {site_packages} -> {target_lib_dir}")
    for item in os.listdir(site_packages):
        src = os.path.join(site_packages, item)
        dst = os.path.join(target_lib_dir, item)
        
        if os.path.isdir(src):
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst)

def copy_python_binary():
    """Python çalıştırılabilir dosyasını kopyala"""
    print("Python çalıştırılabilir dosyası kopyalanıyor...")
    
    # İşletim sistemine göre Python çalıştırılabilir dosyası
    if platform.system() == "Windows":
        python_exe = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
        target_exe = os.path.join(DIST_DIR, 'python.exe')
        
        # DLL'ler de gerekli
        dlls = glob.glob(os.path.join(os.path.dirname(python_exe), '*.dll'))
        for dll in dlls:
            dll_name = os.path.basename(dll)
            shutil.copy2(dll, os.path.join(DIST_DIR, dll_name))
            print(f"Kopyalandı: {dll_name}")
    else:
        python_exe = os.path.join(VENV_DIR, 'bin', 'python')
        target_exe = os.path.join(DIST_DIR, 'python')
    
    # Python çalıştırılabilir dosyasını kopyala
    print(f"Kopyalanıyor: {python_exe} -> {target_exe}")
    shutil.copy2(python_exe, target_exe)

def create_readme():
    """Python dağıtımı için bir README dosyası oluştur"""
    readme_content = """# NextSefer Python Distribution

Bu dizin, NextSefer Electron uygulaması için gerekli Python dağıtımını içerir.
Electron uygulaması, bu dizindeki Python çalıştırılabilir dosyasını ve Django uygulamasını kullanır.

## İçerik

- python.exe: Python çalıştırılabilir dosyası
- lib/: Python kütüphaneleri
- run_app.py: Django başlatma betiği
- manage.py: Django yönetim betiği
- nextsefer/: Django projesi
- sefer_app/: Django uygulaması
- templates/: HTML şablonları
- static/: Statik dosyalar
- db.sqlite3: SQLite veritabanı

## Gereksinimler

Bu dağıtım, aşağıdaki Python paketlerini içerir:

- Django
- Requests
- ReportLab
- OpenPyXL
- Pillow

"""
    with open(os.path.join(DIST_DIR, 'README.md'), 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("README dosyası oluşturuldu")

def main():
    """Ana fonksiyon"""
    print("NextSefer Python dağıtımı hazırlanıyor...")
    
    # Adımları uygula
    cleanup()
    create_virtual_env()
    install_requirements()
    copy_django_app()
    copy_python_libs()
    copy_python_binary()
    create_readme()
    
    print("\nPython dağıtımı hazır!")
    print(f"Dizin: {DIST_DIR}")

if __name__ == "__main__":
    main() 