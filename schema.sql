-- ============================================================
-- Cybersecurity Learning Platform (LMS & Cyber Range) Database Schema
-- Compatible with PostgreSQL and MySQL
-- Author: Senior Database Architect
-- Created: 2025-12-08
-- ============================================================

-- ============================================================
-- ENUM TYPES (PostgreSQL Style - Use VARCHAR for MySQL)
-- ============================================================

-- For PostgreSQL: Uncomment these ENUM types
-- CREATE TYPE user_role AS ENUM ('admin', 'student', 'content_creator');
-- CREATE TYPE module_type AS ENUM ('video', 'article', 'quiz_only', 'lab');
-- CREATE TYPE difficulty_level AS ENUM ('easy', 'medium', 'hard');

-- ============================================================
-- 1. USERS TABLE
-- ============================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    
    -- Profile Information
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    avatar_url VARCHAR(500),
    bio TEXT,
    
    -- Role & Permissions
    role VARCHAR(20) NOT NULL DEFAULT 'student' CHECK (role IN ('admin', 'student', 'content_creator')),
    
    -- Gamification & Progress
    xp_points INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    current_rank VARCHAR(50) DEFAULT 'Script Kiddie',
    streak_days INTEGER DEFAULT 0,
    last_active_date DATE,
    
    -- Account Status
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_xp_points ON users(xp_points DESC);

