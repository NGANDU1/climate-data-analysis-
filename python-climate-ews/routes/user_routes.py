from flask import Blueprint, jsonify, request
from models import db
from models.user import User
from services.notification_service import NotificationService
from datetime import datetime, timedelta

api = Blueprint('users', __name__)

@api.route('', methods=['GET'])
def get_all_users():
    """Get all subscribed users"""
    try:
        limit = request.args.get('limit', None, type=int)

        query = User.query.order_by(User.created_at.desc())
        if limit is not None and limit > 0:
            query = query.limit(limit)

        users = query.all()

        total_users = User.query.count()
        active_users = User.query.filter(User.is_active.is_(True)).count()
        new_users_week = User.query.filter(
            User.created_at >= (datetime.utcnow() - timedelta(days=7))
        ).count()
        
        return jsonify({
            'success': True,
            'data': [user.to_dict() for user in users],
            'count': len(users),
            'statistics': {
                'total_users': total_users,
                'active_users': active_users,
                'new_users_week': new_users_week
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/subscribe', methods=['POST'])
def subscribe_user():
    """Subscribe a user to alerts"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({
                'success': False,
                'message': 'Name is required'
            }), 400
        
        if not data.get('email') and not data.get('phone'):
            return jsonify({
                'success': False,
                'message': 'Email or phone is required'
            }), 400
        
        # Check if user already exists
        existing_user = None
        if data.get('email'):
            existing_user = User.query.filter_by(email=data['email']).first()
        if not existing_user and data.get('phone'):
            existing_user = User.query.filter_by(phone=data['phone']).first()
        
        if existing_user:
            # Update existing user
            existing_user.name = data.get('name', existing_user.name)
            existing_user.phone = data.get('phone', existing_user.phone)
            existing_user.email = data.get('email', existing_user.email)
            existing_user.location = data.get('location', existing_user.location)
            existing_user.subscription_type = data.get('subscription_type', existing_user.subscription_type)
            existing_user.is_active = True
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Subscription updated successfully',
                'user': existing_user.to_dict()
            })
        
        # Create new user
        user = User(
            name=data['name'],
            phone=data.get('phone'),
            email=data.get('email'),
            location=data.get('location'),
            subscription_type=data.get('subscription_type', 'email')
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Subscription successful',
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/<int:user_id>/unsubscribe', methods=['POST'])
def unsubscribe_user(user_id):
    """Unsubscribe a user"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        user.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User unsubscribed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/stats', methods=['GET'])
def get_user_stats():
    """Get user subscription statistics"""
    try:
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        sms_subscribers = User.query.filter_by(subscription_type='sms').count()
        email_subscribers = User.query.filter_by(subscription_type='email').count()
        both_subscribers = User.query.filter_by(subscription_type='both').count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'active_users': active_users,
                'inactive_users': total_users - active_users,
                'sms_subscribers': sms_subscribers,
                'email_subscribers': email_subscribers,
                'both_subscribers': both_subscribers
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
