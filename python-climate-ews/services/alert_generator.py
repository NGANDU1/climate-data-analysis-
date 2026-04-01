from __future__ import annotations

import os
from datetime import datetime, timedelta

from models import db
from models.alert import Alert
from models.region import Region
from models.weather_data import WeatherData


_SEVERITY = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _min_level() -> str:
    raw = (os.environ.get("AUTO_ALERTS_MIN_RISK") or "low").strip().lower()
    return raw if raw in _SEVERITY else "low"


def _rain_thresholds() -> dict[str, float]:
    """
    Rainfall thresholds in mm for generating "small alerts".

    Defaults are intentionally low so the system emits advisories for real rainfall,
    but still rate-limited by cooldown.
    """
    return {
        "low": float(os.environ.get("AUTO_ALERTS_RAIN_LOW_MM") or 1.0),
        "medium": float(os.environ.get("AUTO_ALERTS_RAIN_MEDIUM_MM") or 10.0),
        "high": float(os.environ.get("AUTO_ALERTS_RAIN_HIGH_MM") or 30.0),
        "critical": float(os.environ.get("AUTO_ALERTS_RAIN_CRITICAL_MM") or 60.0),
    }


def _rain_risk_level(rain_mm: float) -> str:
    t = _rain_thresholds()
    if rain_mm >= t["critical"]:
        return "critical"
    if rain_mm >= t["high"]:
        return "high"
    if rain_mm >= t["medium"]:
        return "medium"
    if rain_mm >= t["low"]:
        return "low"
    return "low"


def _should_generate(level: str) -> bool:
    return _SEVERITY.get(level, 0) >= _SEVERITY.get(_min_level(), 1)


def generate_rainfall_alerts() -> dict:
    """
    Generate automatic alerts from the latest weather readings.

    Uses latest WeatherData per region. If readings are stale, no alert is generated.
    Dedupe is enforced with a per-region cooldown window.
    """
    if not _bool_env("AUTO_ALERTS_ENABLED", True):
        return {"success": True, "enabled": False, "generated": 0, "skipped_stale": 0, "skipped_cooldown": 0}

    cooldown_hours = max(1, _int_env("AUTO_ALERTS_COOLDOWN_HOURS", 12))
    stale_hours = max(1, _int_env("AUTO_ALERTS_STALE_HOURS", 72))

    now = datetime.utcnow()
    cooldown_cutoff = now - timedelta(hours=cooldown_hours)
    stale_cutoff = now - timedelta(hours=stale_hours)

    generated = 0
    skipped_stale = 0
    skipped_cooldown = 0

    for region in Region.query.all():
        latest = (
            WeatherData.query.filter_by(region_id=region.id)
            .order_by(WeatherData.timestamp.desc())
            .first()
        )
        if not latest or not latest.timestamp:
            continue
        if latest.timestamp < stale_cutoff:
            skipped_stale += 1
            continue

        rain_mm = float(latest.rainfall or 0.0)
        level = _rain_risk_level(rain_mm)
        if not _should_generate(level):
            continue

        # Avoid spamming: one auto rain alert per region per cooldown window.
        existing = (
            Alert.query.filter(Alert.region_id == region.id)
            .filter(Alert.is_manual.is_(False))
            .filter(Alert.disaster_type == "rain")
            .filter(Alert.created_at >= cooldown_cutoff)
            .order_by(Alert.created_at.desc())
            .first()
        )
        if existing:
            skipped_cooldown += 1
            continue

        day = latest.timestamp.date().isoformat()
        if level in {"critical", "high"}:
            headline = "Heavy rain"
        elif level == "medium":
            headline = "Moderate rain"
        else:
            headline = "Light rain"

        msg = f"{headline} observed in {region.name} on {day}: {rain_mm:.1f}mm"
        alert = Alert(
            message=msg,
            risk_level=level,
            disaster_type="rain",
            region_id=region.id,
            is_manual=False,
        )
        db.session.add(alert)
        generated += 1

    if generated:
        db.session.commit()

    return {
        "success": True,
        "enabled": True,
        "generated": generated,
        "skipped_stale": skipped_stale,
        "skipped_cooldown": skipped_cooldown,
        "cooldown_hours": cooldown_hours,
        "stale_hours": stale_hours,
        "min_risk": _min_level(),
        "thresholds_mm": _rain_thresholds(),
    }

