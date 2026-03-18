from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import text

db = SQLAlchemy()

def _ensure_sqlite_columns(table_name: str, columns: dict[str, str]) -> None:
    """
    Minimal schema "migration" helper for SQLite.

    SQLAlchemy's `create_all()` will not add missing columns to existing tables.
    This adds required columns when running on SQLite without Alembic.
    """
    if db.engine.dialect.name != "sqlite":
        return

    existing = set()
    for row in db.session.execute(text(f"PRAGMA table_info('{table_name}')")).fetchall():
        existing.add(row[1])

    changed = False
    for col, col_type in columns.items():
        if col in existing:
            continue
        db.session.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col}" {col_type}'))
        changed = True

    if changed:
        db.session.commit()

def init_db(app):
    """Initialize database with app context"""
    db.init_app(app)

    with app.app_context():
        from . import admin as _admin
        from . import alert as _alert
        from . import dataset as _dataset
        from . import external_sync_run as _external_sync_run
        from . import forecast_prediction as _forecast_prediction
        from . import model_training_run as _model_training_run
        from . import region as _region
        from . import user as _user
        from . import weather_data as _weather_data
        db.create_all()

        _ensure_sqlite_columns(
            "user",
            {
                "password_hash": "VARCHAR(255)",
                "reset_token": "VARCHAR(255)",
                "reset_token_expires_at": "DATETIME",
            },
        )

        _ensure_sqlite_columns(
            "weather_data",
            {
                "dataset_id": "INTEGER",
                "source": "VARCHAR(50)",
            },
        )

        _ensure_sqlite_columns(
            "model_training_run",
            {
                "dataset_id": "INTEGER",
                "sources": "VARCHAR(255)",
                "min_samples": "INTEGER",
            },
        )

    return db
