@echo off
REM Climate EWS - Quick Start Script for Windows
REM This script will set up and run the application

echo ============================================================
echo Climate Early Warning System - Python Flask
echo Quick Start Script
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] Checking Python version...
python --version

echo.
echo [2/5] Creating virtual environment...
if not exist venv (
    python -m venv venv
    echo Virtual environment created successfully!
) else (
    echo Virtual environment already exists.
)

echo.
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [4/5] Installing dependencies...
pip install -r requirements.txt

echo.
echo [5/5] Seeding database...
python seed_database.py

echo.
echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo To start the application:
echo   1. Run: flask run
echo   2. Open browser: http://localhost:5000
echo   3. Admin login: http://localhost:5000/admin/
echo      Username: admin@123
echo      Password: admin123
echo.
echo ============================================================

pause
