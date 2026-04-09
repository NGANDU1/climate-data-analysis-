from flask import Blueprint, Response, jsonify, request, stream_with_context
from models import db
from models.alert import Alert
from models.region import Region
from models.user import User
from services.notification_service import NotificationService
from services.auth_context import get_auth_payload
from datetime import datetime, date as dt_date
import json
import time

api = Blueprint('alerts', __name__)


def _require_admin():
    auth = get_auth_payload(request)
    if not auth:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    if auth.get("role") != "admin":
        return jsonify({"success": False, "message": "Forbidden"}), 403
    return None

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
        medium_count = Alert.query.filter(Alert.risk_level == 'medium').count()
        low_count = Alert.query.filter(Alert.risk_level == 'low').count()
        manual_count = Alert.query.filter(Alert.is_manual.is_(True)).count()
        pending_count = Alert.query.filter(Alert.is_sent.is_(False)).count()
        
        return jsonify({
            'success': True,
            'data': [alert.to_dict() for alert in alerts],
            'count': len(alerts),
            'statistics': {
                'total_alerts': total_alerts,
                'critical_count': critical_count,
                'high_count': high_count,
                'medium_count': medium_count,
                'low_count': low_count,
                'manual_count': manual_count,
                'pending_count': pending_count
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/stream', methods=['GET'])
def stream_alerts():
    """
    Server-Sent Events stream for newly created alerts.

    Query params:
      - since_id: only stream alerts with id > since_id (default 0)
    """
    try:
        since_id = request.args.get('since_id', 0, type=int) or 0
    except Exception:
        since_id = 0

    def gen():
        last_id = since_id
        last_ping = time.time()
        while True:
            try:
                new_alerts = (
                    Alert.query.filter(Alert.id > last_id)
                    .order_by(Alert.id.asc())
                    .limit(100)
                    .all()
                )
                for a in new_alerts:
                    payload = json.dumps(a.to_dict(), separators=(',', ':'))
                    yield f"data: {payload}\n\n"
                    last_id = max(last_id, int(a.id or 0))

                # Keep-alive comment every ~15s so proxies don't close the connection.
                now = time.time()
                if now - last_ping >= 15:
                    yield ": keep-alive\n\n"
                    last_ping = now

            except Exception:
                # Best-effort stream; if DB is temporarily unavailable, keep the connection open.
                pass

            time.sleep(2)

    return Response(stream_with_context(gen()), mimetype='text/event-stream')

@api.route('/send', methods=['POST'])
def send_alert():
    """Send manual alert"""
    try:
        data = request.get_json(silent=True) or {}
        
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

        # Optional: accept region_name as a convenience for UIs that don't know region_id.
        region_id = data.get('region_id')
        region_name = (data.get('region_name') or '').strip()
        if (not region_id) and region_name:
            region = Region.query.filter(db.func.lower(Region.name) == region_name.lower()).first()
            if not region:
                return jsonify({'success': False, 'message': f"Unknown region: {region_name}"}), 400
            region_id = region.id

        # Optional: prediction_date (YYYY-MM-DD) to help compose the message.
        prediction_date_raw = (data.get('prediction_date') or '').strip()
        prediction_date: dt_date | None = None
        if prediction_date_raw:
            try:
                prediction_date = dt_date.fromisoformat(prediction_date_raw)
            except Exception:
                return jsonify({'success': False, 'message': 'prediction_date must be YYYY-MM-DD'}), 400

        message = str(data.get('message') or '').strip()
        risk_level = str(data.get('risk_level') or '').strip()
        disaster_type = str(data.get('disaster_type') or 'general').strip()

        # Optional: force delivery channels for this send (still respects user contact availability).
        # Accepted shapes: ["email","sms"], "email", "sms", "both"
        method_filter = None
        channels_raw = data.get('channels')
        if isinstance(channels_raw, list):
            method_filter = {str(x).strip().lower() for x in channels_raw if str(x).strip()}
        elif isinstance(channels_raw, str):
            raw = channels_raw.strip().lower()
            if raw in {"email", "sms"}:
                method_filter = {raw}
            elif raw == "both":
                method_filter = {"email", "sms"}

        if method_filter is not None:
            method_filter = {m for m in method_filter if m in {"email", "sms"}}
            if not method_filter:
                method_filter = None

        if prediction_date:
            # If admin didn't include the date explicitly, prepend a clear headline.
            if prediction_date.isoformat() not in message:
                headline_region = region_name or (Region.query.get(region_id).name if region_id else 'National')
                message = f"{headline_region}: {risk_level.title()} level predicted for {prediction_date.isoformat()}. {message}"
        
        # Create alert
        alert = Alert(
            message=message,
            risk_level=risk_level,
            disaster_type=disaster_type,
            region_id=region_id,
            is_manual=True
        )
        
        db.session.add(alert)
        db.session.commit()
        
        # Send notifications
        notification_result = NotificationService.send_alert(alert, method_filter=method_filter)
        
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
        err = _require_admin()
        if err:
            return err

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
