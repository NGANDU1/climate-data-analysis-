from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta

from services.alert_generator import generate_rainfall_alerts


def start_auto_alert_scheduler(app) -> None:
    """
    In-process scheduler that periodically generates auto alerts.

    Env vars:
      - AUTO_ALERTS_ENABLED (default true)
      - AUTO_ALERTS_INTERVAL_MINUTES (default 30)
    """
    global _started
    if _started:
        return
    _started = True

    try:
        interval_minutes = int((app.config.get("AUTO_ALERTS_INTERVAL_MINUTES") or 0) or 0)
    except Exception:
        interval_minutes = 0
    if interval_minutes <= 0:
        # Allow configuring via env without restarting app config machinery.
        import os

        try:
            interval_minutes = int(os.environ.get("AUTO_ALERTS_INTERVAL_MINUTES") or 30)
        except Exception:
            interval_minutes = 30
    interval_minutes = max(5, min(12 * 60, interval_minutes))

    next_run_at = datetime.utcnow()

    def loop():
        nonlocal next_run_at
        while True:
            try:
                now = datetime.utcnow()
                if now >= next_run_at:
                    with app.app_context():
                        generate_rainfall_alerts()
                    next_run_at = now + timedelta(minutes=interval_minutes)
            except Exception:
                # Best-effort background job.
                pass
            time.sleep(30)

    t = threading.Thread(target=loop, daemon=True, name="auto-alert-scheduler")
    t.start()


_started = False

