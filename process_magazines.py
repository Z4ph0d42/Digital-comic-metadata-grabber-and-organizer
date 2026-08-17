import os
import shutil
import sys
import subprocess
import hashlib
import sqlite3
import time
import re
import zipfile
import gc
from datetime import datetime
from io import BytesIO

# --- CONFIGURATION ---
INBOX_DIR = "/srv/magazines/inbox"
LIBRARY_DIR = "/srv/magazines"
QUARANTINE_DIR = "/srv/magazines/quarantine"

# Helper Paths
DB_FILE = os.path.expanduser("~/scripts/comic-organizer/library.db")
LOG_FILE = os.path.expanduser("~/scripts/comic-organizer/process_magazines_log.txt")
CV_API_KEY = "f33a0650ac4c04e3c964c38f7e86f69723344bce" 
COMIC_TAGGER_BIN = os.path.expanduser("~/scripts/comic-organizer/venv/bin/comictagger")

# Dependencies
try:
    from pdf2image import convert_from_path
except ImportError:
    print("Error: pdf2image not found.")

# --- HELPER FUNCTIONS ---

def log(message):
    print(message)
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    except: pass

def ensure_dirs():
    if not os.path.exists(INBOX_DIR): os.makedirs(INBOX_DIR)
    if not os.path.exists(QUARANTINE_DIR): os.makedirs(QUARANTINE_DIR)

def calculate_file_hash(filepath):
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for block in iter(lambda: f.read(65536), b''):
                sha256.update(block)
        return sha256.hexdigest()
    except: return None

def check_duplicate(file_hash):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM library WHERE file_hash = ?", (file_hash,))
    result = cursor.fetchone()
    conn.close()
    if result and os.path.exists(result[0]):
        return result[0]
    return None

def is_comic_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    return ext in ['.cbz', '.cbr', '.pdf']

def move_to_quarantine(filepath, reason_category):
    dest_folder = os.path.join(QUARANTINE_DIR, reason_category)
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    filename = os.path.basename(filepath)
    dest_path = os.path.join(dest_folder, filename)

    if os.path.exists(dest_path):
        base, ext = os.path.splitext(filename)
        dest_path = os.path.join(dest_folder, f"{base}_{int(time.time())}{ext}")

    shutil.move(filepath, dest_path)
    log(f"QUARANTINED [{reason_category}]: {filename}")

def guess_series_name(filename):
    """
    Highly aggressive folder name guesser.
    It will chop off anything that looks like an issue number, date, or volume.
    """
    name = os.path.splitext(filename)[0]
    clean_name = name.replace('_', ' ').replace('.', ' ').strip()
    
    if " - " in clean_name:
        clean_name = clean_name.split(" - ")[0].strip()

    # Regex to find the first occurrence of issue trackers and chop everything after
    cutoff_pattern = re.compile(
        r'(?i)('
        r' \bvol.*|'          # " Volume 1" or " vol 2"
        r' \bissue.*|'        # " Issue 3"
        r' \bno\..*|'         # " no. 4"
        r' #\d.*|'              # " #5"
        r' \b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b.*|' # Months
        r' (19|20)\d{2}\b.*|' # Years like 19xx or 20xx
        r' \d{1,4}(-\d{1,4})?$' # Trailing issue numbers like " 01", " 01-02", " 123"
        r')'
    )
    
    match = cutoff_pattern.search(clean_name)
    if match:
        possible_name = clean_name[:match.start()].strip()
        if len(possible_name) > 2: # Make sure we're not left with just "a" or "the"
            return possible_name

    return clean_name # Fallback to the cleaned name if no pattern matches

def move_to_library_smart_fallback(filepath):
    filename = os.path.basename(filepath)
    
    series_folder = guess_series_name(filename)
    if not series_folder:
        series_folder = "Unsorted Magazines"

    dest_dir = os.path.join(LIBRARY_DIR, series_folder)

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    dest_path = os.path.join(dest_dir, filename)

    if os.path.exists(dest_path):
        base, ext = os.path.splitext(filename)
        dest_path = os.path.join(dest_dir, f"{base}_{int(time.time())}{ext}")

    try:
        shutil.move(filepath, dest_path)
        log(f"Moved to Library: {series_folder}/{filename}")
    except Exception as e:
        log(f"Fallback Move Failed: {e}")

def convert_pdf_to_cbz(pdf_path):
    log(f"Converting PDF to CBZ: {os.path.basename(pdf_path)}...")
    try:
        cbz_path = os.path.splitext(pdf_path)[0] + ".cbz"
        
        if os.path.exists(cbz_path):
             cbz_path = os.path.splitext(pdf_path)[0] + f"_{int(time.time())}.cbz"

        images = convert_from_path(pdf_path, dpi=200, thread_count=2, fmt='jpeg')

        with zipfile.ZipFile(cbz_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, image in enumerate(images):
                img_filename = f"page_{i:04d}.jpg"
                img_byte_arr = BytesIO()
                image.save(img_byte_arr, format='JPEG', quality=85)
                zf.writestr(img_filename, img_byte_arr.getvalue())
        
        images.clear()
        gc.collect()

        if zipfile.is_zipfile(cbz_path):
            log(f"  - Conversion success. Removing original PDF.")
            os.remove(pdf_path)
            return cbz_path
        else:
            log("  - Error: Converted CBZ invalid.")
            return None

    except Exception as e:
        log(f"  - PDF Conversion Failed (Skipping file): {e}")
        return None

def clean_empty_dirs(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        for name in dirs:
            path = os.path.join(root, name)
            try:
                if not os.listdir(path):
                    os.rmdir(path)
            except: pass

# --- MAIN PROCESS ---

def process_file(filepath):
    if not os.path.exists(filepath): return
    if not is_comic_file(filepath): return

    filename = os.path.basename(filepath)
    log(f"Processing: {filename}")
    
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        try:
            new_cbz = convert_pdf_to_cbz(filepath)
            if new_cbz:
                filepath = new_cbz 
                filename = os.path.basename(filepath)
            else:
                move_to_quarantine(filepath, "PDF_Conversion_Failed")
                return
        except Exception as e:
            log(f"Critical error converting PDF: {e}")
            return

    f_hash = calculate_file_hash(filepath)
    existing_path = check_duplicate(f_hash)
    if existing_path:
        log(f"Duplicate of: {existing_path}")
        move_to_quarantine(filepath, "Duplicate")
        return

    move_to_library_smart_fallback(filepath)

def main():
    ensure_dirs()
    
    files_to_process = []
    for root, dirs, files in os.walk(INBOX_DIR):
        for f in files:
            if f.startswith("."): continue
            files_to_process.append(os.path.join(root, f))

    if not files_to_process:
        return

    log(f"Found {len(files_to_process)} magazines in Inbox.")

    for path in files_to_process:
        try:
            if os.path.exists(path):
                process_file(path)
        except Exception as e:
            log(f"CRASH on file {path}: {e}")
            continue

    clean_empty_dirs(INBOX_DIR)

if __name__ == "__main__":
    main()
