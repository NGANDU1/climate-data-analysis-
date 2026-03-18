from models import db
from datetime import datetime, date


class ForecastPrediction(db.Model):
    __tablename__ = "forecast_prediction"

    id = db.Column(db.Integer, primary_key=True)
    region_id = db.Column(db.Integer, db.ForeignKey("region.id"), nullable=False)
    variable = db.Column(db.String(50), nullable=False)  # rainfall, temperature, humidity
    method = db.Column(db.String(50), nullable=False)  # naive, arima
    horizon_days = db.Column(db.Integer, nullable=False, default=7)

    forecast_date = db.Column(db.Date, nullable=False)
    forecast_value = db.Column(db.Float, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    region = db.relationship("Region", backref=db.backref("forecasts", lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "region_id": self.region_id,
            "region_name": self.region.name if self.region else None,
            "variable": self.variable,
            "method": self.method,
            "horizon_days": self.horizon_days,
            "forecast_date": self.forecast_date.isoformat() if isinstance(self.forecast_date, date) else str(self.forecast_date),
            "forecast_value": self.forecast_value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

