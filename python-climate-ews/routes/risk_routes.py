from flask import Blueprint, jsonify, request, Response
from datetime import date as dt_date, datetime, timedelta
import csv
import io
from models.region import Region
from models.weather_data import WeatherData
from services.risk_calculator import RiskCalculator
from services.forecast_service import forecast_region_variable

api = Blueprint('risk', __name__)


def _parse_iso_date(value: str | None, *, default: dt_date) -> dt_date:
    if not value:
        return default
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        # Accept YYYY-MM-DD
        try:
            return dt_date.fromisoformat(value)
        except Exception:
            return default


def _severity_rank(level: str | None) -> int:
    lvl = (level or "low").lower()
    return {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(lvl, 1)


def _plain_language(disaster_type: str, risk_level: str, *, region_name: str, day: dt_date) -> tuple[str, list[str]]:
    level = (risk_level or "low").lower()
    dtype = (disaster_type or "general").lower()

    headline = f"{level.title()} risk in {region_name} on {day.isoformat()}"

    actions: list[str] = []
    if level == "critical":
        actions.append("Act now and follow local guidance.")
    elif level == "high":
        actions.append("Prepare today and stay alert.")
    elif level == "medium":
        actions.append("Be careful and check updates.")
    else:
        actions.append("Keep monitoring.")

    if dtype == "flood":
        actions.append("Avoid rivers and low-lying areas.")
    elif dtype == "drought":
        actions.append("Save water and protect crops/livestock.")
    elif dtype == "extreme_heat":
        actions.append("Drink water and avoid midday sun.")
    elif dtype == "extreme_cold":
        actions.append("Keep warm and protect children/elderly.")
    elif dtype == "storm":
        actions.append("Secure loose items and stay indoors if needed.")

    return headline, actions


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


@api.route('/outlook', methods=['GET'])
def outlook():
    """
    Location + date based outlook.

    Query params:
      - region_id (required)
      - date (optional, ISO YYYY-MM-DD; default today)
      - days (optional, 1-14; default 7)
      - method (optional): naive|arima (default naive) for the internal forecast step
    """
    try:
        region_id = request.args.get("region_id", type=int)
        if not region_id:
            return jsonify({"success": False, "message": "region_id is required"}), 400

        start_date = _parse_iso_date(request.args.get("date"), default=dt_date.today())
        days = int(request.args.get("days", 7, type=int) or 7)
        days = max(1, min(days, 14))

        method = (request.args.get("method") or "naive").lower()
        if method not in {"naive", "arima"}:
            return jsonify({"success": False, "message": "method must be naive or arima"}), 400

        region = Region.query.get_or_404(region_id)
        region_name = region.name

        # Use recent local readings as "today" baseline (works offline).
        recent = (
            WeatherData.query.filter_by(region_id=region.id)
            .order_by(WeatherData.timestamp.desc())
            .limit(3)
            .all()
        )

        estimated = False
        estimate_label = None

        if not recent:
            # Fallback: "last known national estimate" (also works offline),
            # computed from recent readings across all regions that have data.
            per_region = []
            for r in Region.query.all():
                rows = (
                    WeatherData.query.filter_by(region_id=r.id)
                    .order_by(WeatherData.timestamp.desc())
                    .limit(3)
                    .all()
                )
                if not rows:
                    continue
                per_region.append(
                    {
                        "temperature": sum(w.temperature for w in rows) / len(rows),
                        "humidity": sum(w.humidity for w in rows) / len(rows),
                        "rainfall": sum(w.rainfall for w in rows),
                    }
                )

            if not per_region:
                return jsonify(
                    {
                        "success": False,
                        "message": "No saved weather history yet. Sync/collect data first.",
                    }
                ), 404

            avg_temp = sum(x["temperature"] for x in per_region) / len(per_region)
            avg_humidity = sum(x["humidity"] for x in per_region) / len(per_region)
            total_rainfall = sum(x["rainfall"] for x in per_region) / len(per_region)

            estimated = True
            estimate_label = "national"
        else:
            avg_temp = sum(w.temperature for w in recent) / len(recent)
            avg_humidity = sum(w.humidity for w in recent) / len(recent)
            total_rainfall = sum(w.rainfall for w in recent)
        observed = {
            "temperature": float(avg_temp),
            "humidity": float(avg_humidity),
            "rainfall": float(total_rainfall),
        }

        today = dt_date.today()
        end_date = start_date + timedelta(days=days - 1)
        max_offset = max(0, (end_date - today).days)

        # Forecast per variable up to the furthest requested day.
        forecasts: dict[str, dict[str, float]] = {"temperature": {}, "humidity": {}, "rainfall": {}}
        if max_offset > 0:
            for variable in ("temperature", "humidity", "rainfall"):
                result = forecast_region_variable(
                    region_id=region.id,
                    variable=variable,  # type: ignore[arg-type]
                    days=max_offset,
                    method=method,  # type: ignore[arg-type]
                )
                for f in result.get("forecast") or []:
                    forecasts[variable][str(f.get("date"))] = float(f.get("value") or 0.0)

        outlook_rows = []
        for i in range(days):
            day = start_date + timedelta(days=i)
            offset = (day - today).days

            if offset <= 0:
                conditions = dict(observed)
                source = "observed"
            else:
                conditions = {
                    "temperature": forecasts["temperature"].get(day.isoformat(), observed["temperature"]),
                    "humidity": forecasts["humidity"].get(day.isoformat(), observed["humidity"]),
                    "rainfall": forecasts["rainfall"].get(day.isoformat(), observed["rainfall"]),
                }
                source = method

            prediction = RiskCalculator.predict_risk(
                {
                    "temperature": conditions["temperature"],
                    "humidity": conditions["humidity"],
                    "rainfall": conditions["rainfall"],
                    "region_name": region_name,
                }
            )

            # Reduce confidence for further-out forecasts.
            base_conf = float(prediction.get("confidence_score") or 0.0)
            conf_factor = 1.0 if offset <= 0 else max(0.40, 1.0 - (offset * 0.08))
            conf = round(base_conf * conf_factor, 2)

            risk_level = str(prediction.get("risk_level") or "low")
            disaster_type = str(prediction.get("disaster_type") or "general")
            headline, actions = _plain_language(disaster_type, risk_level, region_name=region_name, day=day)
            if estimated and estimate_label:
                headline = f"{headline} (Estimated from {estimate_label} data)"

            outlook_rows.append(
                {
                    "date": day.isoformat(),
                    "risk_level": risk_level,
                    "severity": _severity_rank(risk_level),
                    "disaster_type": disaster_type,
                    "confidence_score": conf,
                    "source": source,
                    "predicted_conditions": {
                        "temperature": round(float(conditions["temperature"]), 1),
                        "humidity": round(float(conditions["humidity"]), 1),
                        "rainfall": round(float(conditions["rainfall"]), 1),
                    },
                    "message": headline,
                    "actions": actions,
                    "alerts": prediction.get("alerts") or [],
                    "recommendations": prediction.get("recommendations") or [],
                }
            )

        worst = max(outlook_rows, key=lambda r: int(r.get("severity") or 1))

        return jsonify(
            {
                "success": True,
                "region_id": region.id,
                "region_name": region_name,
                "start_date": start_date.isoformat(),
                "days": days,
                "method": method,
                "estimated": estimated,
                "estimate_source": estimate_label,
                "generated_at": datetime.utcnow().isoformat(),
                "worst_day": {
                    "date": worst.get("date"),
                    "risk_level": worst.get("risk_level"),
                    "disaster_type": worst.get("disaster_type"),
                },
                "outlook": outlook_rows,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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
