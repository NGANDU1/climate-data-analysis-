# Climate Early Warning System - Python Flask Version

A comprehensive disaster risk prediction and early warning system for Zambia, built with Python Flask.

## 🌟 Features

- **Real-time Weather Monitoring**: Track weather data across 10 Zambian provinces
- **Risk Prediction**: AI-powered disaster risk assessment (floods, droughts, extreme weather)
- **Alert System**: Automated SMS/email notifications to subscribed users
- **Admin Dashboard**: Complete management interface for administrators
- **User Subscriptions**: Multi-channel notification subscriptions (SMS, Email, or Both)
- **Data Analytics**: Weather trends and statistical analysis

## 📁 Project Structure

```
python-climate-ews/
├── app.py                          # Main Flask application
├── config.py                       # Configuration classes
├── requirements.txt                # Python dependencies
├── wsgi.py                         # Production WSGI entry point
├── gunicorn_config.py              # Gunicorn server config
├── seed_database.py                # Database seeder script
├── .env.example                    # Environment variables template
├── runtime.txt                     # Python version spec
├── Procfile                        # Deployment config
│
├── models/                         # Database models
│   ├── __init__.py
│   ├── admin.py                    # Admin user model
│   ├── alert.py                    # Alert model
│   ├── region.py                   # Zambia regions model
│   ├── user.py                     # User subscription model
│   └── weather_data.py             # Weather readings model
│
├── routes/                         # API route blueprints
│   ├── __init__.py
│   ├── weather_routes.py           # /api/weather endpoints
│   ├── risk_routes.py              # /api/risk endpoints
│   ├── alert_routes.py             # /api/alerts endpoints
│   ├── user_routes.py              # /api/users endpoints
│   └── admin_routes.py             # /api/admin endpoints
│
├── services/                       # Business logic
│   ├── __init__.py
│   ├── risk_calculator.py          # Risk prediction algorithm
│   ├── notification_service.py     # SMS/Email notifications
│   ├── weather_service.py          # Weather data processing
│   └── data_seeder.py              # Sample data generator
│
└── templatemo_607_glass_admin/     # Frontend (existing)
    ├── index.html
    ├── subscribe.html
    ├── alerts.html
    └── climate-dashboard.js
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11.x (required)
- pip (Python package manager)
- Virtual environment tool (recommended)

### Installation

1. **Navigate to project directory**
   ```bash
   cd python-climate-ews
   ```

2. **Create virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Seed the database**
    ```bash
    # Real data mode (no demo users)
    python seed_database.py

    # Optional demo data (sample users/alerts)
    # python seed_database.py --with-samples
    ```

5. **Run the application**
   ```bash
   flask run
   ```

6. **Access the application**
   - Open browser and go to: `http://localhost:5000`
   - Admin login: `http://localhost:5000/admin/`

### Default Credentials

After running the seeder:
- **Username**: admin@123
- **Password**: admin123

⚠️ **Important**: Change the default password immediately!

## 🛠️ Development

### Running in Development Mode

```bash
export FLASK_ENV=development  # Linux/Mac
set FLASK_ENV=development      # Windows

flask run --debug
```

### Open-data auto sync (NASA)
By default, the server runs a lightweight background job that periodically pulls NASA POWER data into the database.

Environment variables:
- `AUTO_SYNC_ENABLED` (default `true`)
- `AUTO_SYNC_INTERVAL_HOURS` (default `24`)
- `AUTO_SYNC_LOOKBACK_DAYS` (default `3`)
- `AUTO_SYNC_SOURCES` (default `nasa_power`) e.g. `nasa_power,gpm_imerg` (GPM IMERG needs Earthdata credentials)

### Testing API Endpoints

Use Postman, curl, or the included frontend to test endpoints:

```bash
# Get weather data
curl http://localhost:5000/api/weather

# Predict risk
curl http://localhost:5000/api/risk/predict

# Subscribe user
curl -X POST http://localhost:5000/api/users/subscribe \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john@example.com","phone":"+260977123456"}'
```

## 📡 API Endpoints

### Weather Endpoints
- `GET /api/weather` - Get current weather data for all regions
- `GET /api/weather/region/<id>` - Get weather for specific region

### Risk Assessment
- `GET /api/risk/predict` - Predict risk levels for all regions

