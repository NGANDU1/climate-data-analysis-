from models import db
from datetime import datetime

class WeatherData(db.Model):
    __tablename__ = 'weather_data'
    
    id = db.Column(db.Integer, primary_key=True)
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'))
    dataset_id = db.Column(db.Integer)  # lightweight reference to Dataset.id (no FK for easy SQLite alters)
    source = db.Column(db.String(50), default="system")  # system, upload, api
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    rainfall = db.Column(db.Float)
    wind_speed = db.Column(db.Float)
    pressure = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    region = db.relationship('Region', backref=db.backref('weather_data', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'region_id': self.region_id,
            'region_name': self.region.name if self.region else None,
            'dataset_id': self.dataset_id,
            'source': self.source,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'rainfall': self.rainfall,
            'wind_speed': self.wind_speed,
            'pressure': self.pressure,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    def __repr__(self):
        return f'<WeatherData Region:{self.region_id} Temp:{self.temperature}>'
