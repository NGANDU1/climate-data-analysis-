from __future__ import annotations

from flask import Blueprint, jsonify, request

from models.model_training_run import ModelTrainingRun
from services.model_training_service import trigger_training


api = Blueprint("models_admin", __name__)


@api.route("/training-runs", methods=["GET"])
def list_training_runs():
    runs = ModelTrainingRun.query.order_by(ModelTrainingRun.created_at.desc()).limit(50).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in runs], "count": len(runs)})


@api.route("/train", methods=["POST"])
def train_models():
    try:
        data = request.get_json(silent=True) or {}
        dataset_id = data.get("dataset_id")
        sources = data.get("sources")
        min_samples = data.get("min_samples")

        if isinstance(sources, str):
            sources = [s.strip() for s in sources.split(",") if s.strip()]
        if sources is not None and not isinstance(sources, list):
            return jsonify({"success": False, "message": "sources must be an array or comma-separated string"}), 400

        run = trigger_training(
            dataset_id=int(dataset_id) if dataset_id is not None and str(dataset_id).strip() else None,
            sources=[str(s) for s in sources] if sources else None,
            min_samples=int(min_samples) if min_samples is not None and str(min_samples).strip() else None,
        )
        return jsonify({"success": True, "message": "Training started", "run": run.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
