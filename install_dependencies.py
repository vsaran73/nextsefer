#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NextSefer için bağımlılıkları kontrol etme ve kurma scripti.
"""

import os
import sys
import subprocess
import platform

def main():
    """Ana fonksiyon"""
    print("NextSefer bağımlılıkları kontrol ediliyor...")
    
    # Python dağıtım klasörünü belirle
    proj_dir = os.path.abspath(os.path.dirname(__file__))
    python_dist = os.path.join(proj_dir, 'python_dist')
    site_packages = os.path.join(python_dist, 'lib', 'site-packages')
    
    # Python dağıtımı var mı kontrol et
    if not os.path.exists(python_dist):
        print("HATA: Python dağıtımı bulunamadı!")
        print("Lütfen önce prepare_python_dist.py çalıştırın.")
        return 1
    
    # Gerekli paketler
    required_packages = [
        'django',
        'requests',
        'reportlab',
        'openpyxl',
        'Pillow',
        'xlwt'
    ]
    
    # Python yolunu belirle
    if platform.system() == "Windows":
        python_exe = os.path.join(python_dist, 'python.exe')
    else:
        python_exe = os.path.join(python_dist, 'python')
    
    # Python yürütülebilir dosyası var mı kontrol et
    if not os.path.exists(python_exe):
        print(f"HATA: Python yürütülebilir dosyası bulunamadı: {python_exe}")
        return 1
    
    print(f"Python dağıtımı: {python_dist}")
    print(f"Python yürütülebilir dosyası: {python_exe}")
    
    # Her paketi kontrol et ve gerekirse kur
    for package in required_packages:
        print(f"Kontrol ediliyor: {package}...")
        
        try:
            # Paket var mı kontrol et
            cmd = [python_exe, "-c", f"import {package.lower()}"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"  ✓ {package} yüklü")
            else:
                print(f"  ✗ {package} yüklü değil, kuruluyor...")
                install_cmd = [
                    python_exe, "-m", "pip", "install", 
                    package, "--target", site_packages
                ]
                subprocess.check_call(install_cmd)
                print(f"  ✓ {package} başarıyla kuruldu")
                
        except Exception as e:
            print(f"  ! HATA: {package} paketi kurulurken bir sorun oluştu: {e}")
    
    print("\nTüm bağımlılıklar kontrol edildi.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 