@echo off
echo NextSefer Kurulum Paketi Hazırlama
echo ==================================
echo.

REM Node.js ve npm'in kurulu olduğundan emin olun
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo Node.js bulunamadı! Node.js'nin kurulu olduğundan emin olun.
    pause
    exit /b 1
)

REM Python'un kurulu olduğundan emin olun
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python bulunamadı! Python'un kurulu olduğundan emin olun.
    pause
    exit /b 1
)

REM Gerekli npm paketlerini yükle
echo Gerekli npm paketleri yükleniyor...
call npm install
call npm install png-to-ico --save-dev
if %errorlevel% neq 0 (
    echo npm paketleri yüklenemedi.
    pause
    exit /b 1
)

REM İkon dosyasını hazırla
if not exist icon.ico (
    echo icon.ico dosyası bulunamadı, PNG'den dönüştürülüyor...
    call node create-icon.js
    if %errorlevel% neq 0 (
        echo İkon dönüştürme hatası! Varsayılan ikon kullanılacak.
    )
)

REM Kontrol et: python_dist zaten var mı?
if exist python_dist\manage.py (
    set /p USEEXISTING="python_dist dizini zaten var. Yeniden oluşturmak istiyor musunuz? (E/H): "
    if /i "%USEEXISTING%"=="H" goto skip_python_dist
)

REM Python dağıtımını hazırla
echo Python dağıtımı hazırlanıyor...
python simple_prepare_dist.py
if %errorlevel% neq 0 (
    echo.
    echo UYARI: Python dağıtımı hazırlanamadı.
    echo python_dist dizini zaten var mı kontrol ediliyor...
    
    if exist python_dist\manage.py (
        echo Mevcut python_dist dizini kullanılacak.
    ) else (
        echo python_dist dizini uygun değil veya eksik.
        pause
        exit /b 1
    )
)

:skip_python_dist
echo Python dağıtımı hazır.

REM Electron paketini oluştur
echo Electron kurulum paketi oluşturuluyor...
call npm run build
if %errorlevel% neq 0 (
    echo Electron paketi oluşturulamadı.
    pause
    exit /b 1
)

echo.
echo Kurulum paketi hazırlama tamamlandı!
echo Kurulum dosyası: dist\NextSefer-Setup-1.0.0.exe
echo.
pause 