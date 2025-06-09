@echo off
echo NextSefer Django Launcher
echo ======================
echo.
echo Django sunucusu başlatılıyor...
echo Logs klasörünüzde detaylı log kayıtlarını bulabilirsiniz.
echo.

REM Tkinter hatalarını önlemek için ortam değişkenlerini temizle
SET TCL_LIBRARY=
SET TK_LIBRARY=
SET TCLLIBPATH=

REM Debug modunu aktifleştir
SET DEBUG=True
SET DJANGO_DEBUG=True

REM Basit Python başlatıcıyı çalıştır
python simple_launcher.py

echo.
echo Django sunucusu kapatıldı. 
echo Çıkmak için herhangi bir tuşa basın...
pause 
 
 
 