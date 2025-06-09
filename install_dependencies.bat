@echo off
echo NextSefer Python bağımlılıklarını yükleme

REM Python dist klasörüne giriş
cd python_dist
if not exist lib mkdir lib
if not exist lib\site-packages mkdir lib\site-packages

echo Python bağımlılıkları yükleniyor...
pip install django requests reportlab openpyxl Pillow xlwt --target=lib\site-packages --upgrade --no-cache-dir

echo İşlem tamamlandı!
cd..

echo Done.
pause 