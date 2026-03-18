# Climate EWS - Python Flask API Documentation

## Base URL
```
Development: http://localhost:5000/api
Production: https://your-domain.com/api
```

## Authentication
Currently, admin endpoints use simple session-based authentication. User endpoints are open for subscriptions.

---

## Weather Endpoints

### GET /api/weather
Get current weather data for all regions.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "region_id": 1,
      "region_name": "Lusaka",
      "latitude": -15.4167,
      "longitude": 28.2833,
      "temperature": 28.5,
      "humidity": 65.2,
      "rainfall": 45.3,
      "wind_speed": 12.5,
      "pressure": 1015.2
    }
  ],
  "count": 10
}
```

### GET /api/weather/region/<int:region_id>
Get weather data for a specific region.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "region_id": 1,
    "region_name": "Lusaka",
    "temperature": 28.5,
    "humidity": 65.2,
    "rainfall": 45.3,
    "wind_speed": 12.5,
    "pressure": 1015.2,
    "timestamp": "2024-01-15T10:30:00"
  }
}
```

### GET /api/weather/history
Get historical data for charts/tables (daily by default).

**Query Parameters:**
- `region_id` (optional): Region to filter
- `start` / `end` (optional): ISO date/datetime (e.g., `2025-01-01`)
- `interval` (optional): `daily` (default) or `hourly`
- `limit` (optional): Maximum buckets (default 365)

---

## Risk Assessment Endpoints

### GET /api/risk/predict
Predict risk levels for all regions based on current weather data.

**Response:**
```json
{
  "success": true,
  "predictions": [
    {
      "region_id": 1,
      "region_name": "Lusaka",
      "risk_level": "medium",
      "disaster_type": "drought",
      "confidence_score": 0.75,
      "current_conditions": {
        "temperature": 32.5,
        "humidity": 45.0,
        "rainfall": 15.2
      },
      "alerts": ["Elevated temperature detected"],
      "recommendations": ["Monitor soil moisture levels"]
    }
  ],
  "summary": {
    "overall_risk_level": "medium",
    "critical_regions": 0,
    "high_risk_regions": 2,
    "medium_risk_regions": 3,
    "low_risk_regions": 5,
    "total_regions_monitored": 10,
    "affected_region_names": ["Copperbelt", "Southern"]
  },
  "thresholds": {
    "flood_rainfall_mm": 100,
    "drought_temp_celsius": 35,
    "drought_rainfall_mm": 10,
    "extreme_temp_min": 5,
    "extreme_temp_max": 40
  }
}
```

---

## Forecast / Predictions

### GET /api/predictions/forecast
Forecast a climate variable for a region (used by Analytics “Data Explorer”).

**Query Parameters:**
- `region_id` (required)
- `variable` (required): `rainfall` | `temperature` | `humidity`
- `days` (optional): 1–30 (default 7)
- `method` (optional): `naive` (default) | `arima` (ARIMA requires `statsmodels`)

---

## Alert Endpoints

### GET /api/alerts
Get all alerts (optionally filtered by limit and risk level).

**Query Parameters:**
- `limit` (optional): Maximum number of alerts to return
- `risk_level` (optional): Filter by risk level (low, medium, high, critical)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "message": "Heavy rainfall expected in your area",
      "risk_level": "high",
      "disaster_type": "flood",
      "region_id": 1,
      "region_name": "Lusaka",
      "is_manual": false,
      "is_sent": true,
      "sent_count": 15,
      "created_at": "2024-01-15T08:00:00"
    }
  ],
  "count": 10
}
```

### POST /api/alerts/send
Send a manual alert to all subscribed users.

**Request Body:**
```json
{
  "message": "Severe weather warning issued",
  "risk_level": "critical",
  "disaster_type": "storm",
  "region_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "message": "Alert sent successfully",
  "alert": {
    "id": 5,
    "message": "Severe weather warning issued",
    "risk_level": "critical",
    "disaster_type": "storm",
    "region_id": 1,
    "is_manual": true,
    "is_sent": true,
    "sent_count": 25
  },
  "notification_result": {
    "success": true,
    "sent_count": 25,
    "sms_sent": 15,
    "email_sent": 10,
    "total_recipients": 25
  }
}
```

### DELETE /api/alerts/<int:alert_id>
Delete a specific alert.

**Response:**
```json
{
  "success": true,
  "message": "Alert deleted successfully"
}
```

### POST /api/alerts/auto-generate
Automatically generate alerts based on current risk predictions.

**Response:**
```json
{
  "success": true,
  "message": "Generated 3 alerts",
  "alerts": [
    {
      "id": 6,
      "message": "Automatic alert: flood risk detected in Copperbelt",
      "risk_level": "high",
      "disaster_type": "flood",
      "region_id": 2,
      "is_manual": false
    }
  ]
}
```

---

## Admin - Datasets & Data Quality

### GET /api/admin/datasets
List uploaded datasets.

### POST /api/admin/datasets/upload
Upload and import CSV/Excel into `weather_data`.

Form fields:
- `file` (required): `.csv`, `.xlsx`, `.xls`
- `name` (optional), `notes` (optional)
- `default_region_id` (optional): used if file has no `region` column
- `create_missing_regions` (optional): `true|false`

### POST /api/admin/datasets/import-json
Import records from JSON (API data).

### DELETE /api/admin/datasets/<id>?delete_rows=true
Delete a dataset (and optionally its imported `weather_data` rows).

### GET /api/admin/weather-data
List weather records (supports region/date filters) for editing.

### PATCH /api/admin/weather-data/<id>
Edit incorrect rows (temperature/humidity/rainfall/etc.).

### DELETE /api/admin/weather-data/<id>
Delete incorrect rows.

---

## Admin - Model Training & Monitoring

### POST /api/admin/models/train
Trigger model training (runs in background).

### GET /api/admin/models/training-runs
List recent training runs and logs/metrics.

### GET /api/admin/monitoring
Returns model file status and last training accuracy (validation accuracy when available).

---

## Admin - External Sources (Open Data)

### POST /api/admin/sources/nasa-power/sync
Sync daily climate variables from NASA POWER for all regions (lat/lon).

**Body:**
```json
{ "start": "2026-03-01", "end": "2026-03-17", "community": "RE" }
```

---

### POST /api/admin/sources/gpm-imerg/sync
Sync daily **satellite rainfall** from GPM IMERG (Earthdata login required).

**Body:**
```json
{ "start": "2026-03-01", "end": "2026-03-17", "version": "07", "box_deg": 0.1 }
```

---

### GET /api/admin/sources/sync-runs
List recent external sync runs (auto + manual).

## Admin - Reports

### GET /api/admin/reports/weather-data?format=csv|json
Export weather data (raw rows).

### GET /api/admin/reports/risk-predictions?format=csv|json
Export latest risk predictions.

### GET /api/admin/reports/training-summary
Get latest training run summary (metrics + logs pointers).

## User Endpoints

### GET /api/users
Get all subscribed users.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "John Phiri",
      "phone": "+260977123456",
      "email": "john.phiri@example.com",
      "location": "Lusaka",
      "subscription_type": "both",
      "is_active": true,
      "created_at": "2024-01-10T12:00:00"
    }
  ],
  "count": 25
}
```

