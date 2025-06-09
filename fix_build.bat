@echo off
echo NextSefer kurulum sorunlarını çözme

echo 1. Eski build klasörlerini temizleme...
if exist dist rmdir /s /q dist
if exist dist_electron rmdir /s /q dist_electron
if exist node_modules\.cache rmdir /s /q node_modules\.cache

echo 2. Python dağıtımını güncelleme...
call install_dependencies.bat

echo 3. Çalışan Electron işlemlerini sonlandırma...
taskkill /f /im electron.exe 2>nul
taskkill /f /im NextSefer.exe 2>nul

echo 4. 3 saniye bekleniyor...
timeout /t 3 /nobreak

echo 5. Yeniden kurulum paketi oluşturma...
call npm run build

echo İşlem tamamlandı!
pause 