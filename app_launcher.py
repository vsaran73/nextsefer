#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NextSefer Başlatıcı
Bu script, NextSefer uygulamasını başlatır ve olası hataları yakalar.
"""

import os
import sys
import subprocess
import logging
import time
import traceback
import re
from datetime import datetime
import threading
import webbrowser  # Tek seferlik tarayıcı açma için
import django

# PyInstaller için gerekli fonksiyon
def get_application_path():
    """PyInstaller ile paketlenmiş uygulama için doğru yolu döndürür"""
    if getattr(sys, 'frozen', False):
        # PyInstaller ile paketlenmişse
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        return os.path.dirname(sys.executable)
    else:
        # Normal çalışıyorsa
        return os.path.abspath(os.path.dirname(__file__))

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

# Sürüm bilgisi
VERSION = "1.0.0"

# Tarayıcı açılıp açılmadığını takip etmek için global değişken
browser_opened = False
browser_lock = threading.Lock()  # Thread güvenliği için kilit ekle

# Django kurulumu yapılıp yapılmadığını kontrol etmek için bayrak
django_setup_complete = False

def setup_django():
    """Django'yu başlat"""
    global django_setup_complete
    
    # Eğer zaten kurulum yapılmışsa, tekrar yapmaya gerek yok
    if django_setup_complete:
        return True
        
    try:
        app_path = get_application_path()
        sys.path.append(app_path)
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nextsefer.settings")
        django.setup()
        django_setup_complete = True
        logging.info("Django başarıyla başlatıldı")
        return True
    except Exception as e:
        logging.error(f"Django başlatılamadı: {e}")
        logging.error(traceback.format_exc())
        return False

def check_first_run():
    """İlk çalıştırma kontrolü yaparak kullanıcı ve şifre oluşturur"""
    try:
        # Django'yu başlat (yalnızca bir kez)
        setup_django()
        
        app_dir = get_application_path()
        db_path = os.path.join(app_dir, "db.sqlite3")
        
        # DB dosyasının boyutunu kontrol et, çok küçükse ilk kurulum olabilir
        if os.path.exists(db_path) and os.path.getsize(db_path) < 100000:
            # Django shell ile admin kullanıcısını oluştur
            try:
                from django.contrib.auth.models import User
                
                # Admin kullanıcısı varsa atla
                if not User.objects.filter(username='admin').exists():
                    User.objects.create_superuser(
                        username='admin',
                        email='admin@nextsefer.com',
                        password='nextsefer2023'
                    )
                    logging.info("Admin kullanıcısı oluşturuldu")
                    # Kullanıcıya bilgi ver
                    show_message_box(
                        "NextSefer - İlk Çalıştırma", 
                        "Hoş geldiniz! İlk kullanım için hesap oluşturuldu:\n\n"
                        "Kullanıcı adı: admin\n"
                        "Şifre: nextsefer2023\n\n"
                        "Güvenlik için lütfen şifrenizi değiştirin."
                    )
            except Exception as e:
                logging.error(f"Admin kullanıcısı oluşturulurken hata: {str(e)}")
    except Exception as e:
        logging.error(f"İlk çalıştırma kontrolünde hata: {str(e)}")

def show_message_box(title, message):
    """Farklı platformlarda mesaj kutusu gösterme"""
    try:
        # Windows'da çalışıyorsa MessageBox kullan
        if sys.platform == 'win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0)
        else:
            # Diğer platformlarda konsola yaz
            print(f"\n{title}\n{'-'*len(title)}\n{message}\n")
    except Exception as e:
        # Mesaj gösterme başarısız olursa log'a yaz ve devam et
        logging.error(f"Mesaj gösteriminde hata: {str(e)}")
        print(f"\n{title}\n{'-'*len(title)}\n{message}\n")

def open_browser_once():
    """Tarayıcı açma fonksiyonu - şimdilik devre dışı"""
    # Tarayıcı açma işlemini devre dışı bırakıyoruz - sorunları çözmek için
    logging.info("Tarayıcı otomatik açma devre dışı bırakıldı")
    return

