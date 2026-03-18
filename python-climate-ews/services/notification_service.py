class NotificationService:
    """Handle SMS and email notifications"""
    
    @staticmethod
    def send_alert(alert):
        """
        Send alert notifications to all subscribed users
        
        Args:
            alert: Alert object
            
        Returns:
            dict with notification results
        """
        from models.user import User
        
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
        # In production, integrate with actual SMS/Email services
        # For now, simulate successful delivery
        
        message = f"ALERT [{alert.risk_level.upper()}]: {alert.message}"
        
        if method == 'sms':
            # Simulate SMS sending
            if user.phone:
                print(f"[SMS] To: {user.phone} - {message}")
                return True
            return False
            
        elif method == 'email':
            # Simulate email sending
            if user.email:
                subject = f"Climate Alert: {alert.disaster_type}"
                body = f"""
Dear {user.name},

{message}

Region: {alert.region_name if alert.region else 'All Regions'}
Time: {alert.created_at}

Stay safe!
Climate Early Warning System
                """
                print(f"[EMAIL] To: {user.email} - Subject: {subject}")
                return True
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
