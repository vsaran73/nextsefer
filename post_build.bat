@echo off
echo Running post-build tasks...

rem Check if the build was successful
IF NOT EXIST "dist\win-unpacked" (
    echo Error: Build directory not found! Build may have failed.
    exit /b 1
)

rem Explicitly copy python_dist to ensure it's included in the build
echo Copying Python distribution to build directory...
IF EXIST "python_dist" (
    xcopy /E /I /Y "python_dist" "dist\win-unpacked\resources\python_dist"
    echo Python distribution copied successfully.
) ELSE (
    echo Error: python_dist directory not found!
    exit /b 1
)

echo Creating desktop and start menu shortcuts...
copy "NextSefer.bat" "dist\win-unpacked\NextSefer.bat"

echo Post-build tasks completed successfully.
echo You can now run the installer creation with: electron-builder --win 