def start_nextsefer():
    """Ana uygulamayı başlatır."""
    logging.info(f"NextSefer başlatıcı çalışıyor... Sürüm: {VERSION}")
    
    # Uygulama dizini
    app_dir = get_application_path()
    exec_dir = os.path.dirname(sys.executable)
    
    logging.info(f"Uygulama dizini: {app_dir}")
    logging.info(f"Çalıştırılabilir dizini: {exec_dir}")
    
    # Kendimizi uygulamanın ana örneği olarak işaretle
    # Böylece birden çok kopyanın çalışmasını önleriz
    if os.path.exists(os.path.join(app_dir, "running.lock")):
        logging.info("Uygulama zaten çalışıyor. İkinci kopya başlatılmayacak.")
        show_message_box(
            "NextSefer - Zaten Çalışıyor",
            "NextSefer uygulaması zaten çalışıyor.\nLütfen tarayıcınızda http://localhost:8000 adresine gidin veya mevcut kopyayı kapatın."
        )
        # Tarayıcıyı açıp ana sayfaya yönlendir
        webbrowser.open_new("http://localhost:8000/login/")
        return True
    else:
        # Kilit dosyası oluştur
        try:
            with open(os.path.join(app_dir, "running.lock"), "w") as f:
                f.write(f"PID: {os.getpid()}")
        except Exception as e:
            logging.error(f"Kilit dosyası oluşturulamadı: {str(e)}")
    
    # Program kapanınca kilit dosyası silmek için handler ekle
    def cleanup_on_exit():
        try:
            app_dir = get_application_path()
            lock_file = os.path.join(app_dir, "running.lock")
            if os.path.exists(lock_file):
                os.remove(lock_file)
                logging.info("Kilit dosyası temizlendi.")
        except Exception as e:
            logging.error(f"Kilit dosyası temizlenirken hata: {str(e)}")
    
    # Kapat sinyali handler'ı ekle
    import atexit
    atexit.register(cleanup_on_exit)
    
    # Uygulamayı farklı konumlarda ara
    possible_paths = [
        os.path.join(app_dir, "NextSefer-GUI.exe"),
        os.path.join(app_dir, "NextSefer.exe"),
        os.path.join(exec_dir, "NextSefer-GUI.exe"),
        os.path.join(exec_dir, "NextSefer.exe"),
        os.path.join(exec_dir, "NextSefer-GUI", "NextSefer-GUI.exe")
    ]
    
    # Dosyayı bul
    exe_path = None
    for path in possible_paths:
        logging.info(f"Kontrol ediliyor: {path}")
        if os.path.exists(path):
            exe_path = path
            break
    
    if not exe_path:
        error_msg = f"NextSefer yürütülebilir dosyası bulunamadı. Aşağıdaki konumlar kontrol edildi:\n"
        for path in possible_paths:
            error_msg += f"- {path}\n"
        logging.error(error_msg)
        show_error_dialog(error_msg)
        cleanup_on_exit()  # Temizlik yap
        return False
    
    logging.info(f"NextSefer yürütülebilir dosyası bulundu: {exe_path}")
    
    try:
        # Çalışma dizinini exe'nin bulunduğu dizine ayarla
        work_dir = os.path.dirname(exe_path)
        
        try:
            # İlk çalıştırma kontrolü - bu fonksiyon içinde Django kurulumu yapılacak
            check_first_run()
        except Exception as e:
            logging.error(f"İlk çalıştırma kontrolü sırasında hata: {str(e)}")
            # Hatayı göster ama uygulamayı yine de başlat
            pass
        
        # Uygulamayı başlat
        logging.info(f"NextSefer uygulaması başlatılıyor: {exe_path}, çalışma dizini: {work_dir}")
        
        # Uygulamayı başlat (shell=False ile yeni bir konsol açılmasını önle)
        process = subprocess.Popen(exe_path, cwd=work_dir, shell=False)
        
        # Tarayıcıyı ayrı bir thread'de aç (yalnızca bir kez)
        browser_thread = threading.Thread(target=open_browser_once)
        browser_thread.daemon = True
        browser_thread.start()
        
        # Kullanıcıya bilgi ver
        show_message_box(
            "NextSefer - Uygulama Başlatıldı", 
            "NextSefer başarıyla başlatıldı!\n\n"
            "Uygulama tarayıcınızda açılacak.\n"
            "Eğer otomatik açılmazsa, aşağıdaki adresi manuel olarak açabilirsiniz:\n"
            "http://localhost:8000/login/"
        )
        
        return True
    except Exception as e:
        error_msg = f"NextSefer başlatılırken hata oluştu: {str(e)}"
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        show_error_dialog(error_msg)
        cleanup_on_exit()  # Temizlik yap
        return False

def show_error_dialog(message):
    """Hata mesajını göster"""
    logging.error(message)
    show_message_box("NextSefer - Hata", message)

if __name__ == "__main__":
    try:
        start_nextsefer()
    except Exception as e:
        logging.critical(f"Kritik hata: {str(e)}")
        logging.critical(traceback.format_exc())
        show_error_dialog(f"Beklenmeyen bir hata oluştu:\n{str(e)}\n\nDetaylar için log dosyasını kontrol edin: {log_file}") 
 
 
 