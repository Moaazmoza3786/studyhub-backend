"""
Gamification Engine for Study Hub Platform
Handles leveling, scoring, badges, and rewards
"""

import math
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

from models import db, User, Lab, LabSubmission, Achievement, UserAchievement


class GamificationEngine:
    """Core gamification logic for the platform"""
    
    # ==================== LEVELING SYSTEM ====================
    
    @staticmethod
    def calculate_level(total_xp: int) -> int:
        """
        Calculate level from XP using logarithmic formula
        Level = floor(0.1 * sqrt(Total_XP))
        
        Examples:
        - 100 XP = Level 1
        - 2500 XP = Level 5
        - 10000 XP = Level 10
        - 40000 XP = Level 20
        """
        if total_xp <= 0:
            return 0
        return int(0.1 * math.sqrt(total_xp))
    
    @staticmethod
    def calculate_xp_for_level(level: int) -> int:
        """Calculate XP required to reach a specific level"""
        if level <= 0:
            return 0
        return int((level / 0.1) ** 2)
    
    @staticmethod
    def get_level_progress(total_xp: int) -> Dict:
        """
        Get detailed level progress information
        
        Returns:
            Dict with current_level, current_xp, next_level_xp, progress_percent
        """
        current_level = GamificationEngine.calculate_level(total_xp)
        current_level_xp = GamificationEngine.calculate_xp_for_level(current_level)
        next_level_xp = GamificationEngine.calculate_xp_for_level(current_level + 1)
        
        xp_in_current_level = total_xp - current_level_xp
        xp_needed_for_next = next_level_xp - current_level_xp
        
        progress_percent = (xp_in_current_level / xp_needed_for_next * 100) if xp_needed_for_next > 0 else 100
        
        return {
            'current_level': current_level,
            'total_xp': total_xp,
            'current_level_xp': current_level_xp,
            'next_level_xp': next_level_xp,
            'xp_in_level': xp_in_current_level,
            'xp_needed': xp_needed_for_next - xp_in_current_level,
            'progress_percent': min(100, round(progress_percent, 1)),
            'level_title': GamificationEngine.get_level_title(current_level)
        }
    
    @staticmethod
    def get_level_title(level: int) -> str:
        """Get title/rank based on level"""
        titles = [
            (0, "Newbie", "مبتدئ"),
            (1, "Script Kiddie", "سكريبت كيدي"),
            (3, "Apprentice", "متدرب"),
            (5, "Hacker", "هاكر"),
            (8, "Cyber Warrior", "محارب سيبراني"),
            (12, "Elite Hacker", "هاكر محترف"),
            (16, "Master", "ماستر"),
            (20, "Grandmaster", "جراند ماستر"),
            (25, "Legend", "أسطورة"),
            (30, "Cyber God", "إله السايبر")
        ]
        
        for min_level, title_en, title_ar in reversed(titles):
            if level >= min_level:
                return title_en
        return "Unknown"
    
    # ==================== DYNAMIC SCORING (CTF) ====================
    
    @staticmethod
    def calculate_dynamic_points(
        max_points: int = 500,
        min_points: int = 100,
        decay: int = 20,
        num_solves: int = 0
    ) -> int:
        """
        Calculate dynamic points based on number of solves
        Points decrease as more people solve the challenge
        
        Formula: Current_Points = Max_Points - (Decay * Number_of_Solves)
        
        Args:
            max_points: Maximum points when first solved (default 500)
            min_points: Minimum points floor (default 100)
            decay: Points lost per solve (default 20)
            num_solves: Current number of solves
        
        Returns:
            Current point value for the challenge
        """
        current_points = max_points - (decay * num_solves)
        return max(min_points, current_points)
    
    @staticmethod
    def get_lab_current_points(lab_id: int) -> int:
        """Get current dynamic points for a lab based on solve count"""
        lab = Lab.query.get(lab_id)
        if not lab:
            return 100
        
        # Count correct submissions
        solve_count = LabSubmission.query.filter_by(
            lab_id=lab_id,
            is_correct=True
        ).count()
        
        # Use lab's base points as max
        max_points = lab.points or 500
        
        return GamificationEngine.calculate_dynamic_points(
            max_points=max_points,
            min_points=100,
            decay=15,
            num_solves=solve_count
        )
    
    # ==================== AUTO BADGES SYSTEM ====================
    
    BADGE_CONDITIONS = {
        'first_blood': {
            'name': 'First Blood',
            'name_ar': 'الدم الأول',
            'description': 'First to solve a challenge',
            'icon': '🩸',
            'check': 'check_first_blood'
        },
        'streak_master': {
            'name': 'Streak Master',
            'name_ar': 'سيد السلسلة',
            'description': 'Login for 30 consecutive days',
            'icon': '🔥',
            'check': 'check_streak_master'
        },
        'speed_demon': {
            'name': 'Speed Demon',
            'name_ar': 'شيطان السرعة',
            'description': 'Solve a Hard lab in under 10 minutes',
            'icon': '⚡',
            'check': 'check_speed_demon'
        },
        'sql_ninja': {
            'name': 'SQL Ninja',
            'name_ar': 'نينجا SQL',
            'description': 'Complete all SQL Injection labs',
            'icon': '🥷',
            'check': 'check_category_complete'
        },
        'persistent': {
            'name': 'Persistent',
            'name_ar': 'المثابر',
            'description': 'Submit 100 flag attempts',
            'icon': '💪',
            'check': 'check_total_attempts'
        },
        'perfectionist': {
            'name': 'Perfectionist',
            'name_ar': 'الكمالي',
            'description': 'Complete a path with 100% score',
            'icon': '💯',
            'check': 'check_perfect_path'
        },
        'helper': {
            'name': 'Helper',
            'name_ar': 'المساعد',
            'description': 'Help 10 users in discussions',
            'icon': '🤝',
            'check': 'check_help_count'
        },
        'night_owl': {
            'name': 'Night Owl',
            'name_ar': 'بومة الليل',
            'description': 'Solve 5 challenges between 2-5 AM',
            'icon': '🦉',
            'check': 'check_night_owl'
        }
    }
    
    @staticmethod
    def check_first_blood(user_id: int, lab_id: int) -> bool:
        """Check if user is first to solve a lab"""
        first_solve = LabSubmission.query.filter_by(
            lab_id=lab_id,
            is_correct=True
        ).order_by(LabSubmission.submitted_at.asc()).first()
        
        return first_solve and first_solve.user_id == user_id
    
    @staticmethod
    def check_streak_master(user_id: int) -> bool:
        """Check if user has 30-day login streak"""
        user = User.query.get(user_id)
        if not user:
            return False
        return (user.login_streak or 0) >= 30
    
    @staticmethod
    def check_speed_demon(user_id: int, submission: LabSubmission = None) -> bool:
        """Check if user solved a Hard lab in under 10 minutes"""
        if not submission or not submission.is_correct:
            return False
        
        lab = submission.lab
        if not lab or lab.difficulty != 'hard':
            return False
        
        # Check time (would need start_time tracking)
        # For now, return False
        return False
    
    @staticmethod
    def check_and_award_badges(user_id: int, context: Dict = None) -> List[Dict]:
        """
        Check all badge conditions and award any earned badges
        
        Args:
            user_id: User ID to check
            context: Additional context (lab_id, submission, etc.)
        
        Returns:
            List of newly awarded badges
        """
        awarded = []
        context = context or {}
        
        # Check First Blood
        if 'lab_id' in context:
            if GamificationEngine.check_first_blood(user_id, context['lab_id']):
                badge = GamificationEngine.award_badge(user_id, 'first_blood')
                if badge:
                    awarded.append(badge)
        
        # Check Streak Master
        if GamificationEngine.check_streak_master(user_id):
            badge = GamificationEngine.award_badge(user_id, 'streak_master')
            if badge:
                awarded.append(badge)
        
        return awarded
    
    @staticmethod
    def award_badge(user_id: int, badge_key: str) -> Optional[Dict]:
        """Award a badge to user if not already earned"""
        badge_info = GamificationEngine.BADGE_CONDITIONS.get(badge_key)
        if not badge_info:
            return None
        
        # Find or create achievement
        achievement = Achievement.query.filter_by(name=badge_info['name']).first()
        if not achievement:
            achievement = Achievement(
                name=badge_info['name'],
                name_ar=badge_info.get('name_ar', ''),
                description=badge_info.get('description', ''),
                icon=badge_info.get('icon', '🏆'),
                xp_reward=100,
                points_reward=50,
                rarity='rare'
            )
            db.session.add(achievement)
            db.session.flush()
        
        # Check if user already has this badge
        existing = UserAchievement.query.filter_by(
            user_id=user_id,
            achievement_id=achievement.id
        ).first()
        
        if existing:
            return None  # Already has badge
        
        # Award the badge
        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement.id
        )
        db.session.add(user_achievement)
        
        # Add XP reward
        user = User.query.get(user_id)
        if user:
            user.xp_points = (user.xp_points or 0) + (achievement.xp_reward or 0)
        
        db.session.commit()
        
        return {
            'name': badge_info['name'],
            'name_ar': badge_info.get('name_ar', ''),
            'icon': badge_info.get('icon', '🏆'),
            'xp_reward': achievement.xp_reward or 0
        }
    
    # ==================== STREAK TRACKING ====================
    
    @staticmethod
    def update_login_streak(user_id: int) -> Dict:
        """Update user's login streak"""
        user = User.query.get(user_id)
        if not user:
            return {'streak': 0}
        
        today = datetime.utcnow().date()
        last_login = user.last_login_date.date() if user.last_login_date else None
        
        if last_login == today:
            # Already logged in today
            return {'streak': user.login_streak or 0, 'updated': False}
        
        if last_login == today - timedelta(days=1):
            # Consecutive day - increment streak
            user.login_streak = (user.login_streak or 0) + 1
        else:
            # Streak broken - reset to 1
            user.login_streak = 1
        
        user.last_login_date = datetime.utcnow()
        db.session.commit()
        
        return {
            'streak': user.login_streak,
            'updated': True,
            'bonus_xp': GamificationEngine.get_streak_bonus(user.login_streak)
        }
    
    @staticmethod
    def get_streak_bonus(streak: int) -> int:
        """Calculate bonus XP for login streak"""
        if streak >= 30:
            return 50
        elif streak >= 14:
            return 30
        elif streak >= 7:
            return 20
        elif streak >= 3:
            return 10
        return 5
    
    # ==================== LEADERBOARD ====================
    
    @staticmethod
    def get_leaderboard(limit: int = 100, timeframe: str = 'all') -> List[Dict]:
        """
        Get leaderboard rankings
        
        Args:
            limit: Number of users to return
            timeframe: 'all', 'monthly', 'weekly'
        """
        query = User.query.filter(User.xp_points > 0)
        
        if timeframe == 'weekly':
            week_ago = datetime.utcnow() - timedelta(days=7)
            # Would need weekly XP tracking
        elif timeframe == 'monthly':
            month_ago = datetime.utcnow() - timedelta(days=30)
            # Would need monthly XP tracking
        
        users = query.order_by(User.xp_points.desc()).limit(limit).all()
        
        return [{
            'rank': i + 1,
            'user_id': user.id,
            'username': user.username,
            'avatar': user.avatar_url,
            'xp_points': user.xp_points or 0,
            'level': GamificationEngine.calculate_level(user.xp_points or 0),
            'level_title': GamificationEngine.get_level_title(
                GamificationEngine.calculate_level(user.xp_points or 0)
            )
        } for i, user in enumerate(users)]


