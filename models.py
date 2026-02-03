"""
SQLAlchemy ORM Models for Study Hub Platform
Matches the PostgreSQL/MySQL schema defined in schema.sql
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

db = SQLAlchemy()


# ==================== USER MODELS ====================

class User(db.Model):
    """User accounts with roles, XP, and progress tracking"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    avatar_url = db.Column(db.String(500))
    bio = db.Column(db.Text)
    
    # Role & Permissions
    role = db.Column(db.String(20), default='student', nullable=False)  # admin, student, content_creator
    
    # Gamification
    xp_points = db.Column(db.Integer, default=0, nullable=False)
    level = db.Column(db.Integer, default=1, nullable=False)
    current_rank = db.Column(db.String(50), default='Script Kiddie')
    streak_days = db.Column(db.Integer, default=0)
    last_active_date = db.Column(db.Date)
    
    # League System
    current_league_id = db.Column(db.Integer, db.ForeignKey('leagues.id'), nullable=True)
    weekly_xp = db.Column(db.Integer, default=0, nullable=False)
    
    # Subscription
    subscription_tier = db.Column(db.String(20), default='free', nullable=False)  # free, monthly, annual
    subscription_expires_at = db.Column(db.DateTime, nullable=True)
    
    # Account Status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    progress = db.relationship('UserProgress', backref='user', lazy='dynamic')
    lab_submissions = db.relationship('LabSubmission', backref='user', lazy='dynamic')
    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy='dynamic')
    certificates = db.relationship('Certificate', backref='user', lazy='dynamic')
    enrollments = db.relationship('PathEnrollment', backref='user', lazy='dynamic')
    achievements = db.relationship('UserAchievement', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def add_xp(self, amount):
        """Add XP and check for level up"""
        self.xp_points += amount
        # Level calculation: Level = sqrt(XP / 100)
        new_level = max(1, int((self.xp_points / 100) ** 0.5))
        if new_level > self.level:
            self.level = new_level
            self._update_rank()
        return self.level
    
    def _update_rank(self):
        """Update rank based on level"""
        ranks = {
            1: 'Script Kiddie',
            5: 'Apprentice Hacker',
            10: 'Junior Pentester',
            15: 'Security Analyst',
            25: 'Senior Pentester',
            40: 'Security Expert',
            60: 'Elite Hacker',
            80: 'Master',
            100: 'Legendary'
        }
        for level_threshold, rank in sorted(ranks.items(), reverse=True):
            if self.level >= level_threshold:
                self.current_rank = rank
                break
    
    def to_dict(self, include_email=False):
        """Convert to dictionary for JSON response"""
        data = {
            'id': self.id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'avatar_url': self.avatar_url,
            'role': self.role,
            'xp_points': self.xp_points,
            'level': self.level,
            'current_rank': self.current_rank,
            'streak_days': self.streak_days,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_email:
            data['email'] = self.email
        return data


# ==================== CONTENT MODELS ====================

class Domain(db.Model):
    """Major categories (Red Team, Blue Team, CTF)"""
    __tablename__ = 'domains'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    name_ar = db.Column(db.String(100))
    description = db.Column(db.Text)
    description_ar = db.Column(db.Text)
    icon = db.Column(db.String(50))
    color = db.Column(db.String(20))
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    paths = db.relationship('CareerPath', backref='domain', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_ar': self.name_ar,
            'description': self.description,
            'description_ar': self.description_ar,
            'icon': self.icon,
            'color': self.color,
            'order_index': self.order_index,
            'paths_count': self.paths.count()
        }


class CareerPath(db.Model):
    """Learning paths within a domain"""
    __tablename__ = 'career_paths'
    
    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey('domains.id'), nullable=False)
    
    name = db.Column(db.String(150), nullable=False)
    name_ar = db.Column(db.String(150))
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    description_ar = db.Column(db.Text)
    
    # Visual
    icon = db.Column(db.String(50))
    color = db.Column(db.String(20))
    thumbnail_url = db.Column(db.String(500))
    
    # Meta
    difficulty = db.Column(db.String(20), default='beginner')  # beginner, intermediate, advanced
    estimated_hours = db.Column(db.Integer, default=0)
    
    # Certification
    certification_name = db.Column(db.String(200))
    certification_description = db.Column(db.Text)
    
    # Status
    is_published = db.Column(db.Boolean, default=False)
    is_featured = db.Column(db.Boolean, default=False)
    order_index = db.Column(db.Integer, default=0)
    
    # Denormalized stats
    total_modules = db.Column(db.Integer, default=0)
    total_labs = db.Column(db.Integer, default=0)
    enrolled_count = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    modules = db.relationship('Module', backref='career_path', lazy='dynamic', order_by='Module.order_index')
    enrollments = db.relationship('PathEnrollment', backref='career_path', lazy='dynamic')
    certificates = db.relationship('Certificate', backref='career_path', lazy='dynamic')
    
    def to_dict(self, include_modules=False):
        data = {
            'id': self.id,
            'domain_id': self.domain_id,
            'name': self.name,
            'name_ar': self.name_ar,
            'slug': self.slug,
            'description': self.description,
            'description_ar': self.description_ar,
            'icon': self.icon,
            'color': self.color,
            'thumbnail_url': self.thumbnail_url,
            'difficulty': self.difficulty,
            'estimated_hours': self.estimated_hours,
            'certification_name': self.certification_name,
            'total_modules': self.total_modules or self.modules.count(),
            'total_labs': self.total_labs,
            'enrolled_count': self.enrolled_count,
            'is_published': self.is_published,
            'is_featured': self.is_featured
        }
        if include_modules:
            data['modules'] = [m.to_dict() for m in self.modules.order_by(Module.order_index)]
        return data


class Module(db.Model):
    """Lessons within a path"""
    __tablename__ = 'modules'
    
    id = db.Column(db.Integer, primary_key=True)
    career_path_id = db.Column(db.Integer, db.ForeignKey('career_paths.id'), nullable=False)
    
    name = db.Column(db.String(200), nullable=False)
    name_ar = db.Column(db.String(200))
    slug = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    description_ar = db.Column(db.Text)
    
    # Content Type
    module_type = db.Column(db.String(20), default='article')  # video, article, quiz_only, lab
    
    # Ordering
    order_index = db.Column(db.Integer, default=0, nullable=False)
    
    # Content
    content_html = db.Column(db.Text)
    content_html_ar = db.Column(db.Text)
    video_url = db.Column(db.String(500))
    video_duration_minutes = db.Column(db.Integer)
    
    # Learning Objectives (JSON)
    objectives = db.Column(db.Text)  # JSON array
    objectives_ar = db.Column(db.Text)
    
    # Tools (JSON)
    tools = db.Column(db.Text)  # JSON array
    
    # Meta
    estimated_minutes = db.Column(db.Integer, default=30)
    xp_reward = db.Column(db.Integer, default=50)
    
    # Prerequisites (JSON array of module IDs)
    prerequisites = db.Column(db.Text)
    
    # Status
    is_published = db.Column(db.Boolean, default=False)
    is_free = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    labs = db.relationship('Lab', backref='module', lazy='dynamic')
    quizzes = db.relationship('Quiz', backref='module', lazy='dynamic')
    progress = db.relationship('UserProgress', backref='module', lazy='dynamic')
    
    def to_dict(self, include_content=False):
        import json
        data = {
            'id': self.id,
            'career_path_id': self.career_path_id,
            'name': self.name,
            'name_ar': self.name_ar,
            'slug': self.slug,
            'description': self.description,
            'description_ar': self.description_ar,
            'module_type': self.module_type,
            'order_index': self.order_index,
            'video_url': self.video_url,
            'video_duration_minutes': self.video_duration_minutes,
            'estimated_minutes': self.estimated_minutes,
            'xp_reward': self.xp_reward,
            'is_published': self.is_published,
            'is_free': self.is_free,
            'objectives': json.loads(self.objectives) if self.objectives else [],
            'objectives_ar': json.loads(self.objectives_ar) if self.objectives_ar else [],
            'tools': json.loads(self.tools) if self.tools else []
        }
        if include_content:
            data['content_html'] = self.content_html
            data['content_html_ar'] = self.content_html_ar
        return data


# ==================== LAB MODELS ====================

class Lab(db.Model):
    """Practical exercises with Docker"""
    __tablename__ = 'labs'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False)
    
    title = db.Column(db.String(200), nullable=False)
    title_ar = db.Column(db.String(200))
    description = db.Column(db.Text)
    description_ar = db.Column(db.Text)
    
    # Docker Configuration
    docker_image_id = db.Column(db.String(255), nullable=False)
    docker_compose_yaml = db.Column(db.Text)
    exposed_ports = db.Column(db.Text)  # JSON array
    environment_vars = db.Column(db.Text)  # JSON object
    
    # Challenge
    flag_hash = db.Column(db.String(255), nullable=False)
    flag_format = db.Column(db.String(100), default='FLAG{...}')
    
    # Difficulty & Rewards
    difficulty = db.Column(db.String(20), default='easy')  # easy, medium, hard, insane
    points = db.Column(db.Integer, default=100, nullable=False)
    xp_reward = db.Column(db.Integer, default=100)
    
    # Time Limits
    time_limit_minutes = db.Column(db.Integer, default=60)
    instance_timeout_minutes = db.Column(db.Integer, default=120)
    
    # Hints (JSON)
    hints = db.Column(db.Text)
    hints_ar = db.Column(db.Text)
    
    # Writeup
    writeup_html = db.Column(db.Text)
    writeup_html_ar = db.Column(db.Text)
    
    # Stats
    total_attempts = db.Column(db.Integer, default=0)
    total_solves = db.Column(db.Integer, default=0)
    
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    submissions = db.relationship('LabSubmission', backref='lab', lazy='dynamic')
    
    def verify_flag(self, submitted_flag):
        """Verify if submitted flag matches (supports hash or plaintext)"""
        import hashlib
        # Try direct comparison first (for unhashed flags)
        if submitted_flag == self.flag_hash:
            return True
        # Try SHA256 hash comparison
        flag_sha256 = hashlib.sha256(submitted_flag.encode()).hexdigest()
        return flag_sha256 == self.flag_hash
    
    def to_dict(self, include_writeup=False):
        import json
        data = {
            'id': self.id,
            'module_id': self.module_id,
            'title': self.title,
            'title_ar': self.title_ar,
            'description': self.description,
            'description_ar': self.description_ar,
            'difficulty': self.difficulty,
            'points': self.points,
            'xp_reward': self.xp_reward,
            'time_limit_minutes': self.time_limit_minutes,
            'flag_format': self.flag_format,
            'hints': json.loads(self.hints) if self.hints else [],
            'hints_ar': json.loads(self.hints_ar) if self.hints_ar else [],
            'total_attempts': self.total_attempts,
            'total_solves': self.total_solves,
            'solve_rate': round(self.total_solves / max(self.total_attempts, 1) * 100, 1)
        }
        if include_writeup:
            data['writeup_html'] = self.writeup_html
            data['writeup_html_ar'] = self.writeup_html_ar
        return data


