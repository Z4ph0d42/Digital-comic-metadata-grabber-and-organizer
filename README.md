# Digital Comic Organizer & Metadata Grabber

A robust, automated Python toolset designed to organize digital comic collections (CBZ, CBR, PDF) and loose image folders. It identifies comics using **ComicTagger** (ComicVine API), organizes them into a standardized folder structure, and handles duplicates and errors intelligently.

Designed for self-hosted libraries like **Kavita** or **Komga**.

## Features

*   **Smart Organization:** Moves comics from an Inbox to a Library using the format: `Publisher/Series vVol/Series #Issue (Year).ext`.
*   **Safe Fallback Mode:** If a comic cannot be identified (or has ambiguous matches), it is **not** discarded. It is moved to the Library preserving its original folder/filename so you don't lose it.
*   **Auto-Conversion:** Automatically detects folders containing loose images (`.jpg`, `.png`) and zips them into `.cbz` files before processing.
*   **PDF & CBR Support:** Handles standard `.cbz`, `.cbr`, and `.pdf` comics.
*   **Duplicate Detection:** Calculates SHA256 hashes of files to prevent importing exact duplicates, even if filenames differ.
*   **Quarantine System:** Corrupt archives or unreadable files are moved to a Quarantine folder for manual inspection, ensuring the script never gets stuck.
*   **Strict Filtering:** Ignores non-comic files (text files, system thumbnails) to keep your library clean.

## Prerequisites

*   **Python 3.10+**
*   **System Tools:** `unrar` (Required for CBR support)
    *   *Debian/Ubuntu:* `sudo apt install unrar`
*   **ComicVine API Key:** You need a free API key from [ComicVine](https://comicvine.gamespot.com/api/).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Z4ph0d42/Digital-comic-metadata-grabber-and-organizer.git
    cd Digital-comic-metadata-grabber-and-organizer
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Open `process_inbox.py` and update the **Configuration Section** at the top:

```python
# --- CONFIGURATION ---
INBOX_DIR = "/path/to/comics/inbox"          # Where you dump new downloads
LIBRARY_DIR = "/path/to/comics/library"      # Your organized Kavita/Komga root
QUARANTINE_DIR = "/path/to/comics/quarantine" # Where corrupt files go

# Path to ComicTagger (usually inside your venv/bin folder)
COMIC_TAGGER_BIN = "/home/user/scripts/comic-organizer/venv/bin/comictagger"

# Your API Key
CV_API_KEY = "YOUR_COMICVINE_API_KEY"
Repeat the path configuration for build_library_db.py and manage_quarantine.py.
Usage
1. Initialize the Database (Run Once)
Before starting, scan your existing library (if any) to build the duplicate detection database.
code
Bash
python3 build_library_db.py
2. Process the Inbox (The Main Script)
Run this whenever you add new comics to your Inbox folder.
code
Bash
python3 process_inbox.py
What it does:
Scans INBOX_DIR.
Converts any folders of images into .cbz files.
Checks for duplicates against the database.
Tags the comic using ComicTagger.
Success: Moves file to LIBRARY_DIR/Publisher/Series...
Ambiguous/Failed Tag: Moves file to LIBRARY_DIR/Original_Name (Fallback mode).
Corrupt: Moves file to QUARANTINE_DIR.
3. Manage Quarantine
If files end up in Quarantine (e.g., corrupt archives), use this tool to view or restore them.
code
Bash
python3 manage_quarantine.py
Folder Structure
The script expects and maintains this structure:
code
Text
/Comics
├── Inbox          <-- Drop your messy downloads here
├── Library        <-- Clean, organized folders appear here
└── Quarantine     <-- Broken files go here
```
Feel free to submit issues or pull requests.
