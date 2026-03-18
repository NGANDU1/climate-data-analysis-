from flask import Blueprint, jsonify
from flask import Blueprint, jsonify, request
from models import db
from models.weather_data import WeatherData
from models.region import Region
from datetime import datetime

api = Blueprint('weather', __name__)

@api.route('/weather', methods=['GET'])
def get_weather():
    """Get current weather data for all regions"""
    try:
        # Get latest weather data for each region
        weather_data = db.session.query(
            Region.id,
            Region.name,
            Region.latitude,
            Region.longitude,
            Region.risk_level,
            db.func.avg(WeatherData.temperature).label('temperature'),
            db.func.avg(WeatherData.humidity).label('humidity'),
            db.func.sum(WeatherData.rainfall).label('rainfall'),
            db.func.avg(WeatherData.wind_speed).label('wind_speed'),
            db.func.avg(WeatherData.pressure).label('pressure')
        ).outerjoin(WeatherData).group_by(Region.id).all()
        
        data = []
        for row in weather_data:
            data.append({
                'region_id': row.id,
                'region_name': row.name,
                'latitude': row.latitude,
                'longitude': row.longitude,
                'region_risk': row.risk_level,
                'temperature': float(row.temperature) if row.temperature else 0,
                'humidity': float(row.humidity) if row.humidity else 0,
                'rainfall': float(row.rainfall) if row.rainfall else 0,
                'wind_speed': float(row.wind_speed) if row.wind_speed else 0,
                'pressure': float(row.pressure) if row.pressure else 0
            })
        
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/weather/region/<int:region_id>', methods=['GET'])
def get_weather_by_region(region_id):
    """Get weather data for specific region"""
    try:
        weather = WeatherData.query.filter_by(region_id=region_id)\
            .order_by(WeatherData.timestamp.desc()).first()
        
        if not weather:
            return jsonify({
                'success': False,
                'message': 'No weather data found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': weather.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/weather/history', methods=['GET'])
def get_weather_history():
    """
    Historical weather data for charts/tables.

    Query params:
      - region_id (optional) -> if omitted, returns national daily averages
      - start (ISO date/datetime, optional)
      - end (ISO date/datetime, optional)
      - interval=daily (default) | hourly (best-effort)
      - limit (default 365, max 2000)
    """
    try:
        region_id = request.args.get('region_id', type=int)
        start = request.args.get('start')
        end = request.args.get('end')
        interval = (request.args.get('interval') or 'daily').lower()
        limit = min(request.args.get('limit', 365, type=int) or 365, 2000)

        filters = []
        if region_id:
            filters.append(WeatherData.region_id == region_id)

        if start:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            filters.append(WeatherData.timestamp >= start_dt)
        if end:
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            filters.append(WeatherData.timestamp <= end_dt)

        if interval == 'hourly':
            # SQLite: strftime; other DBs: date_trunc could be used. Keep portable with func.strftime fallback.
            bucket = db.func.strftime('%Y-%m-%d %H:00:00', WeatherData.timestamp)
        else:
            bucket = db.func.date(WeatherData.timestamp)

        rows = (
            db.session.query(
                bucket.label('bucket'),
                db.func.avg(WeatherData.temperature).label('temperature'),
                db.func.avg(WeatherData.humidity).label('humidity'),
                db.func.sum(WeatherData.rainfall).label('rainfall'),
                db.func.avg(WeatherData.wind_speed).label('wind_speed'),
                db.func.avg(WeatherData.pressure).label('pressure'),
            )
            .select_from(WeatherData)
            .filter(*filters)
            .group_by(bucket)
            .order_by(bucket.desc())
            .limit(limit)
            .all()
        )

        data = []
        for r in rows:
            data.append(
                {
                    'bucket': str(r.bucket),
                    'temperature': round(float(r.temperature or 0), 2),
                    'humidity': round(float(r.humidity or 0), 2),
                    'rainfall': round(float(r.rainfall or 0), 2),
                    'wind_speed': round(float(r.wind_speed or 0), 2),
                    'pressure': round(float(r.pressure or 0), 2),
                }
            )

        data = list(reversed(data))  # ascending for charts

        return jsonify(
            {
                'success': True,
                'interval': interval,
                'region_id': region_id,
                'data': data,
                'count': len(data),
            }
        )

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
