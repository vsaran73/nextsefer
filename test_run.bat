@echo off
echo Starting NextSefer Electron app in development mode...

:: Check if python_dist exists, if not create it
if not exist python_dist (
    echo Creating python_dist...
    python prepare_python_dist.py
)

:: Run electron in development mode
echo Starting Electron...
npm run dev 