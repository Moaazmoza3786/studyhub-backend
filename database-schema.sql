-- ==================== STUDY HUB DATABASE SCHEMA ====================
-- Professional Cybersecurity Learning Platform
-- Created: 2025-12-08

-- ========== CORE TABLES ==========

-- Users table - Student data, points, levels
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    avatar_url VARCHAR(500),
    
    -- Gamification
    total_points INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    rank VARCHAR(50) DEFAULT 'Newbie',
    streak_days INTEGER DEFAULT 0,
    last_active_date DATE,
    
    -- Preferences
    preferred_language VARCHAR(10) DEFAULT 'ar',
    theme VARCHAR(20) DEFAULT 'dark',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Domains table - Red Team, Blue Team
CREATE TABLE IF NOT EXISTS domains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(50) UNIQUE NOT NULL,  -- 'red-team', 'blue-team'
    name_en VARCHAR(100) NOT NULL,
    name_ar VARCHAR(100) NOT NULL,
    description_en TEXT,
    description_ar TEXT,
    icon VARCHAR(50),
    color VARCHAR(20),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Paths table - Career paths within domains
CREATE TABLE IF NOT EXISTS paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id INTEGER NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,  -- 'web-pentesting', 'network-hacking'
    name_en VARCHAR(150) NOT NULL,
    name_ar VARCHAR(150) NOT NULL,
    description_en TEXT,
    description_ar TEXT,
    icon VARCHAR(50),
    color VARCHAR(20),
    difficulty VARCHAR(20),  -- 'beginner', 'intermediate', 'advanced'
    estimated_hours INTEGER,
    total_modules INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    prerequisites TEXT,  -- JSON array of path codes
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES domains(id) ON DELETE CASCADE
);

-- Modules table - Learning units within paths
CREATE TABLE IF NOT EXISTS modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path_id INTEGER NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,
    name_en VARCHAR(200) NOT NULL,
    name_ar VARCHAR(200) NOT NULL,
    description_en TEXT,
    description_ar TEXT,
    
    -- Content
    content_type VARCHAR(50),  -- 'video', 'article', 'mixed'
    video_url VARCHAR(500),
    article_content TEXT,
    
    -- Learning objectives
    objectives TEXT,  -- JSON array
    
    -- Requirements
    estimated_minutes INTEGER,
    points_reward INTEGER DEFAULT 50,
    min_quiz_score INTEGER DEFAULT 80,  -- Minimum % to pass
    requires_lab_completion BOOLEAN DEFAULT FALSE,
    
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (path_id) REFERENCES paths(id) ON DELETE CASCADE
);

-- Labs table - Docker-based practical labs
CREATE TABLE IF NOT EXISTS labs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,
    name_en VARCHAR(200) NOT NULL,
    name_ar VARCHAR(200) NOT NULL,
    
    -- Scenario
    scenario_en TEXT,
    scenario_ar TEXT,
    concept_en TEXT,
    concept_ar TEXT,
    
    -- Docker configuration
    docker_image VARCHAR(200),
    docker_ports TEXT,  -- JSON: {"80": 8080, "22": 2222}
    docker_env TEXT,    -- JSON environment variables
    docker_timeout_minutes INTEGER DEFAULT 60,
    
    -- Challenge
    flag VARCHAR(200),
    flag_format VARCHAR(100) DEFAULT 'FLAG{...}',
    hints TEXT,  -- JSON array of hints
    
    -- Gamification
    points_reward INTEGER DEFAULT 100,
    difficulty VARCHAR(20),
    estimated_minutes INTEGER,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
);

-- Quizzes table - Quiz questions
CREATE TABLE IF NOT EXISTS quizzes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    question_en TEXT NOT NULL,
    question_ar TEXT NOT NULL,
    question_type VARCHAR(50) DEFAULT 'multiple_choice',  -- 'multiple_choice', 'true_false', 'text'
    
    -- Options (for multiple choice)
    options TEXT,  -- JSON array of options
    correct_answer TEXT NOT NULL,
    explanation_en TEXT,
    explanation_ar TEXT,
    
    points INTEGER DEFAULT 10,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
);

-- Certificates table - Issued certificates
CREATE TABLE IF NOT EXISTS certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    path_id INTEGER NOT NULL,
    
    -- Certificate details
    certificate_code VARCHAR(100) UNIQUE NOT NULL,
    certificate_title_en VARCHAR(200),
    certificate_title_ar VARCHAR(200),
    
    -- Scores
    final_score DECIMAL(5,2),
    quiz_average DECIMAL(5,2),
    labs_completed INTEGER,
    total_labs INTEGER,
    
    -- File
    pdf_path VARCHAR(500),
    qr_code_path VARCHAR(500),
    
    -- Verification
    verification_url VARCHAR(500),
    is_valid BOOLEAN DEFAULT TRUE,
    
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (path_id) REFERENCES paths(id) ON DELETE CASCADE
);

