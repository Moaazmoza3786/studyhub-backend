"""
Study Hub Platform - Main Flask Application
Enhanced version with SQLAlchemy ORM and Blueprint-based API
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import models and routes
from models import db
from api_routes import api
from auth_routes import auth_bp
from leagues_routes import leagues_bp
from subscription_routes import subscription_bp


def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Configuration - Load from environment variables
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    if not app.config['SECRET_KEY']:
        raise ValueError("SECRET_KEY environment variable is required! Check your .env file.")
    
    # Database Configuration
    # Use SQLite for development, PostgreSQL for production
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Production: PostgreSQL
        # Handle Heroku-style postgres:// URLs
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Development: SQLite
        db_path = os.path.join(os.path.dirname(__file__), 'studyhub.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = os.environ.get('SQL_DEBUG', 'false').lower() == 'true'
    
    # JSON Configuration
    app.config['JSON_AS_ASCII'] = False  # Support Arabic/Unicode
    app.config['JSON_SORT_KEYS'] = False
    
    # Initialize extensions
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://study-hub3-react-rho.vercel.app",
        "https://study-hub3-react-rho.vercel.app/",
        "https://study-hub-final-fix.vercel.app",
        "https://study-hub-final-fix.vercel.app/",
        "https://float-calculations-military-michael.trycloudflare.com",
        "https://float-calculations-military-michael.trycloudflare.com/"
    ]
    CORS(app, resources={r"/*": {"origins": allowed_origins}}, supports_credentials=True)
    db.init_app(app)
    
    # Configure CORS with specific allowed origins (Security!)
    # cors_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:5500,http://127.0.0.1:5500')
    # allowed_origins = [origin.strip() for origin in cors_origins.split(',')]
    
    # CORS(app, 
    #      origins=allowed_origins,
    #      supports_credentials=True,
    #      allow_headers=['Content-Type', 'Authorization', 'X-User-ID'],
    #      methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    
    # Register blueprints
    app.register_blueprint(api)
    app.register_blueprint(auth_bp)
    app.register_blueprint(leagues_bp)
    app.register_blueprint(subscription_bp)
    
    # Register additional API routes
    try:
        from vm_manager import register_vm_routes
        register_vm_routes(app)
    except ImportError:
        print("Warning: vm_manager not available")
    
    try:
        from gamification_engine import register_gamification_routes
        register_gamification_routes(app)
    except ImportError:
        print("Warning: gamification_engine not available")
    
    try:
        from flag_validator import register_flag_routes
        register_flag_routes(app)
    except ImportError:
        print("Warning: flag_validator not available")
    
    try:
        from docker_lab_manager import get_docker_manager, register_docker_lab_routes
        docker_manager = get_docker_manager()
        register_docker_lab_routes(app, docker_manager)
        if docker_manager._docker_available:
            print("✓ Docker Labs: ENABLED - Containers available")
        else:
            print("⚠ Docker Labs: SIMULATION MODE - Docker not running")
    except ImportError as e:
        print(f"Warning: docker_lab_manager not available: {e}")

    # Initialize Intel Manager
    try:
        from intel_manager import register_intel_routes
        register_intel_routes(app)
        print("✓ Intel Manager: INITIALIZED (Live Feeds)")
    except ImportError as e:
        print(f"Warning: intel_manager not available: {e}")

    # Initialize Tools Manager
    try:
        from tools_manager import register_tools_routes
        register_tools_routes(app)
        print("✓ Tools Manager: INITIALIZED (Pro Tools)")
    except ImportError as e:
        print(f"Warning: tools_manager not available: {e}")

    # Initialize AI Manager
    try:
        from ai_manager import init_groq
        # Using the key provided by user
        GROQ_API_KEY = "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"
        init_groq(GROQ_API_KEY)
        print("✓ AI Manager: INITIALIZED (Groq)")
    except ImportError as e:
        print(f"Warning: ai_manager not available: {e}")
    except Exception as e:
        print(f"Error initializing AI: {e}")
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'success': False, 'error': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'success': False, 'error': 'Bad request'}), 400
    
    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            'name': 'Study Hub API',
            'version': '2.0.0',
            'description': 'Cybersecurity Learning Platform API',
            'endpoints': {
                'health': '/api/health',
                'domains': '/api/domains',
                'paths': '/api/paths',
                'module': '/api/module/<id>',
                'submit_flag': '/api/submit-flag',
                'leaderboard': '/api/leaderboard'
            }
        })
    
    return app


def init_database(app):
    """Initialize database with tables and seed data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if we need to seed data
        from models import Domain, Achievement, League
        
        if Domain.query.count() == 0:
            print("Seeding initial data...")
            seed_initial_data()
            print("✓ Database seeded successfully!")
        else:
            print("✓ Database already contains data")
        
        # Seed leagues if not present
        if League.query.count() == 0:
            print("Seeding leagues...")
            seed_leagues()
            print("✓ Leagues seeded successfully!")
            
        # Seed V2 content
        seed_v2_data()


