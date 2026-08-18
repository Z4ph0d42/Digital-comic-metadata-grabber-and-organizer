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
import difflib
from datetime import datetime
from io import BytesIO

# --- CONFIGURATION ---
INBOX_DIR = "/srv/magazines/inbox"
LIBRARY_DIR = "/srv/magazines"
QUARANTINE_DIR = "/srv/magazines/quarantine"

# Helper Paths
DB_FILE = os.path.expanduser("~/scripts/comic-organizer/library.db")
LOG_FILE = os.path.expanduser("~/scripts/comic-organizer/process_magazines_log.txt")

# Dependencies check
try:
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image
except ImportError:
    print("Error: pdf2image, PIL, or pytesseract not found. Run pip install.")

# --- HELPER FUNCTIONS ---

def log(message):
    print(message)
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    except: pass

def ensure_dirs():
    for d in [INBOX_DIR, QUARANTINE_DIR, LIBRARY_DIR]:
        if not os.path.exists(d): 
            os.makedirs(d)

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
        if result and os.path.exists(result[0]):
            return result[0]
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

def is_comic_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    return ext in ['.cbz', '.cbr', '.pdf']

def move_to_quarantine(filepath, reason_category):
    dest_folder = os.path.join(QUARANTINE_DIR, reason_category)
    if not os.path.exists(dest_folder): os.makedirs(dest_folder)
    filename = os.path.basename(filepath)
    dest_path = os.path.join(dest_folder, filename)
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(filename)
        dest_path = os.path.join(dest_folder, f"{base}_{int(time.time())}{ext}")
    shutil.move(filepath, dest_path)
    log(f"QUARANTINED [{reason_category}]: {filename}")

def guess_series_name(filename):
    name = os.path.splitext(filename)[0]
    clean_name = name.replace('_', ' ').replace('.', ' ').strip()
    if " - " in clean_name:
        clean_name = clean_name.split(" - ")[0].strip()

    cutoff_pattern = re.compile(
        r'(?i)('
        r' \bvol.*|'
        r' \bissue.*|'
        r' \bno\..*|'
        r' #\d.*|'
        r' \b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b.*|'
        r' \b\d{1,4}\b\s*(?:19|20)\d{2}\b.*|'  # <-- NEW: Cuts off if it spots a lone number right before a year
        r' (19|20)\d{2}\b.*|'
        r' \d{1,4}(-\d{1,4})?$'
        r')'
    )
    match = cutoff_pattern.search(clean_name)
    if match:
        possible_name = clean_name[:match.start()].strip()
        if len(possible_name) > 2:
            clean_name = possible_name

    clean_name = re.sub(r'(?i)\b(magazine|quarterly|the hacker quarterly)\b', '', clean_name).strip()
    clean_name = re.sub(r'[- ]+$', '', clean_name)

    return clean_name.title() if len(clean_name) > 1 else "Unknown Series"

def find_best_library_match(guessed_name):
    if not os.path.exists(LIBRARY_DIR): return guessed_name
    existing_folders = [d for d in os.listdir(LIBRARY_DIR) if os.path.isdir(os.path.join(LIBRARY_DIR, d))]
    
    for folder in existing_folders:
        base_folder = re.sub(r'(?i)\s+v\d+.*$', '', folder).strip()
        if base_folder.lower() == guessed_name.lower():
            return base_folder
            
    base_folders = list(set([re.sub(r'(?i)\s+v\d+.*$', '', f).strip() for f in existing_folders]))
    matches = difflib.get_close_matches(guessed_name, base_folders, n=1, cutoff=0.7)
    if matches:
        log(f"  - Fuzzy Matched '{guessed_name}' to existing library base '{matches[0]}'")
        return matches[0]
        
    return guessed_name

def parse_magazine_metadata(filename):
    name_without_ext = os.path.splitext(filename)[0]
    series = guess_series_name(filename)
    year = ""
    month = ""
    issue = ""
    volume = ""

    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', name_without_ext)
    if year_match: year = year_match.group(1)

    vol_match = re.search(r'(?:vol(?:ume)?|\bv)\.?\s*(\d+|forty|thirty|twenty|ten)', name_without_ext, re.IGNORECASE)
    if vol_match:
        raw_vol = vol_match.group(1).lower()
        word_to_num = {'ten': '10', 'twenty': '20', 'thirty': '30', 'forty': '40'}
        volume = word_to_num.get(raw_vol, raw_vol).capitalize()

    months = {
        'january': '1', 'jan': '1', 'february': '2', 'feb': '2',
        'march': '3', 'mar': '3', 'april': '4', 'apr': '4',
        'may': '5', 'june': '6', 'jun': '6', 'july': '7', 'jul': '7',
        'august': '8', 'aug': '8', 'september': '9', 'sep': '9', 'sept': '9',
        'october': '10', 'oct': '10', 'november': '11', 'nov': '11',
        'december': '12', 'dec': '12'
    }
    for m_name, m_num in months.items():
        if re.search(r'\b' + m_name + r'\b', name_without_ext, re.IGNORECASE):
            month = m_num
            break

    issue_match = re.search(r'(?:issue|no\.?|#)\s*(\d+)', name_without_ext, re.IGNORECASE)
    if issue_match:
        issue = issue_match.group(1)
    else:
        num_match = re.search(r'\b(\d{1,4})\b', name_without_ext)
        if num_match and num_match.group(1) != year and num_match.group(1) != volume:
            issue = num_match.group(1)

    if not issue: issue = "1"

    return series, year, month, issue, volume

