@echo off
echo Django sunucusunu test ediyoruz
cd python_dist
echo Django sunucusu başlatılıyor... 
echo.
echo Tarayıcınızda http://127.0.0.1:8000 adresini ziyaret edebilirsiniz
echo Sunucuyu durdurmak için Ctrl+C tuşlarına basın
echo.
python run_app.py
pause 