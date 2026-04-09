from flask import Blueprint, jsonify, request
from models import db
from models.weather_data import WeatherData
from models.region import Region
from datetime import datetime
from datetime import timezone
import os
import requests
from requests import HTTPError

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


# ============================================
# External Enrichment (OpenWeather proxy)
# ============================================
def _get_openweather_key(optional: bool = False):
    key = os.getenv("OPENWEATHER_API_KEY")
    if not key:
        if optional:
            return None
        raise ValueError("OPENWEATHER_API_KEY is not set on the server")
    return key


def _resolve_coords(region_id: int | None, lat: float | None, lon: float | None):
    if region_id:
        region = Region.query.get(region_id)
        if not region:
            raise ValueError("Region not found")
        if region.latitude is None or region.longitude is None:
            raise ValueError("Region coordinates are missing (latitude/longitude)")
        return float(region.latitude), float(region.longitude), region.name
    if lat is None or lon is None:
        raise ValueError("Provide region_id or lat/lon")
    return float(lat), float(lon), None


def _open_meteo_forecast(lat: float, lon: float, days: int):
    """
    Fetch daily + hourly fields from Open-Meteo (no API key).

    Returns the raw JSON payload.
    """
    days = max(1, min(int(days or 1), 7))
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "UTC",
        "forecast_days": days,
        "daily": ",".join(
            [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "sunrise",
                "sunset",
                "uv_index_max",
            ]
        ),
        # Visibility is typically an hourly variable; keep it best-effort.
        "hourly": "visibility",
    }
    res = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=12)
    res.raise_for_status()
    return res.json() or {}


def _iso_z(dt: datetime | None):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"


def _parse_open_meteo_utc(ts: str | None):
    if not ts:
        return None
    # Open-Meteo returns "YYYY-MM-DDTHH:MM" in requested timezone.
    try:
        return datetime.fromisoformat(str(ts)).replace(tzinfo=timezone.utc)
    except Exception:
        return None