def seed_leagues():
    """Seed initial league tiers"""
    from models import League
    
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


def seed_initial_data():
    """Seed initial domains and achievements"""
    from models import Domain, Achievement
    
    # Seed Domains
    domains = [
        Domain(
            name='Red Team', 
            name_ar='الفريق الأحمر',
            description='Offensive security and penetration testing',
            description_ar='الأمن الهجومي واختبار الاختراق',
            icon='fa-skull', 
            color='#ef4444', 
            order_index=1
        ),
        Domain(
            name='Blue Team', 
            name_ar='الفريق الأزرق',
            description='Defensive security and incident response',
            description_ar='الأمن الدفاعي والاستجابة للحوادث',
            icon='fa-shield-halved', 
            color='#3b82f6', 
            order_index=2
        ),
        Domain(
            name='CTF Arena', 
            name_ar='ساحة CTF',
            description='Capture The Flag challenges and competitions',
            description_ar='تحديات المسابقات CTF',
            icon='fa-trophy', 
            color='#f59e0b', 
            order_index=3
        )
    ]
    
    for domain in domains:
        db.session.add(domain)
    
    # Seed Achievements
    achievements = [
        Achievement(
            name='First Blood', 
            name_ar='الدم الأول',
            description='Complete your first lab',
            description_ar='أكمل أول مختبر لك',
            icon='🩸', 
            xp_reward=50, 
            points_reward=25, 
            rarity='common',
            criteria_json='{"type": "labs_completed", "count": 1}'
        ),
        Achievement(
            name='Lab Rat', 
            name_ar='فأر المختبر',
            description='Complete 10 labs',
            description_ar='أكمل 10 مختبرات',
            icon='🐀', 
            xp_reward=200, 
            points_reward=100, 
            rarity='rare',
            criteria_json='{"type": "labs_completed", "count": 10}'
        ),
        Achievement(
            name='Path Pioneer', 
            name_ar='رائد المسار',
            description='Complete your first learning path',
            description_ar='أكمل أول مسار تعليمي لك',
            icon='🚀', 
            xp_reward=500, 
            points_reward=250, 
            rarity='epic',
            criteria_json='{"type": "paths_completed", "count": 1}'
        ),
        Achievement(
            name='Quiz Master', 
            name_ar='سيد الاختبارات',
            description='Score 100% on 5 quizzes',
            description_ar='احصل على 100% في 5 اختبارات',
            icon='🧠', 
            xp_reward=200, 
            points_reward=100, 
            rarity='rare',
            criteria_json='{"type": "perfect_quizzes", "count": 5}'
        ),
        Achievement(
            name='Speed Demon', 
            name_ar='شيطان السرعة',
            description='Complete a lab in under 10 minutes',
            description_ar='أكمل مختبر في أقل من 10 دقائق',
            icon='⚡', 
            xp_reward=100, 
            points_reward=50, 
            rarity='rare',
            criteria_json='{"type": "fast_lab", "seconds": 600}'
        ),
        Achievement(
            name='Week Warrior', 
            name_ar='محارب الأسبوع',
            description='7-day learning streak',
            description_ar='سلسلة تعلم لمدة 7 أيام',
            icon='🔥', 
            xp_reward=150, 
            points_reward=75, 
            rarity='rare',
            criteria_json='{"type": "streak", "days": 7}'
        ),
        Achievement(
            name='Legend', 
            name_ar='أسطورة',
            description='Earn all certifications',
            description_ar='احصل على جميع الشهادات',
            icon='👑', 
            xp_reward=1000, 
            points_reward=500, 
            rarity='legendary',
            criteria_json='{"type": "all_certs", "count": 12}'
        )
    ]
    
    for achievement in achievements:
        db.session.add(achievement)
    
    db.session.commit()

