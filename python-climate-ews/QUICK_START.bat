@echo off
REM Climate EWS - Quick Start Script for Windows
REM This script sets up and runs the application automatically

echo ============================================================
echo CLIMATE EARLY WARNING SYSTEM - ZAMBIA
echo Quick Start Setup
echo ============================================================
echo.

REM Check for Python launcher + correct version
py -3.11 -V >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python 3.11 not found!
    echo This project targets Python 3.11.x (see runtime.txt).
    echo Install Python 3.11 from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/7] Python 3.11 found!
echo.

REM Navigate to project directory
cd /d "%~dp0"
echo [2/7] Working directory: %CD%
echo.

REM Create / activate virtual environment
if not exist ".venv\\Scripts\\python.exe" (
    echo [3/7] Creating virtual environment...
    py -3.11 -m venv .venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)
call ".venv\\Scripts\\activate.bat"

REM Install dependencies
echo [4/7] Installing dependencies...
echo This may take 5-10 minutes on first run...
echo.
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully!
echo.

REM Check if .env file exists
if not exist ".env" (
    echo [5/7] Creating environment file...
    echo.
    (
        echo # IMPORTANT: Edit this file and add your OpenWeatherMap API key
        echo OPENWEATHER_API_KEY=your_api_key_here
        echo SECRET_KEY=climate_ews_secret_key_2025
        echo DATABASE_URL=sqlite:///instance/climate_ews.db
        echo FLASK_ENV=development
    ) > ".env"
    echo ================================================
    echo NEXT STEP: Edit .env file with your API key!
    echo Get FREE API key at: https://openweathermap.org/api
    echo ================================================
    echo.
) else (
    echo [5/7] Environment file found
)

REM Initialize database
echo [6/7] Initializing database...
python seed_database.py
if %errorlevel% neq 0 (
    echo ERROR: Database initialization failed
    pause
    exit /b 1
)
echo.

REM Train ML models
echo [7/7] Training ML models...
echo This may take 2-3 minutes...
echo.
python train_models.py
if %errorlevel% neq 0 (
    echo ERROR: Model training failed
    pause
    exit /b 1
)
echo.

echo ============================================================
echo SETUP COMPLETE!
echo ============================================================
echo.
echo Starting Climate EWS server...
echo.
echo Access your application at:
echo   Home Page:     http://localhost:5000
echo   Admin Panel:    http://localhost:5000/admin/index.html
echo.
echo Default Admin Credentials:
echo   Email: admin@123
echo   Password: admin123
echo.
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

REM Start Flask application
flask run

pause
