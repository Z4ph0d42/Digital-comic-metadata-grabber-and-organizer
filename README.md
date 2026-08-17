# Digital Comic Organizer & Metadata Grabber

A robust, automated Python toolset designed to organize digital comic collections (CBZ, CBR, PDF) and loose image folders. It identifies comics using **ComicTagger** (ComicVine API), organizes them into a standardized folder structure, and handles duplicates and errors intelligently.

Designed for self-hosted libraries like **Kavita** or **Komga**.

## Features

*   **Smart Organization:** Moves comics from an Inbox to a Library using the format: `Publisher/Series vVol/Series #Issue (Year).ext`.
*   **Auto-Extraction:** Automatically extracts bulk `.rar` and `.zip` uploads.
*   **PDF & CBR Support:** Handles standard `.cbz`, `.cbr`, and `.pdf` comics.
*   **Duplicate Detection:** Calculates SHA256 hashes of files to prevent importing exact duplicates, even if filenames differ.
*   **Quarantine System:** Corrupt archives or unreadable files are moved to a Quarantine folder for manual inspection, ensuring the script never gets stuck.

## Prerequisites

*   **Python 3.10+**
*   **System Tools:** `unrar` and `unzip`
    *   *Debian/Ubuntu:* `sudo apt install unrar unzip`
*   **ComicVine API Key:** You need a free API key from [ComicVine](https://comicvine.gamespot.com/api/).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/Z4ph0d42/Digital-comic-metadata-grabber-and-organizer.git](https://github.com/Z4ph0d42/Digital-comic-metadata-grabber-and-organizer.git)
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
INBOX = "/srv/comics/inbox"
LIBRARY = "/srv/comics"
DUPLICATES = "/srv/comics/duplicates"
LOG_FILE = "/home/james/scripts/comic-organizer/process_log.txt"
TAGGER_BIN = "/home/james/scripts/comic-organizer/venv/bin/comictagger"
API_KEY = "YOUR_COMICVINE_API_KEY"
DB_FILE = "/home/james/scripts/comic-organizer/library.db"
```

## Usage: How to Add Comics to the Inbox

You can add comics to the `INBOX` directory using two different methods depending on your needs. Run `python3 process_inbox.py` after dropping your files, or rely on a daily cron job.

### Method 1: The Folder Method (Best for Bulk / Specific Series)
Create a folder inside the Inbox (e.g., `/inbox/X-Force (1991)/`) and place your `.cbz` or `.cbr` files inside.
*   **What it does:** The script will strictly preserve this exact folder structure and mirror it into your Library.
*   **Pro-Tip (Forced Matching):** If you map a keyword from the folder name (like "v1" or "uncanny") to a ComicVine ID in the `SERIES_MAP` dictionary inside `process_inbox.py`, the script will force-match every comic inside that folder to the exact ComicVine ID, guaranteeing 100% metadata accuracy.

### Method 2: The Loose File Method (Smart Auto-Sorting)
Drop loose `.cbz` or `.cbr` files directly into the root of the Inbox (e.g., `/inbox/Black Knight 01 (2016).cbz`).
*   **What it does:** The script detects it is a loose file and attempts to read embedded metadata. If it finds none, it intelligently parses the filename to guess the series title (stripping out issue numbers, years, and release group tags). It will then auto-create a folder in your Library (e.g., `/Library/Black Knight v1/`) and sort the comic into it.
*   **Fallback:** If the script completely fails to guess a valid title from the filename, it safely moves the file to an `Unsorted` folder in your library so it never gets lost.

## Folder Structure

The script expects and maintains this structure:
```text
/srv/comics
├── inbox          <-- Drop your messy downloads here
├── duplicates     <-- Hash-matched duplicates go here
└── [Library Folders] <-- Clean, organized folders appear here
```
