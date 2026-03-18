from __future__ import annotations

import os
import threading
import time
from datetime import date, datetime, timedelta

from models import db
from models.external_sync_run import ExternalSyncRun
from services.external_sources import sync_nasa_power_daily


def _bool_env(name: str, default: bool = False) -> bool:
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


def _latest_success(source: str) -> ExternalSyncRun | None:
    return (
        ExternalSyncRun.query.filter_by(source=source, status="success")
        .order_by(ExternalSyncRun.finished_at.desc())
        .first()
    )


def _run_once(app) -> None:
    enabled = _bool_env("AUTO_SYNC_ENABLED", True)
    if not enabled:
        return

    interval_hours = max(1, _int_env("AUTO_SYNC_INTERVAL_HOURS", 24))
    lookback_days = max(1, min(30, _int_env("AUTO_SYNC_LOOKBACK_DAYS", 3)))
    sources = (os.environ.get("AUTO_SYNC_SOURCES") or "nasa_power").strip().lower().split(",")
    sources = [s.strip() for s in sources if s.strip()]

    with app.app_context():
        end = date.today()
        start = end - timedelta(days=lookback_days)

        for source in sources:
            last = _latest_success(source)
            if last and last.finished_at and (datetime.utcnow() - last.finished_at) < timedelta(hours=interval_hours):
                continue

            run = ExternalSyncRun(
                source=source,
                status="running",
                started_at=datetime.utcnow(),
                message=f"Auto sync (lookback {lookback_days}d, interval {interval_hours}h)",
            )
            db.session.add(run)
            db.session.commit()

            try:
                if source == "nasa_power":
                    result = sync_nasa_power_daily(start_date=start, end_date=end, community="RE", track_run=False)
                elif source == "gpm_imerg":
                    from services.imerg_opendap import sync_gpm_imerg_daily_point

                    # Skip if Earthdata credentials are missing.
                    if not (os.environ.get("EARTHDATA_TOKEN") or (os.environ.get("EARTHDATA_USERNAME") and os.environ.get("EARTHDATA_PASSWORD"))):
                        run.status = "failed"
                        run.finished_at = datetime.utcnow()
                        run.message = "Missing EARTHDATA credentials; set EARTHDATA_TOKEN or EARTHDATA_USERNAME/EARTHDATA_PASSWORD"
                        db.session.commit()
                        continue

                    result = sync_gpm_imerg_daily_point(start_date=start, end_date=end, version="07")
                else:
                    run.status = "failed"
                    run.finished_at = datetime.utcnow()
                    run.message = f"Unknown AUTO_SYNC source: {source}"
                    db.session.commit()
                    continue

                run.status = "success"
                run.finished_at = datetime.utcnow()
                run.dataset_id = result.dataset_id
                run.rows_received = result.rows_received
                run.rows_imported = result.rows_imported
                run.rows_skipped = result.rows_skipped
                run.message = (run.message or "") + f"\n{result.notes}"
                db.session.commit()
            except Exception as e:
                run.status = "failed"
                run.finished_at = datetime.utcnow()
                run.message = str(e)
                db.session.commit()


def start_external_sync_scheduler(app) -> None:
    """
    Lightweight in-process scheduler that periodically syncs open-data sources.

    Controlled by env vars:
      - AUTO_SYNC_ENABLED (default true)
      - AUTO_SYNC_INTERVAL_HOURS (default 24)
      - AUTO_SYNC_LOOKBACK_DAYS (default 3)
    """

    global _started
    if _started:
        return
    _started = True

    def loop():
        while True:
            try:
                _run_once(app)
            except Exception:
                # Best-effort background job.
                pass
            time.sleep(60)

    t = threading.Thread(target=loop, daemon=True, name="external-sync-scheduler")
    t.start()


_started = False
