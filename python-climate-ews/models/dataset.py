from models import db
from datetime import datetime


class Dataset(db.Model):
    __tablename__ = "dataset"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    source_type = db.Column(db.String(50), nullable=False)  # csv, excel, api_json
    original_filename = db.Column(db.String(255))
    notes = db.Column(db.Text)

    rows_received = db.Column(db.Integer, default=0)
    rows_imported = db.Column(db.Integer, default=0)
    rows_skipped = db.Column(db.Integer, default=0)

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "source_type": self.source_type,
            "original_filename": self.original_filename,
            "notes": self.notes,
            "rows_received": self.rows_received,
            "rows_imported": self.rows_imported,
            "rows_skipped": self.rows_skipped,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }

