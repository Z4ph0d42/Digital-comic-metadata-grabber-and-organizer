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
LOG_FILE = "/home/james/scripts/comic-organizer/process_log.txt"
TAGGER_BIN = "/home/james/scripts/comic-organizer/venv/bin/comictagger"
API_KEY = "f33a0650ac4c04e3c964c38f7e86f69723344bce"
DB_FILE = "/home/james/scripts/comic-organizer/library.db"

# Kavita Configuration
KAVITA_URL = "http://192.168.2.51:5000"
KAVITA_API_KEY = "db1210d2-8dfc-44fb-8a5d-ec1f22a08985"

SERIES_MAP = {
    "uncanny x-force": "36402",
    "deadpool vs. x-force": "75151",
    "x-statix": "10020",
    "she-hulk": "3960",
    "x-force v1": "4101",
    "x-force v2": "18165",
    "x-force v3": "20743",
    "avengers v3": "2358"
}

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

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
    if not os.path.exists(DB_FILE): return None
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT file_path FROM library WHERE file_hash = ?", (file_hash,))
        result = cursor.fetchone()
        conn.close()
        if result and os.path.exists(result[0]): return result[0]
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
        requests.post(url, headers={'Authorization': f'Bearer {KAVITA_API_KEY}'})
        logging.info("Triggered Kavita Library Scan.")
    except Exception as e:
        logging.error(f"Failed to trigger Kavita scan: {e}")

def get_issue_number(filename):
    # Strip year (YYYY) to prevent false positives
    name_no_year = re.sub(r'\(\d{4}\)', '', filename)
    match = re.search(r'#(\d+)', name_no_year)
    if match: return str(int(match.group(1))) # Normalize by stripping leading zeros
    
    match_num = re.search(r'(?:v\d+\s+)?(?:issue\s+)?0*(\d+)(?:\s|\.|-|_|$)', name_no_year, re.IGNORECASE)
    return str(int(match_num.group(1))) if match_num else None

def process_comics():
    found_files = []
    for root, dirs, files in os.walk(INBOX):
        for file in files:
            if file.endswith(('.cbz', '.cbr', '.rar')):
                found_files.append(os.path.join(root, file))

    if not found_files:
        print("Inbox is empty.")
        return

    for file_path in found_files:
        if not os.path.exists(file_path): continue
        original_name = os.path.basename(file_path)
        
        # --- TIER 1 DUPLICATE CHECK: Exact Hash Match ---
        f_hash = calculate_file_hash(file_path)
        existing_path = check_duplicate(f_hash)
        if existing_path and os.path.abspath(existing_path) != os.path.abspath(file_path):
            if not os.path.exists(existing_path):
                update_database(f_hash, file_path)
            else:
                logging.warning(f"EXACT DUPLICATE (Hash): {original_name}. Deleting.")
                os.remove(file_path)
                continue

        folder_path = os.path.dirname(file_path)
        relative_structure = os.path.relpath(folder_path, INBOX)
        is_root_file = (relative_structure == ".")
        logging.info(f"Processing: {original_name}")

        if original_name.endswith('.cbr'):
            temp_path = file_path.replace('.cbr', '.cbz')
            os.rename(file_path, temp_path)
            file_path = temp_path

        files_before = set(os.listdir(folder_path))

        # --- DETERMINISTIC TARGET ROUTING ---
        clean_name = os.path.splitext(original_name)[0]
        vol_match = re.search(r'\b[vV](\d+)\b', clean_name)
        volume = vol_match.group(1) if vol_match else "1"

        series_match = re.search(r'^(?P<series>.+?)(?:\s+[vV]\d+|\s*#\d+|\s*\(\d{4}\))', clean_name)
        series = series_match.group('series').strip() if series_match else "Unsorted Comics"

        series_lower = series.lower()
        if "avengers" in series_lower and volume == "3":
            series_folder = "Avengers v3 (1998 - 2004)"
        elif "avengers" in series_lower and volume == "1":
            series_folder = "The Avengers v1"
        else:
            vol_str = f" v{volume}" if volume else ""
            series_folder = f"{series}{vol_str}"

        target_dir = os.path.join(LIBRARY, series_folder) if is_root_file else os.path.join(LIBRARY, relative_structure)

        # --- TIER 2 DUPLICATE CHECK: Logical Issue Match ---
        issue_num = get_issue_number(original_name)
        if issue_num and os.path.exists(target_dir):
            is_dupe = False
            for ext_f in os.listdir(target_dir):
                if ext_f.endswith(('.cbz', '.cbr')) and get_issue_number(ext_f) == issue_num:
                    is_dupe = True
                    break
            if is_dupe:
                logging.warning(f"LOGICAL DUPLICATE: Issue {issue_num} already exists in {target_dir}. Deleting {original_name}.")
                os.remove(file_path)
                continue

        # --- METADATA STAMPING ---
        forced_id = None
        combined_check = f"{original_name} {relative_structure}".lower()
        for key, cid in SERIES_MAP.items():
            if key in combined_check:
                forced_id = cid
                break

        tag_cmd = [TAGGER_BIN, "-s", "-f", "-o", "--cv-api-key", API_KEY, "--type", "cr", file_path]
        if forced_id:
            tag_cmd.insert(1, "--id")
            tag_cmd.insert(2, forced_id)
        
        subprocess.run(tag_cmd, capture_output=True)

        files_after = set(os.listdir(folder_path))
        added_files = list(files_after - files_before)
        new_filename = added_files[0] if added_files else os.path.basename(file_path)
        processed_file = os.path.join(folder_path, new_filename)

        if not os.path.exists(processed_file): continue
        if not os.path.exists(target_dir): os.makedirs(target_dir)

        # Final Move
        final_dest = os.path.join(target_dir, new_filename)
        try:
            if os.path.abspath(processed_file) != os.path.abspath(final_dest):
                shutil.move(processed_file, final_dest)
            update_database(f_hash, final_dest)
            logging.info(f" - Organized into: {target_dir}")
        except Exception as e:
            logging.error(f" - Move failed: {e}")

    subprocess.run(["find", INBOX, "-mindepth", "1", "-type", "d", "-empty", "-delete"])
    trigger_kavita_scan()
    print("Job Complete. Check process_log.txt for actions.")

if __name__ == "__main__":
    process_comics()
