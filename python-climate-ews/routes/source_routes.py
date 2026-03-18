from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, jsonify, request

from models import db
from services.external_sources import sync_nasa_power_daily
from services.imerg_opendap import sync_gpm_imerg_daily_point


api = Blueprint("sources_admin", __name__)


def _parse_date(value: str) -> date:
    return datetime.fromisoformat(value).date()


@api.route("/nasa-power/sync", methods=["POST"])
def sync_nasa_power():
    """
    Trigger NASA POWER daily sync for all regions.

    Body (JSON):
      { "start": "2026-01-01", "end": "2026-03-17", "community": "RE" }
    """
    try:
        data = request.get_json(silent=True) or {}
        start = data.get("start")
        end = data.get("end")

        if not start or not end:
            return jsonify({"success": False, "message": "start and end are required (YYYY-MM-DD)"}), 400

        start_date = _parse_date(str(start))
        end_date = _parse_date(str(end))
        community = (data.get("community") or "RE").strip()

        result = sync_nasa_power_daily(start_date=start_date, end_date=end_date, community=community)
        return jsonify(
            {
                "success": True,
                "message": "NASA POWER sync completed",
                "result": {
                    "dataset_id": result.dataset_id,
                    "rows_received": result.rows_received,
                    "rows_imported": result.rows_imported,
                    "rows_skipped": result.rows_skipped,
                    "source": result.source,
                    "notes": result.notes,
                },
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api.route("/gpm-imerg/sync", methods=["POST"])
def sync_gpm_imerg():
    """
    Trigger GPM IMERG (satellite) daily rainfall sync for all regions.

    Requires Earthdata credentials:
      - EARTHDATA_TOKEN or EARTHDATA_USERNAME/EARTHDATA_PASSWORD

    Body (JSON):
      { "start": "2026-03-01", "end": "2026-03-17", "version": "07", "box_deg": 0.1 }
    """
    try:
        data = request.get_json(silent=True) or {}
        start = data.get("start")
        end = data.get("end")
        if not start or not end:
            return jsonify({"success": False, "message": "start and end are required (YYYY-MM-DD)"}), 400

        start_date = _parse_date(str(start))
        end_date = _parse_date(str(end))
        version = str(data.get("version") or "07").strip()
        box_deg = float(data.get("box_deg") or 0.1)

        result = sync_gpm_imerg_daily_point(start_date=start_date, end_date=end_date, version=version, box_deg=box_deg)
        return jsonify(
            {
                "success": True,
                "message": "GPM IMERG sync completed",
                "result": {
                    "dataset_id": result.dataset_id,
                    "rows_received": result.rows_received,
                    "rows_imported": result.rows_imported,
                    "rows_skipped": result.rows_skipped,
                    "source": result.source,
                    "notes": result.notes,
                },
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api.route("/sync-runs", methods=["GET"])
def list_sync_runs():
    from models.external_sync_run import ExternalSyncRun

    runs = ExternalSyncRun.query.order_by(ExternalSyncRun.created_at.desc()).limit(50).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in runs], "count": len(runs)})
