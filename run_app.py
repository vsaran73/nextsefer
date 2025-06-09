#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import logging
import threading
import webbrowser
import traceback

# Log dosyasını kullanıcı klasörüne yaz
log_dir = os.path.join(os.path.expanduser("~"), "NextSefer_Logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "app_log.txt")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("nextsefer")

def check_requirements():
    """Gerekli Python modüllerini kontrol et ve eksikse yükle"""
    required_modules = [
        'django',
        'requests',
        'reportlab',
        'openpyxl',
        'Pillow'
    ]
    
    missing_modules = []
    
    logger.info("Gerekli modüller kontrol ediliyor...")
    
    for module in required_modules:
        try:
            __import__(module)
            logger.info(f"- {module}: OK")
        except ImportError:
            logger.warning(f"- {module}: Bulunamadı")
            missing_modules.append(module)
    
    if missing_modules:
        logger.warning(f"Eksik modüller: {', '.join(missing_modules)}")
        
        try:
            logger.info("Eksik modüller kuruluyor...")
            for module in missing_modules:
                logger.info(f"Kuruluyor: {module}")
                subprocess.run([sys.executable, '-m', 'pip', 'install', module], 
                               check=True, capture_output=True)
                logger.info(f"- {module} kuruldu")
            
            logger.info("Tüm modüller başarıyla kuruldu!")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Modül kurulumunda hata: {e}")
            logger.error(f"Hata çıktısı: {e.stderr.decode('utf-8', errors='replace')}")
            
            # Kullanıcıya hata mesajı göster
            error_message = f"""
Bazı gerekli Python modülleri kurulamadı ve NextSefer çalışamayabilir.
Eksik modüller: {', '.join(missing_modules)}

Hatanın çözümü için aşağıdakileri deneyin:
1. Python'u yönetici olarak çalıştırın ve şu komutu yazın:
   pip install {' '.join(missing_modules)}

2. İnternet bağlantınızı kontrol edin

3. Destek için iletişime geçin
"""
            print(error_message)
            return False
        
        except Exception as e:
            logger.error(f"Modül kurulumunda beklenmedik hata: {str(e)}")
            traceback.print_exc()
            return False
    
    return True

def clean_tcltk_env():
    """TCL/TK ile ilgili ortam değişkenlerini temizle"""
    tcl_vars = ['TCL_LIBRARY', 'TK_LIBRARY', 'TCLTK_PATH', 'TCL_ROOT']
    
    for var in tcl_vars:
        if var in os.environ:
            logger.info(f"Siliniyor: {var}={os.environ[var]}")
            os.environ[var] = ''
    
    logger.info("TCL/TK ortam değişkenleri temizlendi.")
    
    # Ayrıca geçici dosya dizininindeki TCL verilerini bulmaya çalışma
    os.environ["PYINSTALLER_NO_TCL"] = "1"

# Tarayıcıyı açmak için değişken ve kilit
browser_opened = False
browser_lock = threading.Lock()

def open_browser_once(delay=2):
    """Tarayıcıyı bir kez aç"""
    global browser_opened
    
    def _open_browser():
        global browser_opened
        with browser_lock:
            if not browser_opened:
                try:
                    url = "http://127.0.0.1:8000"
                    webbrowser.open(url)
                    browser_opened = True
                    logger.info(f"Tarayıcı açıldı: {url}")
                except Exception as e:
                    logger.error(f"Tarayıcı açılırken hata: {e}")
    
    # Bu özelliği devre dışı bırak - tarayıcı otomatik açılmasın
    # threading.Timer(delay, _open_browser).start()

def run_django():
    """Django sunucusunu başlat"""
    try:
        logger.info("Django sunucusu başlatılıyor...")
        
        # Çalışma dizinini ayarla
        current_dir = os.path.abspath(os.path.dirname(__file__))
        sys.path.append(current_dir)
        
        # Django ayarlarını yükle
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nextsefer.settings")
        
        try:
            from django.core.management import execute_from_command_line
        except ImportError:
            logger.error("Django modülü bulunamadı! Gereksinimleri kontrol edin.")
            print("\nHATA: Django modülü yüklü değil!")
            print("Lütfen terminalde şu komutu çalıştırın: pip install django\n")
            input("Çıkmak için bir tuşa basın...")
            sys.exit(1)
        
        # Sunucuyu başlat
        execute_from_command_line(["manage.py", "runserver", "8000"])
        
    except Exception as e:
        logger.error(f"Django sunucusu başlatılırken hata: {e}")
        logger.error(traceback.format_exc())
        print("\nHATA: Django sunucusu başlatılamadı!")
        print(f"Hata mesajı: {str(e)}\n")
        input("Devam etmek için bir tuşa basın...")
        sys.exit(1)

def ensure_migrations():
    try:
        import django
        import os
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nextsefer.settings")
        django.setup()
        from django.core.management import call_command
        call_command('makemigrations', interactive=False)
        call_command('migrate', interactive=False)
        print("Veritabanı tabloları başarıyla oluşturuldu.")
    except Exception as e:
        print(f"Veritabanı migrate işlemi başarısız: {e}")

if __name__ == "__main__":
    try:
        # TCL/TK ortam değişkenlerini temizle
        clean_tcltk_env()
        
        # Gereksinimleri kontrol et
        if not check_requirements():
            logger.warning("Bazı gereksinimler eksik, uygulama düzgün çalışmayabilir.")
            print("\nUYARI: Bazı gereksinimler eksik!")
            print("Uygulama başlatılmaya devam ediliyor, ancak hatalar oluşabilir.\n")
        
        # Otomatik migrate işlemi
        ensure_migrations()
        
        # Django sunucusunu başlat
        run_django()
        
    except KeyboardInterrupt:
        logger.info("Uygulama kullanıcı tarafından sonlandırıldı.")
    except Exception as e:
        logger.error(f"Beklenmeyen hata: {e}")
        logger.error(traceback.format_exc())
        print(f"\nKRİTİK HATA: {str(e)}")
        input("Devam etmek için bir tuşa basın...") 