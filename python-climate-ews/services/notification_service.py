from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

import requests


class NotificationService:
    """Handle SMS and email notifications"""

    @staticmethod
    def _bool_env(name: str, default: bool) -> bool:
        raw = os.environ.get(name)
        if raw is None:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "y", "on"}

    @staticmethod
    def _sms_configured() -> bool:
        return bool(
            (os.environ.get("TWILIO_ACCOUNT_SID") or "").strip()
            and (os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
            and (os.environ.get("TWILIO_FROM_NUMBER") or "").strip()
        )

    @staticmethod
    def _email_configured() -> bool:
        return bool((os.environ.get("SMTP_HOST") or "").strip() and (os.environ.get("SMTP_FROM") or "").strip())

    @staticmethod
    def _send_sms_twilio(to_number: str, body: str) -> bool:
        sid = (os.environ.get("TWILIO_ACCOUNT_SID") or "").strip()
        token = (os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
        from_number = (os.environ.get("TWILIO_FROM_NUMBER") or "").strip()
        if not (sid and token and from_number):
            return False

        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        res = requests.post(
            url,
            data={"From": from_number, "To": to_number, "Body": body},
            auth=(sid, token),
            timeout=20,
        )
        return 200 <= res.status_code < 300

    @staticmethod
    def _send_email_smtp(to_email: str, subject: str, body: str) -> bool:
        host = (os.environ.get("SMTP_HOST") or "").strip()
        port_raw = (os.environ.get("SMTP_PORT") or "").strip()
        username = (os.environ.get("SMTP_USER") or "").strip()
        password = (os.environ.get("SMTP_PASS") or "").strip()
        sender = (os.environ.get("SMTP_FROM") or "").strip()

        if not host or not sender:
            return False

        try:
            port = int(port_raw) if port_raw else 587
        except Exception:
            port = 587

        use_ssl = NotificationService._bool_env("SMTP_SSL", False)
        use_tls = NotificationService._bool_env("SMTP_TLS", True)

        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=20) as smtp:
                if username and password:
                    smtp.login(username, password)
                smtp.send_message(msg)
            return True

        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(msg)
        return True
    
    @staticmethod
    def send_alert(alert, method_filter: set[str] | None = None):
        """
        Send alert notifications to all subscribed users
        
        Args:
            alert: Alert object
            method_filter: optional set of {"sms","email"} to force channels
            
        Returns:
            dict with notification results
        """
        from models.user import User

        if method_filter is not None:
            method_filter = {str(m).strip().lower() for m in method_filter if str(m).strip()}
            method_filter = {m for m in method_filter if m in {"sms", "email"}}
            if not method_filter:
                method_filter = None
        
        # Get all active users
        users = User.query.filter_by(is_active=True).all()
        
        if not users:
            return {
                'success': False,
                'message': 'No active subscribers found',
                'sent_count': 0
            }
        
        sent_count = 0
        failed_count = 0
        sms_sent = 0
        email_sent = 0
        
        for user in users:
            # Determine notification method
            notify_methods = []
            if user.subscription_type in ['sms', 'both']:
                notify_methods.append('sms')
            if user.subscription_type in ['email', 'both']:
                notify_methods.append('email')

            if method_filter is not None:
                notify_methods = [m for m in notify_methods if m in method_filter]
            
            # Send notifications
            for method in notify_methods:
                success = NotificationService._send_notification(
                    user=user,
                    method=method,
                    alert=alert
                )
                
                if success:
                    sent_count += 1
                    if method == 'sms':
                        sms_sent += 1
                    else:
                        email_sent += 1
                else:
                    failed_count += 1
        
        return {
            'success': sent_count > 0,
            'message': f'Sent {sent_count} notifications',
            'sent_count': sent_count,
            'failed_count': failed_count,
            'sms_sent': sms_sent,
            'email_sent': email_sent,
            'total_recipients': len(users)
        }
    
    @staticmethod
    def _send_notification(user, method, alert):
        """
        Send individual notification (simulated)
        
        Args:
            user: User object
            method: 'sms' or 'email'
            alert: Alert object
            
        Returns:
            bool indicating success
        """
        simulate = NotificationService._bool_env("NOTIFICATIONS_SIMULATE", True)
        
        message = f"ALERT [{alert.risk_level.upper()}]: {alert.message}"
        
        if method == 'sms':
            if user.phone:
                if NotificationService._sms_configured():
                    return NotificationService._send_sms_twilio(user.phone, message)
                if simulate:
                    print(f"[SMS:SIMULATED] To: {user.phone} - {message}")
                    return True
                return False
            return False
            
        elif method == 'email':
            if user.email:
                subject = f"Climate Alert: {alert.disaster_type}"
                body = f"""
Dear {user.name},

{message}

Region: {alert.region.name if getattr(alert, 'region', None) else 'All Regions'}
Time: {alert.created_at}

Stay safe!
Climate Early Warning System
                """
                if NotificationService._email_configured():
                    return NotificationService._send_email_smtp(user.email, subject, body)
                if simulate:
                    print(f"[EMAIL:SIMULATED] To: {user.email} - Subject: {subject}")
                    return True
                return False
            return False
        
        return False
    
    @staticmethod
    def send_test_notification(user, test_message="Test notification"):
        """
        Send test notification to verify system
        
        Args:
            user: User object
            test_message: Test message string
            
        Returns:
            dict with test results
        """
        results = {
            'sms': False,
            'email': False
        }
        
        if user.subscription_type in ['sms', 'both'] and user.phone:
            results['sms'] = NotificationService._send_notification(
                user=user,
                method='sms',
                alert=type('TestAlert', (), {
                    'risk_level': 'test',
                    'message': test_message,
                    'disaster_type': 'test',
                    'region': None,
                    'created_at': None
                })()
            )
        
        if user.subscription_type in ['email', 'both'] and user.email:
            results['email'] = NotificationService._send_notification(
                user=user,
                method='email',
                alert=type('TestAlert', (), {
                    'risk_level': 'test',
                    'message': test_message,
                    'disaster_type': 'test',
                    'region': None,
                    'created_at': None
                })()
            )
        
        return {
            'success': any(results.values()),
            'results': results,
            'user': user.to_dict()
        }
    
    @staticmethod
    def get_notification_stats():
        """Get notification statistics"""
        from models.user import User
        from models.alert import Alert
        
        total_users = User.query.filter_by(is_active=True).count()
        total_alerts = Alert.query.filter_by(is_sent=True).count()
        total_sent = db.session.query(
            db.func.sum(Alert.sent_count)
        ).filter(Alert.is_sent == True).scalar() or 0
        
        return {
            'active_subscribers': total_users,
            'alerts_sent': total_alerts,
            'total_notifications_sent': int(total_sent) if total_sent else 0
        }

# Import db for stats function
from models import db