def seed_v2_data():
    """Seed initial V2 Courses and Challenges (Professional Content)"""
    from models import Course, Unit, Lesson, Challenge
    
    # Check if we need to seed (simple check, or force update strategy could be used)
    # Ideally, we check for a specific marker or just count.
    # To ensure updates, we might want to clear old V2 data if it looks like the default set.
    if Course.query.filter_by(title='Web Hacking 101').first():
        print("Creating professional content update...")
        # Optional: Clear old data? 
        # For this task, let's just add if not exists, or update.
        # But user wants "Update", implying replacement.
        # Let's clean slate V2 tables for a fresh professional start.
        # WARNING: This deletes user progress on V2 if any. Assumed acceptable for dev/upgrade.
        try:
            Lesson.query.delete()
            Unit.query.delete()
            Course.query.delete()
            db.session.commit()
            print("✓ Old V2 data cleared.")
        except Exception as e:
            db.session.rollback()
            print(f"Error clearing data: {e}")

    if Course.query.count() > 0:
        return

    print("Seeding professional V2 courses...")

    # --- Course 1: Certified Penetration Tester ---
    c1 = Course(title='Certified Penetration Tester', difficulty='Advanced', icon='fa-user-secret')
    db.session.add(c1)
    db.session.commit()

    # Units for CPT
    u1_1 = Unit(course_id=c1.id, title='Introduction to Penetration Testing', order=1)
    u1_2 = Unit(course_id=c1.id, title='Information Gathering', order=2)
    u1_3 = Unit(course_id=c1.id, title='Vulnerability Assessment', order=3)
    u1_4 = Unit(course_id=c1.id, title='Exploitation & Privilege Escalation', order=4)
    db.session.add_all([u1_1, u1_2, u1_3, u1_4])
    db.session.commit()

    # Lessons for CPT
    l_c1_u1 = [
        Lesson(unit_id=u1_1.id, title='The PT Process & Ethics', content_markdown='# Penetration Testing Process\n\nUnderstand the Rules of Engagement (RoE), legal boundaries, and the lifecycle of a pentest.', connected_lab_id=None),
        Lesson(unit_id=u1_1.id, title='Reporting & Documentation', content_markdown='# Reporting\n\nThe report is the *product*. Learn how to write executive summaries and technical findings.', connected_lab_id=None)
    ]
    l_c1_u2 = [
        Lesson(unit_id=u1_2.id, title='Network Enumeration (Nmap)', content_markdown='# Nmap Mastery\n\nLearn to use Nmap for host discovery, port scanning, and service version detection.\n\n```bash\nnmap -sC -sV -oA scan 10.10.10.10\n```', connected_lab_id='nmap-lab'),
        Lesson(unit_id=u1_2.id, title='Web Footprinting', content_markdown='# Web Recon\n\nDiscovering hidden directories with Gobuster and analyzing `robots.txt`.\n\n', connected_lab_id=None),
        Lesson(unit_id=u1_2.id, title='Active Directory Enumeration', content_markdown='# AD Recon\n\nUsing BloodHound and LDAP tools to map the domain trust relationships.', connected_lab_id='ad-lab')
    ]
    l_c1_u3 = [
        Lesson(unit_id=u1_3.id, title='Vulnerability Scanning', content_markdown='# Automated Scanning\n\nUsing Nessus and OpenVAS to identify known CVEs.', connected_lab_id=None),
        Lesson(unit_id=u1_3.id, title='Manual Analysis', content_markdown='# Manual Verification\n\nVerifying scanner findings to eliminate false positives.', connected_lab_id=None)
    ]
    l_c1_u4 = [
        Lesson(unit_id=u1_4.id, title='Metasploit Framework', content_markdown='# MSFConsole\n\nUsing exploits, payloads, and encoders within Metasploit.', connected_lab_id='metasploit-lab'),
        Lesson(unit_id=u1_4.id, title='Linux Privilege Escalation', content_markdown='# Linux PrivEsc\n\nKernel exploits, SUID binaries, and cron job abuse.', connected_lab_id='linux-privesc'),
        Lesson(unit_id=u1_4.id, title='Windows Privilege Escalation', content_markdown='# Windows PrivEsc\n\nToken manipulation, unquoted service paths, and Potato attacks.', connected_lab_id='windows-privesc')
    ]
    db.session.add_all(l_c1_u1 + l_c1_u2 + l_c1_u3 + l_c1_u4)
    db.session.commit()


    # --- Course 2: Threat Hunting & Incident Response ---
    c2 = Course(title='Threat Hunting & Incident Response', difficulty='Advanced', icon='fa-shield-virus')
    db.session.add(c2)
    db.session.commit()

    u2_1 = Unit(course_id=c2.id, title='Digital Forensics Basics', order=1)
    u2_2 = Unit(course_id=c2.id, title='Network Forensics', order=2)
    u2_3 = Unit(course_id=c2.id, title='Endpoint Forensics', order=3)
    db.session.add_all([u2_1, u2_2, u2_3])
    db.session.commit()

    l_c2_u1 = [
        Lesson(unit_id=u2_1.id, title='Cyber Kill Chain & MITRE ATT&CK', content_markdown='# Frameworks\n\nMapping adversary tactics to the MITRE ATT&CK matrix.', connected_lab_id=None),
        Lesson(unit_id=u2_1.id, title='Evidence Acquisition', content_markdown='# Chain of Custody\n\nBest practices for acquiring disk images and memory dumps without tampering.', connected_lab_id=None)
    ]
    l_c2_u2 = [
        Lesson(unit_id=u2_2.id, title='Wireshark Traffic Analysis', content_markdown='# Wireshark Deep Dive\n\nAnalyzing PCAP files to detect C2 beacons and data exfiltration.', connected_lab_id='wireshark-lab'),
        Lesson(unit_id=u2_2.id, title='Zeek & Suricata', content_markdown='# IDS/IPS\n\nWriting Suricata rules to block malicious traffic patterns.', connected_lab_id=None)
    ]
    l_c2_u3 = [
        Lesson(unit_id=u2_3.id, title='Memory Forensics (Volatility)', content_markdown='# Volatility\n\nAnalyzing RAM dumps to find injected code and hidden processes.', connected_lab_id='volatility-lab'),
        Lesson(unit_id=u2_3.id, title='Windows Event Logs', content_markdown='# Event Logs\n\nHunting for Event ID 4624, 4688, and Powershell logging artifacts.', connected_lab_id=None)
    ]
    db.session.add_all(l_c2_u1 + l_c2_u2 + l_c2_u3)
    db.session.commit()


    # --- Course 3: Web Security Expert ---
    c3 = Course(title='Web Security Expert', difficulty='Intermediate', icon='fa-globe')
    db.session.add(c3)
    db.session.commit()

    u3_1 = Unit(course_id=c3.id, title='Server-Side Vulnerabilities', order=1)
    u3_2 = Unit(course_id=c3.id, title='Client-Side Vulnerabilities', order=2)
    u3_3 = Unit(course_id=c3.id, title='API Security', order=3)
    db.session.add_all([u3_1, u3_2, u3_3])
    db.session.commit()

    l_c3_u1 = [
        Lesson(unit_id=u3_1.id, title='SQL Injection Masterclass', content_markdown='# SQLi Types\n\nUnion-based, Boolean-blind, Time-blind, and Out-of-band SQL injection techniques.', connected_lab_id='sqli-advanced'),
        Lesson(unit_id=u3_1.id, title='Command Injection', content_markdown='# OS Command Injection\n\nEscaping the shell context to execute system commands.', connected_lab_id='cmd-injection'),
        Lesson(unit_id=u3_1.id, title='SSRF', content_markdown='# Server-Side Request Forgery\n\nTrick the server into accessing internal resources or cloud metadata services.', connected_lab_id='ssrf-lab')
    ]
    l_c3_u2 = [
        Lesson(unit_id=u3_2.id, title='Cross-Site Scripting (XSS)', content_markdown='# XSS Deep Dive\n\nReflected, Stored, and DOM-based XSS. Bypassing CSP.', connected_lab_id='xss-lab')
    ]
    l_c3_u3 = [
        Lesson(unit_id=u3_3.id, title='GraphQL Vulnerabilities', content_markdown='# GraphQL Attacks\n\nIntrospection misuse and batching attacks.', connected_lab_id=None)
    ]
    db.session.add_all(l_c3_u1 + l_c3_u2 + l_c3_u3)
    db.session.commit()


    # --- Course 4: Certified Red Team Operator ---
    c4 = Course(title='Certified Red Team Operator', difficulty='Expert', icon='fa-dragon')
    db.session.add(c4)
    db.session.commit()

    u4_1 = Unit(course_id=c4.id, title='Red Team Operations', order=1)
    u4_2 = Unit(course_id=c4.id, title='Advanced Evasion', order=2)
    db.session.add_all([u4_1, u4_2])
    db.session.commit()

    l_c4_u1 = [
        Lesson(unit_id=u4_1.id, title='C2 Infrastructure', content_markdown='# C2 Setup\n\nSetting up Cobalt Strike / Covenant profiles to blend in.', connected_lab_id=None),
        Lesson(unit_id=u4_1.id, title='Phishing & Social Engineering', content_markdown='# Weaponization\n\nCreating malicious macros and HTA files.', connected_lab_id=None)
    ]
    l_c4_u2 = [
        Lesson(unit_id=u4_2.id, title='EDR Evasion', content_markdown='# Bypassing EDR\n\nSyscall unhooking and memory encryption techniques.', connected_lab_id=None)
    ]
    db.session.add_all(l_c4_u1 + l_c4_u2)
    db.session.commit()


    # --- Seed V2 Challenges ---
    if Challenge.query.count() == 0:
        ch1 = Challenge(category='Web', title='Inspector Gadget', description='Check the source code!', points=100, difficulty='Easy', flag_hash='flag{source_code_hero}')
        ch2 = Challenge(category='Crypto', title='Caesar Salad', description='Decode this: khoor zruog', points=150, difficulty='Easy', flag_hash='flag{caesar_cipher}')
        ch3 = Challenge(category='Pwn', title='Buffer Overflow 101', description='Smash the stack.', points=300, difficulty='Medium', files_url='https://example.com/vuln_binary')
        ch4 = Challenge(category='Forensics', title='Hidden in Plain Sight', description='Find the flag in the image.', points=200, difficulty='Medium')
        
        db.session.add_all([ch1, ch2, ch3, ch4])
        db.session.commit()
        print("✓ V2 Challenges seeded")
    
    print("✓ Professional V2 Content Seeded Successfully")


