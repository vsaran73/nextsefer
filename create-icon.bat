@echo off
echo Converting icon.png to icon.ico...

REM Check if icon.png exists
if not exist icon.png (
    echo Error: icon.png not found!
    pause
    exit /b 1
)

REM Use Node.js to convert PNG to ICO
node create-icon.js

echo Conversion complete!
pause 