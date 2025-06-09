@echo off
echo NextSefer doğrudan başlatma

REM Çalışma dizinini belirle
set PROJ_DIR=%~dp0
cd /d %PROJ_DIR%

REM CTRL+C ile batch dosyasını sonlandırmayı engelle
if not defined CTRL_C_EVENT (
    set CTRL_C_EVENT=1
    cmd /c %0 %*
    exit /b
)

REM Django sunucusunu başlat (arka planda)
echo Django sunucusu başlatılıyor (bekleyin)...
start "Django Server" cmd /c "cd /d %PROJ_DIR%\python_dist && python run_app.py"

REM Django'nun başlaması için bekle
echo 8 saniye bekleniyor...
ping -n 9 127.0.0.1 > nul

REM Test et - Django erişilebilir mi?
echo Django sunucusu kontrol ediliyor...
curl -s http://localhost:8000/ > nul
if %ERRORLEVEL% NEQ 0 (
    echo HATA: Django sunucusu başlatılamadı!
    echo Lütfen Django hata mesajları için diğer pencereyi kontrol edin.
    pause
    exit /b 1
)

REM Django bağlantısı başarılı, Electron başlat
echo Django sunucusu çalışıyor! Electron başlatılıyor...
npm start

echo İşlem tamamlandı.
pause 