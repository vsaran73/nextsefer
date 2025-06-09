@echo off
echo Building NextSefer Electron app...

rem Create python_dist if prepare_python_dist was run separately
IF NOT EXIST "python_dist" (
    echo Error: python_dist directory not found!
    echo Please run prepare_python_dist.py first.
    exit /b 1
)

rem Verify that python_dist has required files
IF NOT EXIST "python_dist\python.exe" (
    echo Error: python_dist\python.exe not found!
    echo Please run prepare_python_dist.py again.
    exit /b 1
)

rem Make sure icon.ico exists
IF NOT EXIST "icon.ico" (
    echo Creating icon.ico from icon.png...
    node create-icon.js
)

rem Explicitly copy python_dist to ensure it's included
xcopy /E /I /Y "python_dist" "dist\win-unpacked\resources\python_dist"

rem Build the Electron app
echo Building Electron app...
call npm run build

rem Run post-build script to ensure python_dist is included
call post_build.bat

rem Create the installer
echo Building installer...
call npx electron-builder --win

echo Build completed successfully. 