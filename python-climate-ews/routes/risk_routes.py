from flask import Blueprint, jsonify, request, Response
import csv
import io
from models.region import Region
from models.weather_data import WeatherData
from services.risk_calculator import RiskCalculator

api = Blueprint('risk', __name__)


@api.route('/predict', methods=['GET'])
def predict_risk():
    try:
        regions = Region.query.all()
        predictions = []

        for region in regions:
            weather = WeatherData.query.filter_by(region_id=region.id)\
                .order_by(WeatherData.timestamp.desc())\
                .limit(3).all()

            if not weather:
                continue

            avg_temp = sum(w.temperature for w in weather) / len(weather)
            avg_humidity = sum(w.humidity for w in weather) / len(weather)
            total_rainfall = sum(w.rainfall for w in weather)

            prediction = RiskCalculator.predict_risk({
                'temperature': avg_temp,
                'humidity': avg_humidity,
                'rainfall': total_rainfall,
                'region_name': region.name
            })

            predictions.append({
                'region_id': region.id,
                'region_name': region.name,
                'risk_level': prediction['risk_level'],
                'disaster_type': prediction['disaster_type'],
                'confidence_score': prediction['confidence_score'],
                'current_conditions': {
                    'temperature': round(avg_temp, 1),
                    'humidity': round(avg_humidity, 1),
                    'rainfall': round(total_rainfall, 1)
                },
                'alerts': prediction['alerts'],
                'recommendations': prediction['recommendations']
            })

        summary = generate_summary(predictions)

        return jsonify({
            'success': True,
            'predictions': predictions,
            'summary': summary
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/predict/<int:region_id>', methods=['GET'])
def predict_single_region(region_id):
    try:
        region = Region.query.get_or_404(region_id)

        weather = WeatherData.query.filter_by(region_id=region_id)\
            .order_by(WeatherData.timestamp.desc())\
            .first()

        if not weather:
            return jsonify({'error': 'No weather data available'}), 404

        prediction = RiskCalculator.predict_risk(weather.to_dict())

        return jsonify({
            'success': True,
            'region': region.name,
            'prediction': prediction
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def generate_summary(p):
    c = sum(1 for x in p if x['risk_level'] == 'critical')
    h = sum(1 for x in p if x['risk_level'] == 'high')
    m = sum(1 for x in p if x['risk_level'] == 'medium')
    l = sum(1 for x in p if x['risk_level'] == 'low')

    return {
        'overall_risk_level': 'critical' if c > 0 else 'high' if h > 0 else 'medium' if m > 0 else 'low',
        'critical_regions': c,
        'high_risk_regions': h,
        'medium_risk_regions': m,
        'low_risk_regions': l,
        'total_regions_monitored': len(p),
        'affected_region_names': [
            x['region_name'] for x in p
            if x['risk_level'] in ['critical', 'high']
        ]
    }


@api.route('/export', methods=['GET'])
def export_predictions():
    """
    Export latest risk predictions as CSV (default) or JSON.
    Query params:
      - format=csv|json
    """
    try:
        fmt = (request.args.get('format') or 'csv').lower()
        resp = predict_risk()
        resp_obj = resp[0] if isinstance(resp, tuple) else resp
        payload = resp_obj.get_json() if hasattr(resp_obj, 'get_json') else None
        if not payload or not payload.get('success'):
            return jsonify({'success': False, 'message': 'Could not generate predictions'}), 500

        if fmt == 'json':
            return jsonify(payload)

        predictions = payload.get('predictions') or []
        rows = []
        for p in predictions:
            cc = p.get('current_conditions') or {}
            rows.append(
                {
                    'region_id': p.get('region_id'),
                    'region_name': p.get('region_name'),
                    'risk_level': p.get('risk_level'),
                    'disaster_type': p.get('disaster_type'),
                    'confidence_score': p.get('confidence_score'),
                    'temperature': cc.get('temperature'),
                    'humidity': cc.get('humidity'),
                    'rainfall': cc.get('rainfall'),
                }
            )

        buf = io.StringIO()
        fieldnames = [
            'region_id',
            'region_name',
            'risk_level',
            'disaster_type',
            'confidence_score',
            'temperature',
            'humidity',
            'rainfall',
        ]
        w = csv.DictWriter(buf, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

        out = Response(buf.getvalue(), mimetype='text/csv; charset=utf-8')
        out.headers['Content-Disposition'] = 'attachment; filename=\"risk_predictions.csv\"'
        return out

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
