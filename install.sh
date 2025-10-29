#!/bin/bash
set -e

echo "================================================="
echo " Comic Organizer & Tagger - Automated Installer "
echo "================================================="
echo

# --- Gather User Information ---
read -p "Enter the absolute path to your main comic library (e.g., /srv/comics): " COMIC_LIBRARY_PATH
read -p "Enter your ComicVine API Key: " COMICVINE_API_KEY
read -p "Enter your Kavita API Key: " KAVITA_API_KEY
echo

# Validate that the comic library path exists
if [ ! -d "$COMIC_LIBRARY_PATH" ]; then
    echo "Warning: Library path '$COMIC_LIBRARY_PATH' does not exist."
    read -p "Do you want to create it now? (y/n): " create_dir
    if [[ "$create_dir" == "y" || "$create_dir" == "Y" ]]; then
        sudo mkdir -p "$COMIC_LIBRARY_PATH"
        sudo chown -R $USER:$USER "$COMIC_LIBRARY_PATH"
        echo "Directory created."
    else
        echo "Aborting. Please create the directory and rerun the installer."
        exit 1
    fi
fi
INBOX_PATH="$COMIC_LIBRARY_PATH/inbox"
KAVITA_DATA_PATH="$HOME/kavita_data"
PROJECT_DIR="$HOME/comic_organizer"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
VENV_DIR="$PROJECT_DIR/venv"

echo "--- Installing System Dependencies ---"
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip unrar curl
echo "System dependencies installed."
echo

echo "--- Setting up Python Virtual Environment ---"
mkdir -p "$SCRIPTS_DIR"
python3 -m venv "$VENV_DIR"
# Install Python packages in the correct order
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install unrar-cffi
"$VENV_DIR/bin/pip" install comictagger
echo "Python environment created and comictagger installed."
echo

echo "--- Creating API Key File ---"
echo "$COMICVINE_API_KEY" > "$HOME/.comic_vine_api_key"
echo "ComicVine API key saved to ~/.comic_vine_api_key"
echo

# --- Generate pack_comics.py ---
echo "--- Generating pack_comics.py ---"
cat << EOF > "$SCRIPTS_DIR/pack_comics.py"
import os
import zipfile
import shutil

COMIC_ROOT = "$COMIC_LIBRARY_PATH"

def is_image_file(filename):
    return filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))

def process_library():
    print("Starting library packing process...")
    for root, dirs, files in os.walk(COMIC_ROOT, topdown=False):
        image_files = sorted([f for f in files if is_image_file(f)])
        if image_files:
            folder_name = os.path.basename(root)
            parent_dir = os.path.dirname(root)
            cbz_path = os.path.join(parent_dir, f"{folder_name}.cbz")
            if os.path.exists(cbz_path):
                continue
            print(f"  -> Packing folder: '{root}'")
            try:
                with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for image in image_files:
                        zf.write(os.path.join(root, image), arcname=image)
                print(f"  -> Successfully created '{cbz_path}'. Removing original folder.")
                shutil.rmtree(root)
            except Exception as e:
                print(f"  -> ERROR: Failed to pack '{root}': {e}")
    print("\nPacking process complete.")

if __name__ == "__main__":
    process_library()
EOF
echo "pack_comics.py created."
echo

# --- Generate process_inbox.py ---
echo "--- Generating process_inbox.py ---"
cat << EOF > "$SCRIPTS_DIR/process_inbox.py"
import os
import subprocess
import shutil
import sys

# --- CONFIGURATION ---
INBOX_DIR = "$INBOX_PATH"
LIBRARY_DIR = "$COMIC_LIBRARY_PATH"
COMIC_TAGGER_EXE = "$VENV_DIR/bin/comictagger"
API_KEY_FILE = "$HOME/.comic_vine_api_key"
KAVITA_BASE_URL = "http://localhost:5000"
KAVITA_API_KEY = "$KAVITA_API_KEY"

def get_comicvine_api_key():
    try:
        with open(os.path.expanduser(API_KEY_FILE), 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"ERROR: ComicVine API Key file not found at {API_KEY_FILE}")
        return None

def process_inbox():
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
            if os.path.exists(dest_path):
                print(f"Warning: Series folder '{series_name}' already exists in the main library. Cannot move.")
            else:
                shutil.move(source_path, dest_path)
                print(f"Moved '{series_name}' to the main library.")
                processed_at_least_one = True

    if processed_at_least_one and KAVITA_API_KEY:
        print("-" * 40)
        print("Telling Kavita to scan the library...")
        scan_command = ["curl", "-X", "POST", f"{KAVITA_BASE_URL}/api/Library/Scan", "-H", f"X-Api-Key: {KAVITA_API_KEY}"]
        try:
            subprocess.run(scan_command, capture_output=True, text=True, check=True)
            print("Kavita scan initiated successfully.")
        except Exception as e:
            print(f"ERROR: Could not trigger Kavita scan. Is the URL and API key correct? Error: {e}")

if __name__ == "__main__":
    process_inbox()
EOF
echo "process_inbox.py created."
echo

# --- Setup Cron Job ---
echo "--- Setting up Cron Job ---"
CRON_COMMAND="$VENV_DIR/bin/python $SCRIPTS_DIR/process_inbox.py"
CRON_JOB="30 2 * * * $CRON_COMMAND"

# Add the cron job if it doesn't already exist
if ! crontab -l | grep -q "process_inbox.py"; then
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Nightly cron job installed to run at 2:30 AM."
else
    echo "Cron job already exists. Skipping installation."
fi
echo

echo "================================================="
echo " Installation Complete! "
echo "================================================="
echo
echo "Your scripts are located in: $SCRIPTS_DIR"
echo "Your Python environment is in: $VENV_DIR"
echo
echo "NEXT STEPS:"
echo "1. If you haven't already, install Kavita using Docker:"
echo
echo "   mkdir -p \"$KAVITA_DATA_PATH\""
echo "   docker run -d \\"
echo "     --name kavita \\"
echo "     -p 5000:5000 \\"
echo "     -v \"$COMIC_LIBRARY_PATH:/comics\" \\"
echo "     -v \"$KAVITA_DATA_PATH:/kavita/data\" \\"
echo "     --restart unless-stopped \\"
echo "     jvmilazz0/kavita:latest"
echo
echo "2. Your automated inbox is ready. Place new comic folders in:"
echo "   $INBOX_PATH"
echo
echo "3. To tag your entire existing library, run this command:"
echo "   (source \"$VENV_DIR/bin/activate\"; comictagger -s -t CR -o -f -R --cv-api-key \"\$(cat \$HOME/.comic_vine_api_key)\" \"$COMIC_LIBRARY_PATH\")"
echo