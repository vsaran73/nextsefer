@echo off
echo NextSefer - Final Kurulum Paketi
echo ==============================
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

REM Kuruluma başla
echo *** Kurulum paketi hazırlanıyor ***
echo.

REM Mevcut build dizinlerini temizle
echo 1/6: Eski build dizinleri temizleniyor...
if exist dist rmdir /s /q dist
if exist dist_electron rmdir /s /q dist_electron
if exist temp_venv rmdir /s /q temp_venv

REM Gerekli npm paketlerini yükle
echo 2/6: Node.js modülleri yükleniyor...
call npm install
if %errorlevel% neq 0 (
    echo Node.js modülleri yüklenemedi!
    pause
    exit /b 1
)

REM İkon kontrolü
echo 3/6: İkon dosyası kontrol ediliyor...
if not exist icon.ico (
    echo icon.ico bulunamadı, PNG'den oluşturuluyor...
    if not exist node_modules\png-to-ico (
        call npm install png-to-ico --save-dev
    )
    call node create-icon.js
)

REM Python dağıtımını geliştirilmiş şekilde hazırla
echo 4/6: Python dağıtımı hazırlanıyor...
python simple_prepare_dist.py
if %errorlevel% neq 0 (
    echo Python dağıtımı hazırlanamadı!
    pause
    exit /b 1
)

REM Ekstra dosyaları kopyala
echo 5/6: Dosyalar hazırlanıyor...
copy icon.ico python_dist\ >nul 2>nul

REM Test için Django sunucusunu başlat
echo Django sunucusu test için başlatılıyor...
start "Django Test" cmd /c "cd python_dist && python manage.py runserver 127.0.0.1:8000"

REM 5 saniye bekle
ping 127.0.0.1 -n 6 >nul

REM Test et
echo Django sunucusu test ediliyor...
powershell -Command "try { $response = Invoke-WebRequest -Uri http://127.0.0.1:8000 -UseBasicParsing -TimeoutSec 5; Write-Host 'Django sunucusu başarıyla çalışıyor!' } catch { Write-Host 'Django sunucusu yanıt vermiyor, ancak kuruluma devam edilecek...' }"

REM Django sürecini sonlandır
echo Django test süreci sonlandırılıyor...
taskkill /f /im python.exe /fi "WINDOWTITLE eq Django Test" >nul 2>nul

REM Electron paketini oluştur
echo 6/6: Electron kurulum paketi oluşturuluyor...
call npm run build
if %errorlevel% neq 0 (
    echo Electron paketi oluşturulamadı!
    pause
    exit /b 1
)

echo.
echo Kurulum paketi hazırlandı!
echo Kurulum dosyası: dist\NextSefer-Setup-1.0.0.exe
echo.
pause 