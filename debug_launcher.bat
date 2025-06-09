@echo off
echo NextSefer Debug Launcher
echo ======================
echo.
echo Starting NextSefer in DEBUG mode...
echo Logs will be shown in this window
echo.

REM Hata ayıklama için gerekli
SET DEBUG=True
SET DJANGO_DEBUG=True

REM TKinter hatalarını önlemek için sistem değişkenlerini temizle
SET TCL_LIBRARY=
SET TK_LIBRARY=
SET TCLLIBPATH=

REM Running.lock dosyasını sil (mevcutsa)
if exist "dist\NextSefer-GUI\running.lock" (
  echo Removing stale lock file...
  del "dist\NextSefer-GUI\running.lock"
)

REM NextSefer-GUI'yi konsol modunda başlat (çıktıları görmek için)
cd dist\NextSefer-GUI
echo.
echo === APPLICATION OUTPUT BELOW THIS LINE ===
echo.
NextSefer-GUI.exe

pause 
 
 
 