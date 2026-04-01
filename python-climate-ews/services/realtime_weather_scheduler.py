from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta

from services.alert_generator import generate_rainfall_alerts
from services.realtime_weather_sync import sync_openweather_current


def start_realtime_weather_scheduler(app) -> None:
    """
    Best-effort scheduler that ingests OpenWeather current conditions periodically,
    then generates rainfall alerts from the freshest readings.

    Env vars:
      - REALTIME_WEATHER_ENABLED (default true, but requires OPENWEATHER_API_KEY)
      - REALTIME_WEATHER_INTERVAL_MINUTES (default 30)
    """
    global _started
    if _started:
        return
    _started = True

    try:
        interval_minutes = int(os.environ.get("REALTIME_WEATHER_INTERVAL_MINUTES") or 30)
    except Exception:
        interval_minutes = 30
    interval_minutes = max(10, min(12 * 60, interval_minutes))

    next_run_at = datetime.utcnow()

    def loop():
        nonlocal next_run_at
        while True:
            try:
                now = datetime.utcnow()
                if now >= next_run_at:
                    with app.app_context():
                        sync_openweather_current(min_interval_minutes=max(10, interval_minutes - 5))
                        generate_rainfall_alerts()
                    next_run_at = now + timedelta(minutes=interval_minutes)
            except Exception:
                pass
            time.sleep(30)

    t = threading.Thread(target=loop, daemon=True, name="realtime-weather-scheduler")
    t.start()


_started = False

