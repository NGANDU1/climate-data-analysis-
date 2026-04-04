# Climate Early Warning System - Zambia
## Real-time Weather Monitoring & Disaster Alerts

A comprehensive climate monitoring system designed for Zambia to provide real-time weather data and disaster alerts for floods, droughts, and extreme temperatures.

---

## 🌟 Features

### Public Dashboard
- **Real-time Weather Data**: Temperature, humidity, rainfall for all 10 Zambian provinces
- **Risk Assessment**: AI-powered prediction of flood, drought, and extreme temperature risks
- **Interactive Map**: Leaflet.js map showing risk levels by region
- **Weather Charts**: Visual trends using Chart.js
- **Alert Subscription**: Users can subscribe via SMS or email
- **Responsive Design**: Works on desktop, tablet, and mobile

### Admin Panel
- **Secure Login**: Authentication system for administrators
- **Manual Alert Triggering**: Send emergency notifications to all subscribers
- **User Management**: View subscribed users and statistics
- **Alert History**: Track all generated alerts
- **Dashboard Analytics**: Real-time statistics and metrics

---

## 🚀 Installation Instructions

### Prerequisites
- **XAMPP** (or any PHP/MySQL stack)
- Modern web browser (Chrome, Firefox, Edge)

### Step 1: Install XAMPP
1. Download XAMPP from [https://www.apachefriends.org](https://www.apachefriends.org)
2. Install XAMPP to `C:\xampp` (default location)
3. Start **Apache** and **MySQL** from XAMPP Control Panel

### Step 2: Setup Database
1. Open phpMyAdmin: [http://localhost/phpmyadmin](http://localhost/phpmyadmin)
2. Click "Import" tab
3. Choose file: `database/climate_ews.sql`
4. Click "Go" to import

**Default Admin Credentials:**
- Username: `admin@123`
- Password: `admin123`

### Step 3: Configure Application
1. Copy entire project folder to XAMPP htdocs:
   ```
   C:\xampp\htdocs\climate-ews\
   ```

2. Verify database configuration in `config/config.php`:
   ```php
   define('DB_HOST', 'localhost');
   define('DB_NAME', 'climate_ews_zambia');
   define('DB_USER', 'root');
   define('DB_PASS', ''); // Empty for XAMPP
   ```

### Step 4: Access the System

**Public Dashboard:**
```
http://localhost/climate-ews/frontend/index.html
```

**Admin Panel:**
```
http://localhost/climate-ews/admin/index.html
```

---

## 📁 Project Structure

```
project/
├── frontend/                     # Public dashboard
│   ├── index.html                 # Main climate dashboard
│   ├── climate-dashboard.js       # Dashboard JavaScript
│   └── templatemo-glass-admin-*   # CSS & base JS
├── admin/                         # Admin panel
│   ├── index.html                 # Admin login
│   ├── dashboard.html             # Admin dashboard
│   ├── users.html                 # User management
│   └── admin-dashboard.js         # Admin JavaScript
├── api/                           # Backend APIs
│   ├── getWeatherData.php         # Fetch weather data
│   ├── predictRisk.php            # Risk prediction
│   ├── sendAlert.php              # Send alerts
│   ├── subscribeUser.php          # User subscription
│   ├── adminLogin.php             # Admin auth
│   ├── getAllAlerts.php           # Get all alerts
│   ├── getAllUsers.php            # Get all users
│   └── getWeatherTrends.php       # Historical trends
├── config/                        # Configuration
│   ├── config.php                 # App constants
│   └── database.php               # DB connection
├── database/                      # Database
│   └── climate_ews.sql           # SQL dump
└── README.md                      # This file
```

---

## 🎨 Color Theme

The system uses a **black, yellow, and white** color scheme:
- **Primary Yellow**: `#FFD700` (Gold)
- **Dark Yellow**: `#B8860B`
- **Background**: Black/Dark Grey `#0a0a0a`
- **Text**: White `#ffffff`

---

## 🔧 API Endpoints

### Public Endpoints
- `GET /api/getWeatherData.php` - Current weather for all regions
- `GET /api/predictRisk.php` - Risk predictions
- `POST /api/subscribeUser.php` - Subscribe to alerts
- `GET /api/getAllAlerts.php` - Get public alerts
- `GET /api/getWeatherTrends.php` - Historical data

### Admin Endpoints
- `POST /api/adminLogin.php` - Admin authentication
- `POST /api/sendAlert.php` - Trigger manual alert
- `GET /api/getAllUsers.php` - Get subscribed users

---

## 📊 Database Schema

### Tables Created

1. **regions** - 10 Zambian provinces with coordinates
2. **weather_data** - Historical weather readings
3. **alerts** - Generated alerts (auto & manual)
4. **users** - Subscribed users for notifications
5. **admin** - Administrator credentials
6. **risk_predictions** - ML predictions (future use)

---

## 🎯 Usage Guide

### For Public Users
1. View current weather conditions on dashboard
2. Check risk levels for your region on the map
3. Subscribe to alerts using the form
4. Receive SMS/Email notifications for emergencies

### For Administrators
1. Login with admin credentials
2. Monitor national weather statistics
3. Trigger manual alerts when needed
4. View user subscription list
5. Analyze alert history and trends

---

## ⚙️ Risk Prediction Logic

The system automatically calculates risk levels:

### Flood Risk → HIGH
- Rainfall > 100mm
- Increasing rainfall trend

### Drought Risk → HIGH
- Temperature > 35°C AND Rainfall < 10mm
- Extended dry period

### Extreme Temperature
- Temperature < 5°C (Cold)
- Temperature > 40°C (Heat wave)

---

## 🔐 Security Notes

**For Production Deployment:**
1. Change default admin password immediately
2. Enable HTTPS/SSL
3. Implement proper session management
4. Add rate limiting to API endpoints
5. Sanitize all user inputs (already implemented)
6. Use environment variables for database credentials

---

## 🌍 Supported Regions

The system monitors all 10 Zambian provinces:
1. Lusaka
2. Copperbelt
3. Eastern
4. Northern
5. Southern
6. Central
7. North-Western
8. Luapula
9. Muchinga
10. Western

---

## 🛠️ Troubleshooting

### Cannot connect to database
- Ensure MySQL is running in XAMPP
- Check database name in `config/config.php`
- Verify database was imported correctly

### API returns errors
- Check Apache is running
- Verify PHP is enabled
- Check error logs in `xampp/apache/logs/error.log`

### Maps not loading
- Ensure internet connection (Leaflet.js loads from CDN)
- Check browser console for errors

### Charts not displaying
- Ensure internet connection (Chart.js loads from CDN)
- Clear browser cache and refresh

---

## 📝 Future Enhancements

- [ ] Integration with real weather APIs (OpenWeatherMap)
- [ ] SMS gateway integration (Twilio/Africa's Talking)
- [ ] Email service (SendGrid/Mailgun)
- [ ] Machine learning predictions
- [ ] Mobile app (React Native)
- [ ] Multi-language support
- [ ] Export reports (PDF/Excel)

---

## 👨‍💻 Developer Information

**Project Type:** University Final Year Project  
**Tech Stack:** HTML, CSS, JavaScript, PHP, MySQL  
**Libraries:** Leaflet.js, Chart.js  
**Design Pattern:** MVC-inspired architecture  

---

## 📄 License

This project is created for educational purposes as a university final year project. Free to use and modify for learning purposes.

---

## 🤝 Support

For questions or issues:
1. Check this README thoroughly
2. Review code comments in source files
3. Check browser console for JavaScript errors
4. Verify XAMPP services are running

---

## ✅ Testing Checklist

- [x] Database imported successfully
- [x] Apache & MySQL running
- [x] Public dashboard loads
- [x] Weather data displays
- [x] Map shows regions
- [x] Charts render correctly
- [x] Admin login works
- [x] Manual alerts can be sent
- [x] User subscription functional
- [x] Responsive design works on mobile

---

**© 2026 Climate Early Warning System - Zambia**  
*Developed for University Final Year Project*
