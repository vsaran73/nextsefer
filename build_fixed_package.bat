@echo off
echo NextSefer Kurulum Paketi Hazırlama (DÜZELTME)
echo =========================================
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
if %errorlevel% neq 0 (
    echo npm paketleri yüklenemedi.
    pause
    exit /b 1
)

REM İkon dosyasını hazırla
if not exist icon.ico (
    echo icon.ico dosyası bulunamadı, PNG'den dönüştürülüyor...
    if not exist node_modules\png-to-ico (
        call npm install png-to-ico --save-dev
    )
    call node create-icon.js
    if %errorlevel% neq 0 (
        echo İkon dönüştürme hatası! Varsayılan ikon kullanılacak.
    )
)

REM Log ve yapılandırma dizinini temizle
echo Mevcut build dizinini temizleniyor...
if exist dist (
    rmdir /s /q dist
)
if exist dist_electron (
    rmdir /s /q dist_electron
)

REM Python dağıtımını hazırla
echo Python dağıtımı hazırlanıyor...

REM python_dist dizinini otomatik olarak hazırla (USEEXISTING=E)
echo E | python simple_prepare_dist.py >nul
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

REM run_app.py dosyasının python_dist içinde olduğundan emin ol
if not exist python_dist\run_app.py (
    echo run_app.py dosyası python_dist dizininde bulunamadı, kopyalanıyor...
    copy run_app.py python_dist\run_app.py
)

REM extraResources kontrolünü göster
echo.
echo Extraresources kontrolü yapılıyor...
powershell -Command "Get-Content package.json | Select-String -Pattern 'extraResources'"
echo.

REM Electron paketini oluştur
echo.
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