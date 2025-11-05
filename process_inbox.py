import os
import subprocess
import shutil
import sys
import sqlite3
import hashlib
import logging
import zipfile
import rarfile
import xml.etree.ElementTree as ET
import fitz
import re

# --- CONFIGURATION ---
# PLEASE UPDATE THESE PATHS BEFORE RUNNING
INBOX_DIR = "/path/to/your/inbox"
LIBRARY_DIR = "/path/to/your/comic_library"
QUARANTINE_DIR = "/path/to/your/quarantine_folder"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__)) # Assumes DB is in the same folder as the script
DB_FILE = os.path.join(PROJECT_DIR, "comics_library.db")
LOG_FILE = os.path.join(PROJECT_DIR, "process_inbox.log")
COMIC_TAGGER_EXE = "/path/to/your/venv/bin/comictagger"
API_KEY_FILE = os.path.expanduser("~/.comic_vine_api_key")

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

# --- HELPER FUNCTIONS ---
def get_db_connection(): return sqlite3.connect(DB_FILE)
def calculate_file_hash(file_path):
    h=hashlib.md5();f=open(file_path,'rb');[h.update(c) for c in iter(lambda:f.read(4096),b"")];return h.hexdigest()
def move_to_quarantine(file_path,reason):
    if not os.path.exists(QUARANTINE_DIR): os.makedirs(QUARANTINE_DIR)
    dest=os.path.join(QUARANTINE_DIR,os.path.basename(file_path)); shutil.move(file_path,dest)
    logging.info(f"QUARANTINED | {dest} | {reason}")
    print(f"Moved '{os.path.basename(file_path)}' to quarantine. Reason: {reason}")
def add_to_library_db(file_path,metadata):
    c=get_db_connection();s,h=os.path.getsize(file_path),calculate_file_hash(file_path)
    c.execute('INSERT OR REPLACE INTO comics (file_path,file_hash,file_size,series_id,issue_id) VALUES (?,?,?,?,?)',(file_path,h,s,metadata.get('series_id'),metadata.get('issue_id')));c.commit();c.close()
def extract_metadata_from_tagged_file(file_path):
    metadata={};
    try:
        if file_path.lower().endswith('.cbz'):
            with zipfile.ZipFile(file_path,'r') as zf:
                if 'ComicInfo.xml' in zf.namelist():
                    with zf.open('ComicInfo.xml') as f:
                        root=ET.fromstring(f.read());metadata['issue_id']=root.findtext('.//{*}IssueID');metadata['series']=root.findtext('.//{*}Series');metadata['year']=root.findtext('.//{*}Year');metadata['series_id']=root.findtext('.//{*}SeriesID')
    except: pass
    return metadata
def parse_metadata_from_filename(filename):
    metadata={};
    match=re.match(r'^(.*?) #?(\d+[.\d]*)\s*\((\d{4})\)',filename)
    if match: metadata['series']=match.group(1).strip();metadata['year']=match.group(3).strip()
    return metadata
def convert_pdf_to_cbz(pdf_path):
    cbz_path=os.path.join(os.path.dirname(pdf_path),f"{os.path.splitext(os.path.basename(pdf_path))[0]}.cbz");print(f"Converting PDF to CBZ...")
    try:
        doc=fitz.open(pdf_path);
        with zipfile.ZipFile(cbz_path,'w',zipfile.ZIP_DEFLATED) as zf:[zf.writestr(f"page_{i+1:03d}.png",p.get_pixmap(dpi=150).tobytes("png")) for i,p in enumerate(doc)]
        doc.close();return cbz_path
    except: return None

def process_inbox():
    """Main function with the final fallback logic and bugfix."""
    try:
        with open(os.path.expanduser(API_KEY_FILE), 'r') as f: cv_api_key = f.read().strip()
    except FileNotFoundError: sys.exit("ERROR: API Key file not found.")

    if not os.path.exists(INBOX_DIR): os.makedirs(INBOX_DIR)
    
    files = [f for f in os.listdir(INBOX_DIR) if os.path.isfile(os.path.join(INBOX_DIR, f))]
    if not files: print("Inbox is empty."); return

    print(f"Found {len(files)} files to process.")
    for filename in files:
        metadata = {} # Reset metadata for every single file to prevent stale data
        
        current_path = os.path.join(INBOX_DIR, filename)
        
        if not filename.lower().endswith(('.cbz', '.cbr', '.pdf')): continue

        print("-" * 40); print(f"Processing: {filename}")

        if filename.lower().endswith('.pdf'):
            new_path = convert_pdf_to_cbz(current_path)
            if new_path: os.remove(current_path); current_path = new_path
            else: move_to_quarantine(current_path, "PDF conversion failed"); continue
        
        if calculate_file_hash(current_path) in [r[0] for r in get_db_connection().execute("SELECT file_hash FROM comics").fetchall()]:
             move_to_quarantine(current_path, "Duplicate file detected"); continue

        print("Attempting to tag with comictagger...")
        command = [COMIC_TAGGER_EXE, "-s", "-t", "CR", "-o", "-f", "--cv-api-key", cv_api_key, current_path]
        subprocess.run(command, capture_output=True, text=True)

        metadata = extract_metadata_from_tagged_file(current_path)

        if not metadata.get('issue_id'):
            print("Tagging failed. Falling back to filename parsing.")
            filename_meta = parse_metadata_from_filename(os.path.basename(current_path))
            if filename_meta:
                metadata = filename_meta
            else:
                metadata['series'] = os.path.splitext(os.path.basename(current_path))[0]
                metadata['year'] = '0'
        else:
            print("Tagging successful!")

        if not metadata.get('series'):
            move_to_quarantine(current_path, "Could not determine series name")
            continue

        try:
            safe_series = metadata['series'].replace('/', '-').replace(':', '')
            year_str = metadata.get('year', '0')
            final_dir = os.path.join(LIBRARY_DIR, f"{safe_series} ({year_str})")
            os.makedirs(final_dir, exist_ok=True)
            final_path = os.path.join(final_dir, os.path.basename(current_path))
            shutil.move(current_path, final_path)
            print(f"Moved to: {final_path}")
            add_to_library_db(final_path, metadata)
        except Exception as e:
            print(f"ERROR during move: {e}")

if __name__ == "__main__":
    process_inbox()