from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.forecast_service import forecast_region_variable


api = Blueprint("forecast", __name__)


@api.route("/forecast", methods=["GET"])
def forecast():
    try:
        region_id = request.args.get("region_id", type=int)
        variable = (request.args.get("variable") or "rainfall").lower()
        method = (request.args.get("method") or "naive").lower()
        days = request.args.get("days", 7, type=int)

        if not region_id:
            return jsonify({"success": False, "message": "region_id is required"}), 400
        if variable not in {"temperature", "humidity", "rainfall"}:
            return jsonify({"success": False, "message": "variable must be temperature, humidity, or rainfall"}), 400
        if method not in {"naive", "arima"}:
            return jsonify({"success": False, "message": "method must be naive or arima"}), 400

        result = forecast_region_variable(
            region_id=region_id,
            variable=variable,  # type: ignore[arg-type]
            days=days,
            method=method,  # type: ignore[arg-type]
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

