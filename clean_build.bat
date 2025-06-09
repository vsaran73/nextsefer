@echo off
echo ========================
echo NextSefer Temiz Build
echo ========================

echo 1. Tüm Electron işlemlerini sonlandırma...
taskkill /f /im electron.exe 2>nul
taskkill /f /im NextSefer.exe 2>nul

echo 2. Temizleme...
if exist dist rmdir /s /q dist
if exist dist_electron rmdir /s /q dist_electron  
if exist node_modules\.cache rmdir /s /q node_modules\.cache

echo 3. node_modules siliniyor (temiz kurulum için)...
if exist node_modules rmdir /s /q node_modules

echo 4. package-lock.json siliniyor...
if exist package-lock.json del /f package-lock.json

echo 5. Bağımlılıklar tekrar kuruluyor...
call npm install

echo 6. Python bağımlılıklarını kontrol et...
call install_dependencies.bat

echo 7. Kurulum paketi oluşturuluyor...
call npm run build

echo İşlem tamamlandı!
pause 