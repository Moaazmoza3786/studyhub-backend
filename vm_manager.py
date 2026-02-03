"""
VM Manager for Study Hub Platform
Manages Docker container lifecycle for lab environments
"""

import uuid
import subprocess
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from models import db


class VMManager:
    """Manages virtual machine/container lifecycle"""
    
    # Store active instances (in production, use Redis)
    active_instances: Dict[str, Dict] = {}
    
    # Default timeout in minutes
    DEFAULT_TIMEOUT = 60
    MAX_TIMEOUT = 1440  # 24 hours
    
    # Machine states
    STATE_PENDING = 'pending'
    STATE_STARTING = 'starting'
    STATE_RUNNING = 'running'
    STATE_STOPPING = 'stopping'
    STATE_STOPPED = 'stopped'
    STATE_EXPIRED = 'expired'
    STATE_ERROR = 'error'
    
    def __init__(self):
        self.docker_available = self._check_docker()
    
    def _check_docker(self) -> bool:
        """Check if Docker is available"""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def spawn_instance(
        self,
        lab_id: str,
        user_id: int,
        docker_image: str = None,
        timeout_minutes: int = None
    ) -> Dict:
        """
        Spawn a new lab instance for a user
        
        Args:
            lab_id: Lab identifier
            user_id: User who requested the instance
            docker_image: Docker image to use
            timeout_minutes: Session timeout
        
        Returns:
            Dict with instance_id, ip_address, expiry_time, status
        """
        instance_id = f"{lab_id}-{user_id}-{uuid.uuid4().hex[:8]}"
        timeout = timeout_minutes or self.DEFAULT_TIMEOUT
        
        # Check for existing instance
        existing = self._get_user_instance(user_id, lab_id)
        if existing and existing['status'] == self.STATE_RUNNING:
            return {
                'success': True,
                'instance_id': existing['instance_id'],
                'ip_address': existing['ip_address'],
                'expiry_time': existing['expiry_time'].isoformat(),
                'time_remaining': self._get_time_remaining(existing['expiry_time']),
                'status': self.STATE_RUNNING,
                'message': 'Existing instance found'
            }
        
        # Calculate expiry
        expiry_time = datetime.utcnow() + timedelta(minutes=timeout)
        
        # In demo mode (no Docker), simulate an instance
        if not self.docker_available:
            ip_address = f"10.10.10.{(hash(instance_id) % 200) + 10}"
            
            instance = {
                'instance_id': instance_id,
                'lab_id': lab_id,
                'user_id': user_id,
                'ip_address': ip_address,
                'port': 80,
                'expiry_time': expiry_time,
                'status': self.STATE_RUNNING,
                'container_id': None,
                'created_at': datetime.utcnow(),
                'demo_mode': True
            }
            
            self.active_instances[instance_id] = instance
            
            return {
                'success': True,
                'instance_id': instance_id,
                'ip_address': ip_address,
                'port': 80,
                'expiry_time': expiry_time.isoformat(),
                'time_remaining': timeout * 60,  # seconds
                'status': self.STATE_RUNNING,
                'demo_mode': True,
                'message': 'Demo instance started (Docker not available)'
            }
        
        # Start Docker container
        try:
            image = docker_image or f"studyhub/labs:{lab_id}"
            container_name = f"studyhub-{instance_id}"
            
            # Run container
            result = subprocess.run([
                'docker', 'run', '-d',
                '--name', container_name,
                '--network', 'studyhub-labs',
                '--label', f'studyhub.instance={instance_id}',
                '--label', f'studyhub.user={user_id}',
                '--label', f'studyhub.lab={lab_id}',
                image
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': 'Failed to start container',
                    'details': result.stderr,
                    'status': self.STATE_ERROR
                }
            
            container_id = result.stdout.strip()
            
            # Get container IP
            ip_result = subprocess.run([
                'docker', 'inspect', '-f',
                '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}',
                container_id
            ], capture_output=True, text=True, timeout=10)
            
            ip_address = ip_result.stdout.strip() or f"10.10.10.{(hash(instance_id) % 200) + 10}"
            
            instance = {
                'instance_id': instance_id,
                'lab_id': lab_id,
                'user_id': user_id,
                'container_id': container_id,
                'container_name': container_name,
                'ip_address': ip_address,
                'expiry_time': expiry_time,
                'status': self.STATE_RUNNING,
                'created_at': datetime.utcnow(),
                'demo_mode': False
            }
            
            self.active_instances[instance_id] = instance
            
            return {
                'success': True,
                'instance_id': instance_id,
                'ip_address': ip_address,
                'expiry_time': expiry_time.isoformat(),
                'time_remaining': timeout * 60,
                'status': self.STATE_RUNNING,
                'message': 'Instance started successfully'
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Container startup timeout',
                'status': self.STATE_ERROR
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status': self.STATE_ERROR
            }
    
    def extend_instance(self, instance_id: str, extra_minutes: int = 60) -> Dict:
        """
        Extend an instance's expiry time
        
        Args:
            instance_id: Instance to extend
            extra_minutes: Minutes to add (default 60)
        
        Returns:
            Dict with new expiry time
        """
        instance = self.active_instances.get(instance_id)
        if not instance:
            return {
                'success': False,
                'error': 'Instance not found'
            }
        
        if instance['status'] != self.STATE_RUNNING:
            return {
                'success': False,
                'error': f"Cannot extend instance in state: {instance['status']}"
            }
        
        # Calculate new expiry
        new_expiry = instance['expiry_time'] + timedelta(minutes=extra_minutes)
        max_expiry = instance['created_at'] + timedelta(minutes=self.MAX_TIMEOUT)
        
        if new_expiry > max_expiry:
            new_expiry = max_expiry
        
        instance['expiry_time'] = new_expiry
        
        return {
            'success': True,
            'instance_id': instance_id,
            'expiry_time': new_expiry.isoformat(),
            'time_remaining': self._get_time_remaining(new_expiry),
            'message': f'Extended by {extra_minutes} minutes'
        }
    
    def terminate_instance(self, instance_id: str) -> Dict:
        """
        Terminate an instance immediately
        
        Args:
            instance_id: Instance to terminate
        
        Returns:
            Dict with termination status
        """
        instance = self.active_instances.get(instance_id)
        if not instance:
            return {
                'success': False,
                'error': 'Instance not found'
            }
        
        # Stop Docker container if running
        if instance.get('container_id') and not instance.get('demo_mode'):
            try:
                subprocess.run([
                    'docker', 'rm', '-f', instance['container_id']
                ], capture_output=True, timeout=30)
            except Exception:
                pass
        
        instance['status'] = self.STATE_STOPPED
        del self.active_instances[instance_id]
        
        return {
            'success': True,
            'instance_id': instance_id,
            'status': self.STATE_STOPPED,
            'message': 'Instance terminated'
        }
    
    def get_instance_status(self, instance_id: str) -> Dict:
        """Get current status of an instance"""
        instance = self.active_instances.get(instance_id)
        if not instance:
            return {
                'success': False,
                'error': 'Instance not found',
                'status': 'not_found'
            }
        
        # Check if expired
        if datetime.utcnow() > instance['expiry_time']:
            instance['status'] = self.STATE_EXPIRED
            return {
                'success': True,
                'instance_id': instance_id,
                'status': self.STATE_EXPIRED,
                'message': 'Instance has expired'
            }
        
        return {
            'success': True,
            'instance_id': instance_id,
            'ip_address': instance['ip_address'],
            'expiry_time': instance['expiry_time'].isoformat(),
            'time_remaining': self._get_time_remaining(instance['expiry_time']),
            'status': instance['status'],
            'demo_mode': instance.get('demo_mode', False)
        }
    
    def get_user_instances(self, user_id: int) -> List[Dict]:
        """Get all active instances for a user"""
        instances = []
        for instance_id, instance in self.active_instances.items():
            if instance['user_id'] == user_id:
                instances.append(self.get_instance_status(instance_id))
        return instances
    
    def _get_user_instance(self, user_id: int, lab_id: str) -> Optional[Dict]:
        """Get existing instance for user and lab"""
        for instance_id, instance in self.active_instances.items():
            if instance['user_id'] == user_id and instance['lab_id'] == lab_id:
                if instance['status'] == self.STATE_RUNNING:
                    if datetime.utcnow() <= instance['expiry_time']:
                        return instance
        return None
    
    def _get_time_remaining(self, expiry_time: datetime) -> int:
        """Get seconds remaining until expiry"""
        delta = expiry_time - datetime.utcnow()
        return max(0, int(delta.total_seconds()))
    
    def cleanup_expired(self):
        """Clean up expired instances"""
        expired = []
        for instance_id, instance in self.active_instances.items():
            if datetime.utcnow() > instance['expiry_time']:
                expired.append(instance_id)
        
        for instance_id in expired:
            self.terminate_instance(instance_id)
        
        return len(expired)


# Global VM manager instance
vm_manager = VMManager()


# ==================== FLASK API ROUTES ====================

def register_vm_routes(app):
    """Register VM management API routes"""
    from flask import request, jsonify
    
    @app.route('/api/vm/spawn', methods=['POST'])
    def spawn_vm():
        """Spawn a new lab instance"""
        data = request.get_json() or {}
        
        lab_id = data.get('lab_id')
        user_id = data.get('user_id')
        
        if not lab_id or not user_id:
            return jsonify({
                'success': False,
                'error': 'lab_id and user_id are required'
            }), 400
        
        result = vm_manager.spawn_instance(
            lab_id=lab_id,
            user_id=user_id,
            docker_image=data.get('docker_image'),
            timeout_minutes=data.get('timeout', 60)
        )
        
        return jsonify(result)
    
    @app.route('/api/vm/extend', methods=['POST'])
    def extend_vm():
        """Extend instance time"""
        data = request.get_json() or {}
        
        instance_id = data.get('instance_id')
        extra_minutes = data.get('minutes', 60)
        
        if not instance_id:
            return jsonify({
                'success': False,
                'error': 'instance_id is required'
            }), 400
        
        result = vm_manager.extend_instance(instance_id, extra_minutes)
        return jsonify(result)
    
    @app.route('/api/vm/terminate', methods=['POST'])
    def terminate_vm():
        """Terminate an instance"""
        data = request.get_json() or {}
        
        instance_id = data.get('instance_id')
        
        if not instance_id:
            return jsonify({
                'success': False,
                'error': 'instance_id is required'
            }), 400
        
        result = vm_manager.terminate_instance(instance_id)
        return jsonify(result)
    
    @app.route('/api/vm/status/<instance_id>', methods=['GET'])
    def vm_status(instance_id):
        """Get instance status"""
        result = vm_manager.get_instance_status(instance_id)
        return jsonify(result)
    
    @app.route('/api/vm/user/<int:user_id>', methods=['GET'])
    def user_vms(user_id):
        """Get all instances for a user"""
        instances = vm_manager.get_user_instances(user_id)
        return jsonify({'instances': instances})


if __name__ == '__main__':
    # Test VM Manager
    print("=== VM Manager Tests ===\n")
    
    manager = VMManager()
    print(f"Docker available: {manager.docker_available}")
    
    # Test spawn
    result = manager.spawn_instance('test-lab', 1)
    print(f"\nSpawn result: {result}")
    
    if result['success']:
        instance_id = result['instance_id']
        
        # Test status
        status = manager.get_instance_status(instance_id)
        print(f"\nStatus: {status}")
        
        # Test extend
        extend = manager.extend_instance(instance_id, 30)
        print(f"\nExtend: {extend}")
        
        # Test terminate
        terminate = manager.terminate_instance(instance_id)
        print(f"\nTerminate: {terminate}")