class LabSubmission(db.Model):
    """Lab attempt tracking"""
    __tablename__ = 'lab_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), nullable=False)
    
    user_input_flag = db.Column(db.String(500))
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    
    # Instance info
    instance_id = db.Column(db.String(100))
    instance_ip = db.Column(db.String(50))
    instance_started_at = db.Column(db.DateTime)
    instance_ended_at = db.Column(db.DateTime)
    
    # Hints used
    hints_used = db.Column(db.Text)  # JSON array
    hints_penalty = db.Column(db.Integer, default=0)
    
    # Points awarded
    points_awarded = db.Column(db.Integer, default=0)
    xp_awarded = db.Column(db.Integer, default=0)
    
    # Time tracking
    attempt_time = db.Column(db.DateTime, default=datetime.utcnow)
    time_to_solve_seconds = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== QUIZ MODELS ====================

class Quiz(db.Model):
    """Quizzes for modules"""
    __tablename__ = 'quizzes'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False)
    
    title = db.Column(db.String(200), nullable=False)
    title_ar = db.Column(db.String(200))
    description = db.Column(db.Text)
    description_ar = db.Column(db.Text)
    
    # Configuration
    passing_score = db.Column(db.Integer, default=70)
    time_limit_minutes = db.Column(db.Integer)
    max_attempts = db.Column(db.Integer, default=3)
    shuffle_questions = db.Column(db.Boolean, default=False)
    shuffle_choices = db.Column(db.Boolean, default=False)
    show_correct_answers = db.Column(db.Boolean, default=True)
    
    # Rewards
    xp_reward = db.Column(db.Integer, default=50)
    points = db.Column(db.Integer, default=50)
    
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='quiz', lazy='dynamic', order_by='Question.order_index')
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy='dynamic')
    
    def to_dict(self, include_questions=False):
        data = {
            'id': self.id,
            'module_id': self.module_id,
            'title': self.title,
            'title_ar': self.title_ar,
            'description': self.description,
            'passing_score': self.passing_score,
            'time_limit_minutes': self.time_limit_minutes,
            'max_attempts': self.max_attempts,
            'xp_reward': self.xp_reward,
            'points': self.points,
            'questions_count': self.questions.count()
        }
        if include_questions:
            data['questions'] = [q.to_dict(include_choices=True) for q in self.questions]
        return data


