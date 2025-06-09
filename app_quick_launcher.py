#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NextSefer uygulama başlatıcı - Django ve Electron'u birlikte başlatır
"""

import os
import sys
import subprocess
import time
import threading
import signal
import webbrowser
import http.client
import logging
import platform
import atexit

# Log dosyasını kullanıcı klasörüne yaz
log_dir = os.path.join(os.path.expanduser("~"), "NextSefer_Logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "quick_launcher.log")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("launcher")

# Global değişkenler
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
DJANGO_PORT = 8000
electron_process = None
django_process = None
should_exit = False

def start_django_server():
    """Django sunucusunu başlatır"""
    logger.info("Django sunucusu başlatılıyor...")
    
    # Python yürütülebilir dosyası
    python_exe = sys.executable
    
    # Python dağıtımı yolu
    python_dist = os.path.join(SCRIPT_DIR, "python_dist")
    
    # Django başlatma betiği
    run_app_py = os.path.join(python_dist, "run_app.py")
    
    if not os.path.exists(run_app_py):
        logger.error(f"Django betiği bulunamadı: {run_app_py}")
        return None
    
    # Django sunucusunu başlat
    cmd = [python_exe, run_app_py]
    
    logger.info(f"Çalıştırılan komut: {' '.join(cmd)}")
    logger.info(f"Çalışma dizini: {python_dist}")
    
    django_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=python_dist,
        env=dict(os.environ, PYTHONPATH=python_dist)
    )
    
    # Çıktıyı ayrı bir iş parçacığında oku
    def log_output(stream, level_func):
        for line in iter(stream.readline, b''):
            line_str = line.decode('utf-8', errors='replace').strip()
            level_func(f"Django: {line_str}")
    
    threading.Thread(
        target=log_output, 
        args=(django_process.stdout, logger.info),
        daemon=True
    ).start()
    
    threading.Thread(
        target=log_output, 
        args=(django_process.stderr, logger.error),
        daemon=True
    ).start()
    
    logger.info(f"Django sunucu işlemi başlatıldı (PID: {django_process.pid})")
    return django_process

def check_django_server():
    """Django sunucusunun hazır olup olmadığını kontrol eder"""
    logger.info("Django sunucusu kontrol ediliyor...")
    max_attempts = 30  # 30 saniye bekle
    
    for attempt in range(max_attempts):
        try:
            conn = http.client.HTTPConnection("localhost", DJANGO_PORT)
            conn.request("HEAD", "/login/")
            response = conn.getresponse()
            conn.close()
            
            if response.status in [200, 302]:
                logger.info(f"Django sunucusu hazır! (Durum: {response.status})")
                return True
        except Exception as e:
            logger.debug(f"Django henüz hazır değil: {e}")
        
        # Çıkış işareti kontrol ediliyor mu?
        if should_exit:
            logger.info("Çıkış sinyali alındı, Django kontrolü durduruldu")
            return False
            
        time.sleep(1)
        if (attempt + 1) % 5 == 0:
            logger.info(f"Django sunucusu hâlâ bekleniyor... ({attempt + 1}/{max_attempts})")
    
    logger.error("Django sunucusu başlatılamadı!")
    return False

def start_electron_app():
    """Electron uygulamasını başlatır"""
    logger.info("Electron uygulaması başlatılıyor...")
    
    # Electron komutu
    if platform.system() == "Windows":
        npm_cmd = "npm.cmd"
    else:
        npm_cmd = "npm"
    
    cmd = [npm_cmd, "start"]
    
    logger.info(f"Çalıştırılan komut: {' '.join(cmd)}")
    
    electron_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=SCRIPT_DIR
    )
    
    # Çıktıyı ayrı bir iş parçacığında oku
    def log_output(stream, level_func):
        for line in iter(stream.readline, b''):
            line_str = line.decode('utf-8', errors='replace').strip()
            level_func(f"Electron: {line_str}")
    
    threading.Thread(
        target=log_output, 
        args=(electron_process.stdout, logger.info),
        daemon=True
    ).start()
    
    threading.Thread(
        target=log_output, 
        args=(electron_process.stderr, logger.error),
        daemon=True
    ).start()
    
    logger.info(f"Electron uygulama işlemi başlatıldı (PID: {electron_process.pid})")
    return electron_process

def cleanup_processes():
    """İşlemleri temizle"""
    global electron_process, django_process, should_exit
    
    should_exit = True
    logger.info("Uygulamalar kapatılıyor...")
    
    if electron_process:
        logger.info(f"Electron işlemi sonlandırılıyor (PID: {electron_process.pid})...")
        try:
            if platform.system() == "Windows":
                electron_process.terminate()
            else:
                electron_process.send_signal(signal.SIGTERM)
            electron_process.wait(timeout=5)
        except Exception as e:
            logger.error(f"Electron işlemi kapatılamadı: {e}")
            try:
                electron_process.kill()
            except:
                pass
    
    if django_process:
        logger.info(f"Django işlemi sonlandırılıyor (PID: {django_process.pid})...")
        try:
            if platform.system() == "Windows":
                django_process.terminate()
            else:
                django_process.send_signal(signal.SIGTERM)
            django_process.wait(timeout=5)
        except Exception as e:
            logger.error(f"Django işlemi kapatılamadı: {e}")
            try:
                django_process.kill()
            except:
                pass
    
    logger.info("Tüm işlemler temizlendi.")

def signal_handler(sig, frame):
    """Sinyal işleyicisi"""
    logger.info(f"Sinyal alındı: {sig}")
    cleanup_processes()
    sys.exit(0)

def main():
    """Ana fonksiyon"""
    global electron_process, django_process
    
    logger.info("NextSefer Launcher başlatılıyor...")
    
    # Çıkışta temizlik işlemini kaydet
    atexit.register(cleanup_processes)
    
    # Sinyal işleyicileri ayarla
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Django sunucusunu başlat
    django_process = start_django_server()
    if not django_process:
        logger.error("Django sunucusu başlatılamadı, çıkılıyor...")
        return 1
    
    # Django sunucusunun hazır olmasını bekle
    if not check_django_server():
        logger.error("Django sunucusu hazır değil, çıkılıyor...")
        cleanup_processes()
        return 1
    
    # Electron uygulamasını başlat
    electron_process = start_electron_app()
    if not electron_process:
        logger.error("Electron uygulaması başlatılamadı, çıkılıyor...")
        cleanup_processes()
        return 1
    
    # Her iki işlemin de tamamlanmasını bekle
    try:
        # Django sunucusu normalde ön planda çalışır, bu yüzden
        # burada Electron'un kapanmasını bekliyoruz
        electron_process.wait()
    except KeyboardInterrupt:
        logger.info("Klavye kesintisi alındı, çıkılıyor...")
    finally:
        cleanup_processes()
    
    logger.info("NextSefer Launcher tamamlandı.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 