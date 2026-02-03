"""
Flag Validator for Study Hub Platform
Validates submitted flags against stored hashes
"""

import hashlib
import re
import requests
from datetime import datetime
from typing import Optional, Tuple

from models import db, Lab, LabSubmission, User, UnlockedHint


class FlagValidator:
    """Validates CTF flags and manages submissions"""
    
    # Supported flag formats
    FLAG_PATTERNS = [
        r'^FLAG\{[A-Za-z0-9_]+\}$',           # FLAG{...}
        r'^flag\{[A-Za-z0-9_]+\}$',           # flag{...}
        r'^STUDYHUB\{[A-Za-z0-9_]+\}$',       # STUDYHUB{...}
        r'^CTF\{[A-Za-z0-9_]+\}$',            # CTF{...}
    ]
    
    def __init__(self):
        pass
    
    def hash_flag(self, flag: str) -> str:
        """Create SHA256 hash of flag"""
        return hashlib.sha256(flag.strip().encode()).hexdigest()
    
    def validate_format(self, flag: str) -> bool:
        """Check if flag matches expected format"""
        for pattern in self.FLAG_PATTERNS:
            if re.match(pattern, flag.strip()):
                return True
        return False
    
    def validate_flag(self, lab_id: int, submitted_flag: str, user_id: Optional[int] = None) -> Tuple[bool, str, dict]:
        """
        Validate a submitted flag against the stored hash
        
        Returns:
            Tuple of (is_correct, message, data)
        """
        # Get lab
        lab = Lab.query.get(lab_id)
        if not lab:
            return False, "Lab not found", {"error": "lab_not_found"}
        
        # Clean submitted flag
        submitted_flag = submitted_flag.strip()
        
        # Check format
        if not self.validate_format(submitted_flag) and not submitted_flag.lower().startswith('flag'):
            return False, "Invalid flag format. Expected: FLAG{...}", {"error": "invalid_format"}
        
        # Hash the submitted flag
        submitted_hash = self.hash_flag(submitted_flag)
        
        # Compare with stored hash
        if submitted_hash == lab.flag_hash:
            # Correct flag!
            result_data = {
                "correct": True,
                "lab_id": lab_id,
                "points_earned": lab.points or 0,
                "xp_earned": lab.xp_reward or 0
            }
            
            # If user is provided, record the submission
            if user_id:
                self._record_submission(user_id, lab, submitted_flag, True)
                result_data["user_updated"] = True
            
            return True, "🎉 Correct! Flag accepted!", result_data
        else:
            # Incorrect flag
            if user_id:
                self._record_submission(user_id, lab, submitted_flag, False)
            
            return False, "❌ Incorrect flag. Try again!", {"error": "wrong_flag"}
    
    def validate_task_answer(self, task_data: dict, submitted_answer: str, user_id: Optional[int] = None) -> Tuple[bool, str, dict]:
        """
        Validate an answer for a specific task
        
        Args:
            task_data: Task dictionary with answer info
            submitted_answer: User's submitted answer
            user_id: Optional user ID for tracking
        
        Returns:
            Tuple of (is_correct, message, data)
        """
        answer_type = task_data.get('answerType', 'text')
        correct_answer = task_data.get('answer', '')
        submitted_answer = submitted_answer.strip()
        
        is_correct = False
        
        if answer_type == 'flag':
            # Hash comparison for flags
            if self.hash_flag(submitted_answer) == self.hash_flag(correct_answer):
                is_correct = True
            # Also allow direct comparison for development
            elif submitted_answer.lower() == correct_answer.lower():
                is_correct = True
        elif answer_type == 'number':
            # Numeric comparison
            try:
                is_correct = int(submitted_answer) == int(correct_answer)
            except ValueError:
                is_correct = False
        else:
            # Text comparison (case-insensitive)
            is_correct = submitted_answer.lower() == correct_answer.lower()
        
        if is_correct:
            points = task_data.get('points', 50)
            return True, "✅ Correct answer!", {
                "correct": True,
                "points_earned": points,
                "task_id": task_data.get('id')
            }
        else:
            return False, "❌ Incorrect. Try again!", {"error": "wrong_answer"}
    
    def _record_submission(self, user_id: int, lab: Lab, submitted_flag: str, is_correct: bool):
        """Record a flag submission in the database"""
        try:
            # Check for existing correct submission
            existing = LabSubmission.query.filter_by(
                user_id=user_id,
                lab_id=lab.id,
                is_correct=True
            ).first()
            
            if existing:
                return  # Already solved, skip
            
            # Create submission record
            submission = LabSubmission(
                user_id=user_id,
                lab_id=lab.id,
                submitted_flag=submitted_flag if not is_correct else "[REDACTED]",
                is_correct=is_correct
            )
            db.session.add(submission)
            
            # If correct, award points
            if is_correct:
                user = User.query.get(user_id)
                if user:
                    user.xp_points = (user.xp_points or 0) + (lab.xp_reward or 0)
            
            db.session.commit()
            
            # Notify real-time server after successful commit
            if is_correct:
                user = User.query.get(user_id)
                if user:
                    self._notify_realtime_server(lab.id, user_id, lab.title, user.username)
        except Exception as e:
            db.session.rollback()
            print(f"Error recording submission: {e}")
            
    def _notify_realtime_server(self, lab_id: int, user_id: int, lab_title: str, username: str):
        """Notify the Node.js server for real-time updates"""
        try:
            # Note: Using localhost:3001 for the internal Node.js server
            # This would need to be the container name in a Docker network
            node_url = "http://localhost:3001/api/trigger-update"
            requests.post(node_url, json={
                "lab_id": lab_id,
                "user_id": user_id,
                "username": username,
                "lab_title": lab_title
            }, timeout=2)
        except Exception as e:
            print(f"Failed to notify real-time server: {e}")
    
    def get_user_submissions(self, user_id: int, lab_id: int = None) -> list:
        """Get user's submission history"""
        query = LabSubmission.query.filter_by(user_id=user_id)
        
        if lab_id:
            query = query.filter_by(lab_id=lab_id)
        
        return query.order_by(LabSubmission.submitted_at.desc()).all()
    
    def has_user_solved(self, user_id: int, lab_id: int) -> bool:
        """Check if user has already solved a lab"""
        return LabSubmission.query.filter_by(
            user_id=user_id,
            lab_id=lab_id,
            is_correct=True
        ).first() is not None


