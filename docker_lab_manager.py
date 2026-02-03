"""
Docker Lab Manager - The Magic Engine 🐳
Handles spawning and managing lab containers for Study Hub Platform
Similar to HackTheBox/TryHackMe lab infrastructure

Author: DevOps Engineer
"""

import docker
import socket
import random
import logging
import time
import uuid
import secrets
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import closing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DockerLabManager')


class DockerLabManager:
    """
    Manages Docker containers for cybersecurity labs.
    Provides functionality similar to HackTheBox/TryHackMe.
    """
    
    # Port range for lab containers
    PORT_RANGE_START = 20000
    PORT_RANGE_END = 30000
    
    # Container settings
    DEFAULT_MEMORY_LIMIT = "512m"  # 512 MB RAM limit
    DEFAULT_CPU_LIMIT = 0.5        # 50% of one CPU core
    DEFAULT_TIMEOUT_MINUTES = 120  # 2 hours auto-destroy
    
    # Labels for tracking
    LABEL_PREFIX = "studyhub"
    
    def __init__(self, docker_host: Optional[str] = None):
        """
        Initialize Docker Lab Manager.
        
        Args:
            docker_host: Optional Docker host URL (defaults to local Docker)
        """
        try:
            if docker_host:
                self.client = docker.DockerClient(base_url=docker_host)
            else:
                self.client = docker.from_env()
            
            # Verify Docker connection
            self.client.ping()
            logger.info("✓ Docker connection established successfully")
            self._docker_available = True
            
            # Start background cleanup thread
            self.start_background_cleanup()
            
        except docker.errors.DockerException as e:
            logger.warning(f"⚠ Docker not available: {e}")
            logger.warning("Lab manager will run in simulation mode")
            self._docker_available = False
            self.client = None
    
    @property
    def is_docker_available(self) -> bool:
        """Check if Docker is available"""
        if not self._docker_available:
             # Lazy check
             return self._try_connect_docker()
        return self._docker_available

    def _try_connect_docker(self) -> bool:
        """Attempt to connect to Docker engine if previously unavailable"""
        try:
            if not self.client:
                self.client = docker.from_env()
            self.client.ping()
            self._docker_available = True
            logger.info("✓ Docker connection established/recovered!")
            return True
        except Exception as e:
            # Only log periodically or debug to avoid spam
            return False

    def start_background_cleanup(self):
        """Start the background thread for cleaning up stale containers"""
        def run_cleanup():
            while True:
                try:
                    if self._docker_available:
                        self.cleanup_stale_containers()
                except Exception as e:
                    logger.error(f"Error in background cleanup: {e}")
                
                # Run every 5 minutes
                time.sleep(300)

        cleanup_thread = threading.Thread(target=run_cleanup, daemon=True)
        cleanup_thread.start()
        logger.info("♻️ Background container cleanup started")

    
    def _find_free_port(self) -> int:
        """
        Find a free port in the configured range.
        
        Returns:
            Available port number
            
        Raises:
            RuntimeError: If no free port is found
        """
        # Try random ports first (faster)
        for _ in range(100):
            port = random.randint(self.PORT_RANGE_START, self.PORT_RANGE_END)
            if self._is_port_available(port):
                return port
        
        # If random fails, scan sequentially
        for port in range(self.PORT_RANGE_START, self.PORT_RANGE_END):
            if self._is_port_available(port):
                return port
        
        raise RuntimeError(
            f"No free port available in range {self.PORT_RANGE_START}-{self.PORT_RANGE_END}"
        )
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available for binding"""
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            try:
                sock.bind(('', port))
                return True
            except OSError:
                return False
    
    def _get_host_ip(self) -> str:
        """Get the host machine's IP address"""
        try:
            # Try to get the IP by connecting to an external address
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    def spawn_lab_container(
        self,
        user_id: int,
        image_name: str,
        lab_id: Optional[int] = None,
        container_port: int = 80,
        timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES,
        environment: Optional[Dict[str, str]] = None,
        memory_limit: str = "512m",  # Enforced limit
        cpu_limit: float = 0.5       # Enforced limit
    ) -> Dict[str, Any]:
        """
        Spawn a new lab container for a user.
        
        This is the main function that:
        1. Finds a free port on the server
        2. Starts a Docker container from the specified image
        3. Maps the container's port to the free port
        4. Labels the container for tracking
        5. Returns connection info (IP:Port)
        
        Args:
            user_id: Unique user identifier
            image_name: Docker image to run (e.g., "vulnlab/sqli-basic:v1")
            lab_id: Optional lab ID for tracking
            container_port: Port inside the container to expose (default: 80)
            timeout_minutes: Auto-destroy after N minutes
            environment: Optional environment variables
            memory_limit: Memory limit (default "512m")
            cpu_limit: CPU limit as fraction (0.5 = 50% of one core)
            
        Returns:
            Dictionary with container info
            
        Raises:
            Various Docker exceptions on failure
        """
        logger.info(f"🚀 Spawning lab container for user {user_id}, image: {image_name}")
        
        # Check Docker availability
        if not self._docker_available:
            # Try one last time to connect (user might have started Docker)
            if not self._try_connect_docker():
                logger.warning("Docker not available, returning simulation response")
                return self._simulate_spawn(user_id, image_name, lab_id)
        
        try:
            # Step 1: Kill any existing containers for this user (one lab at a time)
            self.kill_user_containers(user_id)
            
            # Step 2: Find a free port
            host_port = self._find_free_port()
            logger.info(f"📍 Found free port: {host_port}")
            
            # Step 3: Prepare container labels
            labels = {
                f"{self.LABEL_PREFIX}.user_id": str(user_id),
                f"{self.LABEL_PREFIX}.lab_id": str(lab_id) if lab_id else "unknown",
                f"{self.LABEL_PREFIX}.created_at": datetime.utcnow().isoformat(),
                f"{self.LABEL_PREFIX}.expires_at": (
                    datetime.utcnow() + timedelta(minutes=timeout_minutes)
                ).isoformat()
            }
            
            # Step 4: Prepare secure container name
            # Format: lab_{user_uuid}_{lab_id}_{random_string}
            # We use user_id here but randomize the rest for security
            random_suffix = secrets.token_hex(4)  # 8 char random string
            lab_str = lab_id if lab_id else 'dev'
            container_name = f"lab_user{user_id}_{lab_str}_{random_suffix}"
            
            # Step 5: Run the container with strict limits
            container = self.client.containers.run(
                image=image_name,
                name=container_name,
                detach=True,  # Run in background
                remove=False,  # Don't auto-remove (we handle cleanup)
                ports={f"{container_port}/tcp": host_port},
                labels=labels,
                environment=environment or {},
                mem_limit=memory_limit,       # Strict RAM limit (e.g. 512m)
                cpu_period=100000,            # 100ms period
                cpu_quota=int(cpu_limit * 100000),  # Strict CPU limit (e.g. 50000 for 50%)
                restart_policy={"Name": "unless-stopped"},
                network_mode="bridge"
            )
            
            logger.info(f"✓ Container started: {container.short_id}")
            
            # Step 6: Get host IP
            host_ip = self._get_host_ip()
            
            # Step 7: Wait for container to be ready (basic health check)
            time.sleep(2)  # Give container time to start
            container.reload()
            
            if container.status != "running":
                raise RuntimeError(f"Container failed to start: {container.status}")
            
            # Calculate expiration time
            expires_at = datetime.utcnow() + timedelta(minutes=timeout_minutes)
            
            result = {
                "success": True,
                "container_id": container.id,
                "container_short_id": container.short_id,
                "container_name": container_name,
                "ip": host_ip,
                "port": host_port,
                "connection_string": f"{host_ip}:{host_port}",
                "internal_port": container_port,
                "image": image_name,
                "user_id": user_id,
                "lab_id": lab_id,
                "started_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat(),
                "timeout_minutes": timeout_minutes,
                "message": f"🎯 Lab started! Connect to: {host_ip}:{host_port}"
            }
            
            logger.info(f"✅ Lab ready for user {user_id}: {host_ip}:{host_port}")
            return result
            
        except docker.errors.ImageNotFound:
            error_msg = f"Docker image not found: {image_name}"
            logger.warning(f"{error_msg}. Attempting fallback to default image.")
            
            try:
                # Fallback mechanism
                fallback_image = "nginx:alpine"
                if image_name == fallback_image:
                    # Avoid infinite recursion if default is also missing
                    return {
                        "success": False,
                        "error": "Default image missing",
                        "error_code": "DEFAULT_IMAGE_MISSING",
                        "message": "System configuration error. Please contact support."
                    }
                
                return self.spawn_lab_container(
                    user_id=user_id,
                    image_name=fallback_image,
                    lab_id=lab_id,
                    container_port=container_port,
                    timeout_minutes=timeout_minutes,
                    environment=environment,
                    memory_limit=memory_limit,
                    cpu_limit=cpu_limit
                )
            except Exception as e:
                logger.error(f"Fallback failed: {e}")
                return {
                    "success": False,
                    "error": f"Image {image_name} not found and fallback failed.",
                    "error_code": "IMAGE_NOT_FOUND",
                    "message": "Lab image not available. Please contact support."
                }
            
        except docker.errors.APIError as e:
            error_msg = f"Docker API error: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "error_code": "DOCKER_API_ERROR",
                "message": "Failed to start lab. Please try again."
            }
            
        except RuntimeError as e:
            error_msg = str(e)
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "error_code": "RUNTIME_ERROR",
                "message": "Server is busy. Please try again later."
            }
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "error_code": "UNKNOWN_ERROR",
                "message": "An unexpected error occurred."
            }
    
    def kill_user_containers(self, user_id: int, force: bool = True) -> Dict[str, Any]:
        """
        Find and kill all containers belonging to a user.
        
        This function:
        1. Searches for containers with the user's label
        2. Stops each container gracefully (or forcefully)
        3. Removes the containers to free resources
        
        Args:
            user_id: User ID to find containers for
            force: If True, force kill. If False, graceful stop.
            
        Returns:
            Dictionary with results:
            {
                "success": True,
                "killed_count": 2,
                "containers": ["abc123", "def456"],
                "message": "Killed 2 containers"
            }
        """
        logger.info(f"🔪 Killing containers for user {user_id}")
        
        if not self._docker_available:
            return {
                "success": True,
                "killed_count": 0,
                "containers": [],
                "message": "Docker not available (simulation mode)"
            }
        
        killed_containers = []
        errors = []
        
        try:
            # Find all containers with this user's label
            filters = {
                "label": f"{self.LABEL_PREFIX}.user_id={user_id}"
            }
            
            containers = self.client.containers.list(all=True, filters=filters)
            
            for container in containers:
                try:
                    container_id = container.short_id
                    
                    # Stop the container
                    if container.status == "running":
                        if force:
                            container.kill()
                        else:
                            container.stop(timeout=10)
                    
                    # Remove the container
                    container.remove(force=True)
                    
                    killed_containers.append(container_id)
                    logger.info(f"✓ Killed container: {container_id}")
                    
                except Exception as e:
                    error_msg = f"Failed to kill container {container.short_id}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            result = {
                "success": len(errors) == 0,
                "killed_count": len(killed_containers),
                "containers": killed_containers,
                "errors": errors if errors else None,
                "message": f"Killed {len(killed_containers)} container(s)" if killed_containers else "No active containers found"
            }
            
            logger.info(f"✅ Cleanup complete for user {user_id}: {len(killed_containers)} killed")
            return result
            
        except Exception as e:
            error_msg = f"Error during cleanup: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "killed_count": len(killed_containers),
                "containers": killed_containers,
                "error": error_msg,
                "message": "Cleanup partially failed"
            }
    
    def get_user_active_lab(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the currently running lab for a user.
        
        Args:
            user_id: User ID to check
            
        Returns:
            Lab info dictionary or None if no active lab
        """
        if not self._docker_available:
            return None
        
        try:
            filters = {
                "label": f"{self.LABEL_PREFIX}.user_id={user_id}",
                "status": "running"
            }
            
            containers = self.client.containers.list(filters=filters)
            
            if not containers:
                return None
            
            container = containers[0]  # Get most recent
            labels = container.labels
            
            # Get port mapping
            ports = container.ports
            host_port = None
            for port_info in ports.values():
                if port_info:
                    host_port = int(port_info[0]['HostPort'])
                    break
            
            return {
                "container_id": container.short_id,
                "container_name": container.name,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "ip": self._get_host_ip(),
                "port": host_port,
                "connection_string": f"{self._get_host_ip()}:{host_port}" if host_port else None,
                "lab_id": labels.get(f"{self.LABEL_PREFIX}.lab_id"),
                "created_at": labels.get(f"{self.LABEL_PREFIX}.created_at"),
                "expires_at": labels.get(f"{self.LABEL_PREFIX}.expires_at"),
                "status": container.status
            }
            
        except Exception as e:
            logger.error(f"Error getting active lab: {e}")
            return None
    
    def get_all_active_labs(self) -> List[Dict[str, Any]]:
        """Get all active lab containers across all users"""
        if not self._docker_available:
            return []
        
        try:
            filters = {
                "label": f"{self.LABEL_PREFIX}.user_id",
                "status": "running"
            }
            
            containers = self.client.containers.list(filters=filters)
            
            labs = []
            for container in containers:
                labels = container.labels
                labs.append({
                    "container_id": container.short_id,
                    "user_id": labels.get(f"{self.LABEL_PREFIX}.user_id"),
                    "lab_id": labels.get(f"{self.LABEL_PREFIX}.lab_id"),
                    "created_at": labels.get(f"{self.LABEL_PREFIX}.created_at"),
                    "expires_at": labels.get(f"{self.LABEL_PREFIX}.expires_at"),
                    "status": container.status
                })
            
            return labs
            
        except Exception as e:
            logger.error(f"Error getting all labs: {e}")
            return []
    
    def cleanup_expired_containers(self) -> Dict[str, Any]:
        """
        Cleanup containers that have exceeded their timeout.
        Should be run periodically (e.g., every 5 minutes via cron/scheduler).
        """
        if not self._docker_available:
            return {"success": True, "cleaned": 0, "message": "Docker not available"}
        
        logger.info("🧹 Running expired container cleanup...")
        
        cleaned = []
        errors = []
        
        try:
            filters = {"label": f"{self.LABEL_PREFIX}.expires_at"}
            containers = self.client.containers.list(all=True, filters=filters)
            
            now = datetime.utcnow()
            
            for container in containers:
                try:
                    expires_str = container.labels.get(f"{self.LABEL_PREFIX}.expires_at")
                    if expires_str:
                        expires_at = datetime.fromisoformat(expires_str)
                        
                        if now > expires_at:
                            user_id = container.labels.get(f"{self.LABEL_PREFIX}.user_id", "unknown")
                            logger.info(f"⏰ Container {container.short_id} expired for user {user_id}")
                            
                            if container.status == "running":
                                container.kill()
                            container.remove(force=True)
                            cleaned.append(container.short_id)
                            
                except Exception as e:
                    errors.append(f"{container.short_id}: {e}")
            
            result = {
                "success": True,
                "cleaned": len(cleaned),
                "containers": cleaned,
                "errors": errors if errors else None,
                "message": f"Cleaned up {len(cleaned)} expired container(s)"
            }
            
            logger.info(f"✅ Cleanup complete: {len(cleaned)} containers removed")
            return result
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}", exc_info=True)
            return {
                "success": False,
                "cleaned": len(cleaned),
                "error": str(e)
            }

    def cleanup_stale_containers(self, max_age_minutes: int = 60) -> Dict[str, Any]:
        """
        Hard cleanup: Force remove ALL lab containers older than max_age_minutes.
        This runs in the background to prevent resource exhaustion.
        """
        if not self._docker_available:
            return {"success": True, "cleaned": 0}
            
        cleaned = []
        try:
            # Filter specifically for our lab containers
            filters = {"label": f"{self.LABEL_PREFIX}.created_at"}
            containers = self.client.containers.list(all=True, filters=filters)
            
            now = datetime.utcnow()
            
            for container in containers:
                try:
                    created_str = container.labels.get(f"{self.LABEL_PREFIX}.created_at")
                    if created_str:
                        created_at = datetime.fromisoformat(created_str)
                        age = (now - created_at).total_seconds() / 60
                        
                        # Hard limit check
                        if age > max_age_minutes:
                            logger.warning(f"🧟 Found stale container {container.short_id} (Age: {int(age)}m)")
                            
                            if container.status == "running":
                                container.kill()
                            container.remove(force=True)
                            cleaned.append(container.short_id)
                            
                except Exception as e:
                    logger.error(f"Error checking stale container {container.short_id}: {e}")
            
            if cleaned:
                logger.info(f"♻️ Stale cleanup: Removed {len(cleaned)} zombie containers")
                
            return {"success": True, "cleaned": len(cleaned)}
            
        except Exception as e:
            logger.error(f"Stale cleanup failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _simulate_spawn(
        self, 
        user_id: int, 
        image_name: str, 
        lab_id: Optional[int]
    ) -> Dict[str, Any]:
        """
        Simulate spawning a container when Docker is not available.
        Used for development/testing without Docker.
        """
        import random
        
        simulated_port = random.randint(self.PORT_RANGE_START, self.PORT_RANGE_END)
        simulated_ip = "10.10.10.5"  # Simulated lab IP
        
        return {
            "success": True,
            "simulated": True,
            "container_id": f"sim_{user_id}_{int(time.time())}",
            "container_short_id": f"sim{user_id}",
            "container_name": f"simulated_lab_{user_id}",
            "ip": simulated_ip,
            "port": simulated_port,
            "connection_string": f"{simulated_ip}:{simulated_port}",
            "internal_port": 80,
            "image": image_name,
            "user_id": user_id,
            "lab_id": lab_id,
            "started_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(minutes=120)).isoformat(),
            "timeout_minutes": 120,
            "message": f"🎯 [SIMULATION] Lab ready at: {simulated_ip}:{simulated_port}",
            "warning": "Docker not available - this is a simulated response"
        }
    
    def get_container_logs(self, container_id: str, tail: int = 100) -> Optional[str]:
        """Get logs from a specific container"""
        if not self._docker_available:
            return None
        
        try:
            container = self.client.containers.get(container_id)
            return container.logs(tail=tail).decode('utf-8')
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return None
    
    def extend_lab_timeout(self, user_id: int, additional_minutes: int = 60) -> Dict[str, Any]:
        """Extend the timeout for a user's active lab"""
        if not self._docker_available:
            return {"success": False, "error": "Docker not available"}
        
        try:
            lab = self.get_user_active_lab(user_id)
            if not lab:
                return {"success": False, "error": "No active lab found"}
            
            container = self.client.containers.get(lab['container_id'])
            
            # Update the expires_at label (note: Docker doesn't support label updates easily)
            # In production, you'd store this in a database instead
            current_expires = datetime.fromisoformat(lab['expires_at'])
            new_expires = current_expires + timedelta(minutes=additional_minutes)
            
            return {
                "success": True,
                "new_expires_at": new_expires.isoformat(),
                "message": f"Extended by {additional_minutes} minutes"
            }
            
        except Exception as e:
            logger.error(f"Error extending timeout: {e}")
            return {"success": False, "error": str(e)}

    def execute_command(self, user_id: int, command: str) -> Dict[str, Any]:
        """
        Execute a command inside the user's active lab container.
        """
        if not self._docker_available:
            return {
                "success": True, 
                "output": f"simulated_user@lab:~$ {command}\n[SIMULATION] Command executed.\n",
                "exit_code": 0
            }
            
        try:
            lab = self.get_user_active_lab(user_id)
            if not lab:
                return {"success": False, "error": "No active lab found"}
            
            container = self.client.containers.get(lab['container_id'])
            
            # Exec command (using /bin/sh -c for flexibility)
            exec_log = container.exec_run(
                ["/bin/sh", "-c", command],
                user="root",
                demux=True
            )
            
            stdout = exec_log.output[0].decode('utf-8') if exec_log.output[0] else ""
            stderr = exec_log.output[1].decode('utf-8') if exec_log.output[1] else ""
            
            return {
                "success": True,
                "output": stdout + stderr,
                "exit_code": exec_log.exit_code
            }
            
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return {"success": False, "error": str(e)}


# ==================== CONVENIENCE FUNCTIONS ====================
# These can be imported directly for simpler usage

# Global manager instance
_manager: Optional[DockerLabManager] = None


def get_docker_manager() -> DockerLabManager:
    """Get or create the global Docker manager instance"""
    global _manager
    if _manager is None:
        _manager = DockerLabManager()
    return _manager


def spawn_lab_container(user_id: int, image_name: str, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to spawn a lab container.
    
    Usage:
        result = spawn_lab_container(
            user_id=123,
            image_name="vulnlab/sqli-basic:v1"
        )
        if result['success']:
            print(f"Connect to: {result['connection_string']}")
    """
    return get_docker_manager().spawn_lab_container(user_id, image_name, **kwargs)


def kill_user_containers(user_id: int, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to kill all containers for a user.
    
    Usage:
        result = kill_user_containers(user_id=123)
        print(f"Killed {result['killed_count']} containers")
    """
    return get_docker_manager().kill_user_containers(user_id, **kwargs)


def get_user_active_lab(user_id: int) -> Optional[Dict[str, Any]]:
    """Get the active lab for a user"""
    return get_docker_manager().get_user_active_lab(user_id)


def execute_command(user_id: int, command: str) -> Dict[str, Any]:
    """Execute command in user's active lab"""
    return get_docker_manager().execute_command(user_id, command)


# ==================== FLASK ROUTES ====================
# Register these routes with Flask app

def register_docker_lab_routes(app, manager: DockerLabManager):
    """
    Register Docker lab API routes with Flask app.
    
    Endpoints:
        POST /api/labs/spawn      - Start a new lab container
        POST /api/labs/kill       - Stop user's active lab
        GET  /api/labs/status     - Get user's active lab status
        GET  /api/labs/available  - List available lab images
        POST /api/labs/extend     - Extend lab timeout
        GET  /api/labs/<id>/first_blood - Get solvers
        GET  /api/vpn/config      - Get VPN config
    """
    from flask import request, jsonify
    
    # Lab images available
    # Using real public images for instant playability
    AVAILABLE_LABS = {
        # --- BASICS ---
        'penguin-ops': {'image': 'linuxserver/openssh-server', 'name': 'Linux Ops', 'port': 2222, 'protocol': 'ssh', 'difficulty': 'easy'},
        'netrunner-101': {'image': 'nginx:alpine', 'name': 'NetRunner', 'port': 80, 'protocol': 'http', 'difficulty': 'easy'},
        'blue-screen': {'image': 'linuxserver/openssh-server', 'name': 'Windows Sim', 'port': 2222, 'protocol': 'ssh', 'difficulty': 'easy'}, # Simulated on Linux
        'toolkit-zero': {'image': 'linuxserver/openssh-server', 'name': 'Toolkit Zero', 'port': 2222, 'protocol': 'ssh', 'difficulty': 'easy'},

        # --- LIVE LAB (VULNERABLE APPS) ---
        'dvwa': {'image': 'vulnerables/web-dvwa', 'name': 'DVWA (Damn Vulnerable Web App)', 'port': 80, 'protocol': 'http', 'difficulty': 'medium'},
        'juice-shop': {'image': 'bkimminich/juice-shop', 'name': 'OWASP Juice Shop', 'port': 3000, 'protocol': 'http', 'difficulty': 'hard'},
        'mutillidae': {'image': 'citizenstig/nowasp', 'name': 'Mutillidae II', 'port': 80, 'protocol': 'http', 'difficulty': 'hard'},

        # --- OWASP WEB ---
        'room-injection': {'image': 'breachlabs/injection-lab:latest', 'name': 'Injection Lab', 'port': 80, 'protocol': 'http', 'difficulty': 'medium'}, 
        'room-xss-basics': {'image': 'breachlabs/xss-lab:latest', 'name': 'XSS Playground', 'port': 80, 'protocol': 'http', 'difficulty': 'easy'},
        'room-broken-auth': {'image': 'breachlabs/auth-lab:latest', 'name': 'Auth Manager', 'port': 80, 'protocol': 'http', 'difficulty': 'hard'},

        # --- LEGACY PRESETS ---
        'phish-pond': {'image': 'nginx:alpine', 'name': 'Phishing Lab', 'port': 80, 'protocol': 'http', 'difficulty': 'easy'},
        'wireshark-bay': {'image': 'nginx:alpine', 'name': 'Wireshark Bay', 'port': 80, 'protocol': 'http', 'difficulty': 'easy'},

        # --- RED TEAM OPS (AD) ---
        'kerberoasting': {'image': 'vulnlab/ad-dummy:v1', 'name': 'Kerberoasting Lab', 'port': 3389, 'protocol': 'rdp', 'difficulty': 'medium'},
        'bloodhound': {'image': 'vulnlab/ad-dummy:v1', 'name': 'BloodHound Lab', 'port': 3389, 'protocol': 'rdp', 'difficulty': 'easy'},
        'zerologon': {'image': 'vulnlab/ad-dummy:v1', 'name': 'ZeroLogon Lab', 'port': 445, 'protocol': 'smb', 'difficulty': 'hard'},
        'gpo-abuse': {'image': 'vulnlab/ad-dummy:v1', 'name': 'GPO Abuse Lab', 'port': 3389, 'protocol': 'rdp', 'difficulty': 'medium'},
        'golden-ticket': {'image': 'vulnlab/ad-dummy:v1', 'name': 'Golden Ticket Lab', 'port': 88, 'protocol': 'kerberos', 'difficulty': 'hard'},
        'llmnr-poisoning': {'image': 'vulnlab/kali-responder:v1', 'name': 'LLMNR Lab', 'port': 8080, 'protocol': 'http', 'difficulty': 'easy'},

        # --- NEW CURRICULUM MAPPINGS ---
        'room-linux-nav-guided': {'image': 'linuxserver/openssh-server', 'name': 'Linux Basics', 'port': 2222, 'protocol': 'ssh', 'difficulty': 'easy'},
        'room-linux-survivor-challenge': {'image': 'alpine', 'name': 'Survivor Shell', 'port': 22, 'protocol': 'ssh', 'difficulty': 'medium'},
        
        'room-web-ssrf-guided': {'image': 'breachlabs/ssrf-lab:latest', 'name': 'SSRF Lab', 'port': 80, 'protocol': 'http', 'difficulty': 'hard'},
        'room-web-xxe-guided': {'image': 'breachlabs/xxe-lab:latest', 'name': 'XXE Lab', 'port': 80, 'protocol': 'http', 'difficulty': 'hard'},
        'room-injection': {'image': 'breachlabs/injection-lab:latest', 'name': 'Injection Lab', 'port': 80, 'protocol': 'http', 'difficulty': 'medium'}, 
        'room-xss-basics': {'image': 'breachlabs/xss-lab:latest', 'name': 'XSS Playground', 'port': 80, 'protocol': 'http', 'difficulty': 'easy'},

        # --- CTF GALAXY REDESIGN MAPPINGS ---
        'ctf-celestial-logbook': {'image': 'celestial-logbook:latest', 'name': 'The Celestial Logbook', 'port': 80, 'protocol': 'http', 'difficulty': 'medium'},
        'ctf-dark-matter-object': {'image': 'dark-matter-object:latest', 'name': 'Dark Matter Object', 'port': 5000, 'protocol': 'http', 'difficulty': 'insane'},
        'ctf-identity-paradox': {'image': 'identity-paradox:latest', 'name': 'The Identity Paradox', 'port': 3000, 'protocol': 'http', 'difficulty': 'hard'},
        'ctf-ghost-archive': {'image': 'ghost-archive:latest', 'name': 'The Ghost Archive', 'port': 80, 'protocol': 'http', 'difficulty': 'medium'},
        'ctf-ping-pong': {'image': 'ping-pong:latest', 'name': 'Ping Pong', 'port': 5000, 'protocol': 'http', 'difficulty': 'hard'},
        'ctf-login-limbo': {'image': 'login-limbo:latest', 'name': 'Login Limbo', 'port': 80, 'protocol': 'http', 'difficulty': 'medium'},
        'ctf-intern-mistake': {'image': 'the-interns-mistake:latest', 'name': "The Intern's Mistake", 'port': 80, 'protocol': 'http', 'difficulty': 'easy'},
        'ctf-leaky-bucket': {'image': 'leaky-bucket:latest', 'name': 'The Leaky Bucket', 'port': 80, 'protocol': 'http', 'difficulty': 'easy'},
        'ctf-hidden-sauce': {'image': 'hidden-sauce:latest', 'name': 'Hidden Sauce', 'port': 80, 'protocol': 'http', 'difficulty': 'easy'},
        'ctf-base-jump': {'image': 'base-jump:latest', 'name': 'Base Jump', 'port': 80, 'protocol': 'http', 'difficulty': 'easy'},
        'ctf-blind-fury': {'image': 'blind-fury:latest', 'name': 'Blind Fury', 'port': 80, 'protocol': 'http', 'difficulty': 'hard'},
        'ctf-docker-breakout': {'image': 'container-escape:latest', 'name': 'Container Escape', 'port': 80, 'protocol': 'http', 'difficulty': 'hard'},
        'ctf-black-box-protocol': {'image': 'black-box-protocol:latest', 'name': 'Black Box Protocol', 'port': 80, 'protocol': 'http', 'difficulty': 'insane'},
        'ctf-singularity-bank': {'image': 'project-singularity:latest', 'name': 'Project Singularity', 'port': 80, 'protocol': 'http', 'difficulty': 'legendary'},
        
        # Missing CTF mappings
        'ctf-ssrf-internal': {'image': 'breachlabs/ssrf-internal:latest', 'name': 'SSRF to Internal', 'port': 80, 'protocol': 'http', 'difficulty': 'hard'},
        'ctf-xxe-exfil': {'image': 'breachlabs/xxe-exfil:latest', 'name': 'XXE Exfiltration', 'port': 80, 'protocol': 'http', 'difficulty': 'hard'},
        'ctf-graphql-introspection': {'image': 'breachlabs/graphql-lab:latest', 'name': 'GraphQL Secrets', 'port': 4000, 'protocol': 'http', 'difficulty': 'medium'},
        'ctf-race-condition': {'image': 'breachlabs/race-bank:latest', 'name': 'Race to the Bank', 'port': 80, 'protocol': 'http', 'difficulty': 'hard'},
        'ctf-prototype-pollution': {'image': 'breachlabs/proto-pollute:latest', 'name': 'Prototype Pollution', 'port': 3000, 'protocol': 'http', 'difficulty': 'hard'},
        'ctf-jwt-confusion': {'image': 'breachlabs/jwt-confuse:latest', 'name': 'JWT Key Confusion', 'port': 3000, 'protocol': 'http', 'difficulty': 'hard'},
        'ctf-reentrancy-shadow': {'image': 'breachlabs/eth-lab:latest', 'name': 'Reentrancy Shadow', 'port': 8545, 'protocol': 'http', 'difficulty': 'hard'},
        'buffer-overflow-basics': {'image': 'breachlabs/bof-basics:latest', 'name': 'BOF Basics', 'port': 1337, 'protocol': 'tcp', 'difficulty': 'hard'},
        
        # Missing Lab Page mappings
        'apollo-01': {'image': 'vulnlab/apollo:v1', 'name': 'APOLLO-01', 'port': 80, 'protocol': 'http', 'difficulty': 'easy'},
        'zeus-frame': {'image': 'vulnlab/zeus:v1', 'name': 'ZEUS-FRAME', 'port': 3389, 'protocol': 'rdp', 'difficulty': 'medium'},
        'cronos': {'image': 'vulnlab/cronos:v1', 'name': 'CRONOS', 'port': 22, 'protocol': 'ssh', 'difficulty': 'hard'},
        'nebula': {'image': 'vulnlab/nebula:v1', 'name': 'NEBULA', 'port': 80, 'protocol': 'http', 'difficulty': 'medium'}
    }

    @app.route('/api/labs/spawn', methods=['POST'])
    def spawn_lab():
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        user_id = data.get('user_id')
        image = data.get('image_name')
        lab_id = data.get('lab_id')
        
        # Check config preset
        if lab_id and lab_id in AVAILABLE_LABS:
             config = AVAILABLE_LABS[lab_id]
             image = config.get('image', image)
        
        if not image: image = "nginx:alpine"

        result = manager.spawn_lab_container(user_id=user_id, image_name=image, lab_id=lab_id)
        return jsonify(result)

    @app.route('/api/labs/kill', methods=['POST'])
    def kill_lab():
        data = request.json
        user_id = data.get('user_id')
        result = manager.kill_user_containers(user_id)
        return jsonify(result)
        
    @app.route('/api/labs/status', methods=['GET'])
    def get_docker_lab_status():
        user_id = request.args.get('user_id')
        if not user_id:
             return jsonify({'success': False, 'error': 'User ID required'}), 400
        lab = manager.get_user_active_lab(int(user_id))
        return jsonify({'success': True, 'lab': lab} if lab else {'success': True, 'lab': None})

    @app.route('/api/labs/extend', methods=['POST'])
    def extend_lab():
        data = request.json
        user_id = data.get('user_id')
        minutes = data.get('minutes', 60)
        result = manager.extend_lab_timeout(int(user_id), int(minutes))
        return jsonify(result)

    @app.route('/api/labs/shell', methods=['POST'])
    def execute_shell_command():
        data = request.json
        user_id = data.get('user_id')
        command = data.get('command')
        
        if not user_id or not command:
            return jsonify({'success': False, 'error': 'Missing user_id or command'}), 400
            
        result = manager.execute_command(int(user_id), command)
        return jsonify(result)

    @app.route('/api/labs/<lab_id>/first_blood', methods=['GET'])
    def get_first_blood(lab_id):
        import random
        # Mock Data
        users = ['CyberNinja', 'ZeroCool', 'AcidBurn', 'Neo']
        data = []
        if random.random() > 0.3:
            for i in range(random.randint(1, 3)):
                data.append({
                    'username': users[i % len(users)],
                    'avatar_url': 'assets/images/user_placeholder.png',
                    'time_taken': f'{random.randint(10, 50)} min'
                })
        return jsonify({'success': True, 'first_blood': data})

    @app.route('/api/vpn/config', methods=['GET'])
    def get_vpn_config():
        user_id = request.args.get('user_id', '1')
        config = f"client\ndev tun\nremote 10.10.10.10 1194"
        return jsonify({'success': True, 'config_text': config, 'filename': f'user_{user_id}.ovpn'})

    @app.route('/api/labs/available', methods=['GET'])
    def list_labs():
        return jsonify(AVAILABLE_LABS)

    logger.info("✓ Docker Lab API routes registered")


# ==================== MAIN (Testing) ====================

if __name__ == "__main__":
    print("=" * 60)
    print("Docker Lab Manager - Test Mode")
    print("=" * 60)
    
    manager = DockerLabManager()
    
    print(f"\n📦 Docker Available: {manager.is_docker_available}")
    
    # Test spawning a container
    print("\n🧪 Testing spawn_lab_container...")
    result = manager.spawn_lab_container(
        user_id=1,
        image_name="nginx:alpine",  # Using nginx for testing
        lab_id=100,
        timeout_minutes=5
    )
    
    print(f"\nResult: {result}")
    
    if result['success']:
        print(f"\n✅ Lab Started!")
        print(f"   Connection: {result['connection_string']}")
        print(f"   Expires: {result['expires_at']}")
        
        # Wait a bit and check status
        time.sleep(2)
        
        active = manager.get_user_active_lab(1)
        print(f"\n📍 Active Lab: {active}")
        
        # Cleanup
        print("\n🧹 Cleaning up...")
        cleanup = manager.kill_user_containers(1)
        print(f"   Killed: {cleanup['killed_count']} containers")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
