@echo off
echo ------------------------------------------------------
echo          NEXTSEFER KISAYOL GUNCELLEME ARACI
echo ------------------------------------------------------
echo.
echo Bu betik, Desktop kisayolunuzu guncelleyerek uygulamanin
echo sorunsuz calismasini saglayacaktir.
echo.

set SHORTCUT_NAME=%USERPROFILE%\Desktop\NextSefer.lnk
set TARGET_PATH=%~dp0start_browser.bat
set ICON_PATH=%~dp0sefer_app\static\img\favicon.ico

echo Mevcut kisayol: %SHORTCUT_NAME%
echo Yeni hedef: %TARGET_PATH%
echo.

if not exist "%SHORTCUT_NAME%" (
    echo Masaustunde kisayol bulunamadi.
    echo Yeni kisayol olusturuluyor...
) else (
    echo Mevcut kisayol guncelleniyor...
    del "%SHORTCUT_NAME%"
)

echo.
echo Kisayol olusturuluyor...

REM PowerShell ile kisayol olustur
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_NAME%'); $Shortcut.TargetPath = '%TARGET_PATH%'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.IconLocation = '%ICON_PATH%'; $Shortcut.Save()"

echo.
echo Kisayol basariyla guncellendi!
echo.
echo Artik masaustundeki NextSefer simgesine tikladiginizda,
echo uygulama otomatik olarak calisacaktir.
echo.
echo ------------------------------------------------------
echo.

pause 