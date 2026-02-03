"""
Study Hub - Automated Screenshot Capture Script 📸
Captures full-page screenshots of all key platform pages.

Features:
1. Starts a local HTTP server for frontend.
2. Uses Playwright to navigate the SPA.
3. Logs in automatically.
4. Screenshots public & private pages.
5. Saves to c:/Users/mmoza/Desktop/Study-hub3/screenshots/
"""

import os
import sys
import threading
import time
import subprocess
from http.server import SimpleHTTPRequestHandler, HTTPServer
from playwright.sync_api import sync_playwright

# Configuration
FRONTEND_PORT = 8080
BASE_URL = f"http://localhost:{FRONTEND_PORT}"
SCREENSHOT_DIR = os.path.join("..", "screenshots")  # Relative to backend/
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ensure screenshot directory exists
os.makedirs(os.path.join(ROOT_DIR, "screenshots"), exist_ok=True)

class SPAHandler(SimpleHTTPRequestHandler):
    """Serve index.html for unknown paths (SPA support)"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT_DIR, **kwargs)

    def do_GET(self):
        # Serve index.html for common routes to support SPA refresh if needed
        # But for screenshots we just navigate hash/js routing
        super().do_GET()

def start_server():
    """Start static file server for frontend"""
    server_address = ('', FRONTEND_PORT)
    httpd = HTTPServer(server_address, SPAHandler)
    print(f"🌍 Frontend Server started at {BASE_URL}")
    httpd.serve_forever()

def run_capture():
    print(f"📸 Starting Screenshot Capture...")
    print(f"📂 Saving to: {os.path.join(ROOT_DIR, 'screenshots')}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Emulate a high-res desktop
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        # Helper to take screenshot
        def snap(name, wait_for=None):
            if wait_for:
                try:
                    page.wait_for_selector(wait_for, timeout=5000)
                except:
                    print(f"⚠️ Warning: Timeout waiting for {wait_for} on {name}")
            
            # Allow animations to settle
            time.sleep(2)  
            
            path = os.path.join(ROOT_DIR, "screenshots", f"{name}.png")
            page.screenshot(path=path, full_page=True)
            print(f"✅ Captured: {name}.png")

        # 1. Public Pages
        print("\n--- 🌐 Public Pages ---")
        
        # Login Page
        page.goto(f"{BASE_URL}/#login")
        snap("01_login_page", "#login-form")

        # Register Page
        page.goto(f"{BASE_URL}/#register")
        snap("02_register_page", "#register-form")

        # 2. Authentication
        print("\n--- 🔐 Authenticating ---")
        page.goto(f"{BASE_URL}/#login")
        page.fill("#email", "admin@studyhub.com")  # Using seed data or creating one?
        # Let's try to register a temp user to be safe and clean
        
        print("   Creating temp user for screenshots...")
        page.goto(f"{BASE_URL}/#register")
        page.fill("#username", "photographer")
        page.fill("#email", "photo@studyhub.com")
        page.fill("#password", "Password123!")
        page.fill("#confirm-password", "Password123!")
        page.fill("#first-name", "Screen")
        page.fill("#last-name", "Shot")
        page.click("button[type='submit']")
        
        # Wait for redirect to hub or login
        time.sleep(3)
        
        # Verify login success
        if "login" in page.url:
             # If redirected to login, login manually
             page.fill("#email", "photo@studyhub.com")
             page.fill("#password", "Password123!")
             page.click("button[type='submit']")
             time.sleep(3)

        # 3. Private Pages
        print("\n--- 👤 Private Pages ---")

        # Hub (Home)
        page.goto(f"{BASE_URL}/#hub")
        snap("03_hub_dashboard", ".hero-section")

        # Tracks (Learning Paths)
        page.goto(f"{BASE_URL}/#tracks")
        snap("04_learning_paths", ".tracks-container")

        # Domains
        page.goto(f"{BASE_URL}/#domains")
        snap("05_domains_selection", ".domain-card")

        # Skill Tree
        page.goto(f"{BASE_URL}/#skill-tree")
        snap("06_skill_tree", "#skill-tree-container")

        # Profile
        page.goto(f"{BASE_URL}/#profile")
        snap("07_user_profile", ".profile-header")

        # Settings
        page.goto(f"{BASE_URL}/#settings")
        snap("08_settings", ".settings-container")
        
        # Module View (Simulated)
        # We need to find a path and click it? Or just force URL if we knew IDs
        # Let's try to click first track
        page.goto(f"{BASE_URL}/#tracks")
        try:
            # Wait for content
            page.wait_for_selector(".track-card", timeout=5000)
            page.click(".track-card h3") # Click first track title
            time.sleep(2)
            snap("09_path_details", ".path-header")
        except Exception as e:
            print(f"⚠️ Could not capture path details: {e}")

        browser.close()
        print("\n🎉 Screenshot capture complete!")

if __name__ == "__main__":
    # Start server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Give server a moment to start
    time.sleep(2)
    
    try:
        run_capture()
    except Exception as e:
        print(f"\n❌ Error capturing screenshots: {e}")
    finally:
        sys.exit(0)