def fill_metadata_gaps_with_ocr(filepath, meta):
    if meta['year'] and meta['month']:
        return meta

    log(f"  - Metadata gaps detected. Spinning up OCR cover scanner for {meta['series']}...")
    
    try:
        cover_image = None
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.pdf':
            cover_image = convert_from_path(filepath, first_page=1, last_page=1)[0]
        elif ext == '.cbz':
            with zipfile.ZipFile(filepath, 'r') as zf:
                image_files = [f for f in zf.namelist() if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                image_files.sort()
                if image_files:
                    with zf.open(image_files[0]) as f:
                        cover_image = Image.open(f).copy()
        
        if not cover_image:
            log("  - Could not extract cover image for OCR.")
            return meta

        raw_text = pytesseract.image_to_string(cover_image).lower()

        if not meta['year']:
            year_match = re.search(r'\b(19\d{2}|20\d{2})\b', raw_text)
            if year_match:
                meta['year'] = year_match.group(1)
                log(f"  - OCR found Year: {meta['year']}")

        if not meta['month']:
            months = {
                'january': '1', 'february': '2', 'march': '3', 'april': '4',
                'may': '5', 'june': '6', 'july': '7', 'august': '8',
                'september': '9', 'october': '10', 'november': '11', 'december': '12',
                'jan': '1', 'feb': '2', 'mar': '3', 'apr': '4', 'aug': '8', 
                'sept': '9', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            for m_name, m_num in months.items():
                if re.search(r'\b' + m_name + r'\b', raw_text):
                    meta['month'] = m_num
                    log(f"  - OCR found Month: {m_name.capitalize()} ({m_num})")
                    break

    except Exception as e:
        log(f"  - OCR Error: {e}")

    return meta

def inject_comic_info_xml(cbz_path, meta):
    xml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<ComicInfo xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Series>{meta['series']}</Series>
  <Number>{meta['issue']}</Number>
  <Volume>{meta['volume']}</Volume>
  <Year>{meta['year']}</Year>
  <Month>{meta['month']}</Month>
  <Publisher>Magazines</Publisher>
</ComicInfo>
"""
    try:
        temp_zip = cbz_path + ".tmp"
        with zipfile.ZipFile(cbz_path, 'r') as zin, zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename.lower() != 'comicinfo.xml':
                    zout.writestr(item, zin.read(item.filename))
            zout.writestr('ComicInfo.xml', xml_content)
        os.replace(temp_zip, cbz_path)
        log(f"  - Injected ComicInfo.xml metadata successfully.")
    except Exception as e:
        log(f"  - Warning: Failed to inject ComicInfo.xml: {e}")

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
            return None
    except Exception as e:
        log(f"  - PDF Conversion Failed: {e}")
        return None

def clean_empty_dirs(directory):
    subprocess.run(["find", directory, "-mindepth", "1", "-type", "d", "-empty", "-delete"])

# --- MAIN PROCESS ---

def process_file(filepath):
    if not os.path.exists(filepath): return
    if not is_comic_file(filepath): return

    filename = os.path.basename(filepath)
    folder_path = os.path.dirname(filepath)
    relative_structure = os.path.relpath(folder_path, INBOX_DIR)
    is_root_file = (relative_structure == ".")

    log(f"Processing Magazine: {filename}")

    f_hash = calculate_file_hash(filepath)
    existing_path = check_duplicate(f_hash)
    if existing_path:
        log(f"Duplicate of: {existing_path}. Quarantining.")
        move_to_quarantine(filepath, "Duplicate")
        return

    series_name, year, month, issue, volume = parse_magazine_metadata(filename)
    if not is_root_file:
        series_name = os.path.basename(relative_structure)
    else:
        series_name = find_best_library_match(series_name)

    meta = {'series': series_name, 'year': year, 'month': month, 'issue': issue, 'volume': volume}

    meta = fill_metadata_gaps_with_ocr(filepath, meta)

    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        new_cbz = convert_pdf_to_cbz(filepath)
        if new_cbz:
            filepath = new_cbz
            filename = os.path.basename(filepath)
        else:
            move_to_quarantine(filepath, "PDF_Conversion_Failed")
            return

    if series_name in os.listdir(LIBRARY_DIR) and os.path.isdir(os.path.join(LIBRARY_DIR, series_name)):
        series_folder_name = series_name
    else:
        vol_str = f" v{meta['volume']}" if meta['volume'] and meta['volume'] != "None" else ""
        series_folder_name = f"{meta['series']}{vol_str}"

    dest_dir = os.path.join(LIBRARY_DIR, series_folder_name)
    if not os.path.exists(dest_dir): os.makedirs(dest_dir)

    dest_path = os.path.join(dest_dir, filename)
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(filename)
        dest_path = os.path.join(dest_dir, f"{base}_{int(time.time())}{ext}")

    try:
        xml_meta = meta.copy()
        xml_meta['series'] = meta['series'] 
        
        inject_comic_info_xml(filepath, xml_meta)
        shutil.move(filepath, dest_path)
        update_database(f_hash, dest_path)
        log(f"Moved to Library: {dest_path}")
    except Exception as e:
        log(f"Move Failed: {e}")

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
