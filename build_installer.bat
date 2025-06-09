@echo off
echo Building NextSefer Installer
echo =========================

rem Check for python_dist directory
if not exist python_dist (
    echo ERROR: python_dist directory missing.
    echo Please run prepare_python_dist.py first.
    exit /b 1
)

rem Check if python.exe exists in the python_dist directory
if not exist python_dist\python.exe (
    echo ERROR: python_dist/python.exe missing.
    echo Python distribution seems incomplete.
    exit /b 1
)

rem Create icon if missing
if not exist icon.ico (
    echo Creating icon from icon.png...
    node create-icon.js
    if not exist icon.ico (
        echo ERROR: Failed to create icon.ico
        exit /b 1
    )
)

rem Clean previous build
echo Cleaning previous build...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

rem Build the app
echo Building Electron app...
call npx electron-builder --dir
if %errorlevel% neq 0 (
    echo ERROR: Failed to build app
    exit /b 1
)

rem Copy python_dist manually to ensure it's included
echo Copying Python distribution...
if exist dist\win-unpacked (
    echo Creating resources directory if it doesn't exist
    if not exist dist\win-unpacked\resources mkdir dist\win-unpacked\resources
    
    echo Copying python_dist to build directory
    xcopy /E /I /Y python_dist dist\win-unpacked\resources\python_dist
    
    echo Copying NextSefer.bat to root of build
    copy NextSefer.bat dist\win-unpacked\NextSefer.bat
) else (
    echo ERROR: dist\win-unpacked directory not found.
    exit /b 1
)

rem Create final installer
echo Creating installation package...
call npx electron-builder --win --prepackaged dist/win-unpacked
if %errorlevel% neq 0 (
    echo ERROR: Failed to create installer
    exit /b 1
)

echo.
echo Build and installer creation completed successfully!
echo Installer can be found in the 'dist' directory. 