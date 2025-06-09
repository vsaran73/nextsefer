@echo off
echo NextSefer derleme işlemi başlatılıyor...
echo.

REM Python ve gerekli paketlerin kurulu olduğundan emin olun
python -c "print('Python erişilebilir durumda')" || (
    echo Python bulunamadı! Python'un yüklü ve PATH'e eklenmiş olduğundan emin olun.
    pause
    exit /b 1
)

REM Node.js'nin kurulu olduğundan emin olun
node -v >nul 2>&1 || (
    echo Node.js bulunamadı! Node.js'nin yüklü ve PATH'e eklenmiş olduğundan emin olun.
    pause
    exit /b 1
)

echo 1/4: Python modülleri derleniyor...
echo -------------------------------------------
REM Electron için Python dağıtımını hazırla
python prepare_python_dist.py
if %errorlevel% neq 0 goto error
echo.

echo 2/4: Node.js modülleri yükleniyor...
echo -------------------------------------------
call npm install
if %errorlevel% neq 0 goto error
echo.

echo 3/4: NextSefer Electron uygulaması derleniyor...
echo -------------------------------------------
call npm run build
if %errorlevel% neq 0 goto error
echo.

echo 4/4: Kurulum tamamlandı!
echo -------------------------------------------
echo.
echo Kurulum dosyaları dist_electron/ klasöründe oluşturuldu.
echo.
echo Derleme işlemi tamamlandı!
goto end

:error
echo.
echo Hata: Derleme işlemi başarısız oldu.
echo Lütfen hata mesajlarını kontrol edin.

:end
pause 
 
 
 