### Alerts
- `GET /api/alerts` - Get all alerts
- `POST /api/alerts/send` - Send manual alert
- `DELETE /api/alerts/<id>` - Delete an alert
- `POST /api/alerts/auto-generate` - Auto-generate alerts from predictions

### Users
- `GET /api/users` - Get all subscribed users
- `POST /api/users/subscribe` - Subscribe new user
- `POST /api/users/<id>/unsubscribe` - Unsubscribe user
- `DELETE /api/users/<id>` - Delete user
- `GET /api/users/stats` - Get subscription statistics

### Admin
- `POST /api/admin/login` - Admin login
- `POST /api/admin/logout` - Admin logout
- `GET /api/admin/dashboard` - Get dashboard statistics
- `GET /api/admin/weather-trends` - Get weather trends
- `GET /api/admin/system-status` - Get system status

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///climate_ews.db
```

### Configuration Options

Edit `config.py` to customize:

- `SECRET_KEY`: Session security
- `SQLALCHEMY_DATABASE_URI`: Database connection string
- `DEBUG`: Enable/disable debug mode
- `ENV`: Environment name (development/production)

## 🗄️ Database

The application uses SQLite by default with SQLAlchemy ORM.

### Models

- **Region**: Zambia's 10 provinces with coordinates
- **WeatherData**: Historical weather readings
- **Alert**: Disaster alerts with risk levels
- **User**: Subscriber information
- **Admin**: Administrator accounts

### Reset Database

To reset the database:

```bash
# Delete existing database
rm instance/climate_ews.db  # Linux/Mac
del instance\climate_ews.db  # Windows

# Re-seed
python seed_database.py
```

## 📊 Services

### Risk Calculator

Predicts disaster risk based on weather parameters:

- **Flood Risk**: Rainfall > 100mm
- **Drought Risk**: Temperature > 35°C + Low rainfall
- **Extreme Heat**: Temperature > 40°C
- **Storm Risk**: High humidity + temperature combination

### Notification Service

Simulates SMS/Email notifications (integrate with actual services in production):

- Twilio for SMS
- SendGrid/SMTP for Email

### Weather Service

Weather data processing utilities:

- Historical data retrieval
- Statistical calculations
- Anomaly detection

## 🚢 Production Deployment

### Using Gunicorn

```bash
gunicorn --config gunicorn_config.py wsgi:app
```

### Deploy to Heroku

1. Install Heroku CLI
2. Login: `heroku login`
3. Create app: `heroku create your-app-name`
4. Deploy: `git push heroku main`
5. Seed database: `heroku run python seed_database.py`

### Deploy to Other Platforms

The app follows WSGI standards and can be deployed on:
- AWS Elastic Beanstalk
- Google Cloud Run
- DigitalOcean App Platform
- PythonAnywhere

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest

# Run tests (when added)
pytest
```

## 📝 Data Seeding

The seeder creates:

- 10 Zambian provinces
- 7 days of historical weather data
- Default admin user
- Sample subscribers
- Example alerts

Run anytime with:
```bash
python seed_database.py
```

## 🔐 Security Considerations

Before deploying to production:

1. ✅ Change default admin password
2. ✅ Set strong `SECRET_KEY`
3. ✅ Use environment variables for sensitive data
4. ✅ Enable HTTPS
5. ✅ Configure CORS properly
6. ✅ Add rate limiting
7. ✅ Implement proper authentication (Flask-Login)

## 🆘 Troubleshooting

### Port Already in Use

```bash
# Change port
flask run --port 5001
```

### Database Errors

```bash
# Reset database
rm instance/climate_ews.db
python seed_database.py
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📦 Dependencies

Main packages:
- Flask 3.0.0 - Web framework
- Flask-SQLAlchemy 3.1.1 - ORM
- Flask-CORS 4.0.0 - Cross-origin support
- python-dotenv 1.0.0 - Environment variables
- gunicorn 21.2.0 - Production server
- numpy 1.26.2 - Numerical computations
- pandas 2.1.3 - Data analysis

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📄 License

This project is part of the Climate EWS system for Zambia.

## 👥 Support

For issues or questions:
- Check the troubleshooting section
- Review API endpoint documentation
- Examine logs for error messages

## 🎯 Next Steps

After setup:
1. Explore the admin dashboard
2. Test alert generation
3. Customize risk thresholds
4. Integrate real SMS/Email services
5. Add more advanced ML models
6. Expand to additional regions

---

**Built with ❤️ for Zambia's Climate Resilience**