class Question(db.Model):
    """Quiz questions"""
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    
    question_text = db.Column(db.Text, nullable=False)
    question_text_ar = db.Column(db.Text)
    
    question_type = db.Column(db.String(30), default='multiple_choice')
    code_snippet = db.Column(db.Text)
    code_language = db.Column(db.String(30))
    image_url = db.Column(db.String(500))
    
    order_index = db.Column(db.Integer, default=0)
    
    explanation = db.Column(db.Text)
    explanation_ar = db.Column(db.Text)
    
    points = db.Column(db.Integer, default=10)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    choices = db.relationship('Choice', backref='question', lazy='dynamic', order_by='Choice.order_index')
    
    def to_dict(self, include_choices=False, hide_correct=False):
        data = {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'question_text': self.question_text,
            'question_text_ar': self.question_text_ar,
            'question_type': self.question_type,
            'code_snippet': self.code_snippet,
            'code_language': self.code_language,
            'image_url': self.image_url,
            'points': self.points
        }
        if include_choices:
            data['choices'] = [c.to_dict(hide_correct=hide_correct) for c in self.choices]
        return data


class Choice(db.Model):
    """Answer options for questions"""
    __tablename__ = 'choices'
    
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    
    choice_text = db.Column(db.Text, nullable=False)
    choice_text_ar = db.Column(db.Text)
    
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    order_index = db.Column(db.Integer, default=0)
    
    feedback = db.Column(db.Text)
    feedback_ar = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self, hide_correct=False):
        data = {
            'id': self.id,
            'choice_text': self.choice_text,
            'choice_text_ar': self.choice_text_ar
        }
        if not hide_correct:
            data['is_correct'] = self.is_correct
            data['feedback'] = self.feedback
            data['feedback_ar'] = self.feedback_ar
        return data


