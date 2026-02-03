"""
Authentication Routes for Study Hub Platform
JWT-based authentication with login, register, and profile management
"""

from flask import Blueprint, jsonify, request
from functools import wraps
from datetime import datetime, timedelta
import jwt
import os
import re
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from models import db, User

# Create Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable is required! Check your .env file.")
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days


# ==================== JWT HELPERS ====================

def generate_token(user_id):
    """Generate a JWT token for a user"""
    payload = {
        'user_id': user_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return {'error': 'Token expired'}
    except jwt.InvalidTokenError:
        return {'error': 'Invalid token'}


def get_token_from_request():
    """Extract JWT token from request headers"""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return None


def get_current_user():
    """Get the current authenticated user from the request"""
    token = get_token_from_request()
    if not token:
        return None
    
    payload = decode_token(token)
    if 'error' in payload:
        return None
    
    return User.query.get(payload.get('user_id'))


# ==================== DECORATORS ====================

def require_auth(f):
    """Decorator to require authentication for a route"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'message': 'Please login to access this resource'
            }), 401
        
        payload = decode_token(token)
        
        if 'error' in payload:
            return jsonify({
                'success': False,
                'error': payload['error'],
                'message': 'Please login again'
            }), 401
        
        # Get user
        user = User.query.get(payload.get('user_id'))
        if not user or not user.is_active:
            return jsonify({
                'success': False,
                'error': 'User not found or inactive'
            }), 401
        
        # Add user to request context
        request.current_user = user
        
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Decorator to require admin role"""
    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if request.current_user.role != 'admin':
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403
        return f(*args, **kwargs)
    return decorated


# ==================== VALIDATION HELPERS ====================

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, 'Password must be at least 8 characters'
    if not re.search(r'[A-Za-z]', password):
        return False, 'Password must contain at least one letter'
    if not re.search(r'[0-9]', password):
        return False, 'Password must contain at least one number'
    return True, None


def validate_username(username):
    """Validate username format"""
    if len(username) < 3:
        return False, 'Username must be at least 3 characters'
    if len(username) > 30:
        return False, 'Username must be less than 30 characters'
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, 'Username can only contain letters, numbers, underscores, and hyphens'
    return True, None


# ==================== AUTH ROUTES ====================

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    POST /api/auth/register
    Register a new user
    
    Request body:
    {
        "username": "hacker123",
        "email": "user@example.com",
        "password": "SecurePass123",
        "first_name": "محمد",
        "last_name": "أحمد"
    }
    """
    data = request.json or {}
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    
    # Validate required fields
    if not all([username, email, password]):
        return jsonify({
            'success': False,
            'error': 'Missing required fields',
            'message': 'Username, email, and password are required'
        }), 400
    
    # Validate username
    valid, error = validate_username(username)
    if not valid:
        return jsonify({'success': False, 'error': error}), 400
    
    # Validate email
    if not validate_email(email):
        return jsonify({
            'success': False,
            'error': 'Invalid email format'
        }), 400
    
    # Validate password
    valid, error = validate_password(password)
    if not valid:
        return jsonify({'success': False, 'error': error}), 400
    
    # Check if email exists
    if User.query.filter_by(email=email).first():
        return jsonify({
            'success': False,
            'error': 'Email already registered',
            'message': 'This email is already in use. Please login or use a different email.'
        }), 409
    
    # Check if username exists
    if User.query.filter_by(username=username).first():
        return jsonify({
            'success': False,
            'error': 'Username already taken',
            'message': 'This username is already in use. Please choose a different one.'
        }), 409
    
    # Create user
    user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role='student',
        is_active=True,
        is_verified=False  # Would need email verification in production
    )
    user.set_password(password)
    
    try:
        db.session.add(user)
        db.session.commit()
        
        # Generate token
        token = generate_token(user.id)
        
        return jsonify({
            'success': True,
            'message': 'Registration successful! Welcome to Study Hub.',
            'token': token,
            'user': user.to_dict(include_email=True)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Registration failed',
            'message': str(e)
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    POST /api/auth/login
    Login with email and password
    
    Request body:
    {
        "email": "user@example.com",
        "password": "SecurePass123"
    }
    """
    data = request.json or {}
    
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({
            'success': False,
            'error': 'Email and password are required'
        }), 400
    
    # Find user
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        return jsonify({
            'success': False,
            'error': 'Invalid credentials',
            'message': 'Incorrect email or password'
        }), 401
    
    if not user.is_active:
        return jsonify({
            'success': False,
            'error': 'Account disabled',
            'message': 'Your account has been disabled. Please contact support.'
        }), 403
    
    # Update last active
    user.last_active_date = datetime.utcnow().date()
    
    # Update streak
    today = datetime.utcnow().date()
    if user.last_active_date:
        days_diff = (today - user.last_active_date).days
        if days_diff == 1:
            user.streak_days = (user.streak_days or 0) + 1
        elif days_diff > 1:
            user.streak_days = 1
    else:
        user.streak_days = 1
    
    db.session.commit()
    
    # Generate token
    token = generate_token(user.id)
    
    return jsonify({
        'success': True,
        'message': f'Welcome back, {user.username}!',
        'token': token,
        'user': user.to_dict(include_email=True)
    })


@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """
    POST /api/auth/logout
    Logout (invalidate token on client side)
    """
    # In a stateless JWT setup, logout is handled client-side
    # For added security, you'd maintain a token blacklist
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })


@auth_bp.route('/profile', methods=['GET'])
@require_auth
def get_profile():
    """
    GET /api/auth/profile
    Get current user's profile
    """
    return jsonify({
        'success': True,
        'user': request.current_user.to_dict(include_email=True)
    })


@auth_bp.route('/profile', methods=['PUT'])
@require_auth
def update_profile():
    """
    PUT /api/auth/profile
    Update current user's profile
    """
    data = request.json or {}
    user = request.current_user
    
    # Updateable fields
    if 'first_name' in data:
        user.first_name = data['first_name'].strip()
    
    if 'last_name' in data:
        user.last_name = data['last_name'].strip()
    
    if 'bio' in data:
        user.bio = data['bio'][:500] if data['bio'] else None
    
    if 'avatar_url' in data:
        user.avatar_url = data['avatar_url']
    
    # Username change (with validation)
    if 'username' in data and data['username'] != user.username:
        new_username = data['username'].strip()
        valid, error = validate_username(new_username)
        if not valid:
            return jsonify({'success': False, 'error': error}), 400
        
        if User.query.filter_by(username=new_username).first():
            return jsonify({
                'success': False,
                'error': 'Username already taken'
            }), 409
        
        user.username = new_username
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': user.to_dict(include_email=True)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/change-password', methods=['POST'])
@require_auth
def change_password():
    """
    POST /api/auth/change-password
    Change user's password
    """
    data = request.json or {}
    user = request.current_user
    
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    if not current_password or not new_password:
        return jsonify({
            'success': False,
            'error': 'Current and new passwords are required'
        }), 400
    
    # Verify current password
    if not user.check_password(current_password):
        return jsonify({
            'success': False,
            'error': 'Current password is incorrect'
        }), 401
    
    # Validate new password
    valid, error = validate_password(new_password)
    if not valid:
        return jsonify({'success': False, 'error': error}), 400
    
    # Update password
    user.set_password(new_password)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Password changed successfully'
    })


@auth_bp.route('/verify-token', methods=['GET'])
def verify_token():
    """
    GET /api/auth/verify-token
    Verify if the current token is valid
    """
    token = get_token_from_request()
    
    if not token:
        return jsonify({
            'valid': False,
            'error': 'No token provided'
        })
    
    payload = decode_token(token)
    
    if 'error' in payload:
        return jsonify({
            'valid': False,
            'error': payload['error']
        })
    
    user = User.query.get(payload.get('user_id'))
    
    if not user or not user.is_active:
        return jsonify({
            'valid': False,
            'error': 'User not found or inactive'
        })
    
    return jsonify({
        'valid': True,
        'user': user.to_dict()
    })


# ==================== ADMIN ROUTES ====================

@auth_bp.route('/users', methods=['GET'])
@require_admin
def list_users():
    """
    GET /api/auth/users
    List all users (admin only)
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    pagination = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'success': True,
        'users': [u.to_dict() for u in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@auth_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@require_admin
def toggle_user_active(user_id):
    """
    POST /api/auth/users/<id>/toggle-active
    Enable/disable a user account (admin only)
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    user.is_active = not user.is_active
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'User {"enabled" if user.is_active else "disabled"}',
        'user': user.to_dict()
    })


# ==================== PASSWORD RESET ROUTES ====================

# In-memory store for reset tokens (use Redis in production)
password_reset_tokens = {}

