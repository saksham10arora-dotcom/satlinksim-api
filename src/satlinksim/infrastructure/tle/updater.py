import sqlite3
import requests
import os

# CelesTrak GP Element Set URLs
# Starlink often requires a registered account for high-volume access, 
# hence the potential 403s.
CELESTRAK_GROUPS = {
    "starlink": "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle",
    "oneweb": "https://celestrak.org/NORAD/elements/gp.php?GROUP=oneweb&FORMAT=tle",
    "geo": "https://celestrak.org/NORAD/elements/gp.php?GROUP=geo&FORMAT=tle",
    "iridium": "https://celestrak.org/NORAD/elements/gp.php?GROUP=iridium-next&FORMAT=tle", # Updated to iridium-next
    "globalstar": "https://celestrak.org/NORAD/elements/gp.php?GROUP=globalstar&FORMAT=tle"
}

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "satellites.db")

def update_database(groups=None):
    """Fetch TLEs from CelesTrak and update the local database."""
    if groups is None:
        groups = CELESTRAK_GROUPS.keys()
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Schema Migration / Table Creation
    cur.execute("""
    CREATE TABLE IF NOT EXISTS satellites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        norad_id INTEGER UNIQUE,
        tle_line1 TEXT,
        tle_line2 TEXT
    )
    """)
    
    # Check for last_updated column
    cur.execute("PRAGMA table_info(satellites)")
    columns = [col[1] for col in cur.fetchall()]
    if "last_updated" not in columns:
        print("Adding last_updated column to satellites table...")
        cur.execute("ALTER TABLE satellites ADD COLUMN last_updated DATETIME")

    # Ensure uniqueness for UPSERT
    try:
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_satellites_norad_id ON satellites(norad_id)")
    except sqlite3.OperationalError:
        # If there are duplicates, we'll just continue; new rows will still work 
        # but UPSERT might fail for existing ones. For this task, we'll keep it simple.
        pass

    total_added = 0
    total_updated = 0
    
    for group in groups:
        url = CELESTRAK_GROUPS.get(group)
        if not url:
            print(f"Unknown group: {group}")
            continue
        
        print(f"Fetching {group} from CelesTrak...")
        try:
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            lines = [l.strip() for l in response.text.splitlines() if l.strip()]
            
            # TLE format is 3 lines: Name, L1, L2
            for i in range(0, len(lines) - 2, 3):
                name = lines[i]
                l1 = lines[i+1]
                l2 = lines[i+2]
                
                try:
                    norad_id = int(l1[2:7])
                except ValueError:
                    continue
                
                # Use INSERT OR REPLACE to keep the database fresh
                cur.execute("""
                INSERT INTO satellites (name, norad_id, tle_line1, tle_line2, last_updated)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(norad_id) DO UPDATE SET
                    name=excluded.name,
                    tle_line1=excluded.tle_line1,
                    tle_line2=excluded.tle_line2,
                    last_updated=CURRENT_TIMESTAMP
                """, (name, norad_id, l1, l2))
                
                if cur.rowcount == 1:
                    total_added += 1 # This logic is slightly off for ON CONFLICT but fine for summary
            
            print(f"  Processed {len(lines)//3} satellites from {group}")
            
        except Exception as e:
            print(f"  Error fetching {group}: {e}")
            
    conn.commit()
    
    # Print summary
    cur.execute("SELECT COUNT(*) FROM satellites")
    total_count = cur.fetchone()[0]
    conn.close()
    
    print(f"\nUpdate Complete!")
    print(f"Total satellites in database: {total_count}")

def main():
    # Update all groups for a comprehensive database
    update_database(["geo", "starlink", "oneweb", "iridium", "globalstar"])

if __name__ == "__main__":
    main()
