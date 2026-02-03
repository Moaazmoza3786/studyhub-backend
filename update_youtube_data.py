import os
import glob
import re
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv('YOUTUBE_API_KEY')
# Resolve paths relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Expected structure: backend/script.py -> so root is parent
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
CSV_DIR = os.path.join(ROOT_DIR, 'CSV links')
OUTPUT_FILE = os.path.join(ROOT_DIR, 'youtube-data-gen.js')

def categorize_text(text):
    """Categorizes content based on keywords in text."""
    text = text.lower()
    
    # Red Team / Offensive Security
    red_keywords = ['red team', 'pentest', 'penetration', 'hacking', 'hack', 'exploit', 
                    'xss', 'injection', 'sql injection', 'ceh', 'oscp', 'owasp', 'juice shop',
                    'bug bounty', 'vulnerability', 'offensive', 'metasploit', 'kali',
                    'ethical hacking', 'web hacking', 'buffer overflow', 'privilege escalation',
                    'reverse shell', 'payload', 'pwn', 'ctf', 'capture the flag', 'tryhackme', 
                    'hackthebox', 'htb', 'vulnhub', 'اختبار اختراق', 'اختراق', 'هاكر']
    
    # Blue Team / Defensive Security
    blue_keywords = ['blue team', 'forensics', 'forensic', 'soc', 'defense', 'defensive',
                     'incident response', 'threat hunting', 'siem', 'splunk', 'elk',
                     'malware analysis', 'reverse engineering', 'ida', 'ghidra', 'detection',
                     'dfir', 'threat intelligence', 'security analyst', 'تحليل', 'دفاع']
    
    # Networking
    network_keywords = ['network', 'networking', 'ccna', 'ccnp', 'cisco', 'nmap', 'wireshark',
                        'tcp/ip', 'tcp', 'udp', 'dns', 'dhcp', 'routing', 'switching',
                        'firewall', 'vpn', 'subnet', 'شبكات', 'الشبكات']
    
    # Programming
    prog_keywords = ['python', 'javascript', 'php', 'java', 'c++', 'c#', 'programming',
                     'coding', 'scripting', 'bash', 'powershell', 'automation', 'api',
                     'django', 'flask', 'node', 'برمجة', 'بايثون', 'sql', 'database', 'databases']
    
    # Tools
    tool_keywords = ['burp', 'burpsuite', 'tool', 'tools', 'nessus', 'nikto', 'gobuster',
                     'dirbuster', 'sqlmap', 'hydra', 'john', 'hashcat', 'aircrack',
                     'masscan', 'اداة', 'ادوات']
    
    # Podcast
    podcast_keywords = ['podcast', 'بودكاست', 'بود كاست', 'حوار', 'مقابلة']
    
    # Web Security
    web_keywords = ['web', 'web application', 'owasp', 'api security', 'rest', 'graphql',
                    'authentication', 'authorization', 'session', 'cors', 'csrf', 'ssrf',
                    'ويب', 'تطبيقات الويب']
    
    # Cloud Security
    cloud_keywords = ['cloud', 'aws', 'azure', 'gcp', 'kubernetes', 'docker', 'container',
                      'serverless', 'iam', 'سحابة', 'كلاود']

    # TryHackMe
    thm_keywords = ['thm', 'tryhackme', 'try hack me']
    
    # Check keywords in priority order
    for kw in thm_keywords:
        if kw in text: return 'TryHackMe'
    for kw in podcast_keywords:
        if kw in text: return 'Podcast'
    for kw in red_keywords:
        if kw in text: return 'Red Team'
    for kw in blue_keywords:
        if kw in text: return 'Blue Team'
    for kw in web_keywords:
        if kw in text: return 'Web Security'
    for kw in cloud_keywords:
        if kw in text: return 'Cloud'
    for kw in network_keywords:
        if kw in text: return 'Networking'
    for kw in tool_keywords:
        if kw in text: return 'Tools'
    for kw in prog_keywords:
        if kw in text: return 'Programming'
    
    return 'General'

