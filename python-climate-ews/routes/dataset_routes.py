from __future__ import annotations

from flask import Blueprint, jsonify, request

from models import db
from models.dataset import Dataset
from models.weather_data import WeatherData
from services.dataset_importer import import_dataset_from_upload, import_dataset_from_records


api = Blueprint("datasets", __name__)


@api.route("", methods=["GET"])
def list_datasets():
    datasets = Dataset.query.order_by(Dataset.uploaded_at.desc()).limit(200).all()
    return jsonify({"success": True, "data": [d.to_dict() for d in datasets], "count": len(datasets)})


@api.route("/upload", methods=["POST"])
def upload_dataset():
    """
    Upload a climate dataset (CSV/Excel) and import into weather_data.

    Form fields:
      - file: required (csv/xlsx/xls)
      - name: optional
      - notes: optional
      - default_region_id: optional (used if file has no region column)
      - create_missing_regions: optional (true/false)
    """
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "message": "Missing file"}), 400

        f = request.files["file"]
        if not f or not f.filename:
            return jsonify({"success": False, "message": "Missing filename"}), 400

        name = (request.form.get("name") or f.filename or "Uploaded dataset").strip()
        notes = request.form.get("notes")
        default_region_id = request.form.get("default_region_id", type=int)
        create_missing_regions = (request.form.get("create_missing_regions") or "").lower() in {"1", "true", "yes"}

        res = import_dataset_from_upload(
            file_bytes=f.read(),
            filename=f.filename,
            name=name,
            notes=notes,
            default_region_id=default_region_id,
            create_missing_regions=create_missing_regions,
        )

        return jsonify(
            {
                "success": True,
                "message": "Dataset imported",
                "dataset": res.dataset.to_dict(),
                "import_summary": {
                    "rows_received": res.rows_received,
                    "rows_imported": res.rows_imported,
                    "rows_skipped": res.rows_skipped,
                    "skipped_reasons_sample": res.skipped_reasons_sample,
                },
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api.route("/import-json", methods=["POST"])
def import_json():
    """
    Import climate data from JSON records (API data).

    Body:
      { "name": "...", "notes": "...", "default_region_id": 1, "records": [ { ... }, ... ] }
    """
    try:
        data = request.get_json(silent=True) or {}
        records = data.get("records") or []
        if not isinstance(records, list) or not records:
            return jsonify({"success": False, "message": "records must be a non-empty array"}), 400

        name = (data.get("name") or "API dataset").strip()
        notes = data.get("notes")
        default_region_id = data.get("default_region_id")
        create_missing_regions = bool(data.get("create_missing_regions", False))

        res = import_dataset_from_records(
            records=records,
            name=name,
            notes=notes,
            default_region_id=default_region_id,
            create_missing_regions=create_missing_regions,
        )

        return jsonify(
            {
                "success": True,
                "message": "Dataset imported",
                "dataset": res.dataset.to_dict(),
                "import_summary": {
                    "rows_received": res.rows_received,
                    "rows_imported": res.rows_imported,
                    "rows_skipped": res.rows_skipped,
                    "skipped_reasons_sample": res.skipped_reasons_sample,
                },
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api.route("/<int:dataset_id>", methods=["DELETE"])
def delete_dataset(dataset_id: int):
    """
    Delete a dataset.

    Query params:
      - delete_rows=true to delete imported weather_data rows too.
    """
    try:
        ds = Dataset.query.get(dataset_id)
        if not ds:
            return jsonify({"success": False, "message": "Dataset not found"}), 404

        delete_rows = (request.args.get("delete_rows") or "").lower() in {"1", "true", "yes"}
        deleted_rows = 0
        if delete_rows:
            deleted_rows = WeatherData.query.filter_by(dataset_id=ds.id).delete(synchronize_session=False)

        db.session.delete(ds)
        db.session.commit()
        return jsonify({"success": True, "message": "Dataset deleted", "deleted_rows": deleted_rows})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