class QuizAttempt(db.Model):
    """Quiz attempt tracking"""
    __tablename__ = 'quiz_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    
    score_percentage = db.Column(db.Integer, default=0, nullable=False)
    is_passed = db.Column(db.Boolean, default=False)
    
    points_awarded = db.Column(db.Integer, default=0)
    xp_awarded = db.Column(db.Integer, default=0)
    
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    time_spent_seconds = db.Column(db.Integer)
    
    answers_json = db.Column(db.Text)  # JSON: {question_id: choice_id}
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== PROGRESS MODELS ====================

class UserProgress(db.Model):
    """Module progress tracking"""
    __tablename__ = 'user_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False)
    
    is_started = db.Column(db.Boolean, default=False)
    is_completed = db.Column(db.Boolean, default=False)
    progress_percentage = db.Column(db.Integer, default=0)
    
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    last_accessed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    time_spent_seconds = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'module_id'),)


class PathEnrollment(db.Model):
    """Track path subscriptions"""
    __tablename__ = 'path_enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    career_path_id = db.Column(db.Integer, db.ForeignKey('career_paths.id'), nullable=False)
    
    progress_percentage = db.Column(db.Integer, default=0)
    modules_completed = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    last_accessed_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'career_path_id'),)


# ==================== CERTIFICATE & ACHIEVEMENT MODELS ====================

