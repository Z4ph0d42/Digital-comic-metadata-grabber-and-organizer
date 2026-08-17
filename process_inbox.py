import os
import subprocess
import shutil
import logging
import requests
import re
import sqlite3
import hashlib

# --- CONFIGURATION ---
INBOX = "/srv/comics/inbox"
LIBRARY = "/srv/comics"
DUPLICATES = "/srv/comics/duplicates"
LOG_FILE = "/home/james/scripts/comic-organizer/process_log.txt"
TAGGER_BIN = "/home/james/scripts/comic-organizer/venv/bin/comictagger"
API_KEY = "f33a0650ac4c04e3c964c38f7e86f69723344bce"
DB_FILE = "/home/james/scripts/comic-organizer/library.db"

# Kavita Configuration
KAVITA_URL = "http://192.168.2.51:5000"
KAVITA_API_KEY = "db1210d2-8dfc-44fb-8a5d-ec1f22a08985"

# Forced Series Mapping (ORDER MATTERS: Most specific to least specific)
SERIES_MAP = {
    "uncanny": "36402",    # Uncanny X-Force
    "deadpool": "75151",   # Deadpool vs. X-Force
    "x-statix": "10020",   # X-Statix
    "she-hulk": "3960",    # Sensational She-Hulk
    "v1": "4101",          # X-Force Vol 1 (1991)
    "v2": "18165",         # X-Force Vol 2 (2004)
    "v3": "20743"          # X-Force Vol 3 (2008)
}

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, 
                    format='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# --- DATABASE AND HASH FUNCTIONS ---
def calculate_file_hash(filepath):
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for block in iter(lambda: f.read(65536), b''):
                sha256.update(block)
        return sha256.hexdigest()
    except Exception as e:
        logging.error(f"Hash calculation failed for {filepath}: {e}")
        return None

def check_duplicate(file_hash):
    if not os.path.exists(DB_FILE):
        return None
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT file_path FROM library WHERE file_hash = ?", (file_hash,))
        result = cursor.fetchone()
        conn.close()
        if result and os.path.exists(result[0]):
            return result[0]
    except sqlite3.OperationalError:
        pass
    return None

