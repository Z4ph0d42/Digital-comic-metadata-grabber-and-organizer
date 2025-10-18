# Automated Comic Archiving and Tagging Workflow for Kavita

Have you ever meticulously organized your digital comic collection into a perfect folder structure, only to import it into a media server like [Kavita](https://www.kavita.zip/) and watch it get dumped onto the digital floor in one giant, unsorted pile?

The problem is usually missing metadata. While powerful tools like [Comic Tagger](https://github.com/comictagger/comictagger) exist, they often require manual intervention to get started. To get reliable results, you have to search for each series by hand—an impossible task when you have thousands of comics.

This project was created to solve that exact problem. I automated it.

This workflow uses the folder structure you *already have* as a guide. It provides scripts and a complete guide to set up a fully automated system. You simply drop new, unprocessed comics into an "inbox" folder, and a scheduled script handles the rest. It turns a manual chore into a "set it and forget it" solution.

## What It Does

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
    ```bash
    chmod +x install.sh
    ```

3.  **Run the Script:**
    Execute the script to install all dependencies and set up Comic Tagger in a dedicated project folder (`~/comictagger_project`).
    ```bash
    ./install.sh
    ```

4.  **Install `requests` library:**
    The inbox script needs this library to communicate with the Kavita API.
    ```bash
    # Activate the virtual environment created by the install script
    source ~/comictagger_project/venv/bin/activate
    
    # Install requests
    pip install requests
    ```

## The Workflow: Setting Up Your Automated Inbox

### Step 1: Create the Inbox Folder

On your server, create a dedicated folder where you will drop new comics.

```bash
# Example:
mkdir -p /path/to/your/inbox
```

### Step 2: Get Your API Keys

You will need two API keys for the script to function.

1.  **Comic Vine API Key:**
    *   Sign up for a free account at [comicvine.gamespot.com/api/](https://comicvine.gamespot.com/api/).
    *   Copy the API key and save it to a plain text file on your server (e.g., `/home/user/.comic_vine_api_key`).

2.  **Kavita API Key:**
    *   Log into your Kavita web interface.
    *   Click your user icon and go to **My Profile**.
    *   Under the "API Key" section, copy your key.

### Step 3: Configure the Inbox Script

Before running, you **must** edit the configuration variables at the top of the `process_inbox.py` script:

-   `INBOX_DIR`: The absolute path to the "inbox" folder.
-   `LIBRARY_DIR`: The absolute path to your main comic library.
-   `COMIC_TAGGER_EXE`: The path to the `comictagger` executable (the install script places it at `~/comictagger_project/venv/bin/comictagger`).
-   `API_KEY_FILE`: The path to your Comic Vine API key file.
-   `KAVITA_API_KEY`: Paste the key you copied from your Kavita profile here.
-   `SKIPPED_FILES_LOG`: The path where you want the log file for skipped files to be saved.

### Step 4: Test the Script Manually

1.  **Drop a new comic folder** into your `inbox` directory.
2.  **Activate the Virtual Environment:** `source ~/comictagger_project/venv/bin/activate`
3.  **Run the script:** `python3 /path/to/your/process_inbox.py`
4.  Watch the output and check your Kavita library to see if the new comic appears.

### Step 5: Automate with Cron (The Scheduler)

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