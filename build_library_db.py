import os
import sqlite3
import hashlib

# --- CONFIGURATION ---
LIBRARY_DIR = "/path/to/comics/library"
DB_FILE = "library.db"

EXCLUDE_FOLDERS = {"inbox", "quarantine", "Inbox", "Quarantine", ".kavita", "System Volume Information"}

def calculate_file_hash(filepath, block_size=65536):
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                sha256.update(block)
        return sha256.hexdigest()
    except Exception as e:
        print(f"Skipping {filepath}: {e}")
        return None

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_hash TEXT UNIQUE,
            file_path TEXT,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def scan_library():
    print(f"--- Starting Library Scan: {LIBRARY_DIR} ---")
    conn = init_db()
    cursor = conn.cursor()
    
    count = 0
    new_entries = 0
    
    for root, dirs, files in os.walk(LIBRARY_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_FOLDERS]
        
        for file in files:
            if file.lower().endswith(('.cbz', '.cbr', '.pdf', '.epub')):
                full_path = os.path.join(root, file)
                count += 1
                
                print(f"Scanning: {file[:50].ljust(50)}", end='\r')
                
                f_hash = calculate_file_hash(full_path)
                
                if f_hash:
                    cursor.execute("SELECT id FROM library WHERE file_hash = ?", (f_hash,))
                    data = cursor.fetchone()
                    
                    if data is None:
                        cursor.execute("INSERT INTO library (file_hash, file_path) VALUES (?, ?)", (f_hash, full_path))
                        new_entries += 1
                    else:
                        cursor.execute("UPDATE library SET file_path = ? WHERE file_hash = ?", (full_path, f_hash))
    
    conn.commit()
    conn.close()
    print(f"\n\nScan Complete.")
    print(f"Total Files in DB: {count}")
    print(f"New/Updated: {new_entries}")

if __name__ == "__main__":
    scan_library()