### POST /api/users/subscribe
Subscribe a new user or update existing subscription.

**Request Body:**
```json
{
  "name": "Mary Banda",
  "email": "mary.banda@example.com",
  "phone": "+260966234567",
  "location": "Ndola",
  "subscription_type": "email"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Subscription successful",
  "user": {
    "id": 26,
    "name": "Mary Banda",
    "phone": "+260966234567",
    "email": "mary.banda@example.com",
    "location": "Ndola",
    "subscription_type": "email",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00"
  }
}
```

### POST /api/users/<int:user_id>/unsubscribe
Unsubscribe a user (deactivate without deleting).

**Response:**
```json
{
  "success": true,
  "message": "User unsubscribed successfully"
}
```

### DELETE /api/users/<int:user_id>
Permanently delete a user.

**Response:**
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

### GET /api/users/stats
Get user subscription statistics.

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_users": 50,
    "active_users": 45,
    "inactive_users": 5,
    "sms_subscribers": 15,
    "email_subscribers": 20,
    "both_subscribers": 15
  }
}
```

---

## Admin Endpoints

### POST /api/admin/login
Admin authentication.

**Request Body:**
```json
{
  "username": "admin@123",
  "password": "admin123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "admin": {
    "id": 1,
    "username": "admin@123",
    "created_at": "2024-01-01T00:00:00"
  },
  "session_id": "1_1705312200.123456"
}
```

### POST /api/admin/logout
Admin logout.

**Request Body:**
```json
{
  "session_id": "1_1705312200.123456"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Logout successful"
}
```

### GET /api/admin/dashboard
Get dashboard statistics.

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_regions": 10,
    "active_users": 45,
    "total_alerts": 25,
    "recent_alerts_7days": 8,
    "avg_temperature": 27.5,
    "avg_humidity": 62.3,
    "total_rainfall_24h": 125.6,
    "risk_distribution": {
      "low": 5,
      "medium": 3,
      "high": 2,
      "critical": 0
    }
  }
}
```

### GET /api/admin/weather-trends
Get weather trends over time.

**Query Parameters:**
- `days` (optional): Number of days to retrieve (default: 7)

**Response:**
```json
{
  "success": true,
  "trends": [
    {
      "date": "2024-01-08",
      "avg_temperature": 26.5,
      "avg_humidity": 60.2,
      "total_rainfall": 45.3
    },
    {
      "date": "2024-01-09",
      "avg_temperature": 27.1,
      "avg_humidity": 62.5,
      "total_rainfall": 52.1
    }
  ],
  "period_days": 7
}
```

### GET /api/admin/system-status
Get system health status.

**Response:**
```json
{
  "success": true,
  "status": {
    "database": "connected",
    "last_weather_update": "2024-01-15T10:00:00",
    "records": {
      "regions": 10,
      "users": 50,
      "alerts": 25,
      "weather_readings": 1680
    }
  }
}
```

---

## Error Responses

All endpoints return errors in the following format:

```json
{
  "success": false,
  "error": "Error message here"
}
```

Or for validation errors:

```json
{
  "success": false,
  "message": "Specific error message"
}
```

### HTTP Status Codes

- `200 OK` - Successful request
- `400 Bad Request` - Invalid input or validation error
- `401 Unauthorized` - Authentication required or failed
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Rate Limiting

Currently, no rate limiting is implemented. For production, consider adding:
- Flask-Limiter for rate limiting
- Request throttling per IP
- API key authentication for external services

---

## CORS

Cross-Origin Resource Sharing is enabled for all origins in development mode. For production, configure specific allowed origins in `app.py`.

---

## Testing

Test endpoints using:

**cURL Example:**
```bash
curl http://localhost:5000/api/weather
```

**Postman:**
Import the collection from `/postman_collection.json` (if available)

**Python Requests:**
```python
import requests

response = requests.get('http://localhost:5000/api/weather')
data = response.json()
print(data)
```

---

## Version History

- **v1.0** (Current) - Initial Python Flask implementation
  - All PHP endpoints migrated
  - SQLAlchemy ORM
  - Enhanced risk prediction
  - Improved notification service

---

## Support

For API issues or questions, refer to the main README.md or check the application logs.
