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
import fitz  # PyMuPDF for PDF to image rendering

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

def convert_pdf_to_cbz(pdf_path):
    """Automatically converts an incoming PDF into a CBZ archive by rendering pages as images."""
    filename = os.path.basename(pdf_path)
    name_without_ext = os.path.splitext(filename)[0]
    cbz_path = os.path.join(INBOX_DIR, name_without_ext + ".cbz")
    temp_dir = pdf_path + "_temp_pages"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        log(f"Converting PDF to CBZ: {filename}")
        doc = fitz.open(pdf_path)
        image_files = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150) # 150 DPI balances quality and file size for magazines
            img_filename = f"page_{page_num+1:04d}.jpg"
            img_path = os.path.join(temp_dir, img_filename)
            pix.save(img_path)
            image_files.append(img_path)
        doc.close()

        # Write images into a new uncompressed CBZ archive
        with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_STORED) as zout:
            for img in image_files:
                zout.write(img, os.path.basename(img))
        
        # Cleanup temporary page images
        for img in image_files:
            os.remove(img)
        os.rmdir(temp_dir)
        
        # Remove original PDF so it doesn't stay in the inbox unprocessed
        os.remove(pdf_path)
        log(f"Successfully converted {filename} -> {os.path.basename(cbz_path)}")
        return cbz_path
    except Exception as e:
        log(f"PDF to CBZ conversion failed for {filename}: {e}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return None

def parse_magazine_metadata(filename):
    name_without_ext = os.path.splitext(filename)[0]
    year = ""
    month = ""
    issue = ""
    volume = ""
    series = "Magazines" # Generic fallback if series isn't matched

    # Check for specific title formats or default naming
    if "Scientific_American" in name_without_ext:
        series = "Scientific American"
    elif "Lain" in name_without_ext:
        series = "Lain Wingraphic"
    elif "Omni" in name_without_ext or name_without_ext.startswith("OMNI"):
        series = "Omni"

    # Match Title_Issue_Year format
    match_special = re.search(r'(?i)^(.*?)_(\d+)_((?:19|20)\d{2})$', name_without_ext)
    if match_special:
        series = match_special.group(1).replace('_', ' ').strip().title()
        issue = match_special.group(2)
        month = issue 
        year = match_special.group(3)
        return series, year, month, issue, volume

    # Match standard YYYY_MM or vYYYY #MM
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
        # Fallback year extractor
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
  <Publisher>Magazine Publications</Publisher>
</ComicInfo>
"""
    try:
        temp_zip = archive_path + ".tmp"
        with zipfile.ZipFile(archive_path, 'r') as zin, zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_STORED) as zout:
            for item in zin.infolist():
                if item.filename.lower() != 'comicinfo.xml':
                    zout.writestr(item, zin.read(item.filename))
            zout.writestr('ComicInfo.xml', xml_content)
        os.replace(temp_zip, archive_path)
    except Exception as e:
        log(f"XML Injection failed: {e}")

def process_file(filepath):
    # Handle PDF conversion first
    if filepath.lower().endswith('.pdf'):
        filepath = convert_pdf_to_cbz(filepath)
        if not filepath: return

    if not filepath.lower().endswith('.cbz'): return
    filename = os.path.basename(filepath)
    f_hash = calculate_file_hash(filepath)

    series, year, month, issue, volume = parse_magazine_metadata(filename)
    meta = {'series': series, 'year': year, 'month': month, 'issue': issue, 'volume': volume}

    dest_dir = os.path.join(LIBRARY_DIR, series)
    if not os.path.exists(dest_dir): os.makedirs(dest_dir)

    if year and month:
        month_padded = str(month).zfill(2) 
        new_filename = f"{series} v{year} #{month_padded}.cbz"
    else:
        new_filename = filename 

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
    
    for d in os.listdir(LIBRARY_DIR):
        dir_path = os.path.join(LIBRARY_DIR, d)
        if os.path.isdir(dir_path) and not os.listdir(dir_path):
            try: os.rmdir(dir_path)
            except: pass

if __name__ == "__main__":
    main()
