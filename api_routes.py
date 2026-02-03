"""
API Routes for Study Hub Platform
Clean Flask Blueprint-based API endpoints
"""

from flask import Blueprint, jsonify, request, g
from functools import wraps
from datetime import datetime
import hashlib

from models import (
    db, User, Domain, CareerPath, Module, Lab, Quiz, Question, Choice,
    UserProgress, LabSubmission, QuizAttempt, PathEnrollment, Certificate,
    Achievement, UserAchievement, UnlockedHint,
    Course, Unit, Lesson, Challenge  # V2 Models
)

# Import Badge if exists (for public profile)
try:
    from models import Badge, UserBadge
except ImportError:
    Badge = None
    UserBadge = None


# Create Blueprint
api = Blueprint('api', __name__, url_prefix='/api')

# Import AI Manager (Global instance initialized in main.py)
from ai_manager import groq_manager

# ==================== AI ENDPOINTS ====================

@api.route('/ai/chat', methods=['POST'])
def ai_chat():
    """Generate AI response for Shadow OS Chat"""
    data = request.json
    if not groq_manager:
        return jsonify({'success': False, 'error': 'AI not initialized'}), 503
        
    response = groq_manager.generate_chat_response(
        persona=data.get('persona', 'System'),
        user_message=data.get('message', ''),
        history=data.get('history', [])
    )
    return jsonify({'success': True, 'response': response}) if response else (jsonify({'success': False}), 500)

@api.route('/ai/news', methods=['GET'])
def ai_news():
    """Generate daily AI news"""
    if not groq_manager:
        return jsonify({'success': False, 'error': 'AI not initialized'}), 503
        
    news = groq_manager.generate_news()
    return jsonify({'success': True, 'news': news}) if news else (jsonify({'success': False}), 500)

@api.route('/ai/report', methods=['POST'])
def ai_report():
    """Generate executive summary for reports"""
    data = request.json
    if not groq_manager:
        return jsonify({'success': False, 'error': 'AI not initialized'}), 503
        
    summary = groq_manager.generate_report(data.get('findings', []))
    return jsonify({'success': True, 'summary': summary}) if summary else (jsonify({'success': False}), 500)

@api.route('/ai/wiki', methods=['POST'])
def ai_wiki():
    """Generate wiki content"""
    data = request.json
    if not groq_manager:
        return jsonify({'success': False, 'error': 'AI not initialized'}), 503
        
    content = groq_manager.update_wiki(data.get('topic'))
    return jsonify({'success': True, 'content': content}) if content else (jsonify({'success': False}), 500)

@api.route('/ai/analyze', methods=['POST'])
def ai_analyze():
    """Analyze code snippet"""
    data = request.json
    if not groq_manager:
        return jsonify({'success': False, 'error': 'AI not initialized'}), 503
        
    analysis = groq_manager.analyze_code(data.get('code'), data.get('language', 'python'))
    return jsonify({'success': True, 'analysis': analysis}) if analysis else (jsonify({'success': False}), 500)

@api.route('/ai/optimize', methods=['POST'])
def ai_optimize():
    """Optimize/Obfuscate payload"""
    data = request.json
    if not groq_manager:
        return jsonify({'success': False, 'error': 'AI not initialized'}), 503
        
    result = groq_manager.optimize_payload(data.get('payload'))
    return jsonify({'success': True, 'result': result}) if result else (jsonify({'success': False}), 500)

@api.route('/ai/campaign', methods=['POST'])
def ai_campaign():
    """Generate campaign scenario"""
    data = request.json
    if not groq_manager:
        return jsonify({'success': False, 'error': 'AI not initialized'}), 503
        
    campaign = groq_manager.generate_campaign(data.get('sector', 'Technology'))
    return jsonify({'success': True, 'campaign': campaign}) if campaign else (jsonify({'success': False}), 500)


@api.route('/ai/security-chat', methods=['POST'])
def ai_security_chat():
    """
    Security-focused AI chat for the Security Assistant widget.
    Helps with XSS, SQLi, PrivEsc, API testing, AD attacks, etc.
    """
    data = request.json
    if not groq_manager:
        return jsonify({'success': False, 'error': 'AI not initialized'}), 503
    
    message = data.get('message', '')
    context = data.get('context', 'general')
    history = data.get('history', [])
    
    if not message:
        return jsonify({'success': False, 'error': 'Message is required'}), 400
    
    response = groq_manager.security_chat(message, context, history)
    
    if response:
        return jsonify({'success': True, 'response': response})
    else:
        return jsonify({'success': False, 'error': 'Failed to generate response'}), 500


# ==================== RECON ENDPOINTS ====================

