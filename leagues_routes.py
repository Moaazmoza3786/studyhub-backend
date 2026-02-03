"""
Leagues API Routes for Study Hub Platform
Handles weekly league competition, leaderboards, and user rankings
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from functools import wraps
import jwt
import os

from models import db, User, League, LeagueParticipation

leagues_bp = Blueprint('leagues', __name__, url_prefix='/api/leagues')


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


def get_current_week_start():
    """Get the start of the current week (Monday)"""
    today = datetime.utcnow().date()
    return today - timedelta(days=today.weekday())


def get_week_remaining_time():
    """Get remaining time until Sunday midnight"""
    now = datetime.utcnow()
    week_start = get_current_week_start()
    week_end = datetime.combine(week_start + timedelta(days=7), datetime.min.time())
    remaining = week_end - now
    return {
        'days': remaining.days,
        'hours': remaining.seconds // 3600,
        'minutes': (remaining.seconds % 3600) // 60,
        'total_seconds': int(remaining.total_seconds())
    }


# ==================== API ENDPOINTS ====================

@leagues_bp.route('', methods=['GET'])
def get_all_leagues():
    """Get all available leagues"""
    leagues = League.query.order_by(League.order_index).all()
    return jsonify({
        'success': True,
        'leagues': [league.to_dict() for league in leagues]
    })


@leagues_bp.route('/current', methods=['GET'])
@token_required
def get_current_league(current_user):
    """Get user's current league and participation"""
    week_start = get_current_week_start()
    
    # Get current participation
    participation = LeagueParticipation.query.filter_by(
        user_id=current_user.id,
        week_start=week_start
    ).first()
    
    # Get user's league
    league = current_user.current_league
    if not league:
        # Default to Bronze if no league assigned
        league = League.query.filter_by(name='Bronze').first()
    
    return jsonify({
        'success': True,
        'league': league.to_dict() if league else None,
        'participation': participation.to_dict() if participation else None,
        'weekly_xp': current_user.weekly_xp,
        'week_remaining': get_week_remaining_time()
    })


@leagues_bp.route('/<int:league_id>/leaderboard', methods=['GET'])
def get_league_leaderboard(league_id):
    """Get leaderboard for a specific league"""
    league = League.query.get(league_id)
    if not league:
        return jsonify({'error': 'League not found'}), 404
    
    week_start = get_current_week_start()
    
    # Get all participations for this week in this league
    participations = LeagueParticipation.query.filter_by(
        league_id=league_id,
        week_start=week_start
    ).order_by(LeagueParticipation.weekly_xp.desc()).limit(50).all()
    
    # Build leaderboard with user details
    leaderboard = []
    for idx, p in enumerate(participations, 1):
        user = User.query.get(p.user_id)
        if user:
            leaderboard.append({
                'rank': idx,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'avatar_url': user.avatar_url
                },
                'xp': p.weekly_xp,
                'status': p.status
            })
    
    # Determine promotion/demotion zones
    total_participants = len(leaderboard)
    promotion_threshold = max(3, int(total_participants * 0.1))  # Top 10% or at least 3
    demotion_threshold = max(3, int(total_participants * 0.1))    # Bottom 10% or at least 3
    
    return jsonify({
        'success': True,
        'league': league.to_dict(),
        'leaderboard': leaderboard,
        'zones': {
            'promotion_cutoff': promotion_threshold,
            'demotion_cutoff': total_participants - demotion_threshold + 1 if total_participants > demotion_threshold else 0
        },
        'week_remaining': get_week_remaining_time()
    })


@leagues_bp.route('/join', methods=['POST'])
@token_required
def join_league(current_user):
    """Join the current week's league"""
    week_start = get_current_week_start()
    
    # Check if already participating
    existing = LeagueParticipation.query.filter_by(
        user_id=current_user.id,
        week_start=week_start
    ).first()
    
    if existing:
        return jsonify({
            'error': 'Already participating in this week\'s league',
            'participation': existing.to_dict()
        }), 400
    
    # Get user's current league (or default to Bronze)
    league = current_user.current_league
    if not league:
        league = League.query.filter_by(name='Bronze').first()
        if league:
            current_user.current_league_id = league.id
    
    if not league:
        return jsonify({'error': 'No leagues available'}), 500
    
    # Create participation
    participation = LeagueParticipation(
        user_id=current_user.id,
        league_id=league.id,
        week_start=week_start,
        weekly_xp=current_user.weekly_xp
    )
    
    db.session.add(participation)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Joined {league.name} League for this week!',
        'participation': participation.to_dict()
    })


