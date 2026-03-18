# 🚀 Deployment Guide - Climate EWS Zambia

## Choose Your Deployment Method

---

## ✅ **METHOD 1: Python Flask Direct** (RECOMMENDED - Easiest!)

This method runs the Python application directly without XAMPP.

### **Prerequisites:**
- Python 3.8+ installed
- pip (Python package manager)

### **Step-by-Step:**

#### **1. Navigate to Project**
```bash
cd c:\Users\Ng'andu\OneDrive\Desktop\project\python-climate-ews
```

#### **2. Install Dependencies**
```bash
pip install -r requirements.txt
```

This installs:
- Flask (web framework)
- SQLAlchemy (database)
- scikit-learn (ML)
- xgboost (ML)
- tensorflow (ML)
- + other dependencies

**Installation time:** ~5-10 minutes

---

#### **3. Create Environment File**

Create a file named `.env` in the `python-climate-ews` folder:

```env
OPENWEATHER_API_KEY=your_openweathermap_api_key_here
SECRET_KEY=climate_ews_super_secret_key_2025
DATABASE_URL=sqlite:///instance/climate_ews.db
FLASK_ENV=development
```

**To get FREE API key:**
1. Go to https://openweathermap.org/api
2. Sign up (free)
3. Copy your API key
4. Paste in `.env` file

---

#### **4. Initialize Database**
```bash
python seed_database.py
```

**Expected output:**
```
============================================================
Climate Early Warning System - Database Seeder
============================================================
Initializing database...
✅ Database tables created
✅ Seeded 10 regions
✅ Generated 1,680 weather records
✅ Created default admin user

🎉 Seeding completed successfully!
```

---

#### **5. Train ML Models**
```bash
python train_models.py
```

**Expected output:**
```
============================================================
CLIMATE EWS - ML MODEL TRAINING PIPELINE
============================================================
Training Random Forest Classifier...
Validation Accuracy: 0.8923
✓ Random Forest saved

Training XGBoost Classifier...
Validation Accuracy: 0.9156
✓ XGBoost saved

Training LSTM Forecaster...
✓ LSTM saved

✓ All models trained and saved successfully!
```

---

#### **6. Start Application**
```bash
# Option A: Using Flask CLI
flask run

# Option B: Direct Python
python app.py

# Option C: Use the batch file
start.bat
```

**Server starts at:** `http://localhost:5000`

---

#### **7. Access Your Application**

**Main Dashboard:**
- URL: http://localhost:5000
- Modern fancy UI with green theme

**Admin Panel:**
- URL: http://localhost:5000/admin/index.html
- Login with default credentials

**API Endpoints:**
- http://localhost:5000/api/risk/predict
- http://localhost:5000/api/weather
- http://localhost:5000/api/alerts

---

### **Default Credentials:**

**Admin Login:**
- Email: `admin@123`
- Password: `admin123`

**Change immediately after first login!**

---

### **Stop the Server:**
Press `Ctrl + C` in the terminal

---

## 🐘 **METHOD 2: XAMPP with MySQL** (Advanced)

Use this if you want to use MySQL database instead of SQLite.

### **Prerequisites:**
- XAMPP installed
- Python 3.8+ installed
- MySQL connector for Python

### **Step-by-Step:**

#### **1. Start XAMPP Services**

1. Open **XAMPP Control Panel**
2. Start **MySQL** service
3. Note port (usually 3306)

---

#### **2. Create MySQL Database**

Open phpMyAdmin: http://localhost/phpmyadmin

**SQL Commands:**
```sql
CREATE DATABASE climate_ews;
CREATE USER 'climate_user'@'localhost' IDENTIFIED BY 'climate_pass_2025';
GRANT ALL PRIVILEGES ON climate_ews.* TO 'climate_user'@'localhost';
FLUSH PRIVILEGES;
```

---

#### **3. Update Configuration**

Edit `config.py`:

```python
class DevelopmentConfig(Config):
    DEBUG = True
    ENV = 'development'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://climate_user:climate_pass_2025@localhost:3306/climate_ews'
```

Or update `.env`:
```env
DATABASE_URL=mysql+pymysql://climate_user:climate_pass_2025@localhost:3306/climate_ews
```

