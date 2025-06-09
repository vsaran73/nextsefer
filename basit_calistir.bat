@echo off
echo BasitCalistir - NextSefer icin Manuel Baslat Script

echo 1. Lutfen once Django sunucusunu calistiriniz.
echo    Acilan pencerede "Starting development server at http://0.0.0.0:8000/" yazisini gordukten sonra
echo    bu pencereye donup devam ediniz.

start "Django Server" cmd /c "python python_dist\run_app.py"

echo 2. Django sunucusu acildi. Devam etmek icin herhangi bir tusa basiniz...
pause

echo 3. Electron uygulamasini baslatiyorum...
npm start
echo 4. Islem bitti.
pause 