class Certificate(db.Model):
    """Earned certificates"""
    __tablename__ = 'certificates'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    career_path_id = db.Column(db.Integer, db.ForeignKey('career_paths.id'), nullable=False)
    
    certificate_name = db.Column(db.String(255), nullable=False)
    certificate_name_ar = db.Column(db.String(255))
    
    verify_code = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    pdf_url = db.Column(db.String(500))
    recipient_name = db.Column(db.String(200))
    
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime)
    
    is_valid = db.Column(db.Boolean, default=True)
    revoked_at = db.Column(db.DateTime)
    revoked_reason = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'career_path_id'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'certificate_name': self.certificate_name,
            'certificate_name_ar': self.certificate_name_ar,
            'verify_code': self.verify_code,
            'recipient_name': self.recipient_name,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'is_valid': self.is_valid,
            'pdf_url': self.pdf_url
        }


class Achievement(db.Model):
    """Badge/achievement definitions"""
    __tablename__ = 'achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    name_ar = db.Column(db.String(100))
    description = db.Column(db.Text)
    description_ar = db.Column(db.Text)
    
    icon = db.Column(db.String(50))
    icon_color = db.Column(db.String(20))
    
    criteria_json = db.Column(db.Text)
    
    xp_reward = db.Column(db.Integer, default=50)
    points_reward = db.Column(db.Integer, default=100)
    
    rarity = db.Column(db.String(20), default='common')  # common, rare, epic, legendary
    
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_ar': self.name_ar,
            'description': self.description,
            'description_ar': self.description_ar,
            'icon': self.icon,
            'xp_reward': self.xp_reward,
            'points_reward': self.points_reward,
            'rarity': self.rarity
        }


class UserAchievement(db.Model):
    """Earned achievements"""
    __tablename__ = 'user_achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)
    
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'achievement_id'),)
    
    # Relationship to achievement
    achievement = db.relationship('Achievement', backref='user_achievements')


# ==================== HINT TRACKING MODELS ====================

class UnlockedHint(db.Model):
    """Track which hints users have unlocked (paid for)"""
    __tablename__ = 'unlocked_hints'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), nullable=False)
    hint_index = db.Column(db.Integer, default=0, nullable=False)
    
    points_spent = db.Column(db.Integer, default=5)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'lab_id', 'hint_index'),)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('unlocked_hints', lazy='dynamic'))
    lab = db.relationship('Lab', backref=db.backref('unlocked_hints', lazy='dynamic'))


# Add hints_json property to Lab model for easy access
def _get_lab_hints_json(self):
    """Get hints as JSON list"""
    import json
    try:
        return json.loads(self.hints) if self.hints else []
    except:
        return []

Lab.hints_json = property(_get_lab_hints_json)


# ==================== LEAGUE MODELS ====================

class League(db.Model):
    """League tiers for weekly competition"""
    __tablename__ = 'leagues'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    name_ar = db.Column(db.String(50))
    
    # Visual
    icon = db.Column(db.String(50), default='fa-medal')  # Font Awesome icon
    color = db.Column(db.String(20), default='#cd7f32')  # Hex color
    
    # Ordering
    order_index = db.Column(db.Integer, default=0, nullable=False)
    
    # Requirements
    min_weekly_xp = db.Column(db.Integer, default=0)  # Minimum XP to stay in league
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    participants = db.relationship('LeagueParticipation', backref='league', lazy='dynamic')
    users = db.relationship('User', backref='current_league', lazy='dynamic',
                           foreign_keys='User.current_league_id')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_ar': self.name_ar,
            'icon': self.icon,
            'color': self.color,
            'order_index': self.order_index,
            'min_weekly_xp': self.min_weekly_xp,
            'participant_count': self.participants.count()
        }