---

#### **4. Install MySQL Connector**
```bash
pip install pymysql cryptography
```

---

#### **5. Initialize Database**
```bash
python seed_database.py
```

This creates all tables in MySQL.

---

#### **6. Train Models & Start**
```bash
python train_models.py
flask run
```

---

## 🌐 **METHOD 3: Deploy to htdocs** (Not Recommended for Python)

⚠️ **Important:** Python Flask apps don't run well from htdocs because:
- XAMPP's Apache is configured for PHP, not Python
- WSGI configuration is complex
- Performance issues

**Better Alternative:** Run Flask separately (Method 1) and use XAMPP only for MySQL if needed.

---

## 📋 **Quick Reference Commands**

### **Start Application:**
```bash
cd c:\Users\Ng'andu\OneDrive\Desktop\project\python-climate-ews
flask run
```

### **Check Database:**
```bash
# For SQLite
ls instance/

# For MySQL
mysql -u climate_user -p climate_ews
```

### **Retrain Models:**
```bash
python train_models.py
```

### **Reset Database:**
```bash
# Delete SQLite database
del instance\climate_ews.db

# Re-seed
python seed_database.py
```

---

## 🔧 **Troubleshooting**

### **Error: "ModuleNotFoundError"**
```bash
pip install -r requirements.txt --upgrade
```

### **Error: "Database not found"**
```bash
python seed_database.py
```

### **Error: "Port 5000 already in use"**
```bash
# Change port
flask run --port 5001

# Or kill process using port 5000
netstat -ano | findstr :5000
taskkill /PID <PID_NUMBER> /F
```

### **Error: "API key not provided"**
Check `.env` file exists and contains:
```env
OPENWEATHER_API_KEY=your_actual_key
```

### **Error: "TensorFlow not installed"**
```bash
pip install tensorflow
```

---

## 📊 **What Gets Installed**

### **Database Files:**
```
python-climate-ews/
└── instance/
    └── climate_ews.db          # SQLite database
```

### **ML Models:**
```
python-climate-ews/
└── models/
    └── saved/
        ├── random_forest_model.pkl
        ├── xgboost_model.pkl
        ├── lstm_model.h5
        └── scaler.pkl
```

### **Logs:**
```
python-climate-ews/
└── logs/
    └── app.log                 # Application logs
```

---

## 🎯 **Recommended Setup**

**For Development:**
- ✅ Method 1 (Flask Direct)
- ✅ SQLite database
- ✅ Debug mode enabled
- ✅ Hot reload on changes

**For Production:**
- ✅ Method 1 or 2
- ✅ MySQL database
- ✅ Gunicorn WSGI server
- ✅ Nginx reverse proxy
- ✅ HTTPS enabled

---

## 🌟 **Verify Installation**

After starting the app, check these URLs:

1. **Main Dashboard:** http://localhost:5000
   - Should show modern green-themed dashboard
   
2. **Admin Login:** http://localhost:5000/admin/index.html
   - Should show fancy login page
   
3. **API Test:** http://localhost:5000/api/risk/predict
   - Should return JSON with predictions
   
4. **Analytics:** http://localhost:5000/analytics.html
   - Should show charts and graphs

**If all load successfully → Installation complete!** ✅

---

## 📞 **Need Help?**

### **Check Logs:**
```bash
# View last 50 lines
tail -50 logs/app.log

# Or on Windows
Get-Content logs\app.log -Tail 50
```

### **Test Database:**
```bash
python-c "from app import create_app; from models import db; app = create_app(); print('Database OK')"
```

### **Test ML Models:**
```bash
python-c "from services.ml_risk_service import MLRiskCalculator; print('ML Models OK')"
```

---

## 🎉 **Success Checklist**

Before declaring deployment complete:

- [ ] All dependencies installed
- [ ] Database initialized
- [ ] ML models trained
- [ ] Application starts without errors
- [ ] Main dashboard loads
- [ ] Admin panel accessible
- [ ] API returns predictions
- [ ] Charts display correctly
- [ ] No console errors

**All checked? You're ready to go!** 🚀🇿🇲

---

*Deployment Guide - Climate EWS Zambia*  
*Version 1.0 - March 2025*
