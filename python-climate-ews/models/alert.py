from models import db
from datetime import datetime

class Alert(db.Model):
    __tablename__ = 'alert'
    
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    risk_level = db.Column(db.String(20), nullable=False)
    disaster_type = db.Column(db.String(50), default='general')
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'))
    is_manual = db.Column(db.Boolean, default=False)
    is_sent = db.Column(db.Boolean, default=False)
    sent_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    region = db.relationship('Region', backref=db.backref('alerts', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'message': self.message,
            'risk_level': self.risk_level,
            'disaster_type': self.disaster_type,
            'region_id': self.region_id,
            'region_name': self.region.name if self.region else None,
            'is_manual': self.is_manual,
            'is_sent': self.is_sent,
            'sent_count': self.sent_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Alert {self.risk_level} - {self.disaster_type}>'