@api.route('/recon/subdomains', methods=['POST'])
def recon_subdomains():
    """
    Enumerate subdomains for a given domain using crt.sh
    """
    data = request.json
    domain = data.get('domain', '').strip()
    
    if not domain:
        return jsonify({'success': False, 'error': 'Domain is required'}), 400
    
    try:
        import requests as req
        
        # Use crt.sh certificate transparency logs
        response = req.get(f'https://crt.sh/?q=%.{domain}&output=json', timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # Extract unique subdomains
            subdomains = set()
            for entry in data:
                name = entry.get('name_value', '')
                # Handle wildcards and multiple names
                for sub in name.split('\n'):
                    sub = sub.strip().replace('*.', '')
                    if sub and domain in sub:
                        subdomains.add(sub)
            
            return jsonify({
                'success': True,
                'domain': domain,
                'subdomains': list(subdomains),
                'count': len(subdomains)
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to fetch from crt.sh'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== HELPER DECORATORS ====================

def require_json(f):
    """Decorator to require JSON body"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    """Get current user from request (simplified - would use JWT in production)"""
    user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
    if user_id:
        return User.query.get(int(user_id))
    return None


# ==================== VPN CONFIGURATION ENDPOINTS ====================

@api.route('/vpn/config/<int:user_id>', methods=['GET'])
def get_vpn_config(user_id):
    """
    GET /api/vpn/config/<user_id>
    Generate and download OpenVPN configuration file for user
    """
    from flask import Response
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    try:
        from vpn_generator import generate_vpn_config
        
        config_content = generate_vpn_config(user_id, user.username)
        
        # Return as downloadable file
        filename = f"studyhub_{user.username}.ovpn"
        
        return Response(
            config_content,
            mimetype='application/x-openvpn-profile',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'application/x-openvpn-profile'
            }
        )
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Failed to generate VPN config: {str(e)}'
        }), 500


@api.route('/vpn/status', methods=['GET'])
def get_vpn_status():
    """
    GET /api/vpn/status
    Get VPN server status and connection info
    """
    return jsonify({
        'success': True,
        'vpn_available': True,
        'server': 'lab.studyhub.com',
        'port': 1194,
        'protocol': 'UDP',
        'status': 'online',
        'connected_users': 0,
        'lab_networks': [
            {'name': 'Web Labs', 'subnet': '10.10.10.0/24'},
            {'name': 'Network Labs', 'subnet': '10.10.20.0/24'},
            {'name': 'PWN Labs', 'subnet': '10.10.30.0/24'}
        ]
    })


# ==================== PAID HINTS SYSTEM ====================

HINT_COST = 5  # Points cost per hint

@api.route('/hint/unlock', methods=['POST'])
@require_json
def unlock_hint():
    """
    POST /api/hint/unlock
    Unlock a hint for a lab (costs points)
    
    Request body:
    {
        "user_id": 1,
        "lab_id": 10,
        "hint_index": 0
    }
    
    Response:
    {
        "success": true,
        "hint": "The vulnerability is in the login form...",
        "points_deducted": 5,
        "remaining_points": 95
    }
    """
    data = request.json
    user_id = data.get('user_id')
    lab_id = data.get('lab_id')
    hint_index = data.get('hint_index', 0)
    
    if not user_id or lab_id is None:
        return jsonify({'success': False, 'error': 'user_id and lab_id are required'}), 400
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Check if user has enough points
    user_points = user.total_points or 0
    if user_points < HINT_COST:
        return jsonify({
            'success': False,
            'error': f'Not enough points. You need {HINT_COST} points but have {user_points}.',
            'points_needed': HINT_COST,
            'current_points': user_points
        }), 400
    
    # Get lab and hint
    lab = Lab.query.get(lab_id)
    if not lab:
        return jsonify({'success': False, 'error': 'Lab not found'}), 404
    
    # Check if hint already unlocked
    existing = UnlockedHint.query.filter_by(
        user_id=user_id, 
        lab_id=lab_id, 
        hint_index=hint_index
    ).first()
    
    if existing:
        # Return hint without charging again
        hints = lab.hints_json or []
        if hint_index < len(hints):
            return jsonify({
                'success': True,
                'hint': hints[hint_index],
                'points_deducted': 0,
                'remaining_points': user_points,
                'already_unlocked': True
            })
        return jsonify({'success': False, 'error': 'Hint not found'}), 404
    
    # Deduct points
    user.total_points = user_points - HINT_COST
    
    # Record unlocked hint
    unlocked = UnlockedHint(
        user_id=user_id,
        lab_id=lab_id,
        hint_index=hint_index,
        unlocked_at=datetime.utcnow()
    )
    db.session.add(unlocked)
    db.session.commit()
    
    # Get hint content
    hints = lab.hints_json or []
    hint_content = hints[hint_index] if hint_index < len(hints) else "Hint not available"
    
    return jsonify({
        'success': True,
        'hint': hint_content,
        'points_deducted': HINT_COST,
        'remaining_points': user.total_points
    })


@api.route('/hint/check/<int:user_id>/<int:lab_id>', methods=['GET'])
def check_unlocked_hints(user_id, lab_id):
    """
    GET /api/hint/check/<user_id>/<lab_id>
    Check which hints user has already unlocked for a lab
    """
    unlocked = UnlockedHint.query.filter_by(user_id=user_id, lab_id=lab_id).all()
    
    return jsonify({
        'success': True,
        'unlocked_hints': [h.hint_index for h in unlocked],
        'hint_cost': HINT_COST
    })


# ==================== PATH ENDPOINTS ====================

@api.route('/paths', methods=['GET'])
def get_paths():
    """
    GET /api/paths
    Returns all learning paths with optional domain filter
    """
    domain_id = request.args.get('domain_id', type=int)
    
    query = CareerPath.query.filter_by(is_published=True)
    
    if domain_id:
        query = query.filter_by(domain_id=domain_id)
    
    paths = query.order_by(CareerPath.order_index).all()
    
    return jsonify({
        'success': True,
        'count': len(paths),
        'paths': [path.to_dict() for path in paths]
    })


@api.route('/paths/<slug>', methods=['GET'])
def get_path_by_slug(slug):
    """
    GET /api/paths/<slug>
    Returns path details with modules
    """
    path = CareerPath.query.filter_by(slug=slug, is_published=True).first()
    
    if not path:
        return jsonify({'success': False, 'error': 'Path not found'}), 404
    
    return jsonify({
        'success': True,
        'path': path.to_dict(include_modules=True)
    })


@api.route('/paths/<int:path_id>/enroll', methods=['POST'])
@require_json
def enroll_in_path(path_id):
    """
    POST /api/paths/<id>/enroll
    Enroll current user in a learning path
    """
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    path = CareerPath.query.get(path_id)
    if not path:
        return jsonify({'success': False, 'error': 'Path not found'}), 404
    
    # Check if already enrolled
    existing = PathEnrollment.query.filter_by(
        user_id=user.id, career_path_id=path_id
    ).first()
    
    if existing:
        return jsonify({
            'success': True,
            'message': 'Already enrolled',
            'enrollment': {
                'progress_percentage': existing.progress_percentage,
                'enrolled_at': existing.enrolled_at.isoformat()
            }
        })
    
    # Create enrollment
    enrollment = PathEnrollment(
        user_id=user.id,
        career_path_id=path_id
    )
    db.session.add(enrollment)
    
    # Update path enrolled count
    path.enrolled_count = (path.enrolled_count or 0) + 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Successfully enrolled',
        'enrollment': {
            'progress_percentage': 0,
            'enrolled_at': enrollment.enrolled_at.isoformat()
        }
    }), 201


# ==================== PUBLIC PROFILE ENDPOINT ====================

@api.route('/profile/<username>', methods=['GET'])
def get_public_profile(username):
    """
    GET /api/profile/<username>
    Returns public profile data for a user (no auth required)
    """
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Get user badges
    user_badges = UserBadge.query.filter_by(user_id=user.id).all()
    badges = []
    for ub in user_badges:
        badge = Badge.query.get(ub.badge_id)
        if badge:
            badges.append({
                'icon': badge.icon,
                'name': badge.name,
                'desc': badge.description
            })
    
    # Get user certificates
    certificates = Certificate.query.filter_by(user_id=user.id, is_valid=True).all()
    certs = []
    for cert in certificates:
        path = cert.career_path
        certs.append({
            'name': path.name if path else 'Certificate',
            'date': cert.issued_at.strftime('%Y-%m-%d') if cert.issued_at else None
        })
    
    # Calculate level from points
    level = (user.total_points or 0) // 500 + 1
    
    # Get rank name
    ranks = [
        (0, 'Script Kiddie'),
        (500, 'Novice Hacker'),
        (1500, 'Cyber Apprentice'),
        (3000, 'Security Analyst'),
        (5000, 'Penetration Tester'),
        (8000, 'Cyber Warrior'),
        (12000, 'Elite Hacker'),
        (20000, 'Legend')
    ]
    rank = 'Script Kiddie'
    for points, name in ranks:
        if (user.total_points or 0) >= points:
            rank = name
    
    return jsonify({
        'success': True,
        'user': {
            'username': user.username,
            'displayName': user.username,
            'points': user.total_points or 0,
            'level': level,
            'rank': rank,
            'labsSolved': user.labs_completed or 0,
            'streak': user.streak_days or 0,
            'joinDate': user.created_at.strftime('%Y-%m-%d') if user.created_at else None,
            'badges': badges,
            'certificates': certs
        }
    })


# ==================== MODULE ENDPOINTS ====================

@api.route('/module/<int:module_id>', methods=['GET'])
def get_module(module_id):
    """
    GET /api/module/<id>
    Returns module content (video/text) by ID
    """
    module = Module.query.get(module_id)
    
    if not module:
        return jsonify({'success': False, 'error': 'Module not found'}), 404
    
    if not module.is_published:
        return jsonify({'success': False, 'error': 'Module not available'}), 403
    
    # Get associated lab and quiz if any
    lab = module.labs.first()
    quiz = module.quizzes.first()
    
    response = {
        'success': True,
        'module': module.to_dict(include_content=True),
        'has_lab': lab is not None,
        'has_quiz': quiz is not None
    }
    
    if lab:
        response['lab'] = lab.to_dict()
    
    if quiz:
        response['quiz'] = quiz.to_dict(include_questions=True)
    
    return jsonify(response)


@api.route('/module/<int:module_id>/progress', methods=['POST'])
@require_json
def update_module_progress(module_id):
    """
    POST /api/module/<id>/progress
    Update user progress for a module
    """
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    module = Module.query.get(module_id)
    if not module:
        return jsonify({'success': False, 'error': 'Module not found'}), 404
    
    data = request.json
    progress_percentage = data.get('progress_percentage', 0)
    is_completed = data.get('is_completed', False)
    
    # Get or create progress
    progress = UserProgress.query.filter_by(
        user_id=user.id, module_id=module_id
    ).first()
    
    if not progress:
        progress = UserProgress(
            user_id=user.id,
            module_id=module_id,
            is_started=True,
            started_at=datetime.utcnow()
        )
        db.session.add(progress)
    
    progress.progress_percentage = progress_percentage
    progress.last_accessed_at = datetime.utcnow()
    
    xp_awarded = 0
    
    if is_completed and not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = datetime.utcnow()
        
        # Award XP for completion
        xp_awarded = module.xp_reward or 50
        user.add_xp(xp_awarded)
        
        # Update path enrollment progress
        _update_path_progress(user.id, module.career_path_id)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'progress_percentage': progress.progress_percentage,
        'is_completed': progress.is_completed,
        'xp_awarded': xp_awarded,
        'user_level': user.level,
        'user_xp': user.xp_points
    })


def _update_path_progress(user_id, path_id):
    """Helper to update path enrollment progress"""
    enrollment = PathEnrollment.query.filter_by(
        user_id=user_id, career_path_id=path_id
    ).first()
    
    if not enrollment:
        return
    
    # Count completed modules
    path = CareerPath.query.get(path_id)
    total_modules = path.modules.count()
    
    completed_modules = UserProgress.query.join(Module).filter(
        UserProgress.user_id == user_id,
        Module.career_path_id == path_id,
        UserProgress.is_completed == True
    ).count()
    
    enrollment.modules_completed = completed_modules
    enrollment.progress_percentage = int((completed_modules / max(total_modules, 1)) * 100)
    enrollment.last_accessed_at = datetime.utcnow()
    
    if enrollment.progress_percentage == 100 and not enrollment.is_completed:
        enrollment.is_completed = True
        enrollment.completed_at = datetime.utcnow()


# ==================== FLAG SUBMISSION ENDPOINT ====================

@api.route('/submit-flag', methods=['POST'])
@require_json
def submit_flag():
    """
    POST /api/submit-flag
    Verify a submitted flag for a lab
    
    Request body:
    {
        "user_id": 1,
        "lab_id": 10,
        "submitted_flag": "FLAG{example}"
    }
    
    Response:
    {
        "success": true,
        "correct": true/false,
        "points_awarded": 100,
        "xp_awarded": 50,
        "message": "Congratulations! Flag is correct!",
        "user_stats": {
            "total_xp": 1500,
            "level": 5,
            "rank": "Junior Pentester"
        }
    }
    """
    data = request.json
    
    user_id = data.get('user_id')
    lab_id = data.get('lab_id')
    submitted_flag = data.get('submitted_flag', '').strip()
    
    # Validate required fields
    if not all([user_id, lab_id, submitted_flag]):
        return jsonify({
            'success': False, 
            'error': 'Missing required fields: user_id, lab_id, submitted_flag'
        }), 400
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Get lab
    lab = Lab.query.get(lab_id)
    if not lab:
        return jsonify({'success': False, 'error': 'Lab not found'}), 404
    
    # Check if already solved by this user
    previous_solve = LabSubmission.query.filter_by(
        user_id=user_id, lab_id=lab_id, is_correct=True
    ).first()
    
    if previous_solve:
        return jsonify({
            'success': True,
            'correct': True,
            'already_solved': True,
            'message': 'You have already solved this lab!',
            'solved_at': previous_solve.attempt_time.isoformat()
        })
    
    # Verify flag
    is_correct = lab.verify_flag(submitted_flag)
    
    # Calculate points (with hint penalty if applicable)
    hints_used = data.get('hints_used', [])
    hints_penalty = len(hints_used) * 10  # 10 points per hint
    points_awarded = max(0, lab.points - hints_penalty) if is_correct else 0
    xp_awarded = lab.xp_reward if is_correct else 0
    
    # Create submission record
    submission = LabSubmission(
        user_id=user_id,
        lab_id=lab_id,
        user_input_flag=submitted_flag[:500],  # Limit stored flag length
        is_correct=is_correct,
        hints_used=str(hints_used),
        hints_penalty=hints_penalty,
        points_awarded=points_awarded,
        xp_awarded=xp_awarded
    )
    db.session.add(submission)
    
    # Update lab stats
    lab.total_attempts = (lab.total_attempts or 0) + 1
    
    if is_correct:
        lab.total_solves = (lab.total_solves or 0) + 1
        
        # Award XP to user
        user.add_xp(xp_awarded)
        
        # Update module progress
        module_progress = UserProgress.query.filter_by(
            user_id=user_id, module_id=lab.module_id
        ).first()
        
        if not module_progress:
            module_progress = UserProgress(
                user_id=user_id,
                module_id=lab.module_id,
                is_started=True,
                started_at=datetime.utcnow()
            )
            db.session.add(module_progress)
        
        module_progress.is_completed = True
        module_progress.completed_at = datetime.utcnow()
        module_progress.progress_percentage = 100
        
        # Update path progress
        module = Module.query.get(lab.module_id)
        if module:
            _update_path_progress(user_id, module.career_path_id)
        
        # Check for achievements
        _check_achievements(user)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'correct': is_correct,
        'points_awarded': points_awarded,
        'xp_awarded': xp_awarded,
        'message': 'Congratulations! Flag is correct! 🎉' if is_correct else 'Incorrect flag. Try again! 💪',
        'user_stats': {
            'total_xp': user.xp_points,
            'level': user.level,
            'rank': user.current_rank
        }
    })


def _check_achievements(user):
    """Check and award achievements to user"""
    # Count user's lab solves
    lab_solves = LabSubmission.query.filter_by(
        user_id=user.id, is_correct=True
    ).count()
    
    # First Blood achievement
    if lab_solves == 1:
        _award_achievement(user, 'First Blood')
    
    # Lab Rat achievement (10 labs)
    if lab_solves == 10:
        _award_achievement(user, 'Lab Rat')


def _award_achievement(user, achievement_name):
    """Award an achievement to user if not already earned"""
    achievement = Achievement.query.filter_by(name=achievement_name).first()
    if not achievement:
        return
    
    # Check if already earned
    existing = UserAchievement.query.filter_by(
        user_id=user.id, achievement_id=achievement.id
    ).first()
    
    if existing:
        return
    
    # Award achievement
    user_achievement = UserAchievement(
        user_id=user.id,
        achievement_id=achievement.id
    )
    db.session.add(user_achievement)
    
    # Award XP and points
    user.add_xp(achievement.xp_reward or 0)


# ==================== DOMAINS ENDPOINT ====================

@api.route('/domains', methods=['GET'])
def get_domains():
    """
    GET /api/domains
    Returns all active domains with their paths
    """
    domains = Domain.query.filter_by(is_active=True).order_by(Domain.order_index).all()
    
    result = []
    for domain in domains:
        domain_dict = domain.to_dict()
        domain_dict['paths'] = [
            p.to_dict() for p in domain.paths.filter_by(is_published=True).order_by(CareerPath.order_index)
        ]
        result.append(domain_dict)
    
    return jsonify({
        'success': True,
        'domains': result
    })


# ==================== USER ENDPOINTS ====================

@api.route('/user/<int:user_id>/progress', methods=['GET'])
def get_user_progress(user_id):
    """
    GET /api/user/<id>/progress
    Returns user's overall progress across all paths
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    enrollments = PathEnrollment.query.filter_by(user_id=user_id).all()
    
    paths_progress = []
    for enrollment in enrollments:
        path = enrollment.career_path
        paths_progress.append({
            'path_id': path.id,
            'path_name': path.name,
            'path_name_ar': path.name_ar,
            'progress_percentage': enrollment.progress_percentage,
            'modules_completed': enrollment.modules_completed,
            'total_modules': path.modules.count(),
            'is_completed': enrollment.is_completed,
            'enrolled_at': enrollment.enrolled_at.isoformat()
        })
    
    # Count stats
    labs_solved = LabSubmission.query.filter_by(user_id=user_id, is_correct=True).count()
    quizzes_passed = QuizAttempt.query.filter_by(user_id=user_id, is_passed=True).count()
    certificates = Certificate.query.filter_by(user_id=user_id, is_valid=True).count()
    
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'paths': paths_progress,
        'stats': {
            'labs_solved': labs_solved,
            'quizzes_passed': quizzes_passed,
            'certificates': certificates,
            'paths_enrolled': len(enrollments),
            'paths_completed': sum(1 for e in enrollments if e.is_completed)
        }
    })


@api.route('/user/<int:user_id>/achievements', methods=['GET'])
def get_user_achievements(user_id):
    """
    GET /api/user/<id>/achievements
    Returns user's earned achievements
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    user_achievements = UserAchievement.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'success': True,
        'achievements': [
            {
                'achievement': ua.achievement.to_dict(),
                'earned_at': ua.earned_at.isoformat()
            }
            for ua in user_achievements
        ]
    })




# ==================== CERTIFICATES ENDPOINT ====================

@api.route('/certificate/verify/<verify_code>', methods=['GET'])
def verify_certificate_code(verify_code):
    """
    GET /api/certificate/verify/<code>
    Verify a certificate by its unique code
    """
    certificate = Certificate.query.filter_by(verify_code=verify_code).first()
    
    if not certificate:
        return jsonify({
            'success': False,
            'valid': False,
            'error': 'Certificate not found'
        }), 404
    
    return jsonify({
        'success': True,
        'valid': certificate.is_valid,
        'certificate': certificate.to_dict(),
        'user': certificate.user.to_dict() if certificate.user else None,
        'path': certificate.career_path.to_dict() if certificate.career_path else None
    })


@api.route('/certificate/generate', methods=['POST'])
@require_json
def generate_certificate_endpoint():
    """
    POST /api/certificate/generate
    Generate a PDF certificate for a user who completed a path
    
    Request body:
    {
        "user_id": 1,
        "path_id": 10
    }
    
    Response:
    {
        "success": true,
        "certificate_code": "SH-20241208123456",
        "download_url": "/api/certificate/download/SH-20241208123456",
        "message": "Certificate generated successfully"
    }
    """
    from flask import current_app
    import uuid
    
    data = request.json
    user_id = data.get('user_id')
    path_id = data.get('path_id')
    
    if not user_id or not path_id:
        return jsonify({'success': False, 'error': 'user_id and path_id are required'}), 400
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Get path
    path = CareerPath.query.get(path_id)
    if not path:
        return jsonify({'success': False, 'error': 'Path not found'}), 404
    
    # Check if user completed the path
    enrollment = PathEnrollment.query.filter_by(
        user_id=user_id, career_path_id=path_id
    ).first()
    
    if not enrollment:
        return jsonify({'success': False, 'error': 'User is not enrolled in this path'}), 400
    
    if enrollment.progress_percentage < 100:
        return jsonify({
            'success': False, 
            'error': f'Path not completed. Current progress: {enrollment.progress_percentage}%'
        }), 400
    
    # Check if certificate already exists
    existing_cert = Certificate.query.filter_by(
        user_id=user_id, career_path_id=path_id
    ).first()
    
    if existing_cert:
        return jsonify({
            'success': True,
            'certificate_code': existing_cert.verify_code,
            'download_url': f'/api/certificate/download/{existing_cert.verify_code}',
            'message': 'Certificate already exists',
            'already_exists': True
        })
    
    # Generate unique certificate code
    certificate_code = f"SH-{uuid.uuid4().hex[:12].upper()}"
    
    # Create certificate record in database
    certificate = Certificate(
        user_id=user_id,
        career_path_id=path_id,
        verify_code=certificate_code,
        issued_at=datetime.utcnow(),
        is_valid=True,
        final_score=enrollment.progress_percentage
    )
    db.session.add(certificate)
    db.session.commit()
    
    # Generate PDF using certificate generator
    try:
        from certificate_generator import CertificateGenerator
        import os
        
        output_dir = os.path.join(os.path.dirname(__file__), 'certificates')
        generator = CertificateGenerator(output_dir)
        
        pdf_path = generator.generate(
            student_name=user.username,
            course_name=path.name,
            course_name_ar=path.name_ar,
            certificate_code=certificate_code,
            score=enrollment.progress_percentage
        )
        
        # Update certificate with file path
        certificate.pdf_path = pdf_path
        db.session.commit()
        
    except Exception as e:
        print(f"Certificate PDF generation error: {e}")
        # Certificate record exists but PDF generation failed - can retry later
    
    return jsonify({
        'success': True,
        'certificate_code': certificate_code,
        'download_url': f'/api/certificate/download/{certificate_code}',
        'message': 'Certificate generated successfully'
    })


@api.route('/certificate/download/<certificate_code>', methods=['GET'])
def download_certificate(certificate_code):
    """
    GET /api/certificate/download/<code>
    Download the PDF certificate file
    """
    from flask import send_file
    import os
    
    certificate = Certificate.query.filter_by(verify_code=certificate_code).first()
    
    if not certificate:
        return jsonify({'success': False, 'error': 'Certificate not found'}), 404
    
    # Check if PDF exists
    if certificate.pdf_path and os.path.exists(certificate.pdf_path):
        return send_file(
            certificate.pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'StudyHub_Certificate_{certificate_code}.pdf'
        )
    
    # Try to regenerate if PDF doesn't exist
    try:
        from certificate_generator import CertificateGenerator
        
        user = certificate.user
        path = certificate.career_path
        
        output_dir = os.path.join(os.path.dirname(__file__), 'certificates')
        generator = CertificateGenerator(output_dir)
        
        pdf_path = generator.generate(
            student_name=user.username if user else 'Student',
            course_name=path.name if path else 'Course',
            course_name_ar=path.name_ar if path else None,
            certificate_code=certificate_code,
            score=certificate.final_score
        )
        
        # Update certificate with file path
        certificate.pdf_path = pdf_path
        db.session.commit()
        
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'StudyHub_Certificate_{certificate_code}.pdf'
        )
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Failed to generate certificate: {str(e)}'
        }), 500


@api.route('/certificate/user/<int:user_id>', methods=['GET'])
def get_user_certificates(user_id):
    """
    GET /api/certificate/user/<user_id>
    Get all certificates for a user
    """
    certificates = Certificate.query.filter_by(user_id=user_id, is_valid=True).all()
    
    return jsonify({
        'success': True,
        'certificates': [
            {
                'id': cert.id,
                'path_name': cert.career_path.name if cert.career_path else None,
                'path_name_ar': cert.career_path.name_ar if cert.career_path else None,
                'verify_code': cert.verify_code,
                'issued_at': cert.issued_at.isoformat() if cert.issued_at else None,
                'download_url': f'/api/certificate/download/{cert.verify_code}',
                'final_score': cert.final_score
            }
            for cert in certificates
        ]
    })


# ==================== QUIZ SUBMISSION ENDPOINT ====================


@api.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
@require_json
def submit_quiz(quiz_id):
    """
    POST /api/quiz/<id>/submit
    Submit quiz answers
    
    Request body:
    {
        "user_id": 1,
        "answers": {
            "1": 3,  // question_id: selected_choice_id
            "2": 5
        }
    }
    """
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'success': False, 'error': 'Quiz not found'}), 404
    
    data = request.json
    user_id = data.get('user_id')
    answers = data.get('answers', {})
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Calculate score
    questions = quiz.questions.all()
    total_points = 0
    earned_points = 0
    results = []
    
    for question in questions:
        total_points += question.points
        selected_choice_id = answers.get(str(question.id))
        
        correct_choice = Choice.query.filter_by(
            question_id=question.id, is_correct=True
        ).first()
        
        is_correct = selected_choice_id == correct_choice.id if correct_choice else False
        
        if is_correct:
            earned_points += question.points
        
        results.append({
            'question_id': question.id,
            'is_correct': is_correct,
            'correct_choice_id': correct_choice.id if correct_choice else None,
            'selected_choice_id': selected_choice_id,
            'explanation': question.explanation,
            'explanation_ar': question.explanation_ar
        })
    
    score_percentage = int((earned_points / max(total_points, 1)) * 100)
    is_passed = score_percentage >= quiz.passing_score
    
    xp_awarded = quiz.xp_reward if is_passed else 0
    points_awarded = quiz.points if is_passed else 0
    
    # Record attempt
    attempt = QuizAttempt(
        user_id=user_id,
        quiz_id=quiz_id,
        score_percentage=score_percentage,
        is_passed=is_passed,
        points_awarded=points_awarded,
        xp_awarded=xp_awarded,
        completed_at=datetime.utcnow(),
        answers_json=str(answers)
    )
    db.session.add(attempt)
    
    if is_passed:
        user.add_xp(xp_awarded)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'score_percentage': score_percentage,
        'is_passed': is_passed,
        'passing_score': quiz.passing_score,
        'points_awarded': points_awarded,
        'xp_awarded': xp_awarded,
        'results': results if quiz.show_correct_answers else None,
        'message': '🎉 Congratulations! You passed!' if is_passed else f'You need {quiz.passing_score}% to pass. Try again!'
    })


# ==================== HEALTH CHECK ====================

@api.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.0.0'
    })


# ==================== DOCKER LAB ENDPOINTS ====================

# Import Docker Lab Manager (lazy import to avoid issues if docker not installed)
def get_lab_manager():
    """Get Docker Lab Manager instance"""
    try:
        from docker_lab_manager import get_docker_manager
        return get_docker_manager()
    except ImportError:
        return None


@api.route('/lab/start', methods=['POST'])
@require_json
def start_lab():
    """
    POST /api/lab/start
    Start a Docker lab container for a user
    
    Request body:
    {
        "user_id": 1,
        "lab_id": 10,
        "image_name": "vulnlab/sqli-basic:v1"  // Optional, fetched from DB if not provided
    }
    
    Response:
    {
        "success": true,
        "ip": "192.168.1.100",
        "port": 25430,
        "connection_string": "192.168.1.100:25430",
        "expires_at": "2024-01-01T14:00:00",
        "message": "Lab started successfully"
    }
    """
    data = request.json
    
    user_id = data.get('user_id')
    lab_id = data.get('lab_id')
    image_name = data.get('image_name')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'user_id is required'}), 400
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Get lab info if lab_id provided
    if lab_id:
        lab = Lab.query.get(lab_id)
        if not lab:
            return jsonify({'success': False, 'error': 'Lab not found'}), 404
        image_name = image_name or lab.docker_image_id
    
    if not image_name:
        return jsonify({'success': False, 'error': 'image_name or lab_id is required'}), 400
    
    # Get Docker manager
    manager = get_lab_manager()
    if not manager:
        return jsonify({
            'success': False, 
            'error': 'Docker manager not available',
            'message': 'Lab system is not configured. Please contact support.'
        }), 503
    
    # Spawn the container
    result = manager.spawn_lab_container(
        user_id=user_id,
        image_name=image_name,
        lab_id=lab_id,
        timeout_minutes=data.get('timeout_minutes', 120)
    )
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500


@api.route('/lab/stop', methods=['POST'])
@require_json
def stop_lab():
    """
    POST /api/lab/stop
    Stop and remove all lab containers for a user
    
    Request body:
    {
        "user_id": 1
    }
    """
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'user_id is required'}), 400
    
    manager = get_lab_manager()
    if not manager:
        return jsonify({
            'success': False, 
            'error': 'Docker manager not available'
        }), 503
    
    result = manager.kill_user_containers(user_id)
    return jsonify(result)


@api.route('/lab/status/<int:user_id>', methods=['GET'])
def get_lab_status(user_id):
    """
    GET /api/lab/status/<user_id>
    Get the currently running lab for a user
    
    Response:
    {
        "success": true,
        "active": true,
        "lab": {
            "container_id": "abc123",
            "ip": "192.168.1.100",
            "port": 25430,
            "connection_string": "192.168.1.100:25430",
            "expires_at": "2024-01-01T14:00:00"
        }
    }
    """
    manager = get_lab_manager()
    if not manager:
        return jsonify({
            'success': True, 
            'active': False,
            'message': 'Docker manager not available'
        })
    
    active_lab = manager.get_user_active_lab(user_id)
    
    if active_lab:
        return jsonify({
            'success': True,
            'active': True,
            'lab': active_lab
        })
    else:
        return jsonify({
            'success': True,
            'active': False,
            'message': 'No active lab found'
        })


@api.route('/lab/extend', methods=['POST'])
@require_json
def extend_lab():
    """
    POST /api/lab/extend
    Extend the timeout for a user's active lab
    
    Request body:
    {
        "user_id": 1,
        "additional_minutes": 60
    }
    """
    data = request.json
    user_id = data.get('user_id')
    additional_minutes = data.get('additional_minutes', 60)
    
    if not user_id:
        return jsonify({'success': False, 'error': 'user_id is required'}), 400
    
    manager = get_lab_manager()
    if not manager:
        return jsonify({'success': False, 'error': 'Docker manager not available'}), 503
    
    result = manager.extend_lab_timeout(user_id, additional_minutes)
    return jsonify(result)


@api.route('/lab/reset', methods=['POST'])
@require_json
def reset_lab():
    """
    POST /api/lab/reset
    Reset a user's lab container (stop and restart)
    
    Request body:
    {
        "user_id": 1
    }
    
    Response:
    {
        "success": true,
        "ip": "192.168.1.101",
        "port": 25431,
        "message": "Lab reset successfully"
    }
    """
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'user_id is required'}), 400
    
    manager = get_lab_manager()
    if not manager:
        return jsonify({'success': False, 'error': 'Docker manager not available'}), 503
    
    # Get current active lab info
    active_lab = manager.get_user_active_lab(user_id)
    
    if not active_lab:
        return jsonify({
            'success': False, 
            'error': 'No active lab found to reset'
        }), 404
    
    # Stop current container
    manager.kill_user_containers(user_id)
    
    # Restart with same image
    image_name = active_lab.get('image_name', 'vulnlab/default:v1')
    lab_id = active_lab.get('lab_id')
    
    result = manager.spawn_lab_container(
        user_id=user_id,
        image_name=image_name,
        lab_id=lab_id,
        timeout_minutes=60  # Reset with 1 hour
    )
    
    if result['success']:
        result['message'] = 'Lab reset successfully'
    
    return jsonify(result)

@api.route('/lab/all', methods=['GET'])
def get_all_labs():
    """
    GET /api/lab/all
    Get all currently running labs (admin endpoint)
    """
    manager = get_lab_manager()
    if not manager:
        return jsonify({
            'success': True, 
            'labs': [],
            'message': 'Docker manager not available'
        })
    
    labs = manager.get_all_active_labs()
    
    return jsonify({
        'success': True,
        'count': len(labs),
        'labs': labs,
        'docker_available': manager.is_docker_available
    })


@api.route('/lab/cleanup', methods=['POST'])
def cleanup_expired_labs():
    """
    POST /api/lab/cleanup
    Cleanup expired lab containers (should be called periodically)
    """
    manager = get_lab_manager()
    if not manager:
        return jsonify({'success': False, 'error': 'Docker manager not available'}), 503
    
    result = manager.cleanup_expired_containers()
    return jsonify(result)


# ==================== ENROLLMENT & ACCESS CONTROL ENDPOINTS ====================

@api.route('/path/<path_id>/enroll', methods=['POST'])
@require_json
def enroll_user_in_path(path_id):
    """
    POST /api/path/<path_id>/enroll
    Enroll current user in a learning path
    """
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User ID required'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Check if already enrolled
    existing = PathEnrollment.query.filter_by(
        user_id=user_id,
        career_path_id=path_id
    ).first()
    
    if existing:
        return jsonify({
            'success': True,
            'message': 'Already enrolled',
            'enrollment': {
                'path_id': path_id,
                'enrolled_at': existing.enrolled_at.isoformat() if existing.enrolled_at else None,
                'progress_percentage': existing.progress_percentage
            }
        })
    
    # Create new enrollment
    try:
        # For string path_id (frontend uses string IDs like 'web-pentesting')
        # We store as-is since our frontend uses string IDs
        enrollment = PathEnrollment(
            user_id=user_id,
            career_path_id=path_id if isinstance(path_id, int) else hash(path_id) % 10000,
            progress_percentage=0,
            modules_completed=0,
            enrolled_at=datetime.utcnow(),
            last_accessed_at=datetime.utcnow()
        )
        db.session.add(enrollment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Successfully enrolled in path',
            'enrollment': {
                'id': enrollment.id,
                'path_id': path_id,
                'enrolled_at': enrollment.enrolled_at.isoformat(),
                'progress_percentage': 0
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/path/<path_id>/unenroll', methods=['POST'])
@require_json
def unenroll_from_path(path_id):
    """
    POST /api/path/<path_id>/unenroll
    Remove enrollment from a path
    """
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User ID required'}), 400
    
    enrollment = PathEnrollment.query.filter_by(
        user_id=user_id,
        career_path_id=path_id if isinstance(path_id, int) else hash(path_id) % 10000
    ).first()
    
    if not enrollment:
        return jsonify({'success': False, 'error': 'Not enrolled in this path'}), 404
    
    try:
        db.session.delete(enrollment)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Successfully unenrolled from path'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/path/<path_id>/enrollment-status', methods=['GET'])
def get_enrollment_status(path_id):
    """
    GET /api/path/<path_id>/enrollment-status?user_id=X
    Check if user is enrolled in path
    """
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User ID required'}), 400
    
    enrollment = PathEnrollment.query.filter_by(
        user_id=user_id,
        career_path_id=path_id if isinstance(path_id, int) else hash(path_id) % 10000
    ).first()
    
    if enrollment:
        return jsonify({
            'success': True,
            'is_enrolled': True,
            'enrollment': {
                'path_id': path_id,
                'enrolled_at': enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
                'progress_percentage': enrollment.progress_percentage,
                'modules_completed': enrollment.modules_completed,
                'is_completed': enrollment.is_completed,
                'last_accessed': enrollment.last_accessed_at.isoformat() if enrollment.last_accessed_at else None
            }
        })
    else:
        return jsonify({
            'success': True,
            'is_enrolled': False
        })


@api.route('/path/<path_id>/progress', methods=['POST'])
@require_json
def update_path_progress(path_id):
    """
    POST /api/path/<path_id>/progress
    Update progress in a path
    """
    data = request.get_json()
    user_id = data.get('user_id')
    progress = data.get('progress_percentage', 0)
    modules_completed = data.get('modules_completed', 0)
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User ID required'}), 400
    
    enrollment = PathEnrollment.query.filter_by(
        user_id=user_id,
        career_path_id=path_id if isinstance(path_id, int) else hash(path_id) % 10000
    ).first()
    
    if not enrollment:
        return jsonify({'success': False, 'error': 'Not enrolled in this path'}), 404
    
    try:
        enrollment.progress_percentage = min(100, progress)
        enrollment.modules_completed = modules_completed
        enrollment.last_accessed_at = datetime.utcnow()
        
        if progress >= 100:
            enrollment.is_completed = True
            enrollment.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Progress updated',
            'progress_percentage': enrollment.progress_percentage,
            'is_completed': enrollment.is_completed
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/user/<int:user_id>/enrolled-paths', methods=['GET'])
def get_user_enrolled_paths(user_id):
    """
    GET /api/user/<user_id>/enrolled-paths
    Get all paths user is enrolled in
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    enrollments = PathEnrollment.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'success': True,
        'count': len(enrollments),
        'enrollments': [{
            'path_id': e.career_path_id,
            'enrolled_at': e.enrolled_at.isoformat() if e.enrolled_at else None,
            'progress_percentage': e.progress_percentage,
            'modules_completed': e.modules_completed,
            'is_completed': e.is_completed,
            'last_accessed': e.last_accessed_at.isoformat() if e.last_accessed_at else None
        } for e in enrollments]
    })


