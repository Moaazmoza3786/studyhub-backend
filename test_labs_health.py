"""
Study Hub - Labs Health Check Script 🩺
Validates that all lab Docker images in the database are runnable.

Features:
1. Fetch all lab images from DB.
2. Spin up test containers.
3. Check status and port reachability.
4. Clean up resources.
5. Report broken images.
"""

import sys
import docker
import socket
import time
import logging
from contextlib import closing

# Import app context
from main import create_app
from models import Lab, Module

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('LabHealthCheck')

def check_port_open(ip, port, timeout=2):
    """Check if a port is open and accepting connections"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((ip, int(port)))
            return result == 0
        except:
            return False

def run_health_check():
    """Main health check function"""
    app = create_app()
    
    try:
        client = docker.from_env()
        client.ping()
        logger.info("✅ Connected to Docker Daemon")
    except Exception as e:
        logger.error("❌ Failed to connect to Docker Daemon!")
        logger.error(f"   Error: {str(e)}")
        logger.error("👉 Please ensure Docker Desktop is running.")
        logger.error("👉 If running, try restarting Docker Desktop.")
        return
    
    with app.app_context():
        # Get all labs with docker images
        labs = Lab.query.filter(Lab.docker_image_name != None).all()
        
        logger.info(f"🧪 Starting health check for {len(labs)} labs...")
        
        broken_labs = []
        passed_labs = 0
        
        for lab in labs:
            logger.info(f"\n🔍 Checking Lab: {lab.name} (Image: {lab.docker_image_name})")
            
            container = None
            try:
                # 1. Spawn container
                logger.info("   🚀 Spawning container...")
                container = client.containers.run(
                    image=lab.docker_image_name,
                    detach=True,
                    publish_all_ports=True, # Publish all ports to random host ports
                    mem_limit='256m',
                    name=f"healthcheck_{lab.id}_{int(time.time())}"
                )
                
                # 2. Wait 10 seconds
                logger.info("   ⏳ Waiting 10s for startup...")
                time.sleep(10)
                
                # 3. Check status
                container.reload()
                if container.status != 'running':
                    raise Exception(f"Container died immediately. Status: {container.status}")
                
                logger.info("   ✅ Status: Running")
                
                # 4. Check ports
                container.reload() # Refresh to get port mappings
                ports = container.ports
                
                if not ports:
                     raise Exception("No ports exposed by container")
                
                # Check accessibility of the first mapped port
                is_accessible = False
                for port_info in ports.values():
                    if port_info:
                        host_port = port_info[0]['HostPort']
                        if check_port_open('localhost', host_port):
                            logger.info(f"   ✅ Port Check: Accessible on localhost:{host_port}")
                            is_accessible = True
                            break
                
                if not is_accessible:
                     raise Exception("Ports mapping found but not reachable")

                logger.info("   🎉 Health Check Passed!")
                passed_labs += 1
                
            except docker.errors.ImageNotFound:
                msg = "❌ Image not found locally or on registry"
                logger.error(f"   {msg}")
                broken_labs.append({'name': lab.name, 'image': lab.docker_image_name, 'error': msg})
                
            except Exception as e:
                msg = f"❌ Failure: {str(e)}"
                logger.error(f"   {msg}")
                broken_labs.append({'name': lab.name, 'image': lab.docker_image_name, 'error': str(e)})
                
            finally:
                # 5. Cleanup
                if container:
                    try:
                        logger.info("   🧹 Cleaning up...")
                        container.remove(force=True)
                    except:
                        pass

        # === Report ===
        print("\n" + "="*50)
        print("🩺 HEALTH CHECK REPORT")
        print("="*50)
        print(f"Total Labs: {len(labs)}")
        print(f"✅ Passed: {passed_labs}")
        print(f"❌ Failed: {len(broken_labs)}")
        
        if broken_labs:
            print("\n❌ BROKEN IMAGES:")
            for item in broken_labs:
                print(f" - {item['name']} ({item['image']})")
                print(f"   Error: {item['error']}")
        print("="*50)

if __name__ == "__main__":
    try:
        run_health_check()
    except Exception as e:
        logger.error(f"Fatal script error: {e}")
