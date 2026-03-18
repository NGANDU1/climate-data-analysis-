from flask import Blueprint, jsonify, request
from models import db
from models.admin import Admin
from models.alert import Alert
from models.user import User
from models.weather_data import WeatherData
from models.region import Region
from datetime import datetime, timedelta

api = Blueprint('admin', __name__)

# Simple session storage (use Flask-Login in production)
admin_sessions = {}

@api.route('/login', methods=['POST'])
def login():
    """Admin login"""
    try:
        data = request.get_json()
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': 'Username and password are required'
            }), 400
        
        # Find admin
        admin = Admin.query.filter_by(username=username).first()
        
        if not admin:
            return jsonify({
                'success': False,
                'message': 'Invalid credentials'
            }), 401
        
        # Check password
        if not admin.check_password(password):
            return jsonify({
                'success': False,
                'message': 'Invalid credentials'
            }), 401
        
        # Create session (simple implementation)
        session_id = f"{admin.id}_{datetime.utcnow().timestamp()}"
        admin_sessions[session_id] = {
            'admin_id': admin.id,
            'username': admin.username,
            'login_time': datetime.utcnow()
        }
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'admin': admin.to_dict(),
            'session_id': session_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/logout', methods=['POST'])
def logout():
    """Admin logout"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if session_id and session_id in admin_sessions:
            del admin_sessions[session_id]
        
        return jsonify({
            'success': True,
            'message': 'Logout successful'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/dashboard', methods=['GET'])
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Get counts
        total_regions = Region.query.count()
        total_users = User.query.filter_by(is_active=True).count()
        total_alerts = Alert.query.count()
        recent_alerts = Alert.query.filter(
            Alert.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        # Get latest weather data stats
        latest_weather = db.session.query(
            db.func.avg(WeatherData.temperature),
            db.func.avg(WeatherData.humidity),
            db.func.sum(WeatherData.rainfall)
        ).filter(
            WeatherData.timestamp >= datetime.utcnow() - timedelta(days=24)
        ).first()
        
        # Risk level distribution
        # Prefer ML/rule-based predictions when available; fall back to Region.risk_level if empty.
        risk_levels = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        try:
            from services.risk_calculator import RiskCalculator

            regions = Region.query.all()
            for region in regions:
                weather = (
                    WeatherData.query.filter_by(region_id=region.id)
                    .order_by(WeatherData.timestamp.desc())
                    .limit(3)
                    .all()
                )
                if not weather:
                    continue
                avg_temp = sum(w.temperature for w in weather) / len(weather)
                avg_humidity = sum(w.humidity for w in weather) / len(weather)
                total_rainfall = sum(w.rainfall for w in weather)

                prediction = RiskCalculator.predict_risk(
                    {
                        "temperature": avg_temp,
                        "humidity": avg_humidity,
                        "rainfall": total_rainfall,
                        "region_name": region.name,
                    }
                )
                rl = (prediction.get("risk_level") or "low").lower()
                if rl not in risk_levels:
                    risk_levels[rl] = 0
                risk_levels[rl] += 1
        except Exception:
            # Fall back to stored Region risk levels
            risk_distribution = (
                db.session.query(Region.risk_level, db.func.count(Region.id))
                .group_by(Region.risk_level)
                .all()
            )
            for level, count in risk_distribution:
                if not level:
                    continue
                risk_levels[str(level).lower()] = int(count)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_regions': total_regions,
                'active_users': total_users,
                'total_alerts': total_alerts,
                'recent_alerts_7days': recent_alerts,
                'avg_temperature': round(latest_weather[0] or 0, 1),
                'avg_humidity': round(latest_weather[1] or 0, 1),
                'total_rainfall_24h': round(latest_weather[2] or 0, 1),
                'risk_distribution': risk_levels
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/weather-trends', methods=['GET'])
def get_weather_trends():
    """Get weather trends for the past period"""
    try:
        days = request.args.get('days', 7, type=int)
        # Frontend may pass interval; it's currently informational only.
        _interval = request.args.get('interval', None, type=str)
        
        # Get daily averages
        trends = db.session.query(
            db.func.date(WeatherData.timestamp).label('date'),
            db.func.avg(WeatherData.temperature).label('avg_temp'),
            db.func.avg(WeatherData.humidity).label('avg_humidity'),
            db.func.sum(WeatherData.rainfall).label('total_rainfall')
        ).filter(
            WeatherData.timestamp >= datetime.utcnow() - timedelta(days=days)
        ).group_by(
            db.func.date(WeatherData.timestamp)
        ).order_by(
            db.func.date(WeatherData.timestamp)
        ).all()
        
        trend_data = [{
            'date': str(t.date),
            'avg_temperature': round(t.avg_temp or 0, 1),
            'avg_humidity': round(t.avg_humidity or 0, 1),
            'total_rainfall': round(t.total_rainfall or 0, 1)
        } for t in trends]

        # Chart.js friendly shape used by the dashboard UI.
        labels = [t['date'] for t in trend_data]
        chart_data = {
            'labels': labels,
            'datasets': {
                'temperature': {'data': [t['avg_temperature'] for t in trend_data]},
                'humidity': {'data': [t['avg_humidity'] for t in trend_data]},
                'rainfall': {'data': [t['total_rainfall'] for t in trend_data]},
            }
        }
        
        return jsonify({
            'success': True,
            'trends': trend_data,
            'chart_data': chart_data,
            'period_days': days
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/alert-trends', methods=['GET'])
def get_alert_trends():
    """Get alert trends (daily counts) for the past period"""
    try:
        days = request.args.get('days', 30, type=int)
        days = max(1, min(days, 365))

        since_dt = datetime.utcnow() - timedelta(days=days - 1)
        since_date = since_dt.date()
        today = datetime.utcnow().date()
        labels = []
        d = since_date
        while d <= today:
            labels.append(d.isoformat())
            d = d + timedelta(days=1)

        rows = (
            db.session.query(
                db.func.date(Alert.created_at).label('date'),
                Alert.risk_level.label('risk_level'),
                db.func.count(Alert.id).label('count'),
            )
            .filter(Alert.created_at >= datetime.combine(since_date, datetime.min.time()))
            .group_by(db.func.date(Alert.created_at), Alert.risk_level)
            .order_by(db.func.date(Alert.created_at))
            .all()
        )

        counts = {"low": {}, "medium": {}, "high": {}, "critical": {}}

        for r in rows:
            d = str(r.date)
            risk = (r.risk_level or "low").lower()
            if risk not in counts:
                counts[risk] = {}
            counts[risk][d] = int(r.count or 0)

        def _series(level: str):
            return [counts.get(level, {}).get(d, 0) for d in labels]

        total_series = [0] * len(labels)
        for i in range(len(labels)):
            total_series[i] = (
                _series("critical")[i] + _series("high")[i] + _series("medium")[i] + _series("low")[i]
            )

        chart_data = {
            "labels": labels,
            "datasets": [
                {"label": "Critical", "risk_level": "critical", "data": _series("critical")},
                {"label": "High", "risk_level": "high", "data": _series("high")},
                {"label": "Medium", "risk_level": "medium", "data": _series("medium")},
                {"label": "Low", "risk_level": "low", "data": _series("low")},
                {"label": "Total", "risk_level": "total", "data": total_series},
            ],
        }

        return jsonify({"success": True, "period_days": days, "chart_data": chart_data})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api.route('/system-status', methods=['GET'])
def get_system_status():
    """Get system status"""
    try:
        # Check database connectivity
        db.session.execute(db.text('SELECT 1'))
        db_ok = True
        
        # Get record counts
        regions_count = Region.query.count()
        users_count = User.query.count()
        alerts_count = Alert.query.count()
        weather_count = WeatherData.query.count()
        
        # Get last update time
        last_weather_update = WeatherData.query.order_by(
            WeatherData.timestamp.desc()
        ).first()
        
        return jsonify({
            'success': True,
            'status': {
                'database': 'connected' if db_ok else 'disconnected',
                'last_weather_update': last_weather_update.timestamp.isoformat() if last_weather_update else None,
                'records': {
                    'regions': regions_count,
                    'users': users_count,
                    'alerts': alerts_count,
                    'weather_readings': weather_count
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