-- ============================================================
-- 2. DOMAINS TABLE (Major Categories)
-- ============================================================
CREATE TABLE domains (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    name_ar VARCHAR(100),
    description TEXT,
    description_ar TEXT,
    icon VARCHAR(50),
    color VARCHAR(20),
    order_index INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample Domains: Red Team, Blue Team, CTF Arena
CREATE INDEX idx_domains_order ON domains(order_index);

-- ============================================================
-- 3. CAREER_PATHS TABLE (Learning Paths)
-- ============================================================
CREATE TABLE career_paths (
    id SERIAL PRIMARY KEY,
    domain_id INTEGER NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    
    name VARCHAR(150) NOT NULL,
    name_ar VARCHAR(150),
    slug VARCHAR(100) NOT NULL UNIQUE,  -- URL-friendly identifier
    description TEXT,
    description_ar TEXT,
    
    -- Visual
    icon VARCHAR(50),
    color VARCHAR(20),
    thumbnail_url VARCHAR(500),
    
    -- Meta
    difficulty VARCHAR(20) DEFAULT 'beginner' CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    estimated_hours INTEGER DEFAULT 0,
    
    -- Certification
    certification_name VARCHAR(200),
    certification_description TEXT,
    
    -- Status
    is_published BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE,
    order_index INTEGER DEFAULT 0,
    
    -- Stats (denormalized for performance)
    total_modules INTEGER DEFAULT 0,
    total_labs INTEGER DEFAULT 0,
    enrolled_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Career Paths
CREATE INDEX idx_career_paths_domain ON career_paths(domain_id);
CREATE INDEX idx_career_paths_slug ON career_paths(slug);
CREATE INDEX idx_career_paths_difficulty ON career_paths(difficulty);
CREATE INDEX idx_career_paths_published ON career_paths(is_published);

-- ============================================================
-- 4. MODULES TABLE (Lessons within a Path)
-- ============================================================
CREATE TABLE modules (
    id SERIAL PRIMARY KEY,
    career_path_id INTEGER NOT NULL REFERENCES career_paths(id) ON DELETE CASCADE,
    
    name VARCHAR(200) NOT NULL,
    name_ar VARCHAR(200),
    slug VARCHAR(100) NOT NULL,
    description TEXT,
    description_ar TEXT,
    
    -- Content Type
    module_type VARCHAR(20) DEFAULT 'article' CHECK (module_type IN ('video', 'article', 'quiz_only', 'lab')),
    
    -- Ordering
    order_index INTEGER NOT NULL DEFAULT 0,
    
    -- Content
    content_html TEXT,           -- For article type
    content_html_ar TEXT,
    video_url VARCHAR(500),      -- For video type
    video_duration_minutes INTEGER,
    
    -- Learning Objectives (JSON array)
    objectives TEXT,             -- JSON: ["obj1", "obj2"]
    objectives_ar TEXT,
    
    -- Tools used (JSON array)
    tools TEXT,                  -- JSON: ["Nmap", "Burp Suite"]
    
    -- Meta
    estimated_minutes INTEGER DEFAULT 30,
    xp_reward INTEGER DEFAULT 50,
    
    -- Prerequisites (JSON array of module IDs)
    prerequisites TEXT,          -- JSON: [1, 2, 3]
    
    -- Status
    is_published BOOLEAN DEFAULT FALSE,
    is_free BOOLEAN DEFAULT FALSE,  -- For freemium model
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(career_path_id, slug)
);

-- Indexes for Modules
CREATE INDEX idx_modules_career_path ON modules(career_path_id);
CREATE INDEX idx_modules_order ON modules(career_path_id, order_index);
CREATE INDEX idx_modules_type ON modules(module_type);
CREATE INDEX idx_modules_published ON modules(is_published);

-- ============================================================
-- 5. LABS TABLE (Practical Exercises)
-- ============================================================
CREATE TABLE labs (
    id SERIAL PRIMARY KEY,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    
    title VARCHAR(200) NOT NULL,
    title_ar VARCHAR(200),
    description TEXT,
    description_ar TEXT,
    
    -- Docker Configuration
    docker_image_id VARCHAR(255) NOT NULL,  -- e.g., "vulnlab/sqli-basic:v1"
    docker_compose_yaml TEXT,               -- Optional: Full docker-compose config
    exposed_ports TEXT,                     -- JSON: [80, 443, 22]
    environment_vars TEXT,                  -- JSON: {"VAR1": "value1"}
    
    -- Challenge Configuration
    flag_hash VARCHAR(255) NOT NULL,        -- bcrypt/SHA256 hash of the flag
    flag_format VARCHAR(100) DEFAULT 'FLAG{...}',
    
    -- Difficulty & Rewards
    difficulty VARCHAR(20) DEFAULT 'easy' CHECK (difficulty IN ('easy', 'medium', 'hard', 'insane')),
    points INTEGER NOT NULL DEFAULT 100,
    xp_reward INTEGER DEFAULT 100,
    
    -- Time Limits
    time_limit_minutes INTEGER DEFAULT 60,
    instance_timeout_minutes INTEGER DEFAULT 120,  -- Auto-destroy after this
    
    -- Hints (JSON array)
    hints TEXT,                             -- JSON: [{"text": "hint1", "cost": 10}]
    hints_ar TEXT,
    
    -- Writeup (unlocked after solving)
    writeup_html TEXT,
    writeup_html_ar TEXT,
    
    -- Stats (denormalized)
    total_attempts INTEGER DEFAULT 0,
    total_solves INTEGER DEFAULT 0,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Labs
CREATE INDEX idx_labs_module ON labs(module_id);
CREATE INDEX idx_labs_difficulty ON labs(difficulty);
CREATE INDEX idx_labs_points ON labs(points DESC);
CREATE INDEX idx_labs_active ON labs(is_active);

-- ============================================================
-- 6. QUIZZES TABLE
-- ============================================================
CREATE TABLE quizzes (
    id SERIAL PRIMARY KEY,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    
    title VARCHAR(200) NOT NULL,
    title_ar VARCHAR(200),
    description TEXT,
    description_ar TEXT,
    
    -- Configuration
    passing_score INTEGER DEFAULT 70,       -- Percentage to pass
    time_limit_minutes INTEGER,             -- NULL = unlimited
    max_attempts INTEGER DEFAULT 3,         -- NULL = unlimited
    shuffle_questions BOOLEAN DEFAULT FALSE,
    shuffle_choices BOOLEAN DEFAULT FALSE,
    show_correct_answers BOOLEAN DEFAULT TRUE,  -- After submission
    
    -- Rewards
    xp_reward INTEGER DEFAULT 50,
    points INTEGER DEFAULT 50,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for Quizzes
CREATE INDEX idx_quizzes_module ON quizzes(module_id);

-- ============================================================
-- 7. QUESTIONS TABLE
-- ============================================================
CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    quiz_id INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    
    question_text TEXT NOT NULL,
    question_text_ar TEXT,
    
    -- Question Type
    question_type VARCHAR(30) DEFAULT 'multiple_choice' 
        CHECK (question_type IN ('multiple_choice', 'true_false', 'fill_blank', 'multi_select')),
    
    -- For code-related questions
    code_snippet TEXT,
    code_language VARCHAR(30),
    
    -- Image support
    image_url VARCHAR(500),
    
    -- Ordering
    order_index INTEGER DEFAULT 0,
    
    -- Explanation shown after answering
    explanation TEXT,
    explanation_ar TEXT,
    
    -- Points for this specific question
    points INTEGER DEFAULT 10,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for Questions
CREATE INDEX idx_questions_quiz ON questions(quiz_id);
CREATE INDEX idx_questions_order ON questions(quiz_id, order_index);

-- ============================================================
-- 8. CHOICES TABLE (Answer Options)
-- ============================================================
CREATE TABLE choices (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    
    choice_text TEXT NOT NULL,
    choice_text_ar TEXT,
    
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    order_index INTEGER DEFAULT 0,
    
    -- Optional explanation for this specific choice
    feedback TEXT,
    feedback_ar TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Choices
CREATE INDEX idx_choices_question ON choices(question_id);
CREATE INDEX idx_choices_correct ON choices(question_id, is_correct);

-- ============================================================
-- 9. USER_PROGRESS TABLE (Module/Path Progress Tracking)
-- ============================================================
CREATE TABLE user_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    
    -- Progress Status
    is_started BOOLEAN DEFAULT FALSE,
    is_completed BOOLEAN DEFAULT FALSE,
    progress_percentage INTEGER DEFAULT 0,  -- 0-100
    
    -- Timestamps
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Time spent (in seconds)
    time_spent_seconds INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, module_id)
);

-- Indexes for User Progress
CREATE INDEX idx_user_progress_user ON user_progress(user_id);
CREATE INDEX idx_user_progress_module ON user_progress(module_id);
CREATE INDEX idx_user_progress_completed ON user_progress(user_id, is_completed);

-- ============================================================
-- 10. LAB_SUBMISSIONS TABLE (Lab Attempt Tracking)
-- ============================================================
CREATE TABLE lab_submissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lab_id INTEGER NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
    
    -- Submission Details
    user_input_flag VARCHAR(500),
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Instance Information
    instance_id VARCHAR(100),               -- Docker container ID
    instance_ip VARCHAR(50),
    instance_started_at TIMESTAMP,
    instance_ended_at TIMESTAMP,
    
    -- Hints used (JSON array of hint indices)
    hints_used TEXT,                        -- JSON: [0, 1]
    hints_penalty INTEGER DEFAULT 0,        -- Points deducted for hints
    
    -- Points awarded (after penalties)
    points_awarded INTEGER DEFAULT 0,
    xp_awarded INTEGER DEFAULT 0,
    
    -- Time tracking
    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    time_to_solve_seconds INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Lab Submissions
CREATE INDEX idx_lab_submissions_user ON lab_submissions(user_id);
CREATE INDEX idx_lab_submissions_lab ON lab_submissions(lab_id);
CREATE INDEX idx_lab_submissions_correct ON lab_submissions(user_id, is_correct);
CREATE INDEX idx_lab_submissions_time ON lab_submissions(attempt_time DESC);

-- ============================================================
-- 11. QUIZ_ATTEMPTS TABLE (Quiz Attempt Tracking)
-- ============================================================
CREATE TABLE quiz_attempts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    quiz_id INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    
    -- Attempt Details
    score_percentage INTEGER NOT NULL DEFAULT 0,
    is_passed BOOLEAN DEFAULT FALSE,
    
    -- Points & Rewards
    points_awarded INTEGER DEFAULT 0,
    xp_awarded INTEGER DEFAULT 0,
    
    -- Time Tracking
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    time_spent_seconds INTEGER,
    
    -- Answers (JSON: {question_id: choice_id})
    answers_json TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Quiz Attempts
CREATE INDEX idx_quiz_attempts_user ON quiz_attempts(user_id);
CREATE INDEX idx_quiz_attempts_quiz ON quiz_attempts(quiz_id);
CREATE INDEX idx_quiz_attempts_passed ON quiz_attempts(user_id, is_passed);

-- ============================================================
-- 12. CERTIFICATES TABLE
-- ============================================================
CREATE TABLE certificates (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    career_path_id INTEGER NOT NULL REFERENCES career_paths(id) ON DELETE CASCADE,
    
    -- Certificate Details
    certificate_name VARCHAR(255) NOT NULL,
    certificate_name_ar VARCHAR(255),
    
    -- Verification
    verify_code UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),  -- PostgreSQL
    -- For MySQL: verify_code VARCHAR(36) NOT NULL UNIQUE
    
    -- PDF Storage
    pdf_url VARCHAR(500),
    
    -- Recipient Info (snapshot at time of issue)
    recipient_name VARCHAR(200),
    
    -- Dates
    issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expiry_date TIMESTAMP,  -- NULL = never expires
    
    -- Status
    is_valid BOOLEAN DEFAULT TRUE,
    revoked_at TIMESTAMP,
    revoked_reason TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, career_path_id)
);

-- Indexes for Certificates
CREATE INDEX idx_certificates_user ON certificates(user_id);
CREATE INDEX idx_certificates_path ON certificates(career_path_id);
CREATE INDEX idx_certificates_verify ON certificates(verify_code);
CREATE INDEX idx_certificates_valid ON certificates(is_valid);

-- ============================================================
-- 13. PATH_ENROLLMENTS TABLE (Track path subscriptions)
-- ============================================================
CREATE TABLE path_enrollments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    career_path_id INTEGER NOT NULL REFERENCES career_paths(id) ON DELETE CASCADE,
    
    -- Progress
    progress_percentage INTEGER DEFAULT 0,
    modules_completed INTEGER DEFAULT 0,
    
    -- Status
    is_completed BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    last_accessed_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, career_path_id)
);

