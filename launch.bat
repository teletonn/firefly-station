@echo off
echo Светлячок LLM Radio System Launcher
echo ====================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ and add it to your PATH
    pause
    exit /b 1
)

REM Check if required files exist
if not exist "main.py" (
    echo ❌ main.py not found
    pause
    exit /b 1
)

if not exist "config.yaml" (
    echo ❌ config.yaml not found
    pause
    exit /b 1
)

echo ✅ Requirements check passed
echo.

REM Install dependencies
echo 📦 Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)
echo ✅ Dependencies installed
echo.

REM Build frontend if it exists
if exist "frontend\package.json" (
    echo 🔨 Building React frontend...
    cd frontend
    if exist "build" (
        echo ✅ Frontend already built
    ) else (
        npm install
        if errorlevel 1 (
            echo ❌ Failed to install npm dependencies
            cd ..
            goto launch
        )
        npm run build
        if errorlevel 1 (
            echo ❌ Failed to build frontend
            cd ..
            goto launch
        )
        echo ✅ Frontend built successfully
    )
    cd ..
) else (
    echo ⚠️  Frontend not found, skipping build
)
echo.

:launch
REM Launch the system
echo 🚀 Launching system...
echo.
echo 🌐 Web Interface will be available at: http://localhost:8000
echo 🤖 Bot will connect to Светлячок device
echo.
echo Press Ctrl+C to stop
echo.

python main.py

echo.
echo 🛑 System stopped
pause