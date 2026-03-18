from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request

from models import db
from models.weather_data import WeatherData


api = Blueprint("weather_admin", __name__)


@api.route("", methods=["GET"])
def list_weather_data():
    """
    Query weather_data with optional filters.

    Query params:
      - region_id
      - dataset_id
      - source
      - start (ISO date/datetime)
      - end (ISO date/datetime)
      - limit (default 500, max 5000)
    """
    try:
        region_id = request.args.get("region_id", type=int)
        dataset_id = request.args.get("dataset_id", type=int)
        source = request.args.get("source", type=str)
        start = request.args.get("start")
        end = request.args.get("end")
        limit = min(request.args.get("limit", 500, type=int) or 500, 5000)

        q = WeatherData.query
        if region_id:
            q = q.filter_by(region_id=region_id)
        if dataset_id:
            q = q.filter_by(dataset_id=dataset_id)
        if source:
            q = q.filter_by(source=source)

        if start:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            q = q.filter(WeatherData.timestamp >= start_dt)
        if end:
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            q = q.filter(WeatherData.timestamp <= end_dt)

        rows = q.order_by(WeatherData.timestamp.desc()).limit(limit).all()
        return jsonify({"success": True, "data": [r.to_dict() for r in rows], "count": len(rows)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api.route("/<int:row_id>", methods=["PATCH"])
def update_weather_row(row_id: int):
    try:
        row = WeatherData.query.get(row_id)
        if not row:
            return jsonify({"success": False, "message": "Weather record not found"}), 404

        data = request.get_json(silent=True) or {}
        for key in ["temperature", "humidity", "rainfall", "wind_speed", "pressure"]:
            if key in data:
                setattr(row, key, float(data[key]) if data[key] is not None else None)

        if "timestamp" in data and data["timestamp"]:
            row.timestamp = datetime.fromisoformat(str(data["timestamp"]).replace("Z", "+00:00"))

        db.session.commit()
        return jsonify({"success": True, "message": "Updated", "data": row.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api.route("/<int:row_id>", methods=["DELETE"])
def delete_weather_row(row_id: int):
    try:
        row = WeatherData.query.get(row_id)
        if not row:
            return jsonify({"success": False, "message": "Weather record not found"}), 404
        db.session.delete(row)
        db.session.commit()
        return jsonify({"success": True, "message": "Deleted"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
