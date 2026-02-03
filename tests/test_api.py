import pytest
import json
from models import CareerPath, Lab

def test_login_invalid_password(client, auth_header):
    """Test that login fails with incorrect password"""
    response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'wrongpassword'
    })
    
    assert response.status_code == 401
    assert response.json['success'] is False
    assert 'Invalid credentials' in response.json['error']

def test_login_success(client, app):
    """Test successful login returns token"""
    # Create user first (handled in auth_header fixture but we need fresh one here or use existing)
    # Re-using logic from conftest would be cleaner, but let's test the flow directly
    with app.app_context():
        from models import User, db
        if not User.query.filter_by(email='login@test.com').first():
            u = User(username='loginuser', email='login@test.com', is_active=True)
            u.set_password('correctpassword')
            db.session.add(u)
            db.session.commit()

    response = client.post('/api/auth/login', json={
        'email': 'login@test.com',
        'password': 'correctpassword'
    })
    
    assert response.status_code == 200
    assert response.json['success'] is True
    assert 'token' in response.json
    assert 'user' in response.json

def test_get_paths(client, app):
    """Test fetching learning paths"""
    # Setup data
    with app.app_context():
        from models import db
        p = CareerPath(name='Test Path', slug='test-path', description='desc', is_published=True, domain_id=1)
        # Also need a dummy domain since it's a foreign key
        from models import Domain
        if not Domain.query.get(1):
            d = Domain(id=1, name='Test Domain')
            db.session.add(d)
        
        db.session.add(p)
        db.session.commit()

    response = client.get('/api/paths')
    
    assert response.status_code == 200
    data = response.json
    assert data['success'] is True
    assert len(data['paths']) >= 1
    assert data['paths'][0]['name'] == 'Test Path'

def test_start_lab_not_found(client, auth_header):
    """Test starting a non-existent lab returns 404"""
    user_id = auth_header['X-User-ID']
    
    response = client.post('/api/lab/start', 
        headers=auth_header,
        json={
            'user_id': user_id,
            'lab_id': 99999, # Non-existent ID
            'image_name': 'test/image'
        }
    )
    
    assert response.status_code == 404
    assert response.json['success'] is False
    assert 'not found' in response.json['error'].lower()
