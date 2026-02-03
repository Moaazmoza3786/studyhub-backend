"""
Subscription API Routes for Study Hub Platform
Handles premium subscription management with mock payment processing
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from functools import wraps
import jwt
import os
import uuid

from models import db, User, Subscription

subscription_bp = Blueprint('subscription', __name__, url_prefix='/api/subscription')


def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            secret_key = os.environ.get('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
            data = jwt.decode(token, secret_key, algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated


# Pricing configuration
PRICING = {
    'monthly': {
        'amount': 9.99,
        'duration_days': 30,
        'features': ['premium_rooms', 'ad_free', 'priority_support', 'certificates']
    },
    'annual': {
        'amount': 79.99,
        'duration_days': 365,
        'features': ['premium_rooms', 'ad_free', 'priority_support', 'certificates', 'exclusive_content']
    }
}


# ==================== API ENDPOINTS ====================

@subscription_bp.route('/status', methods=['GET'])
@token_required
def get_subscription_status(current_user):
    """Get current user's subscription status"""
    is_premium = current_user.subscription_tier in ['monthly', 'annual']
    is_expired = False
    
    if is_premium and current_user.subscription_expires_at:
        is_expired = datetime.utcnow() > current_user.subscription_expires_at
        if is_expired:
            # Auto-downgrade expired subscriptions
            current_user.subscription_tier = 'free'
            db.session.commit()
            is_premium = False
    
    # Get active subscription history
    active_subscription = Subscription.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).order_by(Subscription.created_at.desc()).first()
    
    return jsonify({
        'success': True,
        'tier': current_user.subscription_tier,
        'is_premium': is_premium,
        'expires_at': current_user.subscription_expires_at.isoformat() if current_user.subscription_expires_at else None,
        'subscription': active_subscription.to_dict() if active_subscription else None,
        'available_plans': PRICING
    })


@subscription_bp.route('/subscribe', methods=['POST'])
@token_required
def subscribe(current_user):
    """
    Subscribe to premium plan (mock payment)
    Expects: { tier: 'monthly' | 'annual', card_last_four: '1234' }
    """
    data = request.get_json()
    tier = data.get('tier')
    card_last_four = data.get('card_last_four', '****')
    
    if tier not in PRICING:
        return jsonify({'error': 'Invalid subscription tier'}), 400
    
    plan = PRICING[tier]
    
    # Check if already subscribed
    if current_user.subscription_tier != 'free':
        if current_user.subscription_expires_at and datetime.utcnow() < current_user.subscription_expires_at:
            return jsonify({
                'error': 'Already have an active subscription',
                'current_tier': current_user.subscription_tier,
                'expires_at': current_user.subscription_expires_at.isoformat()
            }), 400
    
    # Create mock transaction
    transaction_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
    
    # Calculate expiration
    expiration_date = datetime.utcnow() + timedelta(days=plan['duration_days'])
    
    # Update user subscription
    current_user.subscription_tier = tier
    current_user.subscription_expires_at = expiration_date
    
    # Create subscription record
    subscription = Subscription(
        user_id=current_user.id,
        tier=tier,
        amount=plan['amount'],
        currency='USD',
        started_at=datetime.utcnow(),
        expires_at=expiration_date,
        payment_method=f"mock_card_****{card_last_four}",
        transaction_id=transaction_id,
        is_active=True
    )
    
    # Deactivate any previous subscriptions
    Subscription.query.filter_by(user_id=current_user.id, is_active=True)\
                      .update({'is_active': False})
    
    db.session.add(subscription)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Successfully subscribed to {tier} plan!',
        'transaction_id': transaction_id,
        'tier': tier,
        'amount': plan['amount'],
        'expires_at': expiration_date.isoformat(),
        'features': plan['features']
    })


@subscription_bp.route('/cancel', methods=['POST'])
@token_required
def cancel_subscription(current_user):
    """Cancel the current subscription (remains active until expiration)"""
    if current_user.subscription_tier == 'free':
        return jsonify({'error': 'No active subscription to cancel'}), 400
    
    # Find active subscription
    subscription = Subscription.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if subscription:
        subscription.cancelled_at = datetime.utcnow()
        subscription.is_active = False
    
    # Note: We don't immediately downgrade - they keep access until expiration
    # The status endpoint will handle expiration checks
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Subscription cancelled. You will retain access until the current period ends.',
        'access_until': current_user.subscription_expires_at.isoformat() if current_user.subscription_expires_at else None
    })


@subscription_bp.route('/history', methods=['GET'])
@token_required
def get_subscription_history(current_user):
    """Get user's subscription history"""
    subscriptions = Subscription.query.filter_by(user_id=current_user.id)\
                                       .order_by(Subscription.created_at.desc())\
                                       .limit(10).all()
    
    return jsonify({
        'success': True,
        'subscriptions': [s.to_dict() for s in subscriptions]
    })


@subscription_bp.route('/check-premium', methods=['GET'])
@token_required
def check_premium_access(current_user):
    """Quick check if user has premium access (for content gating)"""
    is_premium = current_user.subscription_tier in ['monthly', 'annual']
    
    if is_premium and current_user.subscription_expires_at:
        if datetime.utcnow() > current_user.subscription_expires_at:
            is_premium = False
    
    return jsonify({
        'has_premium': is_premium,
        'tier': current_user.subscription_tier if is_premium else 'free'
    })


# ==================== ADMIN ENDPOINTS ====================

@subscription_bp.route('/grant', methods=['POST'])
def grant_subscription():
    """Grant subscription to a user (admin only)"""
    admin_key = request.headers.get('X-Admin-Key')
    expected_key = os.environ.get('ADMIN_CRON_KEY', 'dev-cron-key')
    
    if admin_key != expected_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    user_id = data.get('user_id')
    tier = data.get('tier', 'monthly')
    days = data.get('days', 30)
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Grant subscription
    expiration = datetime.utcnow() + timedelta(days=days)
    user.subscription_tier = tier
    user.subscription_expires_at = expiration
    
    # Create subscription record
    subscription = Subscription(
        user_id=user.id,
        tier=tier,
        amount=0.0,  # Free grant
        currency='USD',
        started_at=datetime.utcnow(),
        expires_at=expiration,
        payment_method='admin_grant',
        transaction_id=f"GRANT_{uuid.uuid4().hex[:8].upper()}",
        is_active=True
    )
    
    db.session.add(subscription)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Granted {tier} subscription to {user.username} for {days} days',
        'expires_at': expiration.isoformat()
    })