-- ========== PROGRESS TRACKING TABLES ==========

-- User progress per module
CREATE TABLE IF NOT EXISTS user_module_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    module_id INTEGER NOT NULL,
    
    -- Progress
    status VARCHAR(50) DEFAULT 'not_started',  -- 'not_started', 'in_progress', 'completed'
    content_completed BOOLEAN DEFAULT FALSE,
    quiz_completed BOOLEAN DEFAULT FALSE,
    quiz_score DECIMAL(5,2),
    quiz_attempts INTEGER DEFAULT 0,
    lab_completed BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, module_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
);

-- User progress per path
CREATE TABLE IF NOT EXISTS user_path_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    path_id INTEGER NOT NULL,
    
    -- Progress
    status VARCHAR(50) DEFAULT 'not_started',
    modules_completed INTEGER DEFAULT 0,
    total_modules INTEGER,
    progress_percentage DECIMAL(5,2) DEFAULT 0,
    
    -- Scores
    total_points_earned INTEGER DEFAULT 0,
    average_quiz_score DECIMAL(5,2),
    
    -- Timestamps
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    UNIQUE(user_id, path_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (path_id) REFERENCES paths(id) ON DELETE CASCADE
);

-- ========== CTF & COMPETITION TABLES ==========

-- CTF Challenges
CREATE TABLE IF NOT EXISTS ctf_challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category VARCHAR(50) NOT NULL,  -- 'web', 'crypto', 'pwn', 'forensics', 'misc'
    name_en VARCHAR(200) NOT NULL,
    name_ar VARCHAR(200) NOT NULL,
    description_en TEXT,
    description_ar TEXT,
    
    -- Challenge details
    flag VARCHAR(200) NOT NULL,
    points INTEGER DEFAULT 100,
    difficulty VARCHAR(20),
    
    -- Files & Resources
    files_url VARCHAR(500),
    challenge_url VARCHAR(500),
    docker_image VARCHAR(200),
    
    -- Stats
    solves_count INTEGER DEFAULT 0,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CTF Submissions
CREATE TABLE IF NOT EXISTS ctf_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    challenge_id INTEGER NOT NULL,
    
    submitted_flag VARCHAR(200),
    is_correct BOOLEAN,
    points_earned INTEGER DEFAULT 0,
    
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (challenge_id) REFERENCES ctf_challenges(id) ON DELETE CASCADE
);

-- Seasonal Leagues
CREATE TABLE IF NOT EXISTS leagues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_en VARCHAR(200) NOT NULL,
    name_ar VARCHAR(200) NOT NULL,
    
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- League Leaderboard
CREATE TABLE IF NOT EXISTS league_rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    
    total_points INTEGER DEFAULT 0,
    challenges_solved INTEGER DEFAULT 0,
    rank_position INTEGER,
    
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(league_id, user_id),
    FOREIGN KEY (league_id) REFERENCES leagues(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ========== SMART GUIDANCE TABLES ==========

-- Performance tracking for smart recommendations
CREATE TABLE IF NOT EXISTS performance_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    topic VARCHAR(100) NOT NULL,  -- 'sql_injection', 'xss', 'union_attacks'
    
    -- Performance metrics
    quiz_attempts INTEGER DEFAULT 0,
    quiz_failures INTEGER DEFAULT 0,
    average_score DECIMAL(5,2),
    last_score DECIMAL(5,2),
    
    -- Time spent
    total_time_minutes INTEGER DEFAULT 0,
    
    -- Recommendations
    suggested_resources TEXT,  -- JSON array of resource IDs
    last_recommendation_at TIMESTAMP,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, topic),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Supplementary content for weak areas
CREATE TABLE IF NOT EXISTS supplementary_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic VARCHAR(100) NOT NULL,
    content_type VARCHAR(50),  -- 'video', 'article', 'exercise'
    
    title_en VARCHAR(200) NOT NULL,
    title_ar VARCHAR(200) NOT NULL,
    description_en TEXT,
    description_ar TEXT,
    
    content_url VARCHAR(500),
    duration_minutes INTEGER,
    
    trigger_condition VARCHAR(50),  -- 'quiz_fail_2', 'score_below_60'
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========== LAB SESSIONS TABLE ==========

-- Active lab sessions (Docker containers)
CREATE TABLE IF NOT EXISTS lab_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    lab_id INTEGER NOT NULL,
    
    -- Container info
    container_id VARCHAR(100),
    container_ip VARCHAR(50),
    assigned_port INTEGER,
    
    -- Status
    status VARCHAR(50) DEFAULT 'starting',  -- 'starting', 'running', 'stopped', 'error'
    
    -- Timestamps
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    stopped_at TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE
);

