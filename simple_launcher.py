#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NextSefer Basit Başlatıcı
Bu script, Django'yu doğrudan başlatır.
"""

import os
import sys
import logging
import subprocess
from datetime import datetime

# Log dosyası için dizin oluştur
log_dir = os.path.join(os.path.expanduser("~"), "NextSefer_Logs")
os.makedirs(log_dir, exist_ok=True)

# Logging yapılandırması
log_file = os.path.join(log_dir, f"nextsefer_{datetime.now().strftime('%Y-%m-%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def main():
    """Ana fonksiyon"""
    try:
        # Django çalışma ortamını ayarla
        current_dir = os.path.abspath(os.path.dirname(__file__))
        sys.path.append(current_dir)
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nextsefer.settings")
        
        # Django'yu başlat
        logging.info("Django server başlatılıyor...")
        os.chdir(current_dir)
        
        # Django'yu çalıştır
        command = [sys.executable, "manage.py", "runserver", "8000"]
        logging.info(f"Çalıştırılacak komut: {' '.join(command)}")
        
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Gerçek zamanlı log çıktısı
        for line in process.stdout:
            line = line.strip()
            if line:
                logging.info(f"Django: {line}")
        
        # İşlem tamamlandı mı?
        process.wait()
        if process.returncode != 0:
            logging.error(f"Django sunucusu hata kodu ile sonlandı: {process.returncode}")
        else:
            logging.info("Django sunucusu başarıyla sonlandı.")
    
    except Exception as e:
        logging.error(f"Beklenmeyen hata: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return False
    
    return True

if __name__ == "__main__":
    main() 
 
 
 