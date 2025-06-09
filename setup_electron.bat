@echo off
echo NextSefer Electron Kurulumu
echo ====================================
echo.

REM Node.js kurulumunu kontrol et
node -v >nul 2>&1
if %errorlevel% neq 0 (
    echo HATA: Node.js bulunamadı. Lütfen önce Node.js kurun.
    echo https://nodejs.org/en/download/ adresinden indirebilirsiniz.
    pause
    exit /b 1
)

REM Python kurulumunu kontrol et
python -c "print('Python OK')" >nul 2>&1
if %errorlevel% neq 0 (
    echo HATA: Python bulunamadı. Lütfen önce Python 3.8 veya üstünü kurun.
    echo https://www.python.org/downloads/ adresinden indirebilirsiniz.
    pause
    exit /b 1
)

REM Node.js bağımlılıklarını kur
echo Node.js bağımlılıkları yükleniyor...
call npm install
if %errorlevel% neq 0 (
    echo HATA: Node.js bağımlılıkları yüklenemedi.
    pause
    exit /b 1
)

REM Python virtualenv veya venv paketi için hazırlık
echo Python sanal ortam araçları kontrol ediliyor...
pip install virtualenv
if %errorlevel% neq 0 (
    echo UYARI: virtualenv paketi yüklenemedi, built-in venv modülü kullanılacak.
    python -c "import venv" >nul 2>&1
    if %errorlevel% neq 0 (
        echo HATA: Ne virtualenv ne de venv modülü bulunamadı.
        pause
        exit /b 1
    )
)

REM Python dağıtımını hazırla
echo Python dağıtımı hazırlanıyor...
python prepare_python_dist.py
if %errorlevel% neq 0 (
    echo HATA: Python dağıtımı oluşturulamadı.
    pause
    exit /b 1
)

REM İkon dosyası için varsayılan bir dosya oluştur (yoksa)
if not exist icon.ico (
    echo Varsayılan ikon dosyası oluşturuluyor...
    echo Bu dosyayı kendi logonuzla değiştirmelisiniz.
    copy %WINDIR%\System32\SHELL32.dll,13 icon.ico >nul 2>&1
    if not exist icon.ico (
        echo UYARI: Varsayılan ikon oluşturulamadı.
        echo Lütfen projeye manuel olarak bir icon.ico dosyası ekleyin.
    )
)

echo.
echo ===============================
echo Kurulum tamamlandı!
echo.
echo Uygulamayı test etmek için: npm run dev
echo Uygulamayı paketlemek için: npm run build
echo ===============================
pause 