# Global validator instance
flag_validator = FlagValidator()


# Flask API endpoints for flag validation
def register_flag_routes(app):
    """Register flag validation routes with Flask app"""
    from flask import request, jsonify
    
    @app.route('/api/flag/submit', methods=['POST'])
    def submit_flag():
        """Submit a flag for validation"""
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
        
        lab_id = data.get('lab_id')
        flag = data.get('flag')
        user_id = data.get('user_id')
        
        if not lab_id or not flag:
            return jsonify({"success": False, "message": "lab_id and flag are required"}), 400
        
        is_correct, message, result_data = flag_validator.validate_flag(lab_id, flag, user_id)
        
        return jsonify({
            "success": is_correct,
            "message": message,
            **result_data
        })
    
    @app.route('/api/task/submit', methods=['POST'])
    def submit_task_answer():
        """Submit an answer for a task"""
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
        
        task_data = data.get('task')
        answer = data.get('answer')
        user_id = data.get('user_id')
        
        if not task_data or not answer:
            return jsonify({"success": False, "message": "task and answer are required"}), 400
        
        is_correct, message, result_data = flag_validator.validate_task_answer(task_data, answer, user_id)
        
        return jsonify({
            "success": is_correct,
            "message": message,
            **result_data
        })
    
    @app.route('/api/flag/check/<int:user_id>/<int:lab_id>', methods=['GET'])
    def check_solved_status(user_id, lab_id):
        """Check if user has solved a lab"""
        solved = flag_validator.has_user_solved(user_id, lab_id)
        return jsonify({
            "solved": solved,
            "user_id": user_id,
            "lab_id": lab_id
        })


if __name__ == '__main__':
    # Test flag validation
    validator = FlagValidator()
    
    # Test flag format
    print("Testing flag formats:")
    print(f"  FLAG{{test}}: {validator.validate_format('FLAG{test}')}")
    print(f"  flag{{test}}: {validator.validate_format('flag{test}')}")
    print(f"  invalid: {validator.validate_format('invalid')}")
    
    # Test hash
    print(f"\nHash of FLAG{{test}}: {validator.hash_flag('FLAG{test}')}")
