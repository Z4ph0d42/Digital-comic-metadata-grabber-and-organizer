# Automated Comic Archiving and Tagging Workflow for Kavita

Have you ever meticulously organized your digital comic collection into a perfect folder structure, only to import it into a media server like [Kavita](https://www.kavita.zip/) and watch it get dumped onto the digital floor in one giant, unsorted pile?

The problem is usually missing metadata. While powerful tools like [Comic Tagger](https://github.com/comictagger/comictagger) exist, they often require manual intervention to get started. To get reliable results, you have to search for each series by hand—an impossible task when you have thousands of comics.

This project was created to solve that exact problem. I automated it.

This workflow uses the folder structure you *already have* as a guide. It sets up a fully automated "inbox" system. You simply drop new, unprocessed comics into a folder, and a scheduled script handles the rest. It turns a manual chore into a "set it and forget it" solution.

## What It Does

The Python script (`process_inbox.py`) runs on a schedule and automates a four-stage process for any new comics it finds:

1.  **Archive:** It scans the "inbox" for issue folders containing images (e.g., `.jpg` files) and compresses each one into a new `.cbz` file, deleting the original folder on success.
2.  **Tag & Rename:** It uses the [Comic Tagger](https://github.com/comictagger/comictagger) CLI to fetch metadata from Comic Vine, embed it into the archive, and rename the file to a clean, standardized format.
3.  **Move:** It moves the newly processed comic folders from the inbox into your main library directory, merging them if the series already exists.
4.  **Scan:** It triggers an incremental library scan in Kavita via its API, so your new comics appear automatically.

Any files that cannot be automatically parsed are logged to `inbox_skipped.log` for manual review.

## Installation

These instructions are for a Debian-based system (e.g., Raspberry Pi OS, Debian, Ubuntu).

1.  **Download the Install Script:**
    Download the `install.sh` file from this repository to your server.

2.  **Make the Script Executable:**
    Open a terminal and run the following command:
    ```bash
    chmod +x install.sh
    ```

3.  **Run the Script:**
    Execute the script to install all necessary system dependencies and set up Comic Tagger in a dedicated project folder (`~/comictagger_project`).
    ```bash
    ./install.sh
    ```
    You may be prompted for your password to install system packages.

4.  **Install `requests` library:**
    The inbox script needs one additional Python library to communicate with the Kavita API.
    ```bash
    # Activate the virtual environment created by the install script
    source ~/comictagger_project/venv/bin/activate
    
    # Install requests
    pip install requests
    ```

## The Workflow: Setting Up Your Automated Inbox

### Step 1: Create the Inbox Folder

On your server, create a dedicated folder where you will drop new comics. This should be separate from your main library but can be on the same drive.

```bash
# Example:
mkdir -p /mnt/kavitacomics/inbox
```

### Step 2: Get Your API Keys

You will need two API keys for the script to function.

1.  **Comic Vine API Key:**
    *   Sign up for a free account at [comicvine.gamespot.com/api/](https://comicvine.gamespot.com/api/).
    *   Copy the API key provided.
    *   On your server, save this key into a plain text file (e.g., `/home/user/.comic_vine_api_key`).

2.  **Kavita API Key:**
    *   Log into your Kavita web interface.
    *   Click your user icon in the top right and go to **My Profile**.
    *   Under the "API Key" section, copy your key.

### Step 3: Configure the Inbox Script

Before running, you **must** edit the configuration variables at the top of the `process_inbox.py` script:

-   `INBOX_DIR`: The absolute path to the "inbox" folder you created in Step 1.
-   `LIBRARY_DIR`: The absolute path to your main comic library where processed comics should be moved.
-   `COMIC_TAGGER_EXE`: The path to the `comictagger` executable. The install script places this at `~/comictagger_project/venv/bin/comictagger`.
-   `API_KEY_FILE`: The absolute path to the file where you saved your Comic Vine API key.
-   `KAVITA_API_KEY`: Paste the key you copied from your Kavita profile here.
-   `SKIPPED_FILES_LOG`: The path where you want the log file for skipped files to be saved.

### Step 4: Test the Script Manually

Before automating, it's wise to test the script once.

1.  **Drop a new comic folder** into your `inbox` directory.
2.  **Activate the Virtual Environment** in your terminal:
    ```bash
    source ~/comictagger_project/venv/bin/activate
    ```
3.  **Run the script:**
    ```bash
    python3 /path/to/your/process_inbox.py
    ```
    Watch the output. The script should find the comic, archive it, tag it, move it, and trigger a Kavita scan. Check your Kavita library to see if the new comic appears.

### Step 5: Automate with Cron (The Scheduler)

Once you've confirmed the script works, you can schedule it to run automatically.

1.  **Open the cron editor:**
    ```bash
    crontab -e
    ```
    *(If it's your first time, select `nano` as your editor).*

2.  **Add the scheduled job:**
    Scroll to the bottom of the file and add the following line. This example runs the script every night at 3:00 AM.
    ```
    0 3 * * * /home/user/comictagger_project/venv/bin/python3 /path/to/your/process_inbox.py >> /home/user/inbox_processing.log 2>&1
    ```
    *   **Important:** Make sure to use the correct absolute paths for your user.
    *   `>> /home/user/inbox_processing.log 2>&1` saves all script output to a log file for easy troubleshooting.

3.  Save and exit the editor. The cron job is now active.

### Your Daily Workflow

Your setup is complete. From now on, your workflow is simple:
1.  Download a new comic.
2.  Drag and drop the unprocessed folder into your `inbox`.
3.  The scheduled script will handle the rest overnight.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.