-- ========== INITIAL DATA - DOMAINS ==========

INSERT OR IGNORE INTO domains (code, name_en, name_ar, description_en, description_ar, icon, color, sort_order) VALUES
('red-team', 'Red Team (Offensive)', 'الفريق الأحمر (الهجومي)', 
 'Offensive security, penetration testing, and ethical hacking', 
 'الأمن الهجومي واختبار الاختراق والاختراق الأخلاقي',
 'fa-crosshairs', '#ef4444', 1),
('blue-team', 'Blue Team (Defensive)', 'الفريق الأزرق (الدفاعي)',
 'Defensive security, forensics, SOC operations, and incident response',
 'الأمن الدفاعي والتحليل الجنائي وعمليات SOC والاستجابة للحوادث',
 'fa-shield-halved', '#3b82f6', 2);

-- ========== INITIAL DATA - PATHS ==========

-- Red Team Paths
INSERT OR IGNORE INTO paths (domain_id, code, name_en, name_ar, description_en, description_ar, icon, color, difficulty, estimated_hours, sort_order) VALUES
((SELECT id FROM domains WHERE code = 'red-team'), 'web-pentesting', 
 'Web Penetration Testing', 'اختبار اختراق الويب',
 'Master web application vulnerabilities from basics to advanced exploitation',
 'أتقن ثغرات تطبيقات الويب من الأساسيات إلى الاستغلال المتقدم',
 'fa-globe', '#667eea', 'intermediate', 40, 1),
 
((SELECT id FROM domains WHERE code = 'red-team'), 'network-hacking',
 'Network Hacking', 'اختراق الشبكات',
 'Learn network penetration testing, pivoting, and infrastructure attacks',
 'تعلم اختبار اختراق الشبكات والـ Pivoting وهجمات البنية التحتية',
 'fa-network-wired', '#f59e0b', 'intermediate', 50, 2),
 
((SELECT id FROM domains WHERE code = 'red-team'), 'exploit-dev',
 'Exploit Development', 'تطوير الثغرات',
 'Advanced binary exploitation, buffer overflows, and shellcoding',
 'استغلال متقدم للبرامج وثغرات Buffer Overflow وكتابة Shellcode',
 'fa-bug', '#ef4444', 'advanced', 80, 3),

((SELECT id FROM domains WHERE code = 'red-team'), 'mobile-hacking',
 'Mobile Application Hacking', 'اختراق تطبيقات الجوال',
 'Android and iOS security assessment and exploitation',
 'تقييم واستغلال أمان تطبيقات Android و iOS',
 'fa-mobile-screen', '#8b5cf6', 'intermediate', 45, 4);

-- Blue Team Paths
INSERT OR IGNORE INTO paths (domain_id, code, name_en, name_ar, description_en, description_ar, icon, color, difficulty, estimated_hours, sort_order) VALUES
((SELECT id FROM domains WHERE code = 'blue-team'), 'soc-analyst',
 'SOC Analyst', 'محلل SOC',
 'Security Operations Center analysis, monitoring, and incident response',
 'تحليل مركز عمليات الأمن والمراقبة والاستجابة للحوادث',
 'fa-eye', '#3b82f6', 'beginner', 35, 1),
 
((SELECT id FROM domains WHERE code = 'blue-team'), 'digital-forensics',
 'Digital Forensics', 'التحليل الجنائي الرقمي',
 'Computer and mobile forensics, evidence collection, and analysis',
 'التحليل الجنائي للحاسوب والجوال وجمع الأدلة وتحليلها',
 'fa-magnifying-glass', '#10b981', 'intermediate', 55, 2),
 
((SELECT id FROM domains WHERE code = 'blue-team'), 'malware-analysis',
 'Malware Analysis', 'تحليل البرمجيات الخبيثة',
 'Static and dynamic malware analysis, reverse engineering',
 'التحليل الثابت والديناميكي للبرمجيات الخبيثة والهندسة العكسية',
 'fa-virus', '#ec4899', 'advanced', 70, 3),

((SELECT id FROM domains WHERE code = 'blue-team'), 'threat-hunting',
 'Threat Hunting', 'صيد التهديدات',
 'Proactive threat detection, hunting methodologies, and intelligence',
 'الكشف الاستباقي عن التهديدات ومنهجيات الصيد والاستخبارات',
 'fa-crosshairs', '#f97316', 'advanced', 60, 4);

-- ========== INDEXES FOR PERFORMANCE ==========

CREATE INDEX IF NOT EXISTS idx_user_progress_user ON user_module_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_module ON user_module_progress(module_id);
CREATE INDEX IF NOT EXISTS idx_path_progress_user ON user_path_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_ctf_submissions_user ON ctf_submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_lab_sessions_user ON lab_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_performance_tracking_user ON performance_tracking(user_id);
