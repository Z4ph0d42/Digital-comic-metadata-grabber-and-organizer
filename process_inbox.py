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

# --- CONFIGURATION ---
# Update these paths to match your environment
INBOX_DIR = "/path/to/comics/inbox"
LIBRARY_DIR = "/path/to/comics/library"
QUARANTINE_DIR = "/path/to/comics/quarantine"

# Path to your library database (created by build_library_db.py)
DB_FILE = os.path.expanduser("~/scripts/comic-organizer/library.db")
LOG_FILE = os.path.expanduser("~/scripts/comic-organizer/process_log.txt")

# Path to comictagger executable (usually inside your venv bin)
COMIC_TAGGER_BIN = os.path.expanduser("~/scripts/comic-organizer/venv/bin/comictagger")

# ComicVine API Key (Get one at comicvine.gamespot.com/api)
CV_API_KEY = "YOUR_API_KEY_HERE"

# --- DEPENDENCY CHECK ---
try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF not found. Install it via pip install PyMuPDF")
try:
    import rarfile
except ImportError:
    print("Error: rarfile not found. Install it via pip install rarfile")

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
    """Calculates SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for block in iter(lambda: f.read(65536), b''):
                sha256.update(block)
        return sha256.hexdigest()
    except: return None

def check_duplicate(file_hash):
    """Checks if file hash exists in the library database."""
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

def is_image_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']

def is_valid_archive(filepath):
    """Validates that CBZ/CBR/PDF files are not corrupt."""
    try:
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.pdf':
            doc = fitz.open(filepath)
            valid = doc.page_count > 0
            doc.close()
            return valid
        elif ext == '.cbz':
            import zipfile
            return zipfile.is_zipfile(filepath)
        elif ext == '.cbr':
            return rarfile.is_rarfile(filepath)
    except:
        return False
    return True

def move_to_quarantine(filepath, reason_category):
    """Moves problematic files to a Quarantine subfolder."""
    try:
        rel_path = os.path.relpath(os.path.dirname(filepath), INBOX_DIR)
    except ValueError:
        rel_path = ""
    if rel_path == ".": rel_path = ""

    dest_folder = os.path.join(QUARANTINE_DIR, reason_category, rel_path)
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    
    filename = os.path.basename(filepath)
    dest_path = os.path.join(dest_folder, filename)
    
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(filename)
        dest_path = os.path.join(dest_folder, f"{base}_{int(time.time())}{ext}")
        
    shutil.move(filepath, dest_path)
    log(f"QUARANTINED [{reason_category}]: {filename}")

def move_to_library_fallback(filepath):
    """
    Fallback Mode: If tagging fails, move file to Library preserving its 
    current folder structure instead of quarantining it.
    """
    try:
        rel_path = os.path.relpath(os.path.dirname(filepath), INBOX_DIR)
    except ValueError:
        rel_path = ""
    
    if rel_path == ".": 
        dest_dir = LIBRARY_DIR
    else:
        dest_dir = os.path.join(LIBRARY_DIR, rel_path)

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
        
    filename = os.path.basename(filepath)
    dest_path = os.path.join(dest_dir, filename)
    
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(filename)
        dest_path = os.path.join(dest_dir, f"{base}_{int(time.time())}{ext}")
    
    shutil.move(filepath, dest_path)
    log(f"Fallback: Moved to Library (Untagged): {os.path.join(rel_path, filename)}")

def clean_empty_dirs(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        for name in dirs:
            path = os.path.join(root, name)
            try:
                if not os.listdir(path):
                    os.rmdir(path)
            except: pass

def parse_metadata(output):
    meta = {}
    for line in output.splitlines():
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip().lower()
            val = parts[1].strip()
            meta[key] = val
    return meta

def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '', name)

def smart_rename_if_generic(filepath):
    """Renames 'Issue #1.cbz' to 'ParentFolder #1.cbz' to help the scraper."""
    filename = os.path.basename(filepath)
    parent_dir = os.path.basename(os.path.dirname(filepath))
    
    if re.match(r'^(issue|chapter|\d+|#)', filename, re.IGNORECASE):
        if parent_dir.lower() not in ['inbox', 'comics', 'download', 'completed']:
            clean_fname = re.sub(r'^(issue\s*|chapter\s*)', '', filename, flags=re.IGNORECASE)
            new_name = f"{parent_dir} #{clean_fname.lstrip('# ')}"
            new_path = os.path.join(os.path.dirname(filepath), new_name)
            try:
                os.rename(filepath, new_path)
                log(f"Auto-Renamed generic file: {filename} -> {new_name}")
                return new_path
            except: pass
    return filepath

def convert_folders_to_cbz(root_dir):
    """Converts directories containing images into .cbz files."""
    log("--- Scanning for folders to convert to CBZ ---")
    for root, dirs, files in os.walk(root_dir):
        images = [f for f in files if is_image_file(f)]
        # If folder has images, no subdirs, and is not root
        if images and not dirs and root != root_dir:
            folder_name = os.path.basename(root)
            cbz_name = f"{folder_name}.cbz"
            cbz_path = os.path.join(os.path.dirname(root), cbz_name)
            
            if os.path.exists(cbz_path):
                 cbz_path = os.path.join(os.path.dirname(root), f"{folder_name}_{int(time.time())}.cbz")

            log(f"Packing folder to CBZ: {folder_name}...")
            try:
                with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for img in images:
                        src_path = os.path.join(root, img)
                        zf.write(src_path, arcname=img)
                if zipfile.is_zipfile(cbz_path):
                    log(f"  - Created: {cbz_name}")
                    shutil.rmtree(root)
                else:
                    log("  - Error: Created ZIP appears invalid.")
            except Exception as e:
                log(f"  - Error packing CBZ: {e}")

# --- MAIN PROCESS ---

def process_file(filepath):
    # 1. Filter Non-Comics
    if not is_comic_file(filepath):
        return

    # 2. Smart Rename
    filepath = smart_rename_if_generic(filepath)
    filename = os.path.basename(filepath)
    
    log(f"Processing: {filename}")
    TIMEOUT_SECONDS = 120

    # 3. Integrity Check
    if not is_valid_archive(filepath):
        move_to_quarantine(filepath, "Corrupt_Archive")
        return

    # 4. Duplicate Check
    f_hash = calculate_file_hash(filepath)
    existing_path = check_duplicate(f_hash)
    if existing_path:
        log(f"Duplicate of: {existing_path}")
        move_to_quarantine(filepath, "Duplicate")
        return

    ext = os.path.splitext(filepath)[1].lower()
    
    # 5. Handle PDFs (Move Only)
    if ext == ".pdf":
        pdf_folder = os.path.join(LIBRARY_DIR, "PDF_Comics")
        if not os.path.exists(pdf_folder): os.makedirs(pdf_folder)
        final_path = os.path.join(pdf_folder, filename)
        if os.path.exists(final_path):
             base, e = os.path.splitext(filename)
             final_path = os.path.join(pdf_folder, f"{base}_{int(time.time())}{e}")
        shutil.move(filepath, final_path)
        log(f"PDF moved to: {final_path}")
        return

    # 6. Tagging (ComicTagger)
    cmd_tag = [
        COMIC_TAGGER_BIN, "-s", "--cv-api-key", CV_API_KEY, "--type", "cr", filepath
    ]
    
    try:
        result_tag = subprocess.run(cmd_tag, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        log("  - TIMEOUT: Processing took too long. Quarantining.")
        move_to_quarantine(filepath, "Timeout_TooLarge")
        return

    output_combined = (result_tag.stdout + result_tag.stderr).lower()
    
    # Check Tagging Results
    if result_tag.returncode != 0 or "multiple matches" in output_combined or "select from" in output_combined:
        if "no match found" in output_combined:
            log("  - No match found. Moving to Library as-is.")
            move_to_library_fallback(filepath)
            return
        if "multiple matches" in output_combined or "select from" in output_combined:
             log("  - Ambiguous Match. Moving to Library as-is.")
             move_to_library_fallback(filepath)
             return

        # Script error or other failure
        log(f"  - Tagging failed (Code {result_tag.returncode}). Moving to Library as-is.")
        move_to_library_fallback(filepath)
        return

    # 7. Read Metadata & Move
    cmd_read = [COMIC_TAGGER_BIN, "-p", filepath]
    try:
        result_read = subprocess.run(cmd_read, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        move_to_quarantine(filepath, "Timeout_Read")
        return

    meta = parse_metadata(result_read.stdout)
    
    publisher = sanitize_filename(meta.get('publisher', 'Unknown_Publisher'))
    series = sanitize_filename(meta.get('series', 'Unknown_Series'))
    volume = sanitize_filename(meta.get('volume', ''))
    issue = sanitize_filename(meta.get('issue', ''))
    year = sanitize_filename(meta.get('year', ''))
    
    if not series or series == "Unknown_Series":
        log("  - Metadata incomplete. Moving to Library as-is.")
        move_to_library_fallback(filepath)
        return

    # Construct Optimized Path
    vol_str = f" v{volume}" if volume else ""
    series_folder_name = f"{series}{vol_str}"
    dest_dir = os.path.join(LIBRARY_DIR, publisher, series_folder_name)
    
    year_str = f" ({year})" if year else ""
    new_filename = f"{series} #{issue}{year_str}{ext}"
    
    full_dest_path = os.path.join(dest_dir, new_filename)
    
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
        
    if os.path.exists(full_dest_path):
         base, e = os.path.splitext(new_filename)
         full_dest_path = os.path.join(dest_dir, f"{base}_{int(time.time())}{e}")
    
    try:
        shutil.move(filepath, full_dest_path)
        log(f"  - Success! Moved to: {full_dest_path}")
    except Exception as e:
        log(f"  - Move Failed: {e}")
        move_to_quarantine(filepath, "Move_Failed")

def main():
    ensure_dirs()
    
    # Step 1: Convert loose folders to CBZ
    convert_folders_to_cbz(INBOX_DIR)
    
    # Step 2: Process Files
    files_to_process = []
    for root, dirs, files in os.walk(INBOX_DIR):
        for f in files:
            if f.startswith("."): continue
            files_to_process.append(os.path.join(root, f))
            
    if not files_to_process:
        log("Inbox empty.")
        return

    log(f"Found {len(files_to_process)} files in Inbox.")
    
    for path in files_to_process:
        if os.path.exists(path):
            process_file(path)
            
    clean_empty_dirs(INBOX_DIR)
    log("Batch complete.")

if __name__ == "__main__":
    main()