# ==================== CERTIFICATE ENDPOINTS ====================

@api.route('/certificate/generate', methods=['POST'])
@require_json
def generate_user_certificate():
    """
    POST /api/certificate/generate
    Generate certificate for completed path
    """
    import uuid
    
    data = request.get_json()
    user_id = data.get('user_id')
    path_id = data.get('path_id')
    certificate_name = data.get('certificate_name', 'Completion Certificate')
    recipient_name = data.get('recipient_name')
    
    if not user_id or not path_id:
        return jsonify({'success': False, 'error': 'User ID and Path ID required'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Check if already has certificate
    existing = Certificate.query.filter_by(
        user_id=user_id,
        career_path_id=path_id if isinstance(path_id, int) else hash(path_id) % 10000
    ).first()
    
    if existing:
        return jsonify({
            'success': True,
            'message': 'Certificate already exists',
            'certificate': existing.to_dict()
        })
    
    try:
        cert = Certificate(
            user_id=user_id,
            career_path_id=path_id if isinstance(path_id, int) else hash(path_id) % 10000,
            certificate_name=certificate_name,
            verify_code=str(uuid.uuid4()),
            recipient_name=recipient_name or user.username,
            issue_date=datetime.utcnow(),
            is_valid=True
        )
        db.session.add(cert)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Certificate generated',
            'certificate': cert.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/certificate/verify/<verify_code>', methods=['GET'])
def verify_certificate_public(verify_code):
    """
    GET /api/certificate/verify/<verify_code>
    Public endpoint to verify certificate authenticity
    """
    cert = Certificate.query.filter_by(verify_code=verify_code).first()
    
    if not cert:
        return jsonify({
            'success': False,
            'valid': False,
            'error': 'Certificate not found'
        }), 404
    
    user = User.query.get(cert.user_id)
    
    return jsonify({
        'success': True,
        'valid': cert.is_valid,
        'certificate': {
            'recipient_name': cert.recipient_name,
            'certificate_name': cert.certificate_name,
            'issue_date': cert.issue_date.isoformat() if cert.issue_date else None,
            'verify_code': cert.verify_code,
            'is_valid': cert.is_valid
        },
        'user': {
            'username': user.username if user else None,
            'level': user.level if user else None
        } if user else None
    })


@api.route('/user/<int:user_id>/certificates', methods=['GET'])
def get_user_earned_certificates(user_id):
    """
    GET /api/user/<user_id>/certificates
    Get all certificates earned by user
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    certificates = Certificate.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'success': True,
        'count': len(certificates),
        'certificates': [c.to_dict() for c in certificates]
    })


@api.route('/certificate/email', methods=['POST'])
@require_json
def send_certificate_email():
    """
    POST /api/certificate/email
    Send certificate notification email to user
    
    Request body:
    {
        "user_id": 1,
        "cert_code": "AG-PT1-8829-XJ"
    }
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.application import MIMEApplication
    import os
    
    data = request.get_json()
    user_id = data.get('user_id')
    cert_code = data.get('cert_code')
    
    if not user_id or not cert_code:
        return jsonify({'success': False, 'error': 'User ID and Certificate code required'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    certificate = Certificate.query.filter_by(verify_code=cert_code).first()
    if not certificate:
        return jsonify({'success': False, 'error': 'Certificate not found'}), 404
    
    # Email configuration (use environment variables in production)
    SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USER = os.environ.get('SMTP_USER', '')
    SMTP_PASS = os.environ.get('SMTP_PASS', '')
    FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@studyhub.io')
    
    # Check if email is configured
    if not SMTP_USER or not SMTP_PASS:
        return jsonify({
            'success': False,
            'error': 'Email not configured. Set SMTP_USER and SMTP_PASS environment variables.'
        }), 503
    
    # Build email content
    user_email = user.email
    user_name = user.username
    cert_name = certificate.certificate_name or 'Completion Certificate'
    
    subject = f'مبروك {user_name}! ها هي شهادة {cert_name} الخاصة بك 🎓'
    
    html_body = f'''
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Cairo', Arial, sans-serif; background: #0a0a14; color: #fff; margin: 0; padding: 40px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: linear-gradient(180deg, #1a1a2e 0%, #0f0f1a 100%); border-radius: 20px; padding: 40px; border: 1px solid #22c55e; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .logo {{ font-size: 40px; color: #22c55e; margin-bottom: 10px; }}
            h1 {{ color: #22c55e; margin: 0; font-size: 28px; }}
            .congrats {{ font-size: 48px; text-align: center; margin: 20px 0; }}
            .message {{ color: rgba(255,255,255,0.85); line-height: 1.8; font-size: 16px; }}
            .cert-box {{ background: rgba(34, 197, 94, 0.1); border-radius: 15px; padding: 25px; margin: 25px 0; text-align: center; }}
            .cert-name {{ font-size: 24px; color: #fff; font-weight: 700; }}
            .cert-code {{ font-family: monospace; color: #22c55e; font-size: 18px; margin-top: 10px; }}
            .btn {{ display: inline-block; background: linear-gradient(135deg, #22c55e, #16a34a); color: #000; padding: 15px 35px; border-radius: 10px; text-decoration: none; font-weight: 700; margin: 10px; }}
            .next-steps {{ background: rgba(59, 130, 246, 0.1); border-radius: 15px; padding: 20px; margin-top: 30px; }}
            .next-steps h3 {{ color: #3b82f6; margin: 0 0 15px; }}
            .footer {{ text-align: center; margin-top: 40px; color: rgba(255,255,255,0.5); font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">🛡️</div>
                <h1>STUDY HUB</h1>
            </div>
            
            <div class="congrats">🎉</div>
            
            <h2 style="text-align: center; color: #fff;">مبروك يا {user_name}!</h2>
            
            <p class="message">
                لقد أتممت بنجاح مسار <strong>{cert_name}</strong> على منصة Study Hub!
                هذا إنجاز رائع يثبت التزامك ومهارتك في مجال الأمن السيبراني.
            </p>
            
            <div class="cert-box">
                <div class="cert-name">{cert_name}</div>
                <div class="cert-code">كود التحقق: {cert_code}</div>
            </div>
            
            <div style="text-align: center;">
                <a href="https://studyhub.io/verify/{cert_code}" class="btn">عرض شهادتي</a>
                <a href="https://studyhub.io/certificates" class="btn" style="background: rgba(59, 130, 246, 0.3); color: #3b82f6;">تحميل PDF</a>
            </div>
            
            <div class="next-steps">
                <h3>🚀 ماذا بعد؟</h3>
                <p style="color: rgba(255,255,255,0.8); margin: 0;">
                    أنت الآن جاهز للمسار التالي! نقترح عليك:<br>
                    • <strong>Cyber Defense (CD1)</strong> - تعلم الدفاع السيبراني<br>
                    • <strong>Advanced Web Hacking</strong> - اختراق تطبيقات الويب المتقدم
                </p>
            </div>
            
            <div class="footer">
                <p>© 2025 Study Hub - Cybersecurity Learning Platform</p>
                <p>تم إرسال هذا البريد لأنك أتممت مسار تعليمي على منصتنا.</p>
            </div>
        </div>
    </body>
    </html>
    '''
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = FROM_EMAIL
        msg['To'] = user_email
        
        # Attach HTML
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        # Attach PDF if exists
        if certificate.pdf_path and os.path.exists(certificate.pdf_path):
            with open(certificate.pdf_path, 'rb') as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
                pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                         filename=f'StudyHub_Certificate_{cert_code}.pdf')
                msg.attach(pdf_attachment)
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        
        return jsonify({
            'success': True,
            'message': f'Certificate email sent to {user_email}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to send email: {str(e)}'
        }), 500


# ==================== GAMIFICATION ENDPOINTS ====================

@api.route('/labs/<int:lab_id>/first_blood', methods=['GET'])
def get_lab_first_blood(lab_id):
    """
    GET /api/labs/<lab_id>/first_blood
    Get the top 3 users who solved this lab first.
    """
    # Find existing submissions, ordered by creation time
    first_bloods = LabSubmission.query.filter_by(
        lab_id=lab_id, 
        is_correct=True
    ).order_by(LabSubmission.created_at.asc()).limit(3).all()
    
    results = []
    for sub in first_bloods:
        # Calculate time taken if available, else use default formatting
        time_taken = "N/A"
        if sub.time_to_solve_seconds:
            mins, secs = divmod(sub.time_to_solve_seconds, 60)
            time_taken = f"{mins}m {secs}s"
            
        results.append({
            'username': sub.user.username,
            'avatar_url': sub.user.avatar_url,
            'solved_at': sub.created_at.isoformat(),
            'time_taken': time_taken
        })
        
    return jsonify({
        'success': True,
        'lab_id': lab_id,
        'first_blood': results
    })


@api.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """
    GET /api/leaderboard
    Get global leaderboard sorted by XP.
    """
    # Top 50 users
    top_users = User.query.filter_by(is_active=True).order_by(
        User.xp_points.desc()
    ).limit(50).all()
    
    leaderboard = []
    for idx, user in enumerate(top_users):
        leaderboard.append({
            'rank': idx + 1,
            'username': user.username,
            'avatar_url': user.avatar_url,
            'level': user.level,
            'current_rank': user.current_rank,
            'xp_points': user.xp_points,
            'streak_days': user.streak_days
        })
        
    return jsonify({
        'success': True,
        'leaderboard': leaderboard
    })


# ==================== V2 CONTENT API (Courses & Challenges) ====================

@api.route('/v2/courses', methods=['GET'])
def get_v2_courses():
    """List all V2 Courses"""
    courses = Course.query.all()
    return jsonify({
        'success': True,
        'count': len(courses),
        'courses': [c.to_dict() for c in courses]
    })

@api.route('/v2/courses/<int:course_id>', methods=['GET'])
def get_v2_course_detail(course_id):
    """Get Course Details with Units"""
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'success': False, 'error': 'Course not found'}), 404
        
    return jsonify({
        'success': True,
        'course': course.to_dict()
    })

@api.route('/v2/challenges', methods=['GET'])
def get_v2_challenges():
    """List all V2 Challenges"""
    challenges = Challenge.query.all()
    return jsonify({
        'success': True,
        'count': len(challenges),
        'challenges': [c.to_dict() for c in challenges]
    })

@api.route('/v2/challenges/<int:challenge_id>', methods=['GET'])
def get_v2_challenge_detail(challenge_id):
    """Get Challenge details"""
    challenge = Challenge.query.get(challenge_id)
    if not challenge:
        return jsonify({'success': False, 'error': 'Challenge not found'}), 404

    return jsonify({
        'success': True,
        'challenge': challenge.to_dict()
    })


