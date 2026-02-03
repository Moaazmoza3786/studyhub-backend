"""
Intel Manager - Cybersecurity Intelligence Engine 🛰️
Fetches, parses, and summarizes security news, vulnerabilities, and writeups
from professional sources (RSS, APIs, etc.)
"""

import requests
import feedparser
import logging
from datetime import datetime
import threading
import time
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('IntelManager')

class IntelManager:
    """
    Manages live intelligence feeds for the platform.
    """
    
    DEFAULT_FEEDS = {
        'news': [
            {'name': 'The Hacker News', 'url': 'https://feeds.feedburner.com/TheHackersNews', 'category': 'General'},
            {'name': 'BleepingComputer', 'url': 'https://www.bleepingcomputer.com/feed/', 'category': 'General'},
            {'name': 'Krebs on Security', 'url': 'https://krebsonsecurity.com/feed/', 'category': 'General'},
            {'name': 'Threatpost', 'url': 'https://threatpost.com/feed/', 'category': 'General'}
        ],
        'vulnerabilities': [
            {'name': 'ZDI Blog', 'url': 'https://www.zerodayinitiative.com/blog?format=rss', 'category': 'Research'},
            {'name': 'CVE Details', 'url': 'https://www.cvedetails.com/vulnerability-list/rss.php', 'category': 'CVE'}
        ],
        'writeups': [
            {'name': 'Hack The Box Blog', 'url': 'https://www.hackthebox.com/blog/rss', 'category': 'Writeup'},
            {'name': 'TryHackMe Blog', 'url': 'https://blog.tryhackme.com/rss/', 'category': 'Writeup'}
        ]
    }

    def __init__(self):
        self.cache = {
            'news': [],
            'vulnerabilities': [],
            'writeups': [],
            'last_updated': None
        }
        self.lock = threading.Lock()
        self._start_auto_refresh()

    def _start_auto_refresh(self, interval_seconds: int = 3600):
        """Start background thread to refresh feeds hourly"""
        def refresh_loop():
            while True:
                try:
                    self.refresh_all_feeds()
                except Exception as e:
                    logger.error(f"Error refreshing feeds: {e}")
                time.sleep(interval_seconds)

        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()
        logger.info("📡 Intel auto-refresh background task started")

    def refresh_all_feeds(self):
        """Fetch and parse all configured feeds"""
        logger.info("🔄 Refreshing all intelligence feeds...")
        new_cache = {
            'news': [],
            'vulnerabilities': [],
            'writeups': [],
            'last_updated': datetime.now().isoformat()
        }

        for feed_type, feeds in self.DEFAULT_FEEDS.items():
            for feed_config in feeds:
                try:
                    entries = self._fetch_feed(feed_config)
                    new_cache[feed_type].extend(entries)
                except Exception as e:
                    logger.warning(f"Failed to fetch {feed_config['name']}: {e}")

        # Sort all lists by date (newest first)
        for feed_type in ['news', 'vulnerabilities', 'writeups']:
            new_cache[feed_type].sort(key=lambda x: x.get('published_parsed', ''), reverse=True)
            # Cap at 50 entries per type
            new_cache[feed_type] = new_cache[feed_type][:50]

        with self.lock:
            self.cache = new_cache
        
        logger.info(f"✅ Feeds refreshed. News: {len(self.cache['news'])}, Vulns: {len(self.cache['vulnerabilities'])}, Writeups: {len(self.cache['writeups'])}")

    def _fetch_feed(self, feed_config: Dict[str, str]) -> List[Dict[str, Any]]:
        """Parse an RSS feed into a standard format"""
        feed = feedparser.parse(feed_config['url'])
        entries = []
        
        for entry in feed.entries:
            # Standardize entry format
            standard_entry = {
                'id': entry.get('id', entry.get('link')),
                'title': entry.get('title'),
                'link': entry.get('link'),
                'summary': entry.get('summary', entry.get('description', ''))[:500], # Trucate long summaries
                'published': entry.get('published', ''),
                'published_parsed': entry.get('published_parsed', None),
                'source': feed_config['name'],
                'category': feed_config['category'],
                'author': entry.get('author', 'Anonymous')
            }
            # Remove HTML tags from summary if needed, but keeping for now as frontend can handle
            entries.append(standard_entry)
            
        return entries

    def get_intel(self, feed_type: str = 'news', category: Optional[str] = None) -> Dict[str, Any]:
        """Get cached intel items"""
        with self.lock:
            items = self.cache.get(feed_type, [])
            if category:
                items = [i for i in items if i['category'] == category]
            
            return {
                'success': True,
                'type': feed_type,
                'count': len(items),
                'last_updated': self.cache['last_updated'],
                'items': items
            }

# Global instance
intel_manager = IntelManager()

def register_intel_routes(app):
    """Register intel API routes with Flask app"""
    from flask import jsonify, request

    @app.route('/api/intel/news', methods=['GET'])
    def get_news():
        category = request.args.get('category')
        return jsonify(intel_manager.get_intel('news', category))

    @app.route('/api/intel/vulnerabilities', methods=['GET'])
    def get_vulnerabilities():
        return jsonify(intel_manager.get_intel('vulnerabilities'))

    @app.route('/api/intel/writeups', methods=['GET'])
    def get_writeups():
        return jsonify(intel_manager.get_intel('writeups'))

    @app.route('/api/intel/refresh', methods=['POST'])
    def manual_refresh():
        # Optional: Add simple auth check here
        intel_manager.refresh_all_feeds()
        return jsonify({'success': True, 'message': 'Refresh initiated'})
