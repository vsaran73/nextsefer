@echo off
echo NextSefer Electron Geliştirici Modu
echo ==================================
echo.

REM Node.js modüllerinin kurulu olduğunu kontrol et
if not exist node_modules (
    echo Node.js modülleri bulunamadı. Kurulum yapılıyor...
    call npm install
    if %errorlevel% neq 0 (
        echo HATA: Node.js modülleri yüklenemedi.
        pause
        exit /b 1
    )
)

REM python_dist dizini var mı kontrol et
if not exist python_dist (
    echo Python dağıtımı bulunamadı. Oluşturuluyor...
    call python prepare_python_dist.py
    if %errorlevel% neq 0 (
        echo HATA: Python dağıtımı oluşturulamadı.
        pause
        exit /b 1
    )
)

echo.
echo Electron uygulaması geliştirici modunda başlatılıyor...
echo Kapatmak için pencereyi kapatın veya Ctrl+C tuşlarına basın.
echo.

REM Electron uygulamasını başlat
call npm run dev 