-- Indexes for Path Enrollments
CREATE INDEX idx_path_enrollments_user ON path_enrollments(user_id);
CREATE INDEX idx_path_enrollments_path ON path_enrollments(career_path_id);
CREATE INDEX idx_path_enrollments_completed ON path_enrollments(is_completed);

-- ============================================================
-- 14. ACHIEVEMENTS TABLE (Badge/Achievement Definitions)
-- ============================================================
CREATE TABLE achievements (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    name_ar VARCHAR(100),
    description TEXT,
    description_ar TEXT,
    
    icon VARCHAR(50),
    icon_color VARCHAR(20),
    
    -- Requirements (JSON)
    criteria_json TEXT,  -- JSON: {"type": "labs_completed", "count": 10}
    
    -- Rewards
    xp_reward INTEGER DEFAULT 50,
    points_reward INTEGER DEFAULT 100,
    
    -- Rarity
    rarity VARCHAR(20) DEFAULT 'common' CHECK (rarity IN ('common', 'rare', 'epic', 'legendary')),
    
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 15. USER_ACHIEVEMENTS TABLE (Earned Achievements)
-- ============================================================
CREATE TABLE user_achievements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    achievement_id INTEGER NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
    
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, achievement_id)
);

-- Indexes for User Achievements
CREATE INDEX idx_user_achievements_user ON user_achievements(user_id);
CREATE INDEX idx_user_achievements_achievement ON user_achievements(achievement_id);

-- ============================================================
-- 16. LEADERBOARD VIEW (For Performance)
-- ============================================================
CREATE VIEW leaderboard AS
SELECT 
    u.id,
    u.username,
    u.avatar_url,
    u.xp_points,
    u.level,
    u.current_rank,
    (SELECT COUNT(*) FROM lab_submissions ls WHERE ls.user_id = u.id AND ls.is_correct = TRUE) as labs_solved,
    (SELECT COUNT(*) FROM certificates c WHERE c.user_id = u.id AND c.is_valid = TRUE) as certificates_earned,
    RANK() OVER (ORDER BY u.xp_points DESC) as global_rank
FROM users u
WHERE u.is_active = TRUE
ORDER BY u.xp_points DESC;

-- ============================================================
-- TRIGGERS FOR updated_at
-- ============================================================

-- PostgreSQL Trigger Function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_domains_updated_at BEFORE UPDATE ON domains FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_career_paths_updated_at BEFORE UPDATE ON career_paths FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_modules_updated_at BEFORE UPDATE ON modules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_labs_updated_at BEFORE UPDATE ON labs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_quizzes_updated_at BEFORE UPDATE ON quizzes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_questions_updated_at BEFORE UPDATE ON questions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_choices_updated_at BEFORE UPDATE ON choices FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_progress_updated_at BEFORE UPDATE ON user_progress FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_lab_submissions_updated_at BEFORE UPDATE ON lab_submissions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_quiz_attempts_updated_at BEFORE UPDATE ON quiz_attempts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_certificates_updated_at BEFORE UPDATE ON certificates FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_path_enrollments_updated_at BEFORE UPDATE ON path_enrollments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_achievements_updated_at BEFORE UPDATE ON achievements FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_achievements_updated_at BEFORE UPDATE ON user_achievements FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- SAMPLE DATA (Optional)
-- ============================================================

