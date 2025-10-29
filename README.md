# Digital Comic Metadata Grabber and Organizer

This project provides a set of scripts and a workflow for automatically organizing and tagging a digital comic book library for use with a media server like [Kavita](https://www.kavitareader.com/).

The system is designed to:
-   Automatically tag comic files (`.cbz`, `.cbr`) with rich metadata from ComicVine.
-   Provide a simple "inbox" workflow for adding new comics.
-   Run automatically on a schedule (e.g., nightly).
-   Gracefully handle comics that can't be matched, organizing them by folder name for later review.

---

## Quick Installation (Recommended for Debian/Ubuntu)

This installer automates the entire setup process.

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Z4ph0d42/Digital-comic-metadata-grabber-and-organizer.git
    cd Digital-comic-metadata-grabber-and-organizer
    ```

2.  **Make the Installer Executable:**
    ```bash
    chmod +x install.sh
    ```

3.  **Run the Installer:**
    The script will prompt you for your comic library path and API keys.
    ```bash
    ./install.sh
    ```

The installer will handle system dependencies, Python environment setup, script creation, and cron job installation. Follow the "NEXT STEPS" printed at the end to set up Kavita.

---

## Manual Workflow (for Existing Libraries)

After installation, your first step should be to tag your entire existing library.

**1. Clean Up Junk Files (Optional but Recommended):**
These commands find and permanently delete temporary files.
```bash
# Find and delete leftover temporary files/folders
find /path/to/your/comics -iname "*tmp*" -delete

# Find and delete leftover .bin files
find /path/to/your/comics -type f -name "*.bin" -delete
```

**2. Pack Loose Image Folders:**
The installer creates a `pack_comics.py` script. Run it to convert any folders containing only images into `.cbz` files.
```bash
# Activate the virtual environment first
source ~/comic_organizer/venv/bin/activate

# Run the packer script
python ~/comic_organizer/scripts/pack_comics.py
```

**3. Tag the Entire Library:**
This is the main command. It recursively scans your library and writes metadata to the files.
```bash
# Make sure the virtual environment is active
comictagger -s -t CR -o -f -R --cv-api-key "$(cat ~/.comic_vine_api_key)" /path/to/your/comics
```
- `-s`: Search for and save metadata.
- `-t CR`: Save in ComicRack format.
- `-o`: Overwrite existing tags.
- `-f`: Parse filename/folder for info.
- `-R`: Run recursively.

**4. Manual Curation:**
If the tagger outputs "No match found," the folder name doesn't match the ComicVine database. Rename the folder to match the official series name (usually including the start year, e.g., "X-Force (2008)") and rerun the command.

---

## Automated Inbox Workflow

The installer sets this up for you automatically.

1.  **Add New Comics:** Download a new series and place the entire folder (e.g., a new folder named "New Comic Series") into `/path/to/your/comics/inbox`.
2.  **Wait:** At 2:30 AM, a cron job will run the `process_inbox.py` script.
3.  **Enjoy:** The script tags the new series, moves it to your main library, and tells Kavita to rescan. The new series will appear in your library, fully organized.

---

## Kavita Setup

If you haven't already, run Kavita via Docker. The installer provides the exact command needed for your setup.

**Key Configuration:**
-   When adding your library in Kavita, point it to the `/comics` folder (the path *inside* the container).
-   **Crucially:** Set the **Series Grouping** option to **"Group all files in the folder into one series"**. This prevents duplicates and ensures correct organization.