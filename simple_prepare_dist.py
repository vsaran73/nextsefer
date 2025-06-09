#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NextSefer için basit Python dağıtımı hazırlama scripti.
Bu script, Electron ile birlikte dağıtılmak üzere Python uygulamasını hazırlar.
"""

import os
import sys
import shutil
import subprocess
import platform

# Yapılandırma
PROJ_DIR = os.path.abspath(os.path.dirname(__file__))
DIST_DIR = os.path.join(PROJ_DIR, 'python_dist')

def cleanup():
    """Önceki dağıtımı temizle"""
    print("Daha önce oluşturulmuş dağıtım dizini temizleniyor...")
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR, exist_ok=True)

def copy_python():
    """Python çalıştırılabilir dosyasını kopyala"""
    print("Python çalıştırılabilir dosyası kopyalanıyor...")
    
    # İşletim sistemine göre Python çalıştırılabilir dosyası
    if platform.system() == "Windows":
        python_exe = sys.executable
        target_exe = os.path.join(DIST_DIR, 'python.exe')
    else:
        python_exe = sys.executable
        target_exe = os.path.join(DIST_DIR, 'python')
    
    # Python çalıştırılabilir dosyasını kopyala
    print(f"Kopyalanıyor: {python_exe} -> {target_exe}")
    shutil.copy2(python_exe, target_exe)

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
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)

    # Gerekli Django paketlerini site-packages dizinine kopyala
    print("Django gereksinimleri yükleniyor...")
    try:
        # site-packages dizinini oluştur
        lib_dir = os.path.join(DIST_DIR, 'lib', 'site-packages')
        os.makedirs(lib_dir, exist_ok=True)
        
        # Django ve gerekli kütüphaneler
        install_requirements(lib_dir)
    except Exception as e:
        print(f"Django gereksinimlerini yüklerken hata: {e}")

def install_requirements(lib_dir):
    """Django ve gerekli kütüphaneleri site-packages'e kopyala"""
    # Gerekli paketler
    requirements = [
        'django',
        'requests',
        'pillow',
        'reportlab',
        'openpyxl',
        'xlwt'
    ]
    
    # Geçici bir sanal ortam oluşturup paketleri indir
    temp_venv = os.path.join(PROJ_DIR, 'temp_venv')
    if not os.path.exists(temp_venv):
        print("Geçici sanal ortam oluşturuluyor...")
        try:
            subprocess.check_call([sys.executable, '-m', 'venv', temp_venv])
        except Exception as e:
            print(f"Sanal ortam oluşturma hatası: {e}")
            return False
    
    # Sanal ortamdaki pip yolu
    pip_exe = os.path.join(temp_venv, 'Scripts', 'pip.exe') if platform.system() == "Windows" else os.path.join(temp_venv, 'bin', 'pip')
    
    # Her paketi yükle
    for req in requirements:
        print(f"Yükleniyor: {req}")
        try:
            subprocess.check_call([pip_exe, 'install', req])
        except Exception as e:
            print(f"Paket yükleme hatası ({req}): {e}")
    
    # Paketleri hedef dizine kopyala
    site_packages = os.path.join(temp_venv, 'Lib', 'site-packages') if platform.system() == "Windows" else os.path.join(temp_venv, 'lib', 'python*', 'site-packages')
    
    # Glob kullanarak site-packages'i bul
    import glob
    site_packages_dirs = glob.glob(site_packages)
    
    if not site_packages_dirs:
        print(f"Sanal ortamda site-packages bulunamadı: {site_packages}")
        return False
    
    site_packages = site_packages_dirs[0]
    print(f"Paketler kopyalanıyor: {site_packages} -> {lib_dir}")
    
    # Her dizin ve dosyayı kopyala
    for item in os.listdir(site_packages):
        src = os.path.join(site_packages, item)
        dst = os.path.join(lib_dir, item)
        
        # django, reportlab, pillow gibi ana paketleri kopyala
        if os.path.isdir(src) and item.lower() in [req.lower() for req in requirements]:
            print(f"Kopyalanıyor: {item}")
            shutil.copytree(src, dst, dirs_exist_ok=True)
    
    return True

def create_batch_launcher():
    """Windows için başlatma batch dosyası oluştur"""
    if platform.system() == "Windows":
        print("Başlatma batch dosyası oluşturuluyor...")
        batch_content = '''@echo off
cd /d "%~dp0"
echo Django başlatılıyor...
python.exe manage.py runserver 127.0.0.1:8000
'''
        with open(os.path.join(DIST_DIR, 'start_django.bat'), 'w') as f:
            f.write(batch_content)

def create_config():
    """Python yapılandırma dosyası oluştur"""
    print("Python yapılandırma dosyası oluşturuluyor...")
    
    config_content = f"""# Generated by simple_prepare_dist.py
home = {os.path.dirname(sys.executable)}
include-system-site-packages = true
version = {platform.python_version()}
"""
    
    with open(os.path.join(DIST_DIR, 'pyvenv.cfg'), 'w') as f:
        f.write(config_content)

def main():
    """Ana işlev"""
    try:
        print("Python dağıtımı hazırlanıyor...")
        cleanup()
        copy_python()
        copy_django_app()
        create_config()
        create_batch_launcher()
        print("Python dağıtımı başarıyla hazırlandı!")
        return 0
    except Exception as e:
        print(f"Hata: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 