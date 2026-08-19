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

def calculate_file_hash(filepath, limit_mb=1):
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            # OPTIMIZATION: Only hash the first 1MB to vastly speed up processing
            sha256.update(f.read(limit_mb * 1024 * 1024))
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
    series = "Omni"

    # 1. Match Title_Issue_Year format (e.g. Best_of_OMNI_1_1980)
    match_special = re.search(r'(?i)^(.*?)_(\d+)_((?:19|20)\d{2})$', name_without_ext)
    if match_special:
        series = match_special.group(1).replace('_', ' ').strip().title()
        issue = match_special.group(2)
        month = issue # Route issue through month to utilize standard filename logic
        year = match_special.group(3)
        return series, year, month, issue, volume

    # 2. Match both standard OMNI_YYYY_MM format AND already-formatted "Omni vYYYY #MM"
    # This prevents the script from overwriting metadata with Issue #1 if the file was already renamed
    match_ym = re.search(r'(?i)^(.*?)[_\s]+v?(19\d{2}|20\d{2})[_\s\-#]+(\d{1,2})$', name_without_ext)
    if match_ym:
        extracted_series = match_ym.group(1).replace('_', ' ').strip().title()
        if extracted_series:
            series = extracted_series
        year = match_ym.group(2)
        month_val = int(match_ym.group(3))
        month = str(month_val)
        issue = str(month_val)
    else:
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', name_without_ext)
        if year_match: year = year_match.group(1)
        issue = "1"

    return series, year, month, issue, volume

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
        # OPTIMIZATION: Use ZIP_STORED instead of ZIP_DEFLATED to prevent CPU-heavy re-compression of images
        with zipfile.ZipFile(archive_path, 'r') as zin, zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_STORED) as zout:
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

    # Dynamically set destination directory based on the series name
    dest_dir = os.path.join(LIBRARY_DIR, series)
    if not os.path.exists(dest_dir): os.makedirs(dest_dir)

    # Apply Kavita-friendly naming convention
    if year and month:
        month_padded = str(month).zfill(2) # Zero-pads single digits
        new_filename = f"{series} v{year} #{month_padded}.cbz"
    else:
        new_filename = filename # Fallback to original name if parsing fails entirely

    dest_path = os.path.join(dest_dir, new_filename)

    inject_comic_info_xml(filepath, meta)
    shutil.move(filepath, dest_path)
    log(f"Processed: {filename} -> {new_filename}")
    update_database(f_hash, dest_path)

def main():
    ensure_dirs()
    
    for root, dirs, files in os.walk(INBOX_DIR):
        for f in files:
            if f.startswith("."): continue
            process_file(os.path.join(root, f))

    subprocess.run(["find", INBOX_DIR, "-mindepth", "1", "-type", "d", "-empty", "-delete"])
    
    # Clean up empty directories safely across the whole library
    for d in os.listdir(LIBRARY_DIR):
        dir_path = os.path.join(LIBRARY_DIR, d)
        if os.path.isdir(dir_path) and not os.listdir(dir_path):
            try: os.rmdir(dir_path)
            except: pass

if __name__ == "__main__":
    main()
