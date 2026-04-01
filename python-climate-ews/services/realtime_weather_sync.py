from __future__ import annotations

import os
from datetime import datetime, timedelta

import requests

from models import db
from models.region import Region
from models.weather_data import WeatherData


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _float(v, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def _api_key() -> str:
    return (os.environ.get("OPENWEATHER_API_KEY") or "").strip()


def sync_openweather_current(*, min_interval_minutes: int = 20, timeout_seconds: float = 20.0) -> dict:
    """
    Fetch current conditions per Region from OpenWeather and insert as WeatherData rows.

    Requires OPENWEATHER_API_KEY. If missing, returns enabled=False.
    """
    key = _api_key()
    if not key:
        return {"success": True, "enabled": False, "message": "Missing OPENWEATHER_API_KEY", "inserted": 0, "skipped_recent": 0}

    if not _bool_env("REALTIME_WEATHER_ENABLED", True):
        return {"success": True, "enabled": False, "message": "REALTIME_WEATHER_ENABLED=false", "inserted": 0, "skipped_recent": 0}

    min_interval_minutes = max(5, int(min_interval_minutes))
    cutoff = datetime.utcnow() - timedelta(minutes=min_interval_minutes)

    inserted = 0
    skipped_recent = 0
    errors: list[str] = []

    base = "https://api.openweathermap.org/data/2.5/weather"

    for region in Region.query.all():
        if region.latitude is None or region.longitude is None:
            continue

        recent = (
            WeatherData.query.filter_by(region_id=region.id, source="openweather")
            .order_by(WeatherData.timestamp.desc())
            .first()
        )
        if recent and recent.timestamp and recent.timestamp >= cutoff:
            skipped_recent += 1
            continue

        params = {
            "lat": region.latitude,
            "lon": region.longitude,
            "appid": key,
            "units": "metric",
        }
        try:
            r = requests.get(base, params=params, timeout=timeout_seconds)
            r.raise_for_status()
            payload = r.json() or {}
        except Exception as e:
            errors.append(f"{region.name}: {e}")
            continue

        main = payload.get("main") or {}
        wind = payload.get("wind") or {}
        rain = payload.get("rain") or {}

        # OpenWeather uses rainfall volumes in mm for the last 1h/3h when present.
        rain_mm = _float(rain.get("1h"), _float(rain.get("3h"), 0.0))

        wd = WeatherData(
            region_id=region.id,
            dataset_id=None,
            source="openweather",
            temperature=_float(main.get("temp"), 0.0),
            humidity=_float(main.get("humidity"), 0.0),
            rainfall=rain_mm,
            wind_speed=_float(wind.get("speed"), 0.0),
            pressure=_float(main.get("pressure"), 0.0),
            timestamp=datetime.utcnow(),
        )
        db.session.add(wd)
        inserted += 1

    if inserted:
        db.session.commit()

    return {
        "success": True,
        "enabled": True,
        "inserted": inserted,
        "skipped_recent": skipped_recent,
        "errors": errors[:10],
        "timestamp": datetime.utcnow().isoformat(),
    }

