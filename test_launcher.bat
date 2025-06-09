@echo off
echo NextSefer Test Launcher
echo =====================
echo.
echo Starting NextSefer application...
echo.

REM TKinter hatalarını önlemek için sistem değişkenlerini temizle
SET TCL_LIBRARY=
SET TK_LIBRARY=
SET TCLLIBPATH=

REM NextSefer-GUI'yi doğrudan başlat
start "" dist\NextSefer-GUI\NextSefer-GUI.exe

echo Done!
pause 
 
 
 