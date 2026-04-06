from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta

from models import db
from models.alert import Alert
from services.notification_service import NotificationService


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except Exception:
        return default


def dispatch_pending_alerts(max_alerts: int = 25) -> dict:
    """
    Send notifications for alerts that haven't been sent yet.

    Uses Alert.is_sent + sent_count to track completion.
    """
    if not _bool_env("NOTIFICATIONS_ENABLED", True):
        return {"success": True, "enabled": False, "processed": 0}

    lookback_hours = max(1, _int_env("NOTIFICATIONS_LOOKBACK_HOURS", 24 * 7))
    cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)

    pending = (
        Alert.query.filter(Alert.is_sent.is_(False))
        .filter(Alert.created_at >= cutoff)
        .order_by(Alert.created_at.asc())
        .limit(max(1, min(500, int(max_alerts or 25))))
        .all()
    )

    processed = 0
    sent_alerts = 0

    for alert in pending:
        processed += 1
        method_filter = None
        if (not getattr(alert, "is_manual", False)) and str(getattr(alert, "risk_level", "")).strip().lower() == "medium":
            # Medium warnings: auto-send email notifications.
            method_filter = {"email"}

        result = NotificationService.send_alert(alert, method_filter=method_filter)
        alert.is_sent = bool(result.get("success"))
        alert.sent_count = int(result.get("sent_count") or 0)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

        if alert.is_sent:
            sent_alerts += 1

    return {"success": True, "enabled": True, "processed": processed, "sent_alerts": sent_alerts}


def start_notification_dispatcher(app) -> None:
    """
    In-process scheduler that periodically dispatches pending alerts.

    Env vars:
      - NOTIFICATIONS_ENABLED (default true)
      - NOTIFICATIONS_POLL_SECONDS (default 60)
      - NOTIFICATIONS_MAX_ALERTS_PER_RUN (default 25)
      - NOTIFICATIONS_LOOKBACK_HOURS (default 168)
    """
    global _started
    if _started:
        return
    _started = True

    poll_seconds = max(15, _int_env("NOTIFICATIONS_POLL_SECONDS", 60))
    max_alerts = max(1, _int_env("NOTIFICATIONS_MAX_ALERTS_PER_RUN", 25))

    def loop():
        while True:
            try:
                if _bool_env("NOTIFICATIONS_ENABLED", True):
                    with app.app_context():
                        dispatch_pending_alerts(max_alerts=max_alerts)
            except Exception:
                # Best-effort background job.
                pass
            time.sleep(poll_seconds)

    t = threading.Thread(target=loop, daemon=True, name="notification-dispatcher")
    t.start()


_started = False
