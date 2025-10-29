# Digital Comic Metadata Grabber and Organizer

This project provides a set of scripts and a workflow for automatically organizing and tagging a digital comic book library for use with a media server like [Kavita](https://www.kavitareader.com/).

The system is designed to:
-   Automatically tag comic files (`.cbz`, `.cbr`) with rich metadata from ComicVine.
-   Provide a simple "inbox" workflow for adding new comics.
-   Run automatically on a schedule (e.g., nightly).
-   Gracefully handle comics that can't be matched, organizing them by folder name for later review.

---

<<<<<<< Updated upstream
This workflow uses the folder structure you *already have* as a guide. It provides scripts and a complete guide to set up a fully automated system. You simply drop new, unprocessed comics into an "inbox" folder, and a scheduled script handles the rest. It turns a manual chore into a "set it and forget it" solution.
=======
## Quick Installation (Recommended for Debian/Ubuntu)
>>>>>>> Stashed changes

This installer automates the entire setup process.

<<<<<<< Updated upstream
The main script (`process_inbox.py`) runs on a schedule and automates a four-stage process for any new comics it finds:

1.  **Archive:** It scans the "inbox" for issue folders containing images (e.g., `.jpg` files) and compresses each one into a new `.cbz` file.
2.  **Tag & Rename:** It uses the [Comic Tagger](https://github.com/comictagger/comictagger) CLI to fetch metadata from Comic Vine, embed it into the archive, and rename the file to a clean, standardized format.
3.  **Move:** It moves the newly processed comic folders from the inbox into your main library directory.
4.  **Scan:** It triggers an incremental library scan in Kavita via its API, so your new comics appear automatically.

Any files that cannot be automatically parsed are logged for manual review.

## Installation

These instructions are for a Debian-based system (e.g., Raspberry Pi OS, Debian, Ubuntu).

1.  **Download the Install Script:**
    Download the `install.sh` file from this repository to your server.

2.  **Make the Script Executable:**
    Open a terminal and run the following command:
=======
1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Z4ph0d42/Digital-comic-metadata-grabber-and-organizer.git
    cd Digital-comic-metadata-grabber-and-organizer
    ```

2.  **Make the Installer Executable:**
>>>>>>> Stashed changes
    ```bash
    chmod +x install.sh
    ```

<<<<<<< Updated upstream
3.  **Run the Script:**
    Execute the script to install all dependencies and set up Comic Tagger in a dedicated project folder (`~/comictagger_project`).
=======
3.  **Run the Installer:**
    The script will prompt you for your comic library path and API keys.
>>>>>>> Stashed changes
    ```bash
    ./install.sh
    ```

<<<<<<< Updated upstream
4.  **Install `requests` library:**
    The inbox script needs this library to communicate with the Kavita API.
    ```bash
    # Activate the virtual environment created by the install script
    source ~/comictagger_project/venv/bin/activate
    
    # Install requests
    pip install requests
    ```
=======
The installer will handle system dependencies, Python environment setup, script creation, and cron job installation. Follow the "NEXT STEPS" printed at the end to set up Kavita.
>>>>>>> Stashed changes

---

## Manual Workflow (for Existing Libraries)

<<<<<<< Updated upstream
On your server, create a dedicated folder where you will drop new comics.
=======
After installation, your first step should be to tag your entire existing library.
>>>>>>> Stashed changes

**1. Clean Up Junk Files (Optional but Recommended):**
These commands find and permanently delete temporary files.
```bash
<<<<<<< Updated upstream
# Example:
mkdir -p /path/to/your/inbox
=======
# Find and delete leftover temporary files/folders
find /path/to/your/comics -iname "*tmp*" -delete

# Find and delete leftover .bin files
find /path/to/your/comics -type f -name "*.bin" -delete
>>>>>>> Stashed changes
```

**2. Pack Loose Image Folders:**
The installer creates a `pack_comics.py` script. Run it to convert any folders containing only images into `.cbz` files.
```bash
# Activate the virtual environment first
source ~/comic_organizer/venv/bin/activate

# Run the packer script
python ~/comic_organizer/scripts/pack_comics.py
```

<<<<<<< Updated upstream
1.  **Comic Vine API Key:**
    *   Sign up for a free account at [comicvine.gamespot.com/api/](https://comicvine.gamespot.com/api/).
    *   Copy the API key and save it to a plain text file on your server (e.g., `/home/user/.comic_vine_api_key`).

2.  **Kavita API Key:**
    *   Log into your Kavita web interface.
    *   Click your user icon and go to **My Profile**.
    *   Under the "API Key" section, copy your key.
=======
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
>>>>>>> Stashed changes

---

## Automated Inbox Workflow

<<<<<<< Updated upstream
-   `INBOX_DIR`: The absolute path to the "inbox" folder.
-   `LIBRARY_DIR`: The absolute path to your main comic library.
-   `COMIC_TAGGER_EXE`: The path to the `comictagger` executable (the install script places it at `~/comictagger_project/venv/bin/comictagger`).
-   `API_KEY_FILE`: The path to your Comic Vine API key file.
-   `KAVITA_API_KEY`: Paste the key you copied from your Kavita profile here.
-   `SKIPPED_FILES_LOG`: The path where you want the log file for skipped files to be saved.
=======
The installer sets this up for you automatically.
>>>>>>> Stashed changes

1.  **Add New Comics:** Download a new series and place the entire folder (e.g., a new folder named "New Comic Series") into `/path/to/your/comics/inbox`.
2.  **Wait:** At 2:30 AM, a cron job will run the `process_inbox.py` script.
3.  **Enjoy:** The script tags the new series, moves it to your main library, and tells Kavita to rescan. The new series will appear in your library, fully organized.

<<<<<<< Updated upstream
1.  **Drop a new comic folder** into your `inbox` directory.
2.  **Activate the Virtual Environment:** `source ~/comictagger_project/venv/bin/activate`
3.  **Run the script:** `python3 /path/to/your/process_inbox.py`
4.  Watch the output and check your Kavita library to see if the new comic appears.
=======
---

## Kavita Setup
>>>>>>> Stashed changes

If you haven't already, run Kavita via Docker. The installer provides the exact command needed for your setup.

<<<<<<< Updated upstream
1.  **Open the cron editor:** `crontab -e`
2.  Add a line to schedule the script. This example runs it every night at 3:00 AM.
    ```
    0 3 * * * /home/user/comictagger_project/venv/bin/python3 /path/to/your/process_inbox.py >> /home/user/inbox_processing.log 2>&1
    ```
    *   **Important:** Use the correct absolute paths for your user and script locations.
    *   The `>>` portion saves all script output to a log file for easy troubleshooting.
3.  Save and exit the editor. Your automated system is now live.

## Making Your Server Robust (Highly Recommended)

If your comic library is on an external USB drive, you may encounter a "race condition" on reboot: the Docker service (and thus Kavita) can start before your USB drive is fully mounted and ready. This can cause Kavita to start with an empty or broken library.

You can fix this permanently with a systemd override.

1.  **Edit the Docker service configuration:**
    This command will open a blank text file.
    ```bash
    sudo systemctl edit docker.service
    ```

2.  **Add a Dependency Rule:**
    Paste the following two lines into the file. You must replace `mnt-kavitacomics.mount` with the correct path to your comic library's mount point, as defined in `/etc/fstab`.
    ```
    [Unit]
    Requires=mnt-kavitacomics.mount
    ```

3.  **Save and Exit** the editor.

4.  **Reload the System Configuration:**
    This applies your new rule.
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl restart docker
    ```
This ensures that your server will always boot up in the correct order, making it truly reliable.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
=======
**Key Configuration:**
-   When adding your library in Kavita, point it to the `/comics` folder (the path *inside* the container).
-   **Crucially:** Set the **Series Grouping** option to **"Group all files in the folder into one series"**. This prevents duplicates and ensures correct organization.
>>>>>>> Stashed changes