def send_reset_email(email, reset_token, reset_url):
    """Send password reset email using SMTP"""
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_email = os.environ.get('SMTP_EMAIL')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    from_name = os.environ.get('SMTP_FROM_NAME', 'Study Hub')
    
    if not smtp_email or not smtp_password:
        print("SMTP credentials not configured")
        return False
    
    # Create email
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Reset Your Password - Study Hub'
    msg['From'] = f'{from_name} <{smtp_email}>'
    msg['To'] = email
    
    # HTML email content
    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background: #0f0c29; color: #fff; padding: 40px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: #1a1a2e; padding: 40px; border-radius: 20px; border: 1px solid #22c55e33; }}
            h1 {{ color: #22c55e; margin-bottom: 20px; }}
            p {{ color: #ccc; line-height: 1.6; }}
            .btn {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #22c55e, #16a34a); color: #000; text-decoration: none; border-radius: 10px; font-weight: bold; margin: 20px 0; }}
            .code {{ background: #333; padding: 10px 20px; border-radius: 8px; font-family: monospace; font-size: 18px; letter-spacing: 3px; color: #22c55e; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 Password Reset</h1>
            <p>You requested to reset your password. Use the code below to reset it:</p>
            <p class="code">{reset_token}</p>
            <p>Or click the button below:</p>
            <a href="{reset_url}" class="btn">Reset Password</a>
            <p class="footer">This link expires in 1 hour. If you didn't request this, please ignore this email.</p>
        </div>
    </body>
    </html>
    '''
    
    text_content = f'''
    Password Reset - Study Hub
    
    You requested to reset your password.
    
    Your reset code: {reset_token}
    
    Or visit: {reset_url}
    
    This link expires in 1 hour.
    '''
    
    msg.attach(MIMEText(text_content, 'plain'))
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.send_message(msg)
        print(f"Reset email sent to {email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    POST /api/auth/forgot-password
    Request a password reset email
    """
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    
    if not email or not validate_email(email):
        return jsonify({
            'success': False,
            'error': 'Valid email is required'
        }), 400
    
    # Find user
    user = User.query.filter_by(email=email).first()
    
    # Always return success (security: don't reveal if email exists)
    if user:
        # Generate reset token (6 digits)
        reset_token = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # Store token with expiration
        password_reset_tokens[email] = {
            'token': reset_token,
            'user_id': user.id,
            'expires': datetime.utcnow() + timedelta(hours=1)
        }
        
        # Build reset URL
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:5500')
        reset_url = f"{frontend_url}#reset-password?email={email}&token={reset_token}"
        
        # Send email
        send_reset_email(email, reset_token, reset_url)
    
    return jsonify({
        'success': True,
        'message': 'If this email is registered, you will receive a password reset link.'
    })


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    POST /api/auth/reset-password
    Reset password using token
    """
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    token = data.get('token', '').strip()
    new_password = data.get('new_password', '')
    
    if not all([email, token, new_password]):
        return jsonify({
            'success': False,
            'error': 'Email, token, and new password are required'
        }), 400
    
    # Validate new password
    valid, error = validate_password(new_password)
    if not valid:
        return jsonify({'success': False, 'error': error}), 400
    
    # Check token
    stored = password_reset_tokens.get(email)
    
    if not stored:
        return jsonify({
            'success': False,
            'error': 'Invalid or expired reset token'
        }), 400
    
    if stored['token'] != token:
        return jsonify({
            'success': False,
            'error': 'Invalid reset token'
        }), 400
    
    if datetime.utcnow() > stored['expires']:
        del password_reset_tokens[email]
        return jsonify({
            'success': False,
            'error': 'Reset token has expired'
        }), 400
    
    # Update password
    user = User.query.get(stored['user_id'])
    if not user:
        return jsonify({
            'success': False,
            'error': 'User not found'
        }), 404
    
    user.set_password(new_password)
    db.session.commit()
    
    # Remove used token
    del password_reset_tokens[email]
    
    return jsonify({
        'success': True,
        'message': 'Password has been reset successfully. You can now login.'
    })


@auth_bp.route('/verify-reset-token', methods=['POST'])
def verify_reset_token():
    """
    POST /api/auth/verify-reset-token
    Verify if a reset token is valid
    """
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    token = data.get('token', '').strip()
    
    stored = password_reset_tokens.get(email)
    
    if not stored or stored['token'] != token:
        return jsonify({'valid': False})
    
    if datetime.utcnow() > stored['expires']:
        return jsonify({'valid': False, 'error': 'Token expired'})
    
    return jsonify({'valid': True})
