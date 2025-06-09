@echo off
echo.
echo ------------------------------------------------------
echo              NEXTSEFER UYGULAMASI BASLATILIYOR
echo ------------------------------------------------------
echo.

REM TCL/TK ortam değişkenlerini temizle
SET TCL_LIBRARY=
SET TK_LIBRARY=
SET TCLTK_PATH=
SET TCL_ROOT=
SET PYINSTALLER_NO_TCL=1

echo Django sunucusu baslatiliyor...
echo Islem bitene kadar lutfen bu pencereyi kapatmayin!
echo.
echo Bir sorun yasarsaniz, lutfen destek alin.
echo ------------------------------------------------------
echo.

REM Django'yu başlat
python run_app.py

if %ERRORLEVEL% neq 0 (
    echo Uygulama bir hata ile sonlandı!
    pause
)
pause 