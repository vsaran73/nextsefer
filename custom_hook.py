"""
PyInstaller için özel runtime hook.
Bu dosya, PyInstaller'ın _tkinter runtime hook'unu geçersiz kılar.
"""
import os
import sys
import importlib.util

# Tkinter modüllerini tamamen yasakla
sys.modules['tkinter'] = None
sys.modules['_tkinter'] = None
sys.modules['Tkinter'] = None
sys.modules['tk'] = None
sys.modules['tcl'] = None

# PyInstaller'ın _tkinter runtime hook'unu devre dışı bırak
def _disable_tkinter_hook():
    # PyInstaller hook dizinini bul
    for path in sys.path:
        rthooks_path = os.path.join(path, 'PyInstaller', 'hooks', 'rthooks')
        tk_hook_path = os.path.join(rthooks_path, 'pyi_rth__tkinter.py')
        
        if os.path.exists(tk_hook_path):
            # Hook dosyasının içeriğini geçersiz kıl
            with open(tk_hook_path, 'w') as f:
                f.write("# Tkinter hook disabled\n")
            break

# Uygulama başlatılırken Tkinter hook'unu devre dışı bırak
try:
    _disable_tkinter_hook()
except:
    pass

# Çalışma dizini düzelt
def _fix_working_directory():
    try:
        # PyInstaller tarafından paketlendiyse
        if getattr(sys, 'frozen', False):
            # Çalışma dizinini exe'nin bulunduğu dizine ayarla
            bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
            os.chdir(bundle_dir)
            return bundle_dir
        return os.path.abspath(os.path.dirname(__file__))
    except:
        return os.path.abspath(os.path.dirname(__file__))

# Django çevre değişkenlerini ayarla
def _pyi_rthook():
    base_dir = _fix_working_directory()
    
    # Çalışma dizini doğru ayarlandı mı kontrol et
    print(f"Çalışma dizini: {os.getcwd()}")
    print(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'Not set')}")
    
    # Django ayarlarını yapılandır
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nextsefer.settings")
    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    
    # Debug mod aktif
    os.environ.setdefault("DEBUG", "True")
    
    # SQLite veritabanı dosyasının konumunu ayarla
    if getattr(sys, 'frozen', False):
        db_path = os.path.join(base_dir, "db.sqlite3")
        if os.path.exists(db_path):
            os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")
    
    # Import başarılı mı kontrol et
    try:
        import django
        print(f"Django versiyonu: {django.get_version()}")
    except Exception as e:
        print(f"Django import hatası: {e}")

# Hook çalıştır
_pyi_rthook() 
 
 
 