-- Insert Default Domains
INSERT INTO domains (name, name_ar, description, icon, color, order_index) VALUES
('Red Team', 'الفريق الأحمر', 'Offensive security and penetration testing', 'fa-skull', '#ef4444', 1),
('Blue Team', 'الفريق الأزرق', 'Defensive security and incident response', 'fa-shield-halved', '#3b82f6', 2),
('CTF Arena', 'ساحة CTF', 'Capture The Flag challenges and competitions', 'fa-trophy', '#f59e0b', 3);

-- Insert Default Achievements
INSERT INTO achievements (name, name_ar, description, icon, xp_reward, points_reward, rarity, criteria_json) VALUES
('First Blood', 'الدم الأول', 'Complete your first lab', '🩸', 50, 25, 'common', '{"type": "labs_completed", "count": 1}'),
('Lab Rat', 'فأر المختبر', 'Complete 10 labs', '🐀', 200, 100, 'rare', '{"type": "labs_completed", "count": 10}'),
('Path Pioneer', 'رائد المسار', 'Complete your first learning path', '🚀', 500, 250, 'epic', '{"type": "paths_completed", "count": 1}'),
('Quiz Master', 'سيد الاختبارات', 'Score 100% on 5 quizzes', '🧠', 200, 100, 'rare', '{"type": "perfect_quizzes", "count": 5}'),
('Speed Demon', 'شيطان السرعة', 'Complete a lab in under 10 minutes', '⚡', 100, 50, 'rare', '{"type": "fast_lab", "seconds": 600}'),
('Week Warrior', 'محارب الأسبوع', '7-day learning streak', '🔥', 150, 75, 'rare', '{"type": "streak", "days": 7}'),
('Legend', 'أسطورة', 'Earn all certifications', '👑', 1000, 500, 'legendary', '{"type": "all_certs", "count": 12}');

-- ============================================================
-- END OF SCHEMA
-- ============================================================