def get_playlist_ids_from_files():
    """Scans CSV directory for playlist IDs in filenames."""
    playlists = []
    
    # directories to scan
    dirs_to_scan = [
        os.path.join(ROOT_DIR, 'CSV links'),
        os.path.join(ROOT_DIR, 'CSV links2')
    ]

    files = []
    for d in dirs_to_scan:
        if os.path.exists(d):
            files.extend(glob.glob(os.path.join(d, '*.csv')))
        else:
            print(f"Warning: Directory not found: {d}")
    
    print(f"Found {len(files)} CSV files in total.")
    
    for f in files:
        basename = os.path.basename(f)
        # Extract ID using regex from filename
        match = re.search(r'youtube-playlist-links-([^-\s]+)-', basename)
        pid = None
        
        if match:
            pid = match.group(1)
        else:
            # Fallback: Read file to find 'list=ID' in URL
            try:
                with open(f, 'r', encoding='utf-8', errors='ignore') as csv_file:
                    content = csv_file.read()
                    # Look for list=... in content
                    url_match = re.search(r'list=([a-zA-Z0-9_-]+)', content)
                    if url_match:
                        pid = url_match.group(1)
            except Exception as e:
                print(f"Error reading {basename}: {e}")

        if pid:
            # Categorization based on filename keywords
            category = categorize_text(basename.lower())
                
            if pid not in [p['id'] for p in playlists]:
                playlists.append({
                    'id': pid,
                    'filename_title': basename, # Backup title
                    'category': category
                })
        else:
            print(f"Skipping {basename}: No ID found.")
            
    return playlists

def fetch_youtube_metadata(playlists):
    """Fetches details from YouTube Data API."""
    if not API_KEY:
        print("ERROR: YOUTUBE_API_KEY not found in .env")
        return playlists 

    base_url = "https://www.googleapis.com/youtube/v3/playlists"
    
    # Batch requests (max 50 IDs per call)
    ids = [p['id'] for p in playlists]
    chunks = [ids[i:i + 50] for i in range(0, len(ids), 50)]
    
    enriched_data = []
    
    for chunk in chunks:
        id_str = ','.join(chunk)
        url = f"{base_url}?part=snippet,contentDetails&id={id_str}&key={API_KEY}"
        
        try:
            res = requests.get(url)
            data = res.json()
            
            if 'items' in data:
                for item in data['items']:
                    pid = item['id']
                    snippet = item['snippet']
                    
                    # Find original local object to preserve category
                    local_obj = next((p for p in playlists if p['id'] == pid), None)
                    category = local_obj['category'] if local_obj else 'General'
                    
                    # Re-categorize using API title if still General
                    if category == 'General':
                        api_title = snippet.get('title', '') + ' ' + snippet.get('description', '')
                        category = categorize_text(api_title)
                    
                    # Fetch Playlist Items (Videos) with Pagination
                    videos = []
                    try:
                        next_token = ""
                        while True:
                            v_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId={pid}&key={API_KEY}"
                            if next_token:
                                v_url += f"&pageToken={next_token}"
                            
                            v_res = requests.get(v_url)
                            v_data = v_res.json()
                            
                            if 'items' in v_data:
                                for v in v_data['items']:
                                    videos.append({
                                        'title': v['snippet']['title'],
                                        'videoId': v['snippet']['resourceId']['videoId'],
                                        'position': v['snippet']['position']
                                    })
                            
                            next_token = v_data.get('nextPageToken')
                            if not next_token:
                                break
                                
                    except Exception as ve:
                        print(f"Failed to fetch items for {pid}: {ve}")

                    enriched_data.append({
                        'id': pid,
                        'title': snippet.get('title'),
                        'channel': snippet.get('channelTitle'),
                        'description': snippet.get('description', '')[:200] + '...',
                        'image': snippet.get('thumbnails', {}).get('high', {}).get('url') or snippet.get('thumbnails', {}).get('default', {}).get('url'),
                        'videoCount': item.get('contentDetails', {}).get('itemCount', 0),
                        'category': category,
                        'videos': videos
                    })
        except Exception as e:
            print(f"Failed to fetch chunk: {e}")
            
    return enriched_data

def generate_js_file(data):
    """Writes the data to a JS file."""
    content = f"""/* GENERATED FILE - DO NOT EDIT MANUALLY */
/* Timestamp: {os.popen('date /t').read().strip()} */

window.YouTubeDataGen = {json.dumps(data, indent=4)};
"""
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Successfully generated {OUTPUT_FILE} with {len(data)} playlists.")

if __name__ == "__main__":
    print("Starting YouTube Sync...")
    raw_playlists = get_playlist_ids_from_files()
    if not raw_playlists:
        print("No CSVs found or regex failed.")
    else:
        print(f"Identified {len(raw_playlists)} playlists from files.")
        final_data = fetch_youtube_metadata(raw_playlists)
        
        # If API failed entirely (no key), falls back to raw data with placeholders
        if not final_data and raw_playlists and not API_KEY:
             final_data = [{
                 'id': p['id'], 
                 'title': p['filename_title'], 
                 'channel': 'Unknown', 
                 'category': p['category'],
                 'image': 'assets/images/placeholder_course.jpg'
             } for p in raw_playlists]
             
        generate_js_file(final_data)
        print("Done.")
