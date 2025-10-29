import os
<<<<<<< Updated upstream
import re
import subprocess
import sys
import zipfile
import shutil
import requests

# --- CONFIGURATION ---
# IMPORTANT: The user MUST edit these paths before running the script.

# The "inbox" directory where new, unprocessed comics are dropped.
INBOX_DIR = "/path/to/your/inbox"
# The final destination directory for the main comic library.
LIBRARY_DIR = "/path/to/your/library"
# The absolute path to the comictagger executable inside its virtual environment.
COMIC_TAGGER_EXE = "/home/user/comictagger_project/venv/bin/comictagger"
# The absolute path to the file containing your Comic Vine API key.
API_KEY_FILE = "/home/user/.comic_vine_api_key"
# Your Kavita server URL (as seen from the server itself).
KAVITA_URL = "http://localhost:5000"
# Your Kavita API key (get this from your user profile in the Kavita UI).
KAVITA_API_KEY = "YOUR_KAVITA_API_KEY_HERE"
# The Kavita library ID to scan. Usually '1' for your first library.
KAVITA_LIBRARY_ID = 1
# Log file for any comics that could not be processed.
SKIPPED_FILES_LOG = "/home/user/inbox_skipped.log"
# --- END CONFIGURATION ---

def get_api_key():
    """Reads the Comic Vine API key from the specified file."""
=======
import subprocess
import shutil
import sys

# --- CONFIGURATION ---
# The directory where you place new, unsorted comic folders.
INBOX_DIR = "/path/to/your/comics/inbox"
# The main directory of your comic library.
LIBRARY_DIR = "/path/to/your/comics"
# Full path to the comictagger executable inside your virtual environment.
COMIC_TAGGER_EXE = "/home/<YOUR_USERNAME>/comictagger_project/bin/comictagger"
# The location of your ComicVine API key file.
API_KEY_FILE = "/home/<YOUR_USERNAME>/.comic_vine_api_key"

# --- KAVITA CONFIGURATION ---
# The base URL of your Kavita instance.
KAVITA_BASE_URL = "http://localhost:5000"
# Your Kavita API Key (get this from Kavita's Server Settings -> API Key).
KAVITA_API_KEY = "YOUR_KAVITA_API_KEY_HERE"

def get_comicvine_api_key():
>>>>>>> Stashed changes
    try:
        with open(os.path.expanduser(API_KEY_FILE), 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
<<<<<<< Updated upstream
        return None

def log_skipped_file(filepath, reason):
    """Writes the path of a skipped file to the log."""
    with open(SKIPPED_FILES_LOG, 'a') as f:
        f.write(f"{filepath}: {reason}\n")

def create_cbz_from_folder(issue_folder_path, series_name, issue_number):
    """Creates a CBZ archive from a folder of images, then cleans up."""
    image_files = sorted([f for f in os.listdir(issue_folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))])
    if not image_files:
        log_skipped_file(issue_folder_path, "No image files found."); return None
    cbz_filename = f"{series_name} - #{issue_number}.cbz"
    series_folder_path = os.path.dirname(issue_folder_path)
    cbz_filepath = os.path.join(series_folder_path, cbz_filename)
    print(f"  -> Creating CBZ: {cbz_filename}")
    try:
        with zipfile.ZipFile(cbz_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            for image in image_files:
                zf.write(os.path.join(issue_folder_path, image), arcname=image)
        shutil.rmtree(issue_folder_path)
        print(f"  -> Successfully created CBZ and removed original folder.")
        return cbz_filepath
    except Exception as e:
        print(f"  -> ERROR creating CBZ: {e}"); log_skipped_file(issue_folder_path, f"Failed CBZ creation: {e}"); return None

def trigger_kavita_scan():
    """Sends a request to the Kavita API to scan the library for new files."""
    if not KAVITA_API_KEY or "YOUR_KAVITA_API_KEY_HERE" in KAVITA_API_KEY:
        print("Kavita API Key not set in script. Skipping library scan."); return

    headers = {'Authorization': f'Bearer {KAVITA_API_KEY}', 'Content-Type': 'application/json'}
    url = f"{KAVITA_URL}/api/v1/Library/scan?libraryId={KAVITA_LIBRARY_ID}"
    try:
        print("  -> Triggering Kavita library scan...")
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            print("  -> Kavita scan initiated successfully.")
        else:
            print(f"  -> ERROR: Failed to trigger Kavita scan. Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"  -> ERROR: Exception while trying to trigger Kavita scan: {e}")

def process_inbox():
    """The main function to process all comics in the inbox directory."""
    comicvine_api_key = get_api_key()
    if not comicvine_api_key:
        print(f"ERROR: Comic Vine API Key not found at '{API_KEY_FILE}'. Aborting."); return
    
    print(f"--- Starting Inbox Processing: {INBOX_DIR} ---")
    processed_something = False

    # Stage 1: Archive folders to CBZ within the inbox
    for series_folder in os.listdir(INBOX_DIR):
        series_path = os.path.join(INBOX_DIR, series_folder)
        if not os.path.isdir(series_path): continue
        for issue_folder in os.listdir(series_path):
            issue_path = os.path.join(series_path, issue_folder)
            if not os.path.isdir(issue_path): continue
            issue_number = ""
            if issue_folder.startswith("#"): issue_number = issue_folder.lstrip('#').strip()
            elif "TPB (Part" in issue_folder:
                match = re.search(r'Part (\d+)', issue_folder);
                if match: issue_number = match.group(1)
            if issue_number:
                if create_cbz_from_folder(issue_path, series_folder, issue_number):
                    processed_something = True

    # Stage 2: Tag and Rename all archives found in the inbox
    for series_folder in os.listdir(INBOX_DIR):
        series_path = os.path.join(INBOX_DIR, series_folder)
        if not os.path.isdir(series_path): continue
        for file in os.listdir(series_path):
            if not file.lower().endswith((".cbz", ".cbr")): continue
            
            full_path = os.path.join(series_path, file)
            filename_base = os.path.splitext(file)[0]
            
            issue_number = None
            match = re.search(r'#([\w\d.-]+)', filename_base, re.IGNORECASE)
            if match: issue_number = match.group(1)
            else:
                match = re.search(r'(\d[\d.]*)', filename_base)
                if match: issue_number = match.group(1)

            if not issue_number:
                log_skipped_file(full_path, "Could not parse issue number from filename."); continue
            
            issue_number = issue_number.strip()
            print(f"--- Tagging: {file} ---")

            command = [
                COMIC_TAGGER_EXE,
                "--no-gui", "--verbose", "--overwrite",
                "--type=c2m",
                "--source=ComicVine",
                "--rename-pattern", "{series} ({year})/{series} ({year}) - #{issue}",
                "--api-key", comicvine_api_key,
                "-s", series_folder,
                "-i", issue_number,
                full_path
            ]
            
            try:
                subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)
                processed_something = True
            except Exception as e:
                log_skipped_file(full_path, f"Comic Tagger failed: {e}")
    
    # Stage 3: Move processed folders from inbox to main library
    for item in os.listdir(INBOX_DIR):
        source_path = os.path.join(INBOX_DIR, item)
        dest_path = os.path.join(LIBRARY_DIR, item)
        if os.path.isdir(source_path):
            if os.path.exists(dest_path):
                print(f"  -> Merging '{item}' into existing library folder.")
                for comic_file in os.listdir(source_path):
                    shutil.move(os.path.join(source_path, comic_file), dest_path)
                shutil.rmtree(source_path)
            else:
                print(f"  -> Moving new series '{item}' to library.")
                shutil.move(source_path, LIBRARY_DIR)
    
    # Stage 4: Trigger Kavita Scan if we did anything
    if processed_something:
        trigger_kavita_scan()
    else:
        print("--- No new comics to process. ---")
=======
        print(f"ERROR: ComicVine API Key file not found at {API_KEY_FILE}")
        return None

def process_inbox():
    """
    Scans the inbox for new series, tags them using comictagger, moves them
    to the main library, and triggers a Kavita library scan.
    If tagging fails, it moves the folder anyway for manual curation later.
    """
    cv_api_key = get_comicvine_api_key()
    if not cv_api_key:
        sys.exit("Could not find ComicVine API key. Aborting.")

    if not os.path.exists(INBOX_DIR):
        os.makedirs(INBOX_DIR)
        print(f"Inbox directory created at {INBOX_DIR}. Add new comic series folders here.")
        return

    series_folders = [f for f in os.listdir(INBOX_DIR) if os.path.isdir(os.path.join(INBOX_DIR, f))]
    if not series_folders:
        print("Inbox is empty. Nothing to do.")
        return

    print(f"Found {len(series_folders)} series to process in the inbox.")
    
    processed_at_least_one = False
    for series_name in series_folders:
        source_path = os.path.join(INBOX_DIR, series_name)
        dest_path = os.path.join(LIBRARY_DIR, series_name)
        
        print("-" * 40)
        print(f"Processing series: {series_name}")
        
        try:
            command = [
                COMIC_TAGGER_EXE, "-s", "-t", "CR", "-o", "-f", "-R",
                "--cv-api-key", cv_api_key, source_path
            ]
            
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Successfully tagged series '{series_name}'.")
            else:
                print(f"Warning: comictagger failed for '{series_name}'. The folder will be moved without metadata.")
                print("--- ComicTagger Error Output ---\n" + result.stderr + "\n---------------------------------")
        
        finally:
            # This block runs whether the 'try' succeeded or failed.
            if os.path.exists(dest_path):
                print(f"Warning: Series folder '{series_name}' already exists in the main library. Cannot move.")
            else:
                shutil.move(source_path, dest_path)
                print(f"Moved '{series_name}' to the main library.")
                processed_at_least_one = True

    # After processing all folders, tell Kavita to scan if we moved anything
    if processed_at_least_one and KAVITA_API_KEY != "YOUR_KAVITA_API_KEY_HERE":
        print("-" * 40)
        print("Telling Kavita to scan the library...")
        
        scan_command = ["curl", "-X", "POST", f"{KAVITA_BASE_URL}/api/Library/Scan", "-H", f"X-Api-Key: {KAVITA_API_KEY}"]
        
        try:
            subprocess.run(scan_command, capture_output=True, text=True, check=True)
            print("Kavita scan initiated successfully.")
        except Exception as e:
            print(f"ERROR: Could not trigger Kavita scan. Is the URL and API key correct? Error: {e}")
>>>>>>> Stashed changes

if __name__ == "__main__":
    process_inbox()