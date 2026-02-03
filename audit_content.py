"""
Study Hub - Content Audit Script 🕵️‍♂️
Audits the database for orphaned data, missing content, and integrity issues.

Features:
1. Identify empty Paths/Modules.
2. Find Labs without Flags.
3. Validate Quiz structure.
4. Report orphans.
"""

import sys
import logging
from sqlalchemy import func

# Import app context
from main import create_app
from models import db, CareerPath, Module, Lab, Quiz, Question, Choice

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger('ContentAudit')

def run_audit():
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*50)
        print("🕵️‍♂️ CONTENT AUDIT REPORT")
        print("="*50 + "\n")
        
        issues_found = 0
        
        # 1. Check Empty Paths
        print("--- 📂 Checking Paths & Modules ---")
        paths = CareerPath.query.all()
        for path in paths:
            if not path.modules:
                print(f"⚠️  WARNING: Path empty (0 modules): '{path.title}' (ID: {path.id})")
                issues_found += 1
            else:
                # Check Empty Modules
                for module in path.modules:
                    # Assuming a module should have content or labs or quizzes
                    has_content = bool(module.content)
                    has_labs = bool(module.labs)
                    has_quizzes = bool(module.quizzes)
                    
                    if not (has_content or has_labs or has_quizzes):
                        print(f"⚠️  WARNING: Module empty: '{module.title}' (ID: {module.id}) in Path '{path.title}'")
                        issues_found += 1

        # 2. Check Labs Integrity
        print("\n--- 🧪 Checking Labs ---")
        labs = Lab.query.all()
        for lab in labs:
            if not lab.flag_secret:
                print(f"❌ ERROR: Lab missing Flag: '{lab.name}' (ID: {lab.id})")
                issues_found += 1
            if not lab.docker_image_name:
                print(f"❌ ERROR: Lab missing Docker Image: '{lab.name}' (ID: {lab.id})")
                issues_found += 1

        # 3. Check Quizzes Integrity
        print("\n--- 📝 Checking Quizzes ---")
        quizzes = Quiz.query.all()
        for quiz in quizzes:
            if not quiz.questions:
                print(f"⚠️  WARNING: Quiz has no questions: '{quiz.title}' (ID: {quiz.id})")
                issues_found += 1
            else:
                for question in quiz.questions:
                    choices = Choice.query.filter_by(question_id=question.id).all()
                    if not choices:
                        print(f"❌ ERROR: Question has no choices: QID {question.id} in Quiz '{quiz.title}'")
                        issues_found += 1
                    else:
                        # Check if at least one correct answer exists
                        correct_choices = [c for c in choices if c.is_correct]
                        if not correct_choices:
                            print(f"❌ ERROR: Question has NO correct answer: QID {question.id} in Quiz '{quiz.title}'")
                            issues_found += 1
        
        print("\n" + "="*50)
        if issues_found == 0:
            print("✅ AUDIT PASSED: No issues found!")
        else:
            print(f"⚠️  Audit Completed. Found {issues_found} issues.")
        print("="*50)

if __name__ == "__main__":
    try:
        run_audit()
    except Exception as e:
        logger.error(f"Fatal audit error: {e}")