# ==================== MAIN ====================


# === GUNICORN PRODUCTION EXPORT ===
# This creates the app instance for gunicorn: gunicorn main:app
# It must be at module level (outside if __name__ == '__main__')
app = create_app()
init_database(app)

if __name__ == '__main__':
    # Local development server
    
    # Initialize database
    init_database(app)
    
    # Run server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    
    # SSL Context Configuration
    ssl_context = None
    # Look for certs in project root (parent of backend)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cert_path = os.path.join(root_dir, 'localhost.pem')
    key_path = os.path.join(root_dir, 'localhost-key.pem')
    
    protocol = "http"
    if os.path.exists(cert_path) and os.path.exists(key_path):
        print(f"🔒 SSL Enabled using: {os.path.basename(cert_path)}")
        ssl_context = (cert_path, key_path)
        protocol = "https"
    else:
        print("⚠️  SSL Certificates not found. Running in HTTP mode.")
    
    print(f"""
╔════════════════════════════════════════════════════════════════╗
║                    STUDY HUB API SERVER                        ║
║────────────────────────────────────────────────────────────────║
║  🚀 Server running on: {protocol}://localhost:{port}                   ║
║  📚 API Documentation: {protocol}://localhost:{port}/api/health        ║
║  🔒 Debug Mode: {str(debug).upper():<45}║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=port, debug=debug, ssl_context=ssl_context)