def update_database(file_hash, filepath):
    if not file_hash: return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS library (id INTEGER PRIMARY KEY AUTOINCREMENT, file_hash TEXT UNIQUE, file_path TEXT, added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute("INSERT OR REPLACE INTO library (file_hash, file_path) VALUES (?, ?)", (file_hash, filepath))
    conn.commit()
    conn.close()

def trigger_kavita_scan():
    try:
        url = f"{KAVITA_URL}/api/Library/scan-all"
        headers = {'Authorization': f'Bearer {KAVITA_API_KEY}'}
        requests.post(url, headers=headers)
        logging.info("Triggered Kavita Library Scan.")
    except Exception as e:
        logging.error(f"Failed to trigger Kavita scan: {e}")

def get_issue_number(filename):
    match = re.search(r'#(\d+)', filename)
    return match.group(1) if match else None

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

def extract_archives():
    for item in os.listdir(INBOX):
        file_path = os.path.join(INBOX, item)
        if os.path.isdir(file_path): continue
            
        if item.lower().endswith('.rar'):
            logging.info(f"Auto-Extracting RAR: {item}")
            result = subprocess.run(['unrar', 'x', '-y', file_path, f"{INBOX}/"], capture_output=True)
            if result.returncode == 0: os.remove(file_path)
                
        elif item.lower().endswith('.zip'):
            logging.info(f"Auto-Extracting ZIP: {item}")
            result = subprocess.run(['unzip', '-o', file_path, '-d', INBOX], capture_output=True)
            if result.returncode == 0: os.remove(file_path)

def process_comics():
    if not os.path.exists(DUPLICATES): os.makedirs(DUPLICATES)
    
    extract_archives()
    
    found_files = []
    for root, dirs, files in os.walk(INBOX):
        for file in files:
            if file.endswith(('.cbz', '.cbr')):
                found_files.append(os.path.join(root, file))

    if not found_files:
        print("Inbox is empty or has no comics.")
        logging.info("Inbox empty.")
        return

    for file_path in found_files:
        if not os.path.exists(file_path): continue

        original_name = os.path.basename(file_path)
        
        # Hash Check
        f_hash = calculate_file_hash(file_path)
        existing_path = check_duplicate(f_hash)
        if existing_path:
            logging.warning(f"DUPLICATE DETECTED by Hash: {original_name} matches {existing_path}. Quarantining.")
            shutil.move(file_path, os.path.join(DUPLICATES, original_name))
            continue

        folder_path = os.path.dirname(file_path)
        parent_folder_name = os.path.basename(folder_path)
        
        # Relative structure checking
        relative_structure = os.path.relpath(folder_path, INBOX)
        is_root_file = (relative_structure == ".")

        logging.info(f"Processing: {original_name} from folder [{relative_structure}]")

        if original_name.endswith('.cbr'):
            temp_path = file_path.replace('.cbr', '.cbz')
            os.rename(file_path, temp_path)
            file_path = temp_path

        subprocess.run([TAGGER_BIN, "-d", "-t", "cr", file_path], capture_output=True)

        forced_id = None
        for key, cid in SERIES_MAP.items():
            if key.lower() in parent_folder_name.lower():
                forced_id = cid
                break

        files_before = set(os.listdir(folder_path))

        tag_cmd = [TAGGER_BIN, "-s", "-f", "-o", "--cv-api-key", API_KEY, "--type", "cr", file_path]
        if forced_id:
            tag_cmd.insert(1, "--id")
            tag_cmd.insert(2, forced_id)
        subprocess.run(tag_cmd, capture_output=True)

        files_after = set(os.listdir(folder_path))
        added_files = list(files_after - files_before)

        if added_files:
            new_filename = added_files[0]
            processed_file = os.path.join(folder_path, new_filename)
        else:
            new_filename = os.path.basename(file_path)
            processed_file = file_path

        if not os.path.exists(processed_file): continue

        # --- SMART ROUTING LOGIC ---
        target_dir = None
        if is_root_file:
            meta_res = subprocess.run([TAGGER_BIN, "-p", processed_file], capture_output=True, text=True)
            meta = parse_metadata(meta_res.stdout)
            series = sanitize_filename(meta.get('series', ''))
            volume = sanitize_filename(meta.get('volume', ''))
            publisher = sanitize_filename(meta.get('publisher', ''))

            if not series or series.lower() == "unknown_series":
                clean_name = os.path.splitext(new_filename)[0]
                clean_name = re.sub(r'(?i)(#?\d+|\(\d{4}\)|getcomics|info|_|-|\.)', ' ', clean_name)
                series = " ".join(clean_name.split()).title()
                volume = "1"

            if series and len(series) > 1:
                vol_str = f" v{volume}" if volume and volume != "None" else ""
                series_folder = f"{series}{vol_str}"
                if publisher and publisher.lower() != "unknown_publisher":
                    target_dir = os.path.join(LIBRARY, publisher, series_folder)
                else:
                    target_dir = os.path.join(LIBRARY, series_folder)
                logging.info(f" - Smart-sorted loose file to '{series_folder}'")

        if not target_dir:
            if is_root_file:
                target_dir = os.path.join(LIBRARY, "Unsorted")
                logging.info(" - Smart-sort failed: Defaulted to 'Unsorted'")
            else:
                target_dir = os.path.join(LIBRARY, relative_structure)

        issue_num = get_issue_number(new_filename)
        if issue_num and os.path.exists(target_dir):
            is_dup = any(f"#{issue_num}" in f for f in os.listdir(target_dir))
            if is_dup:
                logging.warning(f" - Duplicate detected for issue #{issue_num}. Quarantining.")
                shutil.move(processed_file, os.path.join(DUPLICATES, new_filename))
                continue

        if not os.path.exists(target_dir): os.makedirs(target_dir)
        
        final_dest = os.path.join(target_dir, new_filename)
        try:
            shutil.move(processed_file, final_dest)
            update_database(f_hash, final_dest)
            logging.info(f" - Organized into: {target_dir}")
        except Exception as e:
            logging.error(f" - Move failed: {e}")

    # Clean empty subfolders while keeping the main INBOX directory intact (-mindepth 1)
    subprocess.run(["find", INBOX, "-mindepth", "1", "-type", "d", "-empty", "-delete"])
    
    subprocess.run(["sudo", "chown", "-R", "james:james", LIBRARY])
    subprocess.run(["sudo", "chmod", "-R", "755", LIBRARY])
    
    trigger_kavita_scan()
    print("Job Complete. Check the logs for details.")

if __name__ == "__main__":
    process_comics()
