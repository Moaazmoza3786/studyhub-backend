"""
Database Migration Script for Study Hub
Adds missing columns to existing database or recreates tables if needed
Run this script to sync the database with the ORM models
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'studyhub.db')

def get_connection():
    """Get database connection"""
    return sqlite3.connect(DB_PATH)

def column_exists(cursor, table, column):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns

def migrate_users_table(cursor):
    """Add missing columns to users table"""
    print("\n📋 Migrating users table...")
    
    migrations = [
        ("first_name", "VARCHAR(100)"),
        ("last_name", "VARCHAR(100)"),
        ("bio", "TEXT"),
        ("role", "VARCHAR(20) DEFAULT 'student'"),
        ("xp_points", "INTEGER DEFAULT 0"),
        ("current_rank", "VARCHAR(50) DEFAULT 'Script Kiddie'"),
        ("current_league_id", "INTEGER"),
        ("weekly_xp", "INTEGER DEFAULT 0"),
        ("subscription_tier", "VARCHAR(20) DEFAULT 'free'"),
        ("subscription_expires_at", "TIMESTAMP"),
        ("is_active", "BOOLEAN DEFAULT 1"),
        ("is_verified", "BOOLEAN DEFAULT 0"),
        ("verification_token", "VARCHAR(100)"),
    ]
    
    for column_name, column_type in migrations:
        if not column_exists(cursor, 'users', column_name):
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                print(f"  ✅ Added column: {column_name}")
            except sqlite3.OperationalError as e:
                print(f"  ⚠️ Could not add {column_name}: {e}")
        else:
            print(f"  ℹ️ Column already exists: {column_name}")

def create_leagues_table(cursor):
    """Create leagues table if it doesn't exist"""
    print("\n📋 Creating leagues table...")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leagues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) UNIQUE NOT NULL,
            name_ar VARCHAR(50),
            icon VARCHAR(50) DEFAULT 'fa-medal',
            color VARCHAR(20) DEFAULT '#cd7f32',
            order_index INTEGER DEFAULT 0,
            min_weekly_xp INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("  ✅ Leagues table ready")
    
    # Insert default leagues
    leagues = [
        ('Bronze', 'برونزي', 'fa-medal', '#cd7f32', 1, 0),
        ('Silver', 'فضي', 'fa-medal', '#c0c0c0', 2, 100),
        ('Gold', 'ذهبي', 'fa-medal', '#ffd700', 3, 300),
        ('Platinum', 'بلاتيني', 'fa-crown', '#e5e4e2', 4, 600),
        ('Diamond', 'ماسي', 'fa-gem', '#b9f2ff', 5, 1000),
    ]
    
    for name, name_ar, icon, color, order_idx, min_xp in leagues:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO leagues (name, name_ar, icon, color, order_index, min_weekly_xp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, name_ar, icon, color, order_idx, min_xp))
        except:
            pass
    print("  ✅ Default leagues inserted")

def create_league_participation_table(cursor):
    """Create league participation table"""
    print("\n📋 Creating league_participation table...")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS league_participation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            league_id INTEGER NOT NULL,
            week_start DATE NOT NULL,
            week_end DATE NOT NULL,
            weekly_xp INTEGER DEFAULT 0,
            rank_in_league INTEGER,
            promoted BOOLEAN DEFAULT 0,
            demoted BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, week_start),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (league_id) REFERENCES leagues(id) ON DELETE CASCADE
        )
    ''')
    print("  ✅ League participation table ready")

def run_migrations():
    """Run all migrations"""
    print("=" * 50)
    print("🔄 Study Hub Database Migration")
    print("=" * 50)
    
    if not os.path.exists(DB_PATH):
        print(f"\n⚠️ Database not found at: {DB_PATH}")
        print("   Run the Flask app first to create the database.")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("\n⚠️ Users table doesn't exist. Database needs to be initialized first.")
            conn.close()
            return False
        
        # Run migrations
        migrate_users_table(cursor)
        create_leagues_table(cursor)
        create_league_participation_table(cursor)
        
        conn.commit()
        print("\n" + "=" * 50)
        print("✅ All migrations completed successfully!")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def reset_database():
    """Delete and let Flask recreate the database"""
    print("\n⚠️ Resetting database...")
    
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"  ✅ Deleted: {DB_PATH}")
    else:
        print(f"  ℹ️ Database file not found")
    
    print("\n📝 Restart the Flask app to create a fresh database.")
    return True

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        reset_database()
    else:
        if not run_migrations():
            print("\n💡 Tip: Run with --reset to delete and recreate the database")
            print("   python migrate_db.py --reset")
