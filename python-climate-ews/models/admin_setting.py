from __future__ import annotations

import json
from datetime import datetime

from models import db


class AdminSetting(db.Model):
    __tablename__ = "admin_setting"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admin.id"), unique=True, nullable=False, index=True)
    settings_json = db.Column(db.Text, nullable=False, default="{}")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def get_settings(self) -> dict:
        try:
            val = json.loads(self.settings_json or "{}")
            return val if isinstance(val, dict) else {}
        except Exception:
            return {}

    def set_settings(self, settings: dict) -> None:
        self.settings_json = json.dumps(settings or {}, ensure_ascii=False, separators=(",", ":"))

    def to_dict(self) -> dict:
        return {
            "admin_id": self.admin_id,
            "settings": self.get_settings(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

