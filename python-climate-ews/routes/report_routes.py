from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from flask import Blueprint, jsonify, request, Response

from models import db
from models.model_training_run import ModelTrainingRun
from models.weather_data import WeatherData
from routes.risk_routes import predict_risk


api = Blueprint("reports_admin", __name__)


def _csv_response(filename: str, rows: list[dict], fieldnames: list[str]) -> Response:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    csv_text = buf.getvalue()

    resp = Response(csv_text, mimetype="text/csv; charset=utf-8")
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@api.route("/weather-data", methods=["GET"])
def export_weather_data():
    """
    Export weather data as CSV (default) or JSON.
    Query params: start, end, region_id, limit, format=csv|json
    """
    try:
        region_id = request.args.get("region_id", type=int)
        start = request.args.get("start")
        end = request.args.get("end")
        limit = min(request.args.get("limit", 5000, type=int) or 5000, 50000)
        fmt = (request.args.get("format") or "csv").lower()

        q = WeatherData.query
        if region_id:
            q = q.filter_by(region_id=region_id)
        if start:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            q = q.filter(WeatherData.timestamp >= start_dt)
        if end:
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            q = q.filter(WeatherData.timestamp <= end_dt)

        rows = q.order_by(WeatherData.timestamp.desc()).limit(limit).all()
        data = [r.to_dict() for r in rows]

        if fmt == "json":
            return jsonify({"success": True, "data": data, "count": len(data)})

        return _csv_response(
            "weather_data.csv",
            data,
            fieldnames=[
                "id",
                "region_id",
                "region_name",
                "dataset_id",
                "source",
                "temperature",
                "humidity",
                "rainfall",
                "wind_speed",
                "pressure",
                "timestamp",
            ],
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api.route("/risk-predictions", methods=["GET"])
def export_risk_predictions():
    """
    Export latest risk predictions as CSV or JSON.
    format=csv|json
    """
    try:
        fmt = (request.args.get("format") or "csv").lower()
        # Reuse the existing risk endpoint function.
        risk_resp = predict_risk()
        resp_obj = risk_resp[0] if isinstance(risk_resp, tuple) else risk_resp
        payload = resp_obj.get_json() if hasattr(resp_obj, "get_json") else None
        if not payload or not payload.get("success"):
            return jsonify({"success": False, "message": "Could not generate predictions"}), 500

        predictions = payload.get("predictions") or []
        if fmt == "json":
            return jsonify(payload)

        flat = []
        for p in predictions:
            flat.append(
                {
                    "region_id": p.get("region_id"),
                    "region_name": p.get("region_name"),
                    "risk_level": p.get("risk_level"),
                    "disaster_type": p.get("disaster_type"),
                    "confidence_score": p.get("confidence_score"),
                    "temperature": (p.get("current_conditions") or {}).get("temperature"),
                    "humidity": (p.get("current_conditions") or {}).get("humidity"),
                    "rainfall": (p.get("current_conditions") or {}).get("rainfall"),
                }
            )

        return _csv_response(
            "risk_predictions.csv",
            flat,
            fieldnames=[
                "region_id",
                "region_name",
                "risk_level",
                "disaster_type",
                "confidence_score",
                "temperature",
                "humidity",
                "rainfall",
            ],
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api.route("/training-summary", methods=["GET"])
def training_summary():
    run = ModelTrainingRun.query.order_by(ModelTrainingRun.created_at.desc()).first()
    if not run:
        return jsonify({"success": True, "data": None})
    metrics = {}
    if run.metrics_json:
        try:
            metrics = json.loads(run.metrics_json)
        except Exception:
            metrics = {}
    return jsonify({"success": True, "data": {"run": run.to_dict(), "metrics": metrics}})
