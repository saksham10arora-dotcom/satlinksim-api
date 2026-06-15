import sqlite3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
import json

# CelesTrak GP Element Set URLs
CELESTRAK_GROUPS = {
    "starlink": "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle",
    "oneweb": "https://celestrak.org/NORAD/elements/gp.php?GROUP=oneweb&FORMAT=tle",
    "geo": "https://celestrak.org/NORAD/elements/gp.php?GROUP=geo&FORMAT=tle",
    "iridium": "https://celestrak.org/NORAD/elements/gp.php?GROUP=iridium-next&FORMAT=tle",
    "globalstar": "https://celestrak.org/NORAD/elements/gp.php?GROUP=globalstar&FORMAT=tle"
}

# Project Root Directory paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DB_PATH = os.path.join(PROJECT_ROOT, "satellites.db")
CACHE_DIR = os.path.join(PROJECT_ROOT, "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "tle_snapshot.json")

def get_session_with_retries(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504, 403)):
    """Configure requests session with retries for resilience."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_cache(cache_data):
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache_data, f, indent=2)

def update_database(groups=None):
    """Fetch TLEs with retries and a local fallback cache."""
    if groups is None:
        groups = list(CELESTRAK_GROUPS.keys())
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Schema Migration
    cur.execute("""
    CREATE TABLE IF NOT EXISTS satellites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        norad_id INTEGER UNIQUE,
        tle_line1 TEXT,
        tle_line2 TEXT
    )
    """)
    
    cur.execute("PRAGMA table_info(satellites)")
    columns = [col[1] for col in cur.fetchall()]
    if "last_updated" not in columns:
        cur.execute("ALTER TABLE satellites ADD COLUMN last_updated DATETIME")

    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_satellites_norad_id ON satellites(norad_id)")

    cache_data = load_cache()
    session = get_session_with_retries()
    
    total_added = 0
    
    for group in groups:
        url = CELESTRAK_GROUPS.get(group)
        if not url:
            print(f"Unknown group: {group}")
            continue
        
        print(f"Fetching {group} from CelesTrak...")
        raw_text = None
        
        try:
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Success: use text and update cache
            raw_text = response.text
            cache_data[group] = raw_text
            save_cache(cache_data)
            print(f"  -> Successfully fetched and cached.")
            
        except requests.exceptions.RequestException as e:
            print(f"  -> Error fetching {group} ({e}).")
            print(f"  -> Attempting to load from fallback cache...")
            
            raw_text = cache_data.get(group)
            if raw_text:
                print(f"  -> Loaded {group} from fallback cache.")
            else:
                print(f"  -> No fallback cache found for {group}. Skipping.")
                continue

        if not raw_text:
            continue

        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        processed_group_count = 0
        
        for i in range(0, len(lines) - 2, 3):
            name = lines[i]
            l1 = lines[i+1]
            l2 = lines[i+2]
            
            try:
                norad_id = int(l1[2:7])
            except ValueError:
                continue
            
            cur.execute("""
            INSERT INTO satellites (name, norad_id, tle_line1, tle_line2, last_updated)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(norad_id) DO UPDATE SET
                name=excluded.name,
                tle_line1=excluded.tle_line1,
                tle_line2=excluded.tle_line2,
                last_updated=CURRENT_TIMESTAMP
            """, (name, norad_id, l1, l2))
            
            processed_group_count += 1
            if cur.rowcount == 1:
                total_added += 1
        
        print(f"  Processed {processed_group_count} satellites from {group}")
            
    conn.commit()
    
    cur.execute("SELECT COUNT(*) FROM satellites")
    total_count = cur.fetchone()[0]
    conn.close()
    
    print(f"\nUpdate Complete!")
    print(f"Total satellites in database: {total_count}")

def main():
    update_database(["geo", "starlink", "oneweb", "iridium", "globalstar"])

if __name__ == "__main__":
    main()
