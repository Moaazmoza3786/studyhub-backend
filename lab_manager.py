"""
Docker Lab Manager for Study Hub
Manages Docker containers for hands-on labs
"""

import docker
import random
import time
from datetime import datetime, timedelta


class LabManager:
    """Manages Docker containers for lab environments"""
    
    def __init__(self):
        """Initialize Docker client"""
        try:
            self.client = docker.from_env()
            self.active_labs = {}  # user_id -> container info
            print("Docker client initialized successfully")
        except docker.errors.DockerException as e:
            print(f"Warning: Docker not available - {e}")
            self.client = None
    
    def start_lab(self, user_id: int, lab_image: str, lab_id: int, timeout_minutes: int = 60) -> dict:
        """
        Start a new Docker container for a user's lab session
        
        Args:
            user_id: The user's ID
            lab_image: Docker image name to run
            lab_id: The lab ID
            timeout_minutes: Auto-shutdown timeout
            
        Returns:
            dict with container info or error
        """
        # Check if user already has a running lab
        if user_id in self.active_labs:
            return {
                'success': False,
                'error': 'You already have an active lab. Please stop it first.',
                'existing_lab': self.active_labs[user_id]
            }
        
        # If Docker not available, return simulated response
        if not self.client:
            return self._simulate_lab_start(user_id, lab_id, timeout_minutes)
        
        try:
            # Generate random port in safe range
            host_port = random.randint(10000, 60000)
            
            # Create container with networking
            container = self.client.containers.run(
                image=lab_image,
                name=f"studyhub_lab_{user_id}_{lab_id}_{int(time.time())}",
                detach=True,
                remove=False,
                ports={'80/tcp': host_port},
                labels={
                    'studyhub': 'true',
                    'user_id': str(user_id),
                    'lab_id': str(lab_id)
                },
                mem_limit='512m',
                cpu_period=100000,
                cpu_quota=50000  # 50% CPU limit
            )
            
            # Wait for container to start
            time.sleep(2)
            container.reload()
            
            # Get container IP (for internal communication)
            networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
            container_ip = None
            for network in networks.values():
                container_ip = network.get('IPAddress')
                if container_ip:
                    break
            
            lab_info = {
                'success': True,
                'container_id': container.id[:12],
                'ip': container_ip or f'10.10.{random.randint(1,254)}.{random.randint(1,254)}',
                'port': host_port,
                'url': f'http://localhost:{host_port}',
                'started_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(minutes=timeout_minutes)).isoformat(),
                'timeout_minutes': timeout_minutes
            }
            
            self.active_labs[user_id] = {
                'container': container,
                **lab_info
            }
            
            return lab_info
            
        except docker.errors.ImageNotFound:
            return {
                'success': False,
                'error': f'Lab image "{lab_image}" not found. Please contact administrator.'
            }
        except docker.errors.APIError as e:
            return {
                'success': False,
                'error': f'Docker API error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to start lab: {str(e)}'
            }
    
    def _simulate_lab_start(self, user_id: int, lab_id: int, timeout_minutes: int = 60) -> dict:
        """Simulate lab start when Docker is not available (for development)"""
        simulated_ip = f'10.10.{random.randint(1, 254)}.{random.randint(1, 254)}'
        simulated_port = random.randint(10000, 60000)
        
        lab_info = {
            'success': True,
            'container_id': f'sim_{user_id}_{lab_id}_{int(time.time())}',
            'ip': simulated_ip,
            'port': simulated_port,
            'url': f'http://localhost:{simulated_port}',
            'started_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(minutes=timeout_minutes)).isoformat(),
            'timeout_minutes': timeout_minutes,
            'simulated': True
        }
        
        self.active_labs[user_id] = lab_info
        return lab_info
    
    def stop_lab(self, user_id: int) -> bool:
        """
        Stop and remove a user's lab container
        
        Args:
            user_id: The user's ID
            
        Returns:
            True if stopped successfully, False otherwise
        """
        if user_id not in self.active_labs:
            return False
        
        lab_info = self.active_labs[user_id]
        
        # If simulated, just remove from tracking
        if lab_info.get('simulated'):
            del self.active_labs[user_id]
            return True
        
        if not self.client:
            del self.active_labs[user_id]
            return True
        
        try:
            container = lab_info.get('container')
            if container:
                container.stop(timeout=5)
                container.remove(force=True)
            
            del self.active_labs[user_id]
            return True
            
        except Exception as e:
            print(f"Error stopping container: {e}")
            # Still remove from tracking
            del self.active_labs[user_id]
            return True
    
    def get_lab_status(self, user_id: int) -> dict:
        """
        Get the status of a user's lab
        
        Args:
            user_id: The user's ID
            
        Returns:
            dict with lab status or None if no active lab
        """
        if user_id not in self.active_labs:
            return {'running': False}
        
        lab_info = self.active_labs[user_id]
        
        # Check if container is still running (if not simulated)
        if not lab_info.get('simulated') and self.client:
            try:
                container = lab_info.get('container')
                if container:
                    container.reload()
                    if container.status != 'running':
                        del self.active_labs[user_id]
                        return {'running': False}
            except:
                del self.active_labs[user_id]
                return {'running': False}
        
        # Check if expired
        expires_at = datetime.fromisoformat(lab_info['expires_at'])
        if datetime.now() > expires_at:
            self.stop_lab(user_id)
            return {'running': False, 'expired': True}
        
        return {
            'running': True,
            'ip': lab_info['ip'],
            'port': lab_info['port'],
            'url': lab_info.get('url'),
            'started_at': lab_info['started_at'],
            'expires_at': lab_info['expires_at'],
            'time_remaining': str(expires_at - datetime.now()).split('.')[0]
        }
    
    def check_flag(self, user_id: int, submitted_flag: str, correct_flag: str) -> bool:
        """
        Check if a submitted flag is correct
        
        Args:
            user_id: The user's ID
            submitted_flag: The flag submitted by the user
            correct_flag: The correct flag from the database
            
        Returns:
            True if flag is correct, False otherwise
        """
        return submitted_flag.strip() == correct_flag.strip()
    
    def cleanup_expired_labs(self):
        """Clean up all expired lab sessions"""
        expired_users = []
        
        for user_id, lab_info in self.active_labs.items():
            expires_at = datetime.fromisoformat(lab_info['expires_at'])
            if datetime.now() > expires_at:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self.stop_lab(user_id)
        
        return len(expired_users)
    
    def get_active_labs_count(self) -> int:
        """Get count of active labs"""
        return len(self.active_labs)
    
    def list_all_active_labs(self) -> list:
        """List all active labs (admin function)"""
        return [
            {
                'user_id': user_id,
                'ip': info['ip'],
                'port': info['port'],
                'started_at': info['started_at'],
                'expires_at': info['expires_at']
            }
            for user_id, info in self.active_labs.items()
        ]


# Singleton instance
_lab_manager_instance = None


def get_lab_manager() -> LabManager:
    """Get singleton instance of LabManager"""
    global _lab_manager_instance
    if _lab_manager_instance is None:
        _lab_manager_instance = LabManager()
    return _lab_manager_instance
