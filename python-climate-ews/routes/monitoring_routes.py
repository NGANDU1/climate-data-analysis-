from __future__ import annotations

import json
import os
from datetime import datetime

from flask import Blueprint, jsonify

from models.model_training_run import ModelTrainingRun
from models.weather_data import WeatherData


api = Blueprint("monitoring_admin", __name__)


def _file_info(path: str):
    if not os.path.exists(path):
        return {"exists": False, "path": path}
    st = os.stat(path)
    return {
        "exists": True,
        "path": path,
        "size_bytes": int(st.st_size),
        "modified_at": datetime.utcfromtimestamp(st.st_mtime).isoformat() + "Z",
    }


@api.route("", methods=["GET"])
def monitoring_summary():
    try:
        latest_run = ModelTrainingRun.query.order_by(ModelTrainingRun.created_at.desc()).first()
        metrics = {}
        if latest_run and latest_run.metrics_json:
            try:
                metrics = json.loads(latest_run.metrics_json)
            except Exception:
                metrics = {}

        # Model files (best-effort, may differ by OS / cwd)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        model_dir = os.path.join(base_dir, "models", "saved")
        model_files = [
            os.path.join(model_dir, "random_forest_model.pkl"),
            os.path.join(model_dir, "xgboost_model.pkl"),
            os.path.join(model_dir, "lstm_model.h5"),
        ]

        # Prediction accuracy: report last training validation accuracy when available.
        val_accuracy = {
            "random_forest": (metrics.get("random_forest") or {}).get("val_accuracy"),
            "xgboost": (metrics.get("xgboost") or {}).get("val_accuracy"),
        }

        last_weather = WeatherData.query.order_by(WeatherData.timestamp.desc()).first()
        return jsonify(
            {
                "success": True,
                "monitoring": {
                    "last_weather_update": last_weather.timestamp.isoformat() if last_weather else None,
                    "model_files": [_file_info(p) for p in model_files],
                    "last_training_run": latest_run.to_dict() if latest_run else None,
                    "last_training_val_accuracy": val_accuracy,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

