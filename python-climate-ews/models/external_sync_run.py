from models import db
from datetime import datetime


class ExternalSyncRun(db.Model):
    __tablename__ = "external_sync_run"

    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(100), nullable=False)  # e.g. nasa_power
    status = db.Column(db.String(20), nullable=False, default="queued")  # queued, running, success, failed

    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)

    dataset_id = db.Column(db.Integer)
    rows_received = db.Column(db.Integer, default=0)
    rows_imported = db.Column(db.Integer, default=0)
    rows_skipped = db.Column(db.Integer, default=0)

    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "source": self.source,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "dataset_id": self.dataset_id,
            "rows_received": self.rows_received,
            "rows_imported": self.rows_imported,
            "rows_skipped": self.rows_skipped,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