# ==================== FLASK API ROUTES ====================

def register_gamification_routes(app):
    """Register gamification API routes"""
    from flask import request, jsonify
    
    @app.route('/api/user/<int:user_id>/level', methods=['GET'])
    def get_user_level(user_id):
        """Get user level and progress"""
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        level_info = GamificationEngine.get_level_progress(user.xp_points or 0)
        return jsonify(level_info)
    
    @app.route('/api/lab/<int:lab_id>/points', methods=['GET'])
    def get_lab_points(lab_id):
        """Get current dynamic points for a lab"""
        points = GamificationEngine.get_lab_current_points(lab_id)
        solve_count = LabSubmission.query.filter_by(
            lab_id=lab_id,
            is_correct=True
        ).count()
        
        return jsonify({
            'lab_id': lab_id,
            'current_points': points,
            'solve_count': solve_count
        })
    
    @app.route('/api/leaderboard', methods=['GET'])
    def get_leaderboard():
        """Get leaderboard"""
        limit = request.args.get('limit', 100, type=int)
        timeframe = request.args.get('timeframe', 'all')
        
        leaderboard = GamificationEngine.get_leaderboard(limit, timeframe)
        return jsonify({'leaderboard': leaderboard})
    
    @app.route('/api/user/<int:user_id>/streak', methods=['POST'])
    def update_streak(user_id):
        """Update user login streak"""
        result = GamificationEngine.update_login_streak(user_id)
        return jsonify(result)


# Global engine instance
gamification = GamificationEngine()


if __name__ == '__main__':
    # Test the engine
    print("=== Gamification Engine Tests ===\n")
    
    # Test leveling
    print("Level Calculation:")
    test_xps = [0, 100, 400, 2500, 10000, 40000, 90000]
    for xp in test_xps:
        level = GamificationEngine.calculate_level(xp)
        title = GamificationEngine.get_level_title(level)
        print(f"  {xp:>6} XP = Level {level:>2} ({title})")
    
    print("\n\nDynamic Scoring:")
    for solves in [0, 5, 10, 15, 20, 25]:
        points = GamificationEngine.calculate_dynamic_points(num_solves=solves)
        print(f"  {solves:>2} solves = {points:>3} points")
    
    print("\n\nLevel Progress Example (5000 XP):")
    progress = GamificationEngine.get_level_progress(5000)
    for key, value in progress.items():
        print(f"  {key}: {value}")
