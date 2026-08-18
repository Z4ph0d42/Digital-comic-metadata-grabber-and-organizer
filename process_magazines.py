import os
import shutil
import sys
import subprocess
import hashlib
import sqlite3
import time
import re
import zipfile
from datetime import datetime

INBOX_DIR = "/srv/magazines/inbox"
LIBRARY_DIR = "/srv/magazines"
QUARANTINE_DIR = "/srv/magazines/quarantine"

DB_FILE = os.path.expanduser("~/scripts/comic-organizer/library.db")
LOG_FILE = os.path.expanduser("~/scripts/comic-organizer/process_magazines_log.txt")

def log(message):
    print(message)
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    except: pass

def ensure_dirs():
    for d in [INBOX_DIR, QUARANTINE_DIR, LIBRARY_DIR]:
        if not os.path.exists(d): os.makedirs(d)

def calculate_file_hash(filepath):
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for block in iter(lambda: f.read(65536), b''):
                sha256.update(block)
        return sha256.hexdigest()
    except: return None

def check_duplicate(file_hash):
    if not os.path.exists(DB_FILE): return None
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT file_path FROM library WHERE file_hash = ?", (file_hash,))
        result = cursor.fetchone()
        conn.close()
        if result and os.path.exists(result[0]): return result[0]
    except: pass
    return None

def update_database(file_hash, filepath):
    if not file_hash: return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS library (id INTEGER PRIMARY KEY AUTOINCREMENT, file_hash TEXT UNIQUE, file_path TEXT, added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute("INSERT OR REPLACE INTO library (file_hash, file_path) VALUES (?, ?)", (file_hash, filepath))
    conn.commit()
    conn.close()

def parse_magazine_metadata(filename):
    name_without_ext = os.path.splitext(filename)[0]
    year = ""
    month = ""
    issue = ""
    volume = ""

    # Match OMNI_YYYY_MM format explicitly (e.g. OMNI_1988_02)
    match_ym = re.search(r'(19\d{2}|20\d{2})[_\-](\d{1,2})', name_without_ext)
    if match_ym:
        year = match_ym.group(1)
        month = str(int(match_ym.group(2))) # strip leading zero for internal storage
        issue = f"{year}.{int(match_ym.group(2)):02d}"
    else:
        # Fallback year search
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', name_without_ext)
        if year_match: year = year_match.group(1)
        issue = "1"

    return "Omni", year, month, issue, volume

def inject_comic_info_xml(archive_path, meta):
    if not archive_path.lower().endswith('.cbz'): return
    xml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<ComicInfo xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Series>{meta['series']}</Series>
  <Number>{meta['issue']}</Number>
  <Volume>{meta['volume']}</Volume>
  <Year>{meta['year']}</Year>
  <Month>{meta['month']}</Month>
  <Publisher>Omni Publications</Publisher>
</ComicInfo>
"""
    try:
        temp_zip = archive_path + ".tmp"
        with zipfile.ZipFile(archive_path, 'r') as zin, zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename.lower() != 'comicinfo.xml':
                    zout.writestr(item, zin.read(item.filename))
            zout.writestr('ComicInfo.xml', xml_content)
        os.replace(temp_zip, archive_path)
    except Exception as e:
        log(f"XML Injection failed: {e}")

def process_file(filepath):
    if not filepath.lower().endswith('.cbz'): return
    filename = os.path.basename(filepath)
    f_hash = calculate_file_hash(filepath)
    
    series, year, month, issue, volume = parse_magazine_metadata(filename)
    meta = {'series': series, 'year': year, 'month': month, 'issue': issue, 'volume': volume}

    dest_dir = os.path.join(LIBRARY_DIR, "Omni")
    if not os.path.exists(dest_dir): os.makedirs(dest_dir)

    dest_path = os.path.join(dest_dir, filename)
    
    inject_comic_info_xml(filepath, meta)
    shutil.move(filepath, dest_path)
    update_database(f_hash, dest_path)
    log(f"Moved: {filename} -> Issue {issue}")

def main():
    ensure_dirs()
    for root, dirs, files in os.walk(INBOX_DIR):
        for f in files:
            if f.startswith("."): continue
            process_file(os.path.join(root, f))
    subprocess.run(["find", INBOX_DIR, "-mindepth", "1", "-type", "d", "-empty", "-delete"])

if __name__ == "__main__":
    main()
