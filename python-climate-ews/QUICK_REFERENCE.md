# 🚀 Quick Reference - Climate EWS Python Flask

## Installation (First Time)

### Windows
```bash
cd python-climate-ews
start.bat
```

### Linux/Mac
```bash
cd python-climate-ews
chmod +x start.sh
./start.sh
```

## Running the Application

```bash
# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Run Flask server
flask run

# Or use production server
gunicorn --config gunicorn_config.py wsgi:app
```

## Access Points

- **Main Dashboard**: http://localhost:5000
- **Admin Login**: http://localhost:5000/admin/
- **Default Credentials**: 
  - Username: `admin@123`
  - Password: `admin123`

## Key Commands

```bash
# Seed database (reset data)
python seed_database.py

# Install dependencies
pip install -r requirements.txt

# Check Python version
python --version

# List installed packages
pip list

# Deactivate virtual env
deactivate
```

## API Endpoints Quick Reference

### Weather
```bash
GET /api/weather              # All regions weather
GET /api/weather/region/<id>  # Specific region
```

### Risk Assessment
```bash
GET /api/risk/predict         # Risk predictions
```

### Alerts
```bash
GET    /api/alerts            # Get all alerts
POST   /api/alerts/send       # Send manual alert
DELETE /api/alerts/<id>       # Delete alert
POST   /api/alerts/auto-generate  # Auto-generate
```

### Users
```bash
GET    /api/users             # Get all users
POST   /api/users/subscribe   # Subscribe user
POST   /api/users/<id>/unsubscribe  # Unsubscribe
DELETE /api/users/<id>        # Delete user
GET    /api/users/stats       # Get statistics
```

### Admin
```bash
POST /api/admin/login         # Admin login
POST /api/admin/logout        # Admin logout
GET  /api/admin/dashboard     # Dashboard stats
GET  /api/admin/weather-trends # Weather trends
GET  /api/admin/system-status # System status
```

## Testing with cURL

```bash
# Get weather data
curl http://localhost:5000/api/weather

# Get risk predictions
curl http://localhost:5000/api/risk/predict

# Subscribe a user
curl -X POST http://localhost:5000/api/users/subscribe \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com"}'

# Admin login
curl -X POST http://localhost:5000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@123","password":"admin123"}'
```

## File Locations

```
📁 Configuration:
  - app.py                      # Main application
  - config.py                   # Settings
  - .env                        # Environment variables

📁 Database:
  - instance/climate_ews.db     # SQLite database
  - models/                     # Data models

📁 API Routes:
  - routes/                     # Flask blueprints

📁 Business Logic:
  - services/                   # Services layer

📁 Frontend:
  - templatemo_607_glass_admin/ # HTML/CSS/JS
```

## Troubleshooting

### Port Already in Use
```bash
flask run --port 5001
```

### Reset Database
```bash
rm -rf instance/climate_ews.db  # Linux/Mac
del /q instance\climate_ews.db  # Windows
python seed_database.py
```

### Reinstall Dependencies
```bash
pip install -r requirements.txt --force-reinstall
```

### Check Virtual Environment
```bash
# Should show (venv) in prompt
# If not, activate manually
```

## Project Structure at a Glance

```
python-climate-ews/
├── app.py                 # Entry point
├── config.py              # Configuration
├── requirements.txt       # Dependencies
├── seed_database.py       # Data seeder
│
├── models/                # Database models
├── routes/                # API endpoints
├── services/              # Business logic
│
└── instance/              # Database files
```

## Common Tasks

### Add New Dependency
```bash
pip install package-name
pip freeze > requirements.txt
```

### Create New Model
```python
# models/new_model.py
from models import db

class NewModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # ... fields ...
```

### Add New Route
```python
# routes/new_routes.py
from flask import Blueprint

api = Blueprint('new', __name__)

@api.route('/endpoint', methods=['GET'])
def endpoint():
    return jsonify({'success': True})
```

## Security Checklist (Production)

- [ ] Change default admin password
- [ ] Set strong SECRET_KEY
- [ ] Use environment variables
- [ ] Enable HTTPS
- [ ] Configure CORS
- [ ] Add rate limiting
- [ ] Setup proper logging
- [ ] Configure firewall rules

## Performance Tips

1. Use production server (Gunicorn)
2. Enable database connection pooling
3. Add caching layer (Redis)
4. Use CDN for static files
5. Enable gzip compression
6. Optimize database queries
7. Monitor system resources

## Next Steps After Installation

1. ✅ Run seeder: `python seed_database.py`
2. ✅ Start server: `flask run`
3. ✅ Access dashboard: http://localhost:5000
4. ✅ Login to admin panel
5. ✅ Change default password
6. ✅ Explore API endpoints
7. ✅ Test alert generation
8. ✅ Customize settings

## Getting Help

- 📖 Full README: See README.md
- 📡 API Docs: See API_DOCUMENTATION.md
- 🔧 Implementation: See IMPLEMENTATION_SUMMARY.md
- 💻 Source Code: Check models/, routes/, services/

---

**Quick Start Command:**
```bash
cd python-climate-ews && start.bat  # Windows
cd python-climate-ews && ./start.sh  # Linux/Mac
```

**That's it! The application will be running at http://localhost:5000**

---

Made with ❤️ for Zambia's Climate Monitoring
