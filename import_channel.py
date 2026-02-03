import os
import requests
import json
from dotenv import load_dotenv

# Load Env
load_dotenv()
API_KEY = os.getenv('YOUTUBE_API_KEY')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
CSV_DIR = os.path.join(ROOT_DIR, 'CSV links')

def resolve_channel_id(input_str):
    """Tries to resolve a channel ID from various inputs (URL, Handle, Name)."""
    input_str = input_str.strip()
    
    # CASE 1: Full URL
    if 'youtube.com' in input_str or 'youtu.be' in input_str:
        if '/channel/' in input_str:
            return input_str.split('/channel/')[1].split('/')[0].split('?')[0]
        elif '/@' in input_str:
            input_str = '@' + input_str.split('/@')[1].split('/')[0].split('?')[0]
    
    # CASE 2: Handle (@username)
    if input_str.startswith('@'):
        url = f"https://www.googleapis.com/youtube/v3/channels?part=id&forHandle={input_str}&key={API_KEY}"
        try:
            res = requests.get(url)
            data = res.json()
            if 'items' in data and len(data['items']) > 0:
                print(f"Resolved handle {input_str} -> {data['items'][0]['id']}")
                return data['items'][0]['id']
        except:
            pass
            
    # CASE 3: Direct ID (UC...)
    if input_str.startswith('UC'):
        return input_str

    # CASE 4: Search by name (Fallback)
    print(f"Searching for channel '{input_str}'...")
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=channel&q={input_str}&key={API_KEY}"
    try:
        res = requests.get(url)
        data = res.json()
        if 'items' in data and len(data['items']) > 0:
            found = data['items'][0]
            print(f"Found Channel: {found['snippet']['channelTitle']} ({found['id']['channelId']})")
            return found['id']['channelId']
    except Exception as e:
        print(f"Search failed: {e}")

    return input_str  # Return original if all else fails

def get_channel_playlists(raw_input):
    if not API_KEY:
        print("Error: YOUTUBE_API_KEY missing in .env")
        return []

    channel_id = resolve_channel_id(raw_input)
    if not channel_id:
        print("Could not resolve Channel ID.")
        return []

    print(f"Using Channel ID: {channel_id}")
        
    url = f"https://www.googleapis.com/youtube/v3/playlists?part=snippet,contentDetails&channelId={channel_id}&maxResults=50&key={API_KEY}"
    try:
        res = requests.get(url)
        data = res.json()
        if 'items' in data:
            return data['items']
        else:
            print("No playlists found.")
            if 'error' in data:
                print(f"API Error: {data['error']['message']}")
            return []
    except Exception as e:
        print(f"Error: {e}")
        return []

def create_csv_for_playlist(playlist, category="General"):
    pid = playlist['id']
    title = playlist['snippet']['title']
    # Sanitize title for filename
    safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).strip()
    
    filename = f"youtube-playlist-links-{pid}-2025-01-01- {safe_title}.csv"
    path = os.path.join(CSV_DIR, filename)
    
    # Just create an empty CSV or with a header, the sync script only cares about the filename ID
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"Title,URL,ID,Date\n{title},https://www.youtube.com/playlist?list={pid},{pid},2025-01-01")
    
    print(f"Created: {path}")

if __name__ == "__main__":
    print("--- YouTube Playlist Importer ---")
    channel_id = input("Enter YouTube Channel ID (e.g., UC...): ").strip()
    
    if channel_id:
        print(f"Fetching playlists for {channel_id}...")
        playlists = get_channel_playlists(channel_id)
        
        if playlists:
            print(f"\nFound {len(playlists)} playlists:")
            for i, p in enumerate(playlists):
                print(f"[{i+1}] {p['snippet']['title']} ({p['contentDetails']['itemCount']} videos)")
            
            selection = input("\nEnter numbers to import (comma separated, e.g., '1,3,5') or 'all': ").strip()
            
            selected_indices = []
            if selection.lower() == 'all':
                selected_indices = range(len(playlists))
            else:
                try:
                    selected_indices = [int(x.strip())-1 for x in selection.split(',') if x.strip().isdigit()]
                except:
                    print("Invalid selection.")
            
            if selected_indices:
                # Optional: Ask for category? Defaulting to 'General' or auto-detect is easier.
                print("Importing...")
                for idx in selected_indices:
                    if 0 <= idx < len(playlists):
                        create_csv_for_playlist(playlists[idx])
                
                print("\nDone! running sync script now...")
                os.system(f"python \"{os.path.join(SCRIPT_DIR, 'update_youtube_data.py')}\"")
            else:
                print("No playlists selected.")
        else:
            print("No playlists found.")
    else:
        print("Channel ID is required.")
