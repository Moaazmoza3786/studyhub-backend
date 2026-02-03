"""
Flask Backend API for Study Hub Platform
Handles lab management, certificate generation, and API endpoints
"""

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import sqlite3
import os
import hashlib
import time
from datetime import datetime, timedelta
from lab_manager import LabManager
from certificate_generator import CertificateGenerator
from ai_manager import init_groq, get_groq_manager

app = Flask(__name__)
# Configuration
# Configuration for CORS
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

# Configuration
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'studyhub.db')
CERTIFICATES_DIR = os.path.join(os.path.dirname(__file__), 'certificates')
GROQ_API_KEY = "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"

# Initialize managers
lab_manager = LabManager()
cert_generator = CertificateGenerator(CERTIFICATES_DIR)
init_groq(GROQ_API_KEY)
groq_manager = get_groq_manager()

# Ensure directories exist
os.makedirs(CERTIFICATES_DIR, exist_ok=True)


def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if os.path.exists(DATABASE_PATH):
        return

    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    if os.path.exists(schema_path):
        conn = get_db()
        with open(schema_path, mode='r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
        print("Database initialized.")
    else:
        print(f"Warning: Schema file not found at {schema_path}")


# ==================== API ROUTES ====================

# ---------- AI Routes ----------

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """Generate AI response for Shadow OS Chat"""
    data = request.json
    response = groq_manager.generate_chat_response(
        persona=data.get('persona', 'System'),
        user_message=data.get('message', ''),
        history=data.get('history', [])
    )
    return jsonify({'success': True, 'response': response}) if response else jsonify({'success': False}), 500

@app.route('/api/ai/news', methods=['GET'])
def ai_news():
    """Generate daily AI news"""
    try:
        news = groq_manager.generate_news()
        return jsonify({'success': True, 'news': news}) if news else jsonify({'success': False, 'error': 'AI generation failed or timed out'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/report', methods=['POST'])
def ai_report():
    """Generate executive summary for reports"""
    try:
        data = request.json
        summary = groq_manager.generate_report(data.get('findings', []))
        return jsonify({'success': True, 'summary': summary}) if summary else jsonify({'success': False, 'error': 'AI generation failed or timed out'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/wiki', methods=['POST'])
def ai_wiki():
    """Generate wiki content"""
    try:
        data = request.json
        content = groq_manager.update_wiki(data.get('topic'))
        return jsonify({'success': True, 'content': content}) if content else jsonify({'success': False, 'error': 'AI generation failed or timed out'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/playbook', methods=['POST'])
def ai_playbook():
    """Generate a custom playbook"""
    try:
        data = request.json
        playbook = groq_manager.generate_playbook(data.get('topic'))
        if playbook:
            return jsonify({'success': True, 'playbook': playbook})
        return jsonify({'success': False, 'error': 'AI generation returned no content'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/search', methods=['POST'])
def ai_search():
    """AI-powered semantic search"""
    try:
        data = request.json
        results = groq_manager.semantic_search(data.get('query'), data.get('dataset', []))
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/analyze', methods=['POST'])
def ai_analyze():
    """Analyze code snippet"""
    try:
        data = request.json
        analysis = groq_manager.analyze_code(data.get('code'), data.get('language', 'python'))
        return jsonify({'success': True, 'analysis': analysis}) if analysis else jsonify({'success': False, 'error': 'AI generation failed or timed out'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/cards', methods=['POST'])
def ai_flashcards():
    """Generate SRS flashcards from snippet content"""
    try:
        data = request.json
        cards = groq_manager.generate_flashcards(data.get('title'), data.get('content'))
        return jsonify({'success': True, 'cards': cards}) if cards else jsonify({'success': False, 'error': 'AI generation failed or timed out'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/payloads', methods=['POST'])
def ai_payloads():
    """Generate specific payloads for a topic"""
    try:
        data = request.json
        payloads = groq_manager.generate_payloads(data.get('topic'))
        return jsonify({'success': True, 'payloads': payloads}) if payloads else jsonify({'success': False, 'error': 'AI generation failed or timed out'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/command', methods=['POST'])
def ai_command():
    """Generate a single command from natural language"""
    try:
        data = request.json
        cmd_data = groq_manager.generate_command(data.get('query'))
        return jsonify({'success': True, 'command': cmd_data}) if cmd_data else jsonify({'success': False, 'error': 'AI generation failed'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------- Lab Management ----------

@app.route('/api/lab/start', methods=['POST'])
def start_lab():
    """Start a Docker lab for a user"""
    data = request.json
    user_id = data.get('user_id')
    lab_id = data.get('lab_id')
    
    if not user_id or not lab_id:
        return jsonify({'success': False, 'error': 'Missing user_id or lab_id'}), 400
    
    # Get lab info from database
    conn = get_db()
    lab = conn.execute('SELECT * FROM labs WHERE id = ?', (lab_id,)).fetchone()
    conn.close()
    
    if not lab:
        return jsonify({'success': False, 'error': 'Lab not found'}), 404
    
    try:
        result = lab_manager.start_lab(
            user_id=user_id,
            lab_image=lab['docker_image'] or 'vulnerable-app:latest',
            lab_id=lab_id,
            timeout_minutes=lab['docker_timeout_minutes'] or 60
        )
        
        if result['success']:
            # Save session to database
            conn = get_db()
            conn.execute('''
                INSERT INTO lab_sessions (user_id, lab_id, container_id, container_ip, assigned_port, status, expires_at)
                VALUES (?, ?, ?, ?, ?, 'running', ?)
            ''', (user_id, lab_id, result['container_id'], result['ip'], result['port'], 
                  datetime.now() + timedelta(minutes=lab['docker_timeout_minutes'] or 60)))
            conn.commit()
            conn.close()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lab/stop', methods=['POST'])
def stop_lab():
    """Stop a running lab for a user"""
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'Missing user_id'}), 400
    
    try:
        result = lab_manager.stop_lab(user_id)
        
        if result:
            # Update session in database
            conn = get_db()
            conn.execute('''
                UPDATE lab_sessions SET status = 'stopped', stopped_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND status = 'running'
            ''', (user_id,))
            conn.commit()
            conn.close()
        
        return jsonify({'success': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/lab/status/<int:user_id>', methods=['GET'])
def get_lab_status(user_id):
    """Get current lab status for a user"""
    conn = get_db()
    session = conn.execute('''
        SELECT ls.*, l.name_en as lab_name 
        FROM lab_sessions ls
        JOIN labs l ON ls.lab_id = l.id
        WHERE ls.user_id = ? AND ls.status = 'running'
        ORDER BY ls.started_at DESC LIMIT 1
    ''', (user_id,)).fetchone()
    conn.close()
    
    if session:
        return jsonify({
            'running': True,
            'lab_name': session['lab_name'],
            'ip': session['container_ip'],
            'port': session['assigned_port'],
            'started_at': session['started_at'],
            'expires_at': session['expires_at']
        })
    
    return jsonify({'running': False})


# ---------- Flag Verification ----------

@app.route('/api/flag/check', methods=['POST'])
def check_flag():
    """Verify a submitted flag"""
    data = request.json
    user_id = data.get('user_id')
    lab_id = data.get('lab_id')
    submitted_flag = data.get('flag', '').strip()
    
    if not all([user_id, lab_id, submitted_flag]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    conn = get_db()
    lab = conn.execute('SELECT * FROM labs WHERE id = ?', (lab_id,)).fetchone()
    
    if not lab:
        conn.close()
        return jsonify({'success': False, 'error': 'Lab not found'}), 404
    
    is_correct = submitted_flag == lab['flag']
    points_earned = lab['points_reward'] if is_correct else 0
    
    if is_correct:
        # Update user progress
        conn.execute('''
            INSERT OR REPLACE INTO user_module_progress 
            (user_id, module_id, lab_completed, completed_at)
            VALUES (?, ?, TRUE, CURRENT_TIMESTAMP)
        ''', (user_id, lab['module_id']))
        
        # Add points to user
        conn.execute('''
            UPDATE users SET total_points = total_points + ? WHERE id = ?
        ''', (points_earned, user_id))
        
        conn.commit()
    
    conn.close()
    
    return jsonify({
        'success': True,
        'correct': is_correct,
        'points_earned': points_earned,
        'message': 'Congratulations! Flag is correct!' if is_correct else 'Incorrect flag. Try again!'
    })


# ---------- Certificate Generation ----------

@app.route('/api/certificate/generate', methods=['POST'])
def generate_certificate():
    """Generate a certificate for path completion"""
    data = request.json
    user_id = data.get('user_id')
    path_id = data.get('path_id')
    
    if not user_id or not path_id:
        return jsonify({'success': False, 'error': 'Missing user_id or path_id'}), 400
    
    conn = get_db()
    
    # Get user info
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Get path info
    path = conn.execute('SELECT * FROM paths WHERE id = ?', (path_id,)).fetchone()
    if not path:
        conn.close()
        return jsonify({'success': False, 'error': 'Path not found'}), 404
    
    # Check if user completed the path
    progress = conn.execute('''
        SELECT * FROM user_path_progress 
        WHERE user_id = ? AND path_id = ? AND status = 'completed'
    ''', (user_id, path_id)).fetchone()
    
    if not progress:
        conn.close()
        return jsonify({'success': False, 'error': 'Path not completed'}), 400
    
    # Generate unique certificate code
    cert_code = hashlib.sha256(f"{user_id}-{path_id}-{time.time()}".encode()).hexdigest()[:16].upper()
    
    try:
        # Generate certificate PDF
        cert_path = cert_generator.generate(
            student_name=user['display_name'] or user['username'],
            course_name=path['name_en'],
            course_name_ar=path['name_ar'],
            date=datetime.now().strftime('%Y-%m-%d'),
            certificate_code=cert_code,
            score=progress['average_quiz_score']
        )
        
        # Save certificate record
        conn.execute('''
            INSERT INTO certificates (user_id, path_id, certificate_code, certificate_title_en, 
                                      certificate_title_ar, final_score, pdf_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, path_id, cert_code, path['name_en'], path['name_ar'],
              progress['average_quiz_score'], cert_path))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'certificate_code': cert_code,
            'download_url': f'/api/certificate/download/{cert_code}'
        })
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/certificate/download/<cert_code>', methods=['GET'])
def download_certificate(cert_code):
    """Download a certificate PDF"""
    conn = get_db()
    cert = conn.execute('SELECT * FROM certificates WHERE certificate_code = ?', (cert_code,)).fetchone()
    conn.close()
    
    if not cert or not cert['pdf_path']:
        return jsonify({'error': 'Certificate not found'}), 404
    
    return send_file(cert['pdf_path'], as_attachment=True, download_name=f'certificate_{cert_code}.pdf')


@app.route('/api/certificate/verify/<cert_code>', methods=['GET'])
def verify_certificate(cert_code):
    """Verify a certificate is valid"""
    conn = get_db()
    cert = conn.execute('''
        SELECT c.*, u.display_name, u.username, p.name_en as path_name
        FROM certificates c
        JOIN users u ON c.user_id = u.id
        JOIN paths p ON c.path_id = p.id
        WHERE c.certificate_code = ?
    ''', (cert_code,)).fetchone()
    conn.close()
    
    if not cert:
        return jsonify({'valid': False, 'error': 'Certificate not found'})
    
    return jsonify({
        'valid': cert['is_valid'],
        'student_name': cert['display_name'] or cert['username'],
        'course_name': cert['path_name'],
        'issued_at': cert['issued_at'],
        'score': cert['final_score']
    })


# ---------- Progress Tracking ----------

@app.route('/api/progress/user/<int:user_id>', methods=['GET'])
def get_user_progress(user_id):
    """Get overall progress for a user"""
    conn = get_db()
    
    # Get path progress
    paths = conn.execute('''
        SELECT up.*, p.name_en, p.name_ar, p.icon, p.color
        FROM user_path_progress up
        JOIN paths p ON up.path_id = p.id
        WHERE up.user_id = ?
    ''', (user_id,)).fetchall()
    
    # Get user stats
    user = conn.execute('SELECT total_points, level, rank FROM users WHERE id = ?', (user_id,)).fetchone()
    
    conn.close()
    
    return jsonify({
        'user_stats': dict(user) if user else {},
        'paths': [dict(p) for p in paths]
    })


@app.route('/api/progress/update', methods=['POST'])
def update_progress():
    """Update user progress for a module"""
    data = request.json
    user_id = data.get('user_id')
    module_id = data.get('module_id')
    progress_type = data.get('type')  # 'content', 'quiz', 'lab'
    score = data.get('score')
    
    if not all([user_id, module_id, progress_type]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    conn = get_db()
    
    # Get or create progress record
    existing = conn.execute('''
        SELECT * FROM user_module_progress WHERE user_id = ? AND module_id = ?
    ''', (user_id, module_id)).fetchone()
    
    if existing:
        # Update existing
        if progress_type == 'content':
            conn.execute('UPDATE user_module_progress SET content_completed = TRUE WHERE id = ?', (existing['id'],))
        elif progress_type == 'quiz':
            conn.execute('''
                UPDATE user_module_progress SET quiz_completed = TRUE, quiz_score = ?, quiz_attempts = quiz_attempts + 1
                WHERE id = ?
            ''', (score, existing['id']))
        elif progress_type == 'lab':
            conn.execute('UPDATE user_module_progress SET lab_completed = TRUE, completed_at = CURRENT_TIMESTAMP WHERE id = ?', (existing['id'],))
    else:
        # Create new record
        conn.execute('''
            INSERT INTO user_module_progress (user_id, module_id, status, started_at)
            VALUES (?, ?, 'in_progress', CURRENT_TIMESTAMP)
        ''', (user_id, module_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})


# ---------- Smart Guidance ----------

@app.route('/api/guidance/check', methods=['POST'])
def check_guidance():
    """Check if user needs guidance and suggest resources"""
    data = request.json
    user_id = data.get('user_id')
    topic = data.get('topic')
    
    conn = get_db()
    
    # Get performance for this topic
    perf = conn.execute('''
        SELECT * FROM performance_tracking WHERE user_id = ? AND topic = ?
    ''', (user_id, topic)).fetchone()
    
    suggestions = []
    
    if perf:
        # If failed quiz twice, suggest supplementary content
        if perf['quiz_failures'] >= 2 or (perf['last_score'] and perf['last_score'] < 60):
            supplementary = conn.execute('''
                SELECT * FROM supplementary_content 
                WHERE topic = ? AND is_active = TRUE
            ''', (topic,)).fetchall()
            
            suggestions = [dict(s) for s in supplementary]
            
            # Update recommendation timestamp
            conn.execute('''
                UPDATE performance_tracking SET last_recommendation_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND topic = ?
            ''', (user_id, topic))
            conn.commit()
    
    conn.close()
    
    return jsonify({
        'needs_guidance': len(suggestions) > 0,
        'suggestions': suggestions,
        'message': 'نلاحظ أنك تواجه صعوبة في هذا المفهوم. إليك بعض الموارد الإضافية لمساعدتك!' if suggestions else None
    })


@app.route('/api/guidance/update-performance', methods=['POST'])
def update_performance():
    """Update performance tracking for smart guidance"""
    data = request.json
    user_id = data.get('user_id')
    topic = data.get('topic')
    score = data.get('score')
    is_failure = score < 60 if score else False
    
    conn = get_db()
    
    existing = conn.execute('''
        SELECT * FROM performance_tracking WHERE user_id = ? AND topic = ?
    ''', (user_id, topic)).fetchone()
    
    if existing:
        new_avg = ((existing['average_score'] or 0) * existing['quiz_attempts'] + score) / (existing['quiz_attempts'] + 1)
        conn.execute('''
            UPDATE performance_tracking 
            SET quiz_attempts = quiz_attempts + 1,
                quiz_failures = quiz_failures + ?,
                average_score = ?,
                last_score = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND topic = ?
        ''', (1 if is_failure else 0, new_avg, score, user_id, topic))
    else:
        conn.execute('''
            INSERT INTO performance_tracking (user_id, topic, quiz_attempts, quiz_failures, average_score, last_score)
            VALUES (?, ?, 1, ?, ?, ?)
        ''', (user_id, topic, 1 if is_failure else 0, score, score))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})


# ---------- Live Lab & Utilities ----------

@app.route('/api/tools/sanitize', methods=['POST'])
def sanitize_payload():
    """
    POST /api/tools/sanitize
    Test how different inputs are sanitized/processed.
    """
    data = request.json
    payload = data.get('payload', '')
    mode = data.get('mode', 'html') # html, sql, command

    result = {
        'original': payload,
        'mode': mode,
        'sanitized': '',
        'safe': True,
        'analysis': []
    }

    if mode == 'html':
        # Simulate HTML sanitization (basic mapping for demo)
        sanitized = payload.replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#x27;')
        result['sanitized'] = sanitized
        
        # Check for dangerous tags
        danger_tags = ['<script>', 'javascript:', 'onload=', 'onerror=']
        detected = [tag for tag in danger_tags if tag in payload.lower()]
        
        if detected:
            result['safe'] = False
            result['analysis'].append(f"Dangerous patterns detected: {', '.join(detected)}")
            result['analysis'].append("Input would be escaped by standard WAF/Frameworks.")
        else:
            result['analysis'].append("No obvious XSS vectors detected in raw input.")

    elif mode == 'sql':
        # Visualize SQL Injection
        # We don't actually santize SQL here usually (we use parameterized queries), 
        # but we can show what a "naïve" filter might do.
        
        # Simulate a basic blacklist filter
        blacklist = ['OR', 'AND', 'UNION', 'SELECT', 'DROP', '--', '#']
        
        sanitized = payload
        detected = []
        for word in blacklist:
            if word in payload.upper():
                detected.append(word)
                # Naive sanitization demo
                sanitized = sanitized.replace(word, '') 
                
        result['sanitized'] = sanitized
        
        if detected:
            result['safe'] = False
            result['analysis'].append(f"SQL Keywords detected: {', '.join(detected)}")
            result['analysis'].append("⚠️ Warning: Blacklisting is not a secure defense!")
        else:
            result['analysis'].append("Standard query structure seems safe (or uses parameterized queries).")

    elif mode == 'command':
        # Command Injection
        dangerous_chars = [';', '&&', '|', '`', '$', '(', ')']
        detected = [char for char in dangerous_chars if char in payload]
        
        if detected:
            result['safe'] = False
            result['analysis'].append(f"Shell operators detected: {' '.join(detected)}")
            result['analysis'].append("Input contains characters used for chaining commands.")
        else:
            result['sanitized'] = payload
            result['analysis'].append("No shell operators found.")

    return jsonify(result)


@app.route('/api/leagues/<int:league_id>/leaderboard', methods=['GET'])
def get_league_leaderboard(league_id):
    """Get leaderboard rankings for a specific league"""
    conn = get_db()
    
    # Get league info
    league = conn.execute('SELECT * FROM leagues WHERE id = ?', (league_id,)).fetchone()
    if not league:
        # Fallback if league 3 doesn't exist (mock it for now or return empty)
        league = {'id': league_id, 'name_en': 'Gold League', 'name_ar': 'الدوري الذهبي'}
    
    # Get rankings with user info
    rankings = conn.execute('''
        SELECT lr.*, u.username, u.avatar_url
        FROM league_rankings lr
        JOIN users u ON lr.user_id = u.id
        WHERE lr.league_id = ?
        ORDER BY lr.total_points DESC, lr.challenges_solved DESC
        LIMIT 100
    ''', (league_id,)).fetchall()
    
    result = []
    for i, row in enumerate(rankings):
        result.append({
            'rank': i + 1,
            'xp': row['total_points'],
            'user': {
                'username': row['username'],
                'avatar_url': row['avatar_url']
            }
        })
    
    conn.close()
    return jsonify({
        'success': True,
        'league': dict(league),
        'leaderboard': result
    })


@app.route('/api/leagues/current', methods=['GET'])
def get_current_user_league():
    """Get current logged-in user's league status"""
    # Simple mock for now since full auth is complex
    # In a real app, we'd use the JWT token to get user_id
    user_id = 1 # Assuming default user for demo
    
    conn = get_db()
    ranking = conn.execute('''
        SELECT lr.*, l.name_en as league_name
        FROM league_rankings lr
        JOIN leagues l ON lr.league_id = l.id
        WHERE lr.user_id = ? AND l.is_active = TRUE
        ORDER BY l.start_date DESC LIMIT 1
    ''', (user_id,)).fetchone()
    
    conn.close()
    
    if ranking:
        return jsonify({
            'success': True,
            'rank': ranking['rank_position'],
            'points': ranking['total_points'],
            'league_name': ranking['league_name']
        })
    
    return jsonify({'success': False, 'message': 'No active league found for user'}), 404


# ---------- Domains & Paths ----------

@app.route('/api/domains', methods=['GET'])
def get_domains():
    """Get all domains with their paths"""
    conn = get_db()
    
    domains = conn.execute('SELECT * FROM domains WHERE is_active = TRUE ORDER BY sort_order').fetchall()
    result = []
    
    for domain in domains:
        paths = conn.execute('''
            SELECT * FROM paths WHERE domain_id = ? AND is_active = TRUE ORDER BY sort_order
        ''', (domain['id'],)).fetchall()
        
        domain_dict = dict(domain)
        domain_dict['paths'] = [dict(p) for p in paths]
        result.append(domain_dict)
    
    conn.close()
    return jsonify(result)


@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Study Hub Neural API",
        "version": "6.0",
        "docs": "/api/health"
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "online",
        "message": "API is healthy and running."
    })

@app.route('/api/path/<path_code>', methods=['GET'])
def get_path_details(path_code):
    """Get path details with modules"""
    conn = get_db()
    
    path = conn.execute('SELECT * FROM paths WHERE code = ?', (path_code,)).fetchone()
    if not path:
        conn.close()
        return jsonify({'error': 'Path not found'}), 404
    
    modules = conn.execute('''
        SELECT * FROM modules WHERE path_id = ? AND is_active = TRUE ORDER BY sort_order
    ''', (path['id'],)).fetchall()
    
    path_dict = dict(path)
    path_dict['modules'] = [dict(m) for m in modules]
    
    conn.close()
    return jsonify(path_dict)



# ==================== DOCKER LABS INTEGRATION ====================

try:
    from docker_lab_manager import register_docker_lab_routes, get_docker_manager
    # Register the /api/labs/* routes (spawn, kill, status)
    manager = get_docker_manager()
    register_docker_lab_routes(app, manager)
    print("Docker Lab Routes Registered Successfully")
except ImportError as e:
    print(f"Warning: Could not import docker_lab_manager: {e}")
except Exception as e:
    print(f"Error registering docker lab routes: {e}")


if __name__ == '__main__':
    init_db()
    
    # SSL Context Configuration
    # SSL Context Configuration - DISABLED for Local Dev (Fixing Cert Errors)
    ssl_context = None
    # root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # cert_path = os.path.join(root_dir, 'localhost.pem')
    # key_path = os.path.join(root_dir, 'localhost-key.pem')
    
    # if os.path.exists(cert_path) and os.path.exists(key_path):
    #     print(f"🔒 SSL Enabled using: {os.path.basename(cert_path)}")
    #     ssl_context = (cert_path, key_path)
    # else:
    print("⚠️  Running in HTTP mode (SSL Verified Disabled).")
        
    print("Starting Study Hub API Server...")
    app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=None)
