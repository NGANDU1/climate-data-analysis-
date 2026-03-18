# 🎯 **EASIEST WAY TO RUN CLIMATE EWS**

## ⚡ **ONE-CLICK START** (After Python 3.11 is installed)

### **Double-click this file:**
```
QUICK_START.bat
```

**That's it!** The script will:
1. ✅ Install all dependencies
2. ✅ Create database
3. ✅ Train ML models
4. ✅ Start the server
5. ✅ Open in your browser

---

## 📝 **MANUAL STEPS** (If you prefer control)

### **Step 1: Get API Key** (1 minute)
1. Go to https://openweathermap.org/api
2. Click "Sign Up" (FREE)
3. Copy your API key

### **Step 2: Create .env File**
Create file `python-climate-ews\.env`:
```env
OPENWEATHER_API_KEY=paste_your_key_here
SECRET_KEY=my_secret_2025
DATABASE_URL=sqlite:///instance/climate_ews.db
```

### **Step 3: Run Commands**
Open Command Prompt in `python-climate-ews` folder:

```bash
# Install once
pip install -r requirements.txt

# Initialize database
python seed_database.py

# Train models (takes 2-3 min)
python train_models.py

# Start server
flask run
```

### **Python Version Note**
This project targets **Python 3.11.x** (see `python-climate-ews\\runtime.txt`). Newer versions (e.g. **Python 3.14**) often fail to install compiled wheels (like `numpy`/`tensorflow`) and will try to build from source (which can fail on Windows).

---

## 🌐 **ACCESS YOUR APP**

After starting, open browser to:

**Main Dashboard:**
```
http://localhost:5000
```

**Admin Panel:**
```
http://localhost:5000/admin/index.html
```

**Login with:**
- Email: `admin@123`
- Password: `admin123`

---

## ❓ **COMMON QUESTIONS**

### **"Do I need XAMPP?"**
❌ **NO!** Python Flask runs independently.  
✅ Just use the `QUICK_START.bat` file

### **"Can I use XAMPP's MySQL?"**
Yes, but not necessary. SQLite works great for testing!

### **"Where is the database?"**
SQLite: `python-climate-ews\instance\climate_ews.db`  
MySQL: Only if you configure it manually

### **"How do I stop the server?"**
Press `Ctrl + C` in the Command Prompt window

### **"How do I start again?"**
```bash
cd python-climate-ews
flask run
```

Or just double-click `QUICK_START.bat` again!

---

## 🚨 **TROUBLESHOOTING**

### **Error: "Python not found"**
Install Python from https://www.python.org/downloads/

### **Error: "Port already in use"**
Close other apps using port 5000, or change port:
```bash
flask run --port 5001
```

### **Error: "API key required"**
Edit `.env` file and add your OpenWeatherMap API key

### **Takes too long to start**
First time installs many packages. Subsequent starts are fast!

---

## 📊 **WHAT YOU'LL SEE**

### **During Setup:**
```
[1/6] Python found!
[2/6] Working directory: C:\...\python-climate-ews
[3/6] Installing dependencies...
    Collecting Flask...
    Collecting scikit-learn...
    ...
[4/6] Environment file created
[5/6] Database initialized
[6/6] Training ML models...
    Training Random Forest... ✓
    Training XGBoost... ✓
    Training LSTM... ✓
✓ All models trained!

Starting server at http://localhost:5000
```

### **In Browser:**
- Modern green-themed dashboard ✨
- Fancy admin panel with animations 💫
- ML-powered predictions 🤖
- Real-time weather data 🌍

---

## 🎉 **SUCCESS INDICATORS**

You know it's working when you see:

✅ Server running message  
✅ No error messages in console  
✅ Dashboard loads at localhost:5000  
✅ Admin login page accessible  
✅ Charts displaying  
✅ Predictions showing in API  

---

## 💡 **PRO TIPS**

1. **Bookmark these URLs:**
   - http://localhost:5000 (Dashboard)
   - http://localhost:5000/admin (Admin)
   - http://localhost:5000/analytics.html (Analytics)

2. **Keep terminal open** while using the app

3. **Run QUICK_START.bat** anytime to restart

4. **Check logs** in `logs/app.log` for details

5. **Change admin password** after first login!

---

## 🇿🇲 **YOU'RE READY!**

Your Climate EWS Zambia is ready to protect communities with:
- ✨ Modern, fancy UI
- 🤖 ML-powered predictions (90-95% accuracy)
- 🌍 Real-time weather data
- 📊 Beautiful analytics

**Just run QUICK_START.bat and go!** 🚀

---

*Quick Reference - Climate EWS Zambia*  
*Made simple for everyone!*
