import os
import re
import subprocess
import sys
import zipfile
import shutil

# --- CONFIGURATION ---
# IMPORTANT: You MUST edit these paths before running the script.

# The absolute path to the root directory of your comic collection.
COMIC_ROOT = "/path/to/your/comics"
# The absolute path to the comictagger executable inside your virtual environment.
COMIC_TAGGER_EXE = "/path/to/your/comictagger_project/venv/bin/comictagger"
# The absolute path to the file containing your Comic Vine API key.
API_KEY_FILE = "/home/user/.comic_vine_api_key"
# The desired folder and file naming pattern for Comic Tagger.
# {series} ({year}) creates a folder, the rest is the filename.
RENAME_PATTERN = "{series} ({year})/{series} ({year}) - #{issue}"
# Log file for comics that could not be parsed automatically.
SKIPPED_FILES_LOG = "skipped_files.log"
# Set to True to run in "test mode" (prints commands but doesn't execute them).
# Set to False to run for real. ALWAYS START WITH TRUE!
DRY_RUN = True
# --- END CONFIGURATION ---

def get_api_key():
    """Reads the API key from the specified file."""
    try:
        with open(os.path.expanduser(API_KEY_FILE), 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"ERROR: API Key file not found at {API_KEY_FILE}")
        sys.exit(1)

def log_skipped_file(filepath, reason):
    """Writes the path of a skipped file to the log."""
    with open(SKIPPED_FILES_LOG, 'a') as f:
        f.write(f"{filepath}: {reason}\n")

def create_cbz_from_folder(issue_folder_path, series_name, issue_number):
    """Creates a CBZ archive from a folder of images, then cleans up."""
    image_files = sorted([f for f in os.listdir(issue_folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))])
    
    if not image_files:
        log_skipped_file(issue_folder_path, "Directory contains no image files.")
        return None

    cbz_filename = f"{series_name} - #{issue_number}.cbz"
    series_folder_path = os.path.dirname(issue_folder_path)
    cbz_filepath = os.path.join(series_folder_path, cbz_filename)

    print(f"  -> Creating CBZ: {cbz_filename}")
    
    if not DRY_RUN:
        try:
            with zipfile.ZipFile(cbz_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
                for image in image_files:
                    image_path = os.path.join(issue_folder_path, image)
                    zf.write(image_path, arcname=image)
            shutil.rmtree(issue_folder_path)
            print(f"  -> Successfully created CBZ and removed original folder.")
        except Exception as e:
            print(f"  -> ERROR creating CBZ file: {e}")
            log_skipped_file(issue_folder_path, f"Failed during CBZ creation: {e}")
            return None
    
    return cbz_filepath

def process_collection():
    """Main function to walk the collection, archive, and tag."""
    api_key = get_api_key()
    if not api_key:
        return

    # Clear the log file at the beginning of each run
    if os.path.exists(SKIPPED_FILES_LOG):
        os.remove(SKIPPED_FILES_LOG)

    print("Starting comic processing...")
    if DRY_RUN:
        print("--- RUNNING IN DRY RUN MODE. FILES/FOLDERS WILL NOT BE MODIFIED. ---")
    
    print("\n" + "="*50)
    print("STAGE 1: ARCHIVING FOLDERS TO CBZ")
    print("="*50 + "\n")
    
    comics_to_tag = []
    
    for root, dirs, files in os.walk(COMIC_ROOT, topdown=True):
        for dir_name in list(dirs):
            issue_path = os.path.join(root, dir_name)
            series_name = os.path.basename(root)
            issue_number = ""
            
            if dir_name.startswith("#"):
                issue_number = dir_name.lstrip('#').strip()
            elif "TPB (Part" in dir_name:
                match = re.search(r'Part (\d+)', dir_name)
                if match: issue_number = match.group(1)
            
            if issue_number and series_name != os.path.basename(COMIC_ROOT):
                new_cbz_path = create_cbz_from_folder(issue_path, series_name, issue_number)
                if new_cbz_path:
                    comics_to_tag.append((new_cbz_path, series_name, issue_number))
                dirs.remove(dir_name)
            else:
                log_skipped_file(issue_path, "Could not parse as an issue folder.")

    print("\n" + "="*50)
    print("ARCHIVING STAGE COMPLETE.")
    print("STAGE 2: TAGGING ARCHIVES")
    if DRY_RUN:
         print("--- CONTINUING IN DRY RUN MODE. NO FILES WILL BE TAGGED. ---")
    print("="*50 + "\n")

    for root, dirs, files in os.walk(COMIC_ROOT):
        for file in files:
            if file.lower().endswith((".cbz", ".cbr")):
                full_path = os.path.join(root, file)
                if not any(full_path in t for t in comics_to_tag):
                     series_name = os.path.basename(root)
                     match = re.search(r'(\d[\d.]*)', os.path.splitext(file)[0])
                     if series_name and match and series_name != os.path.basename(COMIC_ROOT):
                         issue_number = match.group(1).strip()
                         comics_to_tag.append((full_path, series_name, issue_number))
                     else:
                        log_skipped_file(full_path, "Could not parse series/issue for existing archive.")

    for cbz_path, series_name, issue_number in comics_to_tag:
        print("-" * 40)
        print(f"Tagging Comic: {cbz_path}")
        print(f"  -> Using Series: '{series_name}'")
        print(f"  -> Using Issue:  '{issue_number}'")

        command = [
            COMIC_TAGGER_EXE, "--no-gui", "--verbose", "--overwrite", "--save", "--rename",
            "--rename-pattern", RENAME_PATTERN,
            "--api-key", api_key, "-t", "ComicVine", "-s", series_name, "-i", issue_number, cbz_path
        ]

        if DRY_RUN:
            print("  -> Command: " + " ".join(f'"{arg}"' if " " in arg else arg for arg in command))
        else:
            try:
                print("  -> Executing Comic Tagger...")
                result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)
                print("  -> SUCCESS:")
                for line in result.stdout.strip().splitlines()[-3:]:
                    print(f"     {line}")
            except subprocess.TimeoutExpired:
                print(f"  -> ERROR: comictagger command timed out after 5 minutes.")
                log_skipped_file(cbz_path, "Comic Tagger timed out.")
            except subprocess.CalledProcessError as e:
                print(f"  -> ERROR running comictagger:\n{e.stderr}")
                log_skipped_file(cbz_path, f"Comic Tagger failed: {e.stderr.strip()}")

    print("-" * 40)
    print("Processing complete.")
    print(f"Check 'skipped_files.log' for any files that could not be processed.")

if __name__ == "__main__":
    process_collection()