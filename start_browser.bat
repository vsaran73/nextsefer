@echo off
echo Nextsefer Tarayici Aciliyor...

REM Port kontrolü yap
netstat -an | find "8000" > nul
if %ERRORLEVEL% NEQ 0 (
    echo Sunucu calismiyor, baslatiliyor...
    start "" "%~dp0start_app.bat"
    
    REM Sunucunun başlaması için biraz bekle
    echo Sunucunun baslamasi bekleniyor...
    timeout /t 5 /nobreak > nul
)

echo Tarayici aciliyor...
start http://127.0.0.1:8000

echo Islem tamamlandi. 