from flask import Blueprint, jsonify, request
from models import db
from models.alert import Alert
from models.region import Region
from models.user import User
from services.notification_service import NotificationService
from datetime import datetime

api = Blueprint('alerts', __name__)

@api.route('', methods=['GET'])
def get_all_alerts():
    """Get all alerts"""
    try:
        limit = request.args.get('limit', None, type=int)
        risk_level = request.args.get('risk_level', None, type=str)

        query = Alert.query
        if risk_level:
            query = query.filter(Alert.risk_level == risk_level)

        query = query.order_by(Alert.created_at.desc())
        if limit is not None and limit > 0:
            query = query.limit(limit)

        alerts = query.all()

        # Aggregate stats (unfiltered) for dashboard counters.
        total_alerts = Alert.query.count()
        critical_count = Alert.query.filter(Alert.risk_level == 'critical').count()
        high_count = Alert.query.filter(Alert.risk_level == 'high').count()
        manual_count = Alert.query.filter(Alert.is_manual.is_(True)).count()
        
        return jsonify({
            'success': True,
            'data': [alert.to_dict() for alert in alerts],
            'count': len(alerts),
            'statistics': {
                'total_alerts': total_alerts,
                'critical_count': critical_count,
                'high_count': high_count,
                'manual_count': manual_count
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/send', methods=['POST'])
def send_alert():
    """Send manual alert"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('message'):
            return jsonify({
                'success': False,
                'message': 'Alert message is required'
            }), 400
        
        if not data.get('risk_level'):
            return jsonify({
                'success': False,
                'message': 'Risk level is required'
            }), 400
        
        # Create alert
        alert = Alert(
            message=data['message'],
            risk_level=data['risk_level'],
            disaster_type=data.get('disaster_type', 'general'),
            region_id=data.get('region_id'),
            is_manual=True
        )
        
        db.session.add(alert)
        db.session.commit()
        
        # Send notifications
        notification_result = NotificationService.send_alert(alert)
        
        # Update sent status
        alert.is_sent = notification_result['success']
        alert.sent_count = notification_result.get('sent_count', 0)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Alert sent successfully',
            'alert': alert.to_dict(),
            'notification_result': notification_result
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/<int:alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    """Delete an alert"""
    try:
        alert = Alert.query.get(alert_id)
        
        if not alert:
            return jsonify({
                'success': False,
                'message': 'Alert not found'
            }), 404
        
        db.session.delete(alert)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Alert deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/auto-generate', methods=['POST'])
def auto_generate_alerts():
    """Auto-generate alerts based on risk predictions"""
    try:
        from services.risk_calculator import RiskCalculator
        
        regions = Region.query.all()
        generated_alerts = []
        
        for region in regions:
            prediction = RiskCalculator.predict_risk_for_region(region)
            
            if prediction['risk_level'] in ['high', 'critical']:
                alert = Alert(
                    message=f"Automatic alert: {prediction['disaster_type']} risk detected in {region.name}",
                    risk_level=prediction['risk_level'],
                    disaster_type=prediction['disaster_type'],
                    region_id=region.id,
                    is_manual=False
                )
                
                db.session.add(alert)
                generated_alerts.append(alert.to_dict())
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Generated {len(generated_alerts)} alerts',
            'alerts': generated_alerts
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