class LeagueParticipation(db.Model):
    """Track user participation in weekly leagues"""
    __tablename__ = 'league_participation'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    league_id = db.Column(db.Integer, db.ForeignKey('leagues.id'), nullable=False)
    
    # Week tracking
    week_start = db.Column(db.Date, nullable=False)  # ISO week start date (Monday)
    weekly_xp = db.Column(db.Integer, default=0, nullable=False)
    
    # Final results (set at week end)
    final_rank = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, promoted, demoted, stayed
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'week_start'),)
    
    # Relationship to user
    user = db.relationship('User', backref=db.backref('league_participations', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'league_id': self.league_id,
            'week_start': self.week_start.isoformat() if self.week_start else None,
            'weekly_xp': self.weekly_xp,
            'final_rank': self.final_rank,
            'status': self.status
        }


class Subscription(db.Model):
    """Subscription history for premium users"""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Subscription details
    tier = db.Column(db.String(20), nullable=False)  # monthly, annual
    amount = db.Column(db.Float, default=0.0)  # Price paid
    currency = db.Column(db.String(10), default='USD')
    
    # Dates
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    
    # Payment info (mock)
    payment_method = db.Column(db.String(50), default='mock_card')
    transaction_id = db.Column(db.String(100), nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to user
    user = db.relationship('User', backref=db.backref('subscriptions', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'tier': self.tier,
            'amount': self.amount,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active
        }


# Add total_points and labs_completed properties to User model
def _get_user_total_points(self):
    """Get total points (alias for xp_points for backward compatibility)"""
    return self.xp_points or 0

def _set_user_total_points(self, value):
    """Set total points"""
    self.xp_points = value

def _get_user_labs_completed(self):
    """Get count of labs completed"""
    return self.lab_submissions.filter_by(is_correct=True).count()

User.total_points = property(_get_user_total_points, _set_user_total_points)
User.labs_completed = property(_get_user_labs_completed)

# ==================== NEW SCHEMA V2 (Requested) ====================

class Course(db.Model):
    """v2: Organized Courses (e.g., Web Hacking 101)"""
    __tablename__ = 'courses_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    difficulty = db.Column(db.String(50), default='Beginner')  # Beginner, Advanced
    icon = db.Column(db.String(500))  # URL or path
    
    # Relationships
    units = db.relationship('Unit', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'difficulty': self.difficulty,
            'icon': self.icon,
            'units': [u.to_dict() for u in self.units]
        }

class Unit(db.Model):
    """v2: Units within a Course (e.g., SQL Injection)"""
    __tablename__ = 'units_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses_v2.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    order = db.Column(db.Integer, default=0)
    
    # Relationships
    lessons = db.relationship('Lesson', backref='unit', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'order': self.order,
            'lessons': [l.to_dict() for l in self.lessons]
        }

class Lesson(db.Model):
    """v2: Specific Lessons within a Unit"""
    __tablename__ = 'lessons_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('units_v2.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content_markdown = db.Column(db.Text)
    gif_url = db.Column(db.String(500))
    
    # Optional link to a Lab/Machine (using string ID or foreign key if LabMachine exists)
    # Using String ID for flexibility with existing Docker logic
    connected_lab_id = db.Column(db.String(100), nullable=True) 
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content_markdown': self.content_markdown,
            'gif_url': self.gif_url,
            'connected_lab_id': self.connected_lab_id
        }

class Challenge(db.Model):
    """v2: CTF Challenges (Practice Section)"""
    __tablename__ = 'challenges_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50))  # Web, Crypto, Pwn
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    flag_hash = db.Column(db.String(256))
    points = db.Column(db.Integer, default=0)
    files_url = db.Column(db.String(500))  # URL to downloadable assets
    
    # Metadata
    difficulty = db.Column(db.String(20), default='Medium')
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'title': self.title,
            'description': self.description,
            'points': self.points,
            'files_url': self.files_url,
            'difficulty': self.difficulty
        }
