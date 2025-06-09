@echo off
echo NextSefer başlatılıyor...

REM Çalışma dizinini belirleme
set APP_DIR=%~dp0

REM Django sunucusunu başlat
start "Django Sunucusu" /min cmd /c "cd /d %APP_DIR%\resources\python_dist && python run_app.py"

REM Django sunucusunun başlaması için bekle
echo Django sunucusu başlatılıyor, lütfen bekleyin...
ping 127.0.0.1 -n 6 > nul

REM Electron uygulamasını başlat
echo Uygulama başlatılıyor...
start "" "%APP_DIR%\NextSefer.exe" 