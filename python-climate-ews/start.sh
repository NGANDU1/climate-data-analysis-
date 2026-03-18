#!/bin/bash
# Climate EWS - Quick Start Script for Linux/Mac
# This script will set up and run the application

echo "============================================================"
echo "Climate Early Warning System - Python Flask"
echo "Quick Start Script"
echo "============================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.11+"
    exit 1
fi

echo "[1/5] Checking Python version..."
python3 --version

echo ""
echo "[2/5] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created successfully!"
else
    echo "Virtual environment already exists."
fi

echo ""
echo "[3/5] Activating virtual environment..."
source venv/bin/activate

echo ""
echo "[4/5] Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "[5/5] Seeding database..."
python seed_database.py

echo ""
echo "============================================================"
echo "Setup Complete!"
echo "============================================================"
echo ""
echo "To start the application:"
echo "  1. Run: flask run"
echo "  2. Open browser: http://localhost:5000"
echo "  3. Admin login: http://localhost:5000/admin/"
echo "     Username: admin@123"
echo "     Password: admin123"
echo ""
echo "============================================================"
