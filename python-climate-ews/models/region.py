from models import db

class Region(db.Model):
    __tablename__ = 'region'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    risk_level = db.Column(db.String(20), default='low')  # low, medium, high, critical
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'risk_level': self.risk_level
        }
    
    def __repr__(self):
        return f'<Region {self.name}>'