@api.route("/external/weather", methods=["GET"])
def external_weather():
    """
    Proxy minimal OpenWeather current weather fields used by the replica UI.
    Query params:
      - region_id OR lat/lon
    Returns:
      - sunrise/sunset (UTC ISO), visibility_m, description, icon, uvi_max (best-effort)
    """
    try:
        region_id = request.args.get("region_id", type=int)
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)

        rlat, rlon, region_name = _resolve_coords(region_id, lat, lon)

        key = _get_openweather_key(optional=True)
        if key:
            try:
                res = requests.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"lat": rlat, "lon": rlon, "appid": key, "units": "metric"},
                    timeout=12,
                )
                res.raise_for_status()
                data = res.json() or {}

                sys = data.get("sys") or {}
                weather0 = (data.get("weather") or [{}])[0] or {}

                sunrise = sys.get("sunrise")
                sunset = sys.get("sunset")

                def iso_utc(ts):
                    if not ts:
                        return None
                    return datetime.utcfromtimestamp(int(ts)).isoformat() + "Z"

                return jsonify(
                    {
                        "success": True,
                        "region_id": region_id,
                        "region_name": region_name,
                        "source": "openweather",
                        "data": {
                            "sunrise_utc": iso_utc(sunrise),
                            "sunset_utc": iso_utc(sunset),
                            "visibility_m": data.get("visibility"),
                            "description": weather0.get("description"),
                            "icon": weather0.get("icon"),
                            "uvi_max": None,
                        },
                    }
                )
            except Exception:
                # Fall back to Open-Meteo if the OpenWeather key is invalid/unauthorized or the request fails.
                pass

        # Fallback: Open-Meteo (no key required)
        payload = _open_meteo_forecast(rlat, rlon, 1)
        daily = payload.get("daily") or {}
        sunrise0 = (daily.get("sunrise") or [None])[0]
        sunset0 = (daily.get("sunset") or [None])[0]
        uvi0 = (daily.get("uv_index_max") or [None])[0]
        sunrise_dt = _parse_open_meteo_utc(sunrise0)
        sunset_dt = _parse_open_meteo_utc(sunset0)

        visibility_m = None
        hourly = payload.get("hourly") or {}
        times = hourly.get("time") or []
        vis = hourly.get("visibility") or []
        if times and vis and len(times) == len(vis):
            # Pick the closest hourly value to "now" in UTC.
            now = datetime.now(timezone.utc)
            best_i = 0
            best_delta = None
            for i, t in enumerate(times):
                dt = _parse_open_meteo_utc(t)
                if not dt:
                    continue
                d = abs((dt - now).total_seconds())
                if best_delta is None or d < best_delta:
                    best_delta = d
                    best_i = i
            try:
                visibility_m = float(vis[best_i]) if vis[best_i] is not None else None
            except Exception:
                visibility_m = None

        return jsonify(
            {
                "success": True,
                "region_id": region_id,
                "region_name": region_name,
                "source": "open-meteo",
                "data": {
                    "sunrise_utc": _iso_z(sunrise_dt),
                    "sunset_utc": _iso_z(sunset_dt),
                    "visibility_m": visibility_m,
                    "description": None,
                    "icon": None,
                    "uvi_max": float(uvi0) if uvi0 is not None else None,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api.route("/external/air-quality", methods=["GET"])
def external_air_quality():
    """
    Proxy OpenWeather air pollution (AQI + components).
    Query params:
      - region_id OR lat/lon
    """
    try:
        region_id = request.args.get("region_id", type=int)
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)

        rlat, rlon, region_name = _resolve_coords(region_id, lat, lon)
        key = _get_openweather_key()

        res = requests.get(
            "https://api.openweathermap.org/data/2.5/air_pollution",
            params={"lat": rlat, "lon": rlon, "appid": key},
            timeout=12,
        )
        res.raise_for_status()
        payload = res.json() or {}
        item = (payload.get("list") or [{}])[0] or {}

        main = item.get("main") or {}
        components = item.get("components") or {}

        return jsonify(
            {
                "success": True,
                "region_id": region_id,
                "region_name": region_name,
                "data": {
                    "aqi": main.get("aqi"),  # 1..5 (Good..Very Poor)
                    "components": components,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api.route("/external/forecast", methods=["GET"])
def external_forecast():
    """
    Proxy OpenWeather 5-day /forecast (3-hour) and aggregate to daily.
    Query params:
      - region_id OR lat/lon
      - days (optional, 1-5; default 5)
    Returns:
      - daily: [{date, temp_avg_c, pop_max, rain_mm_sum}]
    """
    try:
        region_id = request.args.get("region_id", type=int)
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        days = request.args.get("days", 5, type=int) or 5
        days = max(1, min(days, 5))

        rlat, rlon, region_name = _resolve_coords(region_id, lat, lon)

        key = _get_openweather_key(optional=True)
        if key:
            try:
                res = requests.get(
                    "https://api.openweathermap.org/data/2.5/forecast",
                    params={"lat": rlat, "lon": rlon, "appid": key, "units": "metric"},
                    timeout=12,
                )
                res.raise_for_status()
                payload = res.json() or {}
                items = payload.get("list") or []

                by_day: dict[str, dict[str, float]] = {}
                for item in items:
                    dt_txt = item.get("dt_txt")
                    if not dt_txt:
                        continue
                    day = str(dt_txt).split(" ")[0]
                    main = item.get("main") or {}
                    temp = main.get("temp")
                    pop = item.get("pop")
                    rain = (item.get("rain") or {}).get("3h") or 0.0

                    row = by_day.setdefault(day, {"temp_sum": 0.0, "temp_n": 0.0, "pop_max": 0.0, "rain_sum": 0.0})
                    if temp is not None:
                        row["temp_sum"] += float(temp)
                        row["temp_n"] += 1.0
                    if pop is not None:
                        row["pop_max"] = max(row["pop_max"], float(pop))
                    if rain is not None:
                        row["rain_sum"] += float(rain)

                daily = []
                for day, v in sorted(by_day.items()):
                    temp_avg = (v["temp_sum"] / v["temp_n"]) if v["temp_n"] else None
                    daily.append(
                        {
                            "date": day,
                            "temp_avg_c": temp_avg,
                            "pop_max": v["pop_max"],
                            "rain_mm_sum": v["rain_sum"],
                            "sunrise_utc": None,
                            "sunset_utc": None,
                            "uvi_max": None,
                        }
                    )

                daily = daily[:days]

                return jsonify(
                    {
                        "success": True,
                        "region_id": region_id,
                        "region_name": region_name,
                        "source": "openweather",
                        "data": {"daily": daily},
                    }
                )
            except Exception:
                # Fall back to Open-Meteo if the OpenWeather key is invalid/unauthorized or the request fails.
                pass

        # Fallback: Open-Meteo daily forecast (includes POP + sunrise/sunset + UV)
        payload = _open_meteo_forecast(rlat, rlon, days)
        daily = payload.get("daily") or {}
        dates = daily.get("time") or []
        tmax = daily.get("temperature_2m_max") or []
        tmin = daily.get("temperature_2m_min") or []
        pr_sum = daily.get("precipitation_sum") or []
        pr_prob = daily.get("precipitation_probability_max") or []
        sunrise = daily.get("sunrise") or []
        sunset = daily.get("sunset") or []
        uvmax = daily.get("uv_index_max") or []

        out = []
        for i, day in enumerate(dates[:days]):
            try:
                mx = float(tmax[i]) if i < len(tmax) and tmax[i] is not None else None
                mn = float(tmin[i]) if i < len(tmin) and tmin[i] is not None else None
                temp_avg = ((mx + mn) / 2.0) if mx is not None and mn is not None else mx or mn
            except Exception:
                temp_avg = None

            try:
                rain_sum = float(pr_sum[i]) if i < len(pr_sum) and pr_sum[i] is not None else 0.0
            except Exception:
                rain_sum = 0.0

            try:
                prob = float(pr_prob[i]) if i < len(pr_prob) and pr_prob[i] is not None else None
            except Exception:
                prob = None

            sr_dt = _parse_open_meteo_utc(sunrise[i] if i < len(sunrise) else None)
            ss_dt = _parse_open_meteo_utc(sunset[i] if i < len(sunset) else None)

            try:
                uvi = float(uvmax[i]) if i < len(uvmax) and uvmax[i] is not None else None
            except Exception:
                uvi = None

            out.append(
                {
                    "date": str(day),
                    "temp_avg_c": temp_avg,
                    "pop_max": (prob / 100.0) if prob is not None else None,
                    "rain_mm_sum": rain_sum,
                    "sunrise_utc": _iso_z(sr_dt),
                    "sunset_utc": _iso_z(ss_dt),
                    "uvi_max": uvi,
                }
            )

        return jsonify(
            {
                "success": True,
                "region_id": region_id,
                "region_name": region_name,
                "source": "open-meteo",
                "data": {"daily": out},
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api.route("/external/uv", methods=["GET"])
def external_uv():
    """
    Best-effort UV index via OpenWeather One Call 3.0.
    Note: This may require a paid plan; if unavailable, returns success=false.

    Query params:
      - region_id OR lat/lon
    """
    try:
        region_id = request.args.get("region_id", type=int)
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)

        rlat, rlon, region_name = _resolve_coords(region_id, lat, lon)
        key = _get_openweather_key(optional=True)
        if key:
            try:
                res = requests.get(
                    "https://api.openweathermap.org/data/3.0/onecall",
                    params={"lat": rlat, "lon": rlon, "appid": key, "units": "metric", "exclude": "minutely,hourly,daily,alerts"},
                    timeout=12,
                )
                res.raise_for_status()
                payload = res.json() or {}
                current = payload.get("current") or {}
                uvi = current.get("uvi")
                if uvi is not None:
                    return jsonify(
                        {"success": True, "region_id": region_id, "region_name": region_name, "source": "openweather", "data": {"uvi": float(uvi)}}
                    )
            except HTTPError:
                # One Call 3.0 often requires special access; fall back to Open-Meteo.
                pass
            except Exception:
                pass

        # Fallback: Open-Meteo daily UV max (today)
        payload = _open_meteo_forecast(rlat, rlon, 1)
        daily = payload.get("daily") or {}
        uvs = daily.get("uv_index_max") or []
        if not uvs or uvs[0] is None:
            return jsonify({"success": False, "message": "UV index not available"}), 502
        return jsonify(
            {"success": True, "region_id": region_id, "region_name": region_name, "source": "open-meteo", "data": {"uvi": float(uvs[0])}}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
