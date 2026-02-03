"""
Database Seeder for Study Hub Platform
Seeds the database with learning paths, rooms, tasks, and CTF challenges
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path

# Import models
from models import (
    db, Domain, CareerPath, Module, Lab, Quiz, Question, Choice, 
    Achievement, User
)


class DatabaseSeeder:
    """Seeds the database with initial content data"""
    
    def __init__(self, app=None):
        self.app = app
        self.seed_file = Path(__file__).parent / 'seed_data.json'
        
    def load_seed_data(self):
        """Load seed data from JSON file"""
        with open(self.seed_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def hash_flag(self, flag):
        """Create SHA256 hash of flag"""
        return hashlib.sha256(flag.encode()).hexdigest()
    
    def seed_domains(self):
        """Seed initial domains"""
        domains = [
            {
                'name': 'Red Team',
                'name_ar': 'الفريق الأحمر',
                'description': 'Offensive Security & Penetration Testing',
                'description_ar': 'الأمن الهجومي واختبار الاختراق',
                'icon': 'fa-skull-crossbones',
                'color': '#ef4444',
                'order_index': 1
            },
            {
                'name': 'Blue Team',
                'name_ar': 'الفريق الأزرق',
                'description': 'Defensive Security & Incident Response',
                'description_ar': 'الأمن الدفاعي والاستجابة للحوادث',
                'icon': 'fa-shield-halved',
                'color': '#3b82f6',
                'order_index': 2
            },
            {
                'name': 'CTF Arena',
                'name_ar': 'ساحة CTF',
                'description': 'Capture The Flag Challenges',
                'description_ar': 'تحديات الاختراق التنافسية',
                'icon': 'fa-flag',
                'color': '#f59e0b',
                'order_index': 3
            }
        ]
        
        for domain_data in domains:
            existing = Domain.query.filter_by(name=domain_data['name']).first()
            if not existing:
                domain = Domain(**domain_data)
                db.session.add(domain)
                print(f"✓ Created domain: {domain_data['name']}")
        
        db.session.commit()
        return Domain.query.all()
    
    def seed_paths(self, data):
        """Seed learning paths from seed data"""
        domains = {d.name: d for d in Domain.query.all()}
        red_team = domains.get('Red Team')
        
        for path_data in data.get('paths', []):
            existing = CareerPath.query.filter_by(slug=path_data['id']).first()
            if existing:
                print(f"  → Path already exists: {path_data['name']}")
                continue
            
            path = CareerPath(
                domain_id=red_team.id if red_team else 1,
                name=path_data['name'],
                name_ar=path_data.get('nameAr', ''),
                slug=path_data['id'],
                description=path_data.get('description', ''),
                description_ar=path_data.get('descriptionAr', ''),
                icon=path_data.get('icon', '🎯'),
                color=path_data.get('color', '#22c55e'),
                difficulty=path_data.get('difficulty', 'beginner'),
                estimated_hours=path_data.get('estimatedHours', 20),
                is_published=True,
                is_featured=True
            )
            db.session.add(path)
            print(f"✓ Created path: {path_data['name']}")
        
        db.session.commit()
    
    def seed_rooms_as_modules(self, data):
        """Seed rooms as modules with labs"""
        paths = {p.slug: p for p in CareerPath.query.all()}
        
        for room_data in data.get('rooms', []):
            path = paths.get(room_data.get('pathId'))
            if not path:
                print(f"  ✗ Path not found for room: {room_data['title']}")
                continue
            
            existing = Module.query.filter_by(slug=room_data['id']).first()
            if existing:
                print(f"  → Room already exists: {room_data['title']}")
                continue
            
            # Create module for the room
            module = Module(
                career_path_id=path.id,
                name=room_data['title'],
                name_ar=room_data.get('titleAr', ''),
                slug=room_data['id'],
                description=room_data.get('scenario', ''),
                description_ar=room_data.get('scenarioAr', ''),
                module_type='lab',
                order_index=len(path.modules.all()),
                estimated_minutes=room_data.get('estimatedMinutes', 45),
                xp_reward=room_data.get('points', 100),
                is_published=True
            )
            db.session.add(module)
            db.session.flush()  # Get module ID
            
            # Create lab for the room
            lab_config = room_data.get('labConfig', {})
            tasks = room_data.get('tasks', [])
            
            # Calculate total points
            total_points = sum(t.get('points', 50) for t in tasks)
            
            # Build hints JSON
            all_hints = []
            for task in tasks:
                for hint in task.get('hints', []):
                    all_hints.append(hint.get('text', ''))
            
            lab = Lab(
                module_id=module.id,
                title=room_data['title'],
                title_ar=room_data.get('titleAr', ''),
                description=room_data.get('scenario', ''),
                description_ar=room_data.get('scenarioAr', ''),
                docker_image_id=lab_config.get('image', 'studyhub/labs:default'),
                flag_hash=self.hash_flag(tasks[-1].get('answer', 'FLAG{DEFAULT}') if tasks else 'FLAG{DEFAULT}'),
                flag_format='FLAG{...}',
                difficulty=room_data.get('difficulty', 'easy'),
                points=total_points,
                xp_reward=room_data.get('points', 100),
                time_limit_minutes=lab_config.get('timeout', 60),
                instance_timeout_minutes=lab_config.get('timeout', 60) * 2,
                hints=json.dumps(all_hints),
                is_active=True
            )
            db.session.add(lab)
            print(f"✓ Created room/lab: {room_data['title']}")
        
        db.session.commit()
    
    def seed_achievements(self):
        """Seed achievement badges"""
        achievements = [
            {
                'name': 'First Blood',
                'name_ar': 'الدم الأول',
                'description': 'Complete your first lab',
                'description_ar': 'أكمل أول مختبر',
                'icon': '🩸',
                'xp_reward': 100,
                'points_reward': 50,
                'rarity': 'common'
            },
            {
                'name': 'Script Kiddie',
                'name_ar': 'سكريبت كيدي',
                'description': 'Complete 5 labs',
                'description_ar': 'أكمل 5 مختبرات',
                'icon': '👶',
                'xp_reward': 200,
                'points_reward': 100,
                'rarity': 'common'
            },
            {
                'name': 'SQL Ninja',
                'name_ar': 'نينجا SQL',
                'description': 'Master all SQL Injection labs',
                'description_ar': 'أتقن جميع مختبرات حقن SQL',
                'icon': '🥷',
                'xp_reward': 500,
                'points_reward': 250,
                'rarity': 'rare'
            },
            {
                'name': 'Root Access',
                'name_ar': 'صلاحيات الجذر',
                'description': 'Get root on 10 machines',
                'description_ar': 'احصل على صلاحيات root في 10 ماكينات',
                'icon': '👑',
                'xp_reward': 1000,
                'points_reward': 500,
                'rarity': 'epic'
            },
            {
                'name': 'Legend',
                'name_ar': 'أسطورة',
                'description': 'Complete all learning paths',
                'description_ar': 'أكمل جميع مسارات التعلم',
                'icon': '🏆',
                'xp_reward': 5000,
                'points_reward': 2500,
                'rarity': 'legendary'
            },
            {
                'name': 'Streak Master',
                'name_ar': 'سيد السلسلة',
                'description': 'Maintain a 30-day streak',
                'description_ar': 'حافظ على سلسلة 30 يوماً',
                'icon': '🔥',
                'xp_reward': 750,
                'points_reward': 300,
                'rarity': 'rare'
            },
            {
                'name': 'Bug Hunter',
                'name_ar': 'صائد الثغرات',
                'description': 'Find and report 5 bugs',
                'description_ar': 'اكتشف وأبلغ عن 5 ثغرات',
                'icon': '🐛',
                'xp_reward': 600,
                'points_reward': 300,
                'rarity': 'rare'
            }
        ]
        
        for ach_data in achievements:
            existing = Achievement.query.filter_by(name=ach_data['name']).first()
            if not existing:
                achievement = Achievement(**ach_data)
                db.session.add(achievement)
                print(f"✓ Created achievement: {ach_data['name']}")
        
        db.session.commit()
    
    def run(self):
        """Run all seeders"""
        print("\n🌱 Starting Database Seeder...\n")
        print("=" * 50)
        
        # Load seed data
        data = self.load_seed_data()
        print(f"✓ Loaded seed data from {self.seed_file}")
        print()
        
        # Seed domains
        print("📁 Seeding Domains...")
        self.seed_domains()
        print()
        
        # Seed paths
        print("🛤️ Seeding Learning Paths...")
        self.seed_paths(data)
        print()
        
        # Seed rooms/modules
        print("🏠 Seeding Rooms & Labs...")
        self.seed_rooms_as_modules(data)
        print()
        
        # Seed achievements
        print("🏆 Seeding Achievements...")
        self.seed_achievements()
        print()
        
        print("=" * 50)
        print("✅ Database seeding complete!\n")
        
        # Print summary
        print("📊 Summary:")
        print(f"   - Domains: {Domain.query.count()}")
        print(f"   - Paths: {CareerPath.query.count()}")
        print(f"   - Modules: {Module.query.count()}")
        print(f"   - Labs: {Lab.query.count()}")
        print(f"   - Achievements: {Achievement.query.count()}")


def seed_database(app):
    """Convenience function to seed database"""
    with app.app_context():
        seeder = DatabaseSeeder(app)
        seeder.run()


if __name__ == '__main__':
    # For running directly
    from main import create_app
    
    app = create_app()
    seed_database(app)
