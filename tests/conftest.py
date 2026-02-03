import pytest
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import create_app
from models import db, User, CareerPath, Module

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Use a temporary database for testing
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['JWT_SECRET'] = 'test-jwt-secret'
    
    app = create_app()
    app.config['TESTING'] = True
    
    # Create tables
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's CLI commands."""
    return app.test_cli_runner()

@pytest.fixture
def auth_header(client, app):
    """Create a user and return auth headers"""
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com',
            role='student',
            is_active=True
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        # Determine the correct module for generate_token based on imports
        from auth_routes import generate_token
        token = generate_token(user.id)
        
        return {
            'Authorization': f'Bearer {token}',
            'X-User-ID': str(user.id)
        }
