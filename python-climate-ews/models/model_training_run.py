from models import db
from datetime import datetime


class ModelTrainingRun(db.Model):
    __tablename__ = "model_training_run"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False, default="queued")  # queued, running, success, failed

    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)

    # Optional training filters (so training can use newly imported datasets)
    dataset_id = db.Column(db.Integer)
    sources = db.Column(db.String(255))  # comma-separated sources, e.g. "nasa_power,upload"
    min_samples = db.Column(db.Integer)

    metrics_json = db.Column(db.Text)  # JSON string
    logs_text = db.Column(db.Text)
    error_message = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "dataset_id": self.dataset_id,
            "sources": self.sources,
            "min_samples": self.min_samples,
            "metrics_json": self.metrics_json,
            "logs_text": self.logs_text,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