@leagues_bp.route('/add-xp', methods=['POST'])
@token_required
def add_weekly_xp(current_user):
    """Add XP to user's weekly total (called when user completes activities)"""
    data = request.get_json()
    xp_amount = data.get('xp', 0)
    
    if xp_amount <= 0:
        return jsonify({'error': 'Invalid XP amount'}), 400
    
    # Update user's weekly XP
    current_user.weekly_xp += xp_amount
    current_user.xp_points += xp_amount  # Also add to total XP
    
    # Update participation if exists
    week_start = get_current_week_start()
    participation = LeagueParticipation.query.filter_by(
        user_id=current_user.id,
        week_start=week_start
    ).first()
    
    if participation:
        participation.weekly_xp = current_user.weekly_xp
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'weekly_xp': current_user.weekly_xp,
        'total_xp': current_user.xp_points
    })


# ==================== ADMIN/CRON ENDPOINTS ====================

@leagues_bp.route('/reset-weekly', methods=['POST'])
def reset_weekly_leagues():
    """
    Weekly reset endpoint - should be called by cron job on Sunday midnight
    1. Calculate final ranks for all participants
    2. Promote top 10% to next league
    3. Demote bottom 10% to previous league
    4. Reset weekly XP for all users
    """
    # Verify admin key (for cron job security)
    admin_key = request.headers.get('X-Admin-Key')
    expected_key = os.environ.get('ADMIN_CRON_KEY', 'dev-cron-key')
    
    if admin_key != expected_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    week_start = get_current_week_start()
    leagues = League.query.order_by(League.order_index).all()
    
    promotion_count = 0
    demotion_count = 0
    
    for league in leagues:
        # Get all participations for this league
        participations = LeagueParticipation.query.filter_by(
            league_id=league.id,
            week_start=week_start
        ).order_by(LeagueParticipation.weekly_xp.desc()).all()
        
        if not participations:
            continue
        
        total = len(participations)
        promotion_cutoff = max(1, int(total * 0.1))  # Top 10%
        demotion_cutoff = total - max(1, int(total * 0.1))  # Bottom 10%
        
        # Find next and previous leagues
        next_league = League.query.filter(League.order_index > league.order_index)\
                        .order_by(League.order_index).first()
        prev_league = League.query.filter(League.order_index < league.order_index)\
                        .order_by(League.order_index.desc()).first()
        
        for idx, p in enumerate(participations):
            p.final_rank = idx + 1
            user = User.query.get(p.user_id)
            
            if idx < promotion_cutoff and next_league:
                # Promote
                p.status = 'promoted'
                if user:
                    user.current_league_id = next_league.id
                promotion_count += 1
            elif idx >= demotion_cutoff and prev_league:
                # Demote
                p.status = 'demoted'
                if user:
                    user.current_league_id = prev_league.id
                demotion_count += 1
            else:
                p.status = 'stayed'
    
    # Reset weekly XP for all users
    User.query.update({User.weekly_xp: 0})
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Weekly reset completed',
        'promotions': promotion_count,
        'demotions': demotion_count
    })


@leagues_bp.route('/seed', methods=['POST'])
def seed_leagues():
    """Seed initial league data (run once during setup)"""
    admin_key = request.headers.get('X-Admin-Key')
    expected_key = os.environ.get('ADMIN_CRON_KEY', 'dev-cron-key')
    
    if admin_key != expected_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Check if leagues already exist
    if League.query.count() > 0:
        return jsonify({'message': 'Leagues already seeded', 'count': League.query.count()})
    
    leagues_data = [
        {'name': 'Bronze', 'name_ar': 'البرونز', 'icon': 'fa-medal', 'color': '#cd7f32', 'order_index': 1, 'min_weekly_xp': 0},
        {'name': 'Silver', 'name_ar': 'الفضة', 'icon': 'fa-medal', 'color': '#c0c0c0', 'order_index': 2, 'min_weekly_xp': 500},
        {'name': 'Gold', 'name_ar': 'الذهب', 'icon': 'fa-medal', 'color': '#ffd700', 'order_index': 3, 'min_weekly_xp': 1000},
        {'name': 'Platinum', 'name_ar': 'البلاتين', 'icon': 'fa-gem', 'color': '#e5e4e2', 'order_index': 4, 'min_weekly_xp': 2000},
        {'name': 'Diamond', 'name_ar': 'الماس', 'icon': 'fa-gem', 'color': '#b9f2ff', 'order_index': 5, 'min_weekly_xp': 4000},
        {'name': 'Master', 'name_ar': 'الماستر', 'icon': 'fa-crown', 'color': '#9b59b6', 'order_index': 6, 'min_weekly_xp': 7000},
        {'name': 'Grandmaster', 'name_ar': 'الغراند ماستر', 'icon': 'fa-crown', 'color': '#e74c3c', 'order_index': 7, 'min_weekly_xp': 10000}
    ]
    
    for data in leagues_data:
        league = League(**data)
        db.session.add(league)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Leagues seeded successfully',
        'count': len(leagues_data)
    })
