import os
import sqlite3
import hashlib
import zipfile
import rarfile
import xml.etree.ElementTree as ET
import sys

# --- CONFIGURATION ---
LIBRARY_DIR = "/path/to/your/comic_library"
INBOX_DIR = "/path/to/your/inbox" # Must exclude this from the scan
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(PROJECT_DIR, "comics_library.db")
# ---------------------

def create_database():
    conn = sqlite3.connect(DB_FILE); cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS comics (id INTEGER PRIMARY KEY, file_path TEXT UNIQUE, file_hash TEXT, file_size INTEGER, series_id TEXT, issue_id TEXT)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hash ON comics(file_hash)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_metadata ON comics(series_id, issue_id)')
    conn.commit(); return conn

def calculate_file_hash(file_path):
    h=hashlib.md5();f=open(file_path,'rb');[h.update(c) for c in iter(lambda:f.read(4096),b"")];return h.hexdigest()

def extract_metadata_from_archive(file_path):
    series_id, issue_id = None, None
    try:
        if file_path.lower().endswith('.cbz'):
            with zipfile.ZipFile(file_path, 'r') as zf:
                if 'ComicInfo.xml' in zf.namelist():
                    with zf.open('ComicInfo.xml') as f:
                        root = ET.fromstring(f.read()); series_id=root.findtext('.//{*}SeriesID'); issue_id=root.findtext('.//{*}IssueID')
        elif file_path.lower().endswith('.cbr'):
             with rarfile.RarFile(file_path, 'r') as rf:
                if 'ComicInfo.xml' in rf.namelist():
                    with rf.open('ComicInfo.xml') as f:
                        root = ET.fromstring(f.read()); series_id=root.findtext('.//{*}SeriesID'); issue_id=root.findtext('.//{*}IssueID')
    except Exception as e:
        print(f"  [Warning] {os.path.basename(file_path)}: {e}")
    return series_id, issue_id

def scan_library(conn):
    cursor = conn.cursor(); count = 0
    print(f"Starting library scan in: {LIBRARY_DIR}")
    for root, _, files in os.walk(LIBRARY_DIR):
        if root.startswith(INBOX_DIR): continue
        for file in files:
            if file.lower().endswith(('.cbz', '.cbr')):
                file_path = os.path.join(root, file); print(f"Processing: {file}")
                file_size = os.path.getsize(file_path); file_hash = calculate_file_hash(file_path)
                series_id, issue_id = extract_metadata_from_archive(file_path)
                cursor.execute('INSERT OR REPLACE INTO comics (file_path, file_hash, file_size, series_id, issue_id) VALUES (?, ?, ?, ?, ?)',
                               (file_path, file_hash, file_size, series_id, issue_id))
                count += 1
                if count % 100 == 0: conn.commit(); print(f"  ...processed {count} files...")
    conn.commit(); print(f"\nScan complete! Processed {count} files.")

if __name__ == '__main__':
    if "/path/to/" in LIBRARY_DIR: sys.exit("Error: Please update the placeholder paths in the script before running.")
    conn = create_database(); scan_library(conn); conn.close()