# Automated Comic Archiving and Tagging Workflow for Kavita

This project provides a script and a workflow to automatically process a comic library for use with a media server like [Kavita](https://www.kavita.zip/). It is designed to solve two specific problems:
1.  Comic issues that are stored as folders of images (e.g., `.jpg` files) instead of `.cbz` archives.
2.  Inconsistent naming that makes it difficult for metadata scrapers to identify series and issues automatically.

The Python script (`process_comics.py`) automates a two-stage process:
-   **Stage 1 (Archive):** It scans the comic library, finds issue folders containing images, and compresses each one into a new `.cbz` file, deleting the original folder on success.
-   **Stage 2 (Tag & Rename):** It then uses the [Comic Tagger](https://github.com/comictagger/comictagger) Command Line Interface (CLI) to accurately fetch metadata from Comic Vine, embed it into the `.cbz` file, and rename the file to a clean, standardized format.

Any files that cannot be automatically parsed are logged to `skipped_files.log` for manual review.

## Installation

These instructions are for a Debian-based system (e.g., Raspberry Pi OS, Debian, Ubuntu).

1.  **Download the Install Script:**
    Download the `install.sh` file from this repository to your server.

2.  **Make the Script Executable:**
    Open a terminal and run the following command to give the script permission to execute:
    ```bash
    chmod +x install.sh
    ```

3.  **Run the Script:**
    Execute the script. It will handle all necessary system updates, dependency installations, and the setup of Comic Tagger in a dedicated project folder (`~/comictagger_project`).
    ```bash
    ./install.sh
    ```
    You may be prompted for your password as the script needs to install system packages.

## The Workflow

### Step 1: Initial Folder Structure

This script is designed to handle a library that primarily contains **folders of images**.

```
/path/to/comics/
├── Series Name (Year)/
│   ├── #1/
│   │   ├── 01.jpg
│   │   ├── 02.jpg
│   │   └── ...
│   ├── #2/
│   │   ├── 01.jpg
│   │   └── ...
```

### Step 2: Get Your Comic Vine API Key

1.  Sign up for a free account at [comicvine.gamespot.com/api/](https://comicvine.gamespot.com/api/).
2.  Copy the API key provided on that page.
3.  On your server, save this key into a plain text file (e.g., `/home/user/.comic_vine_api_key`).

### Step 3: Configure the Processing Script

Before running, you **must** edit the configuration variables at the top of the `process_comics.py` script:

-   `COMIC_ROOT`: The absolute path to the root of your comic library (e.g., `/mnt/kavitacomics`).
-   `COMIC_TAGGER_EXE`: The path to the `comictagger` executable. The install script places this at `~/comictagger_project/venv/bin/comictagger`.
-   `API_KEY_FILE`: The absolute path to the file where you saved your Comic Vine API key.
-   `DRY_RUN`: **Leave this as `True` for your first run.** This is a critical safety feature.

### Step 4: Execute the Processing Script

1.  **Activate the Virtual Environment:**
    The install script created a virtual environment. You must activate it in your terminal before running the processing script.
    ```bash
    source ~/comictagger_project/venv/bin/activate
    ```

2.  **Perform a "Dry Run":**
    Run the script with `DRY_RUN = True`.
    ```bash
    python3 /path/to/your/process_comics.py
    ```
    The script will print all actions it *would* take without modifying any files. Review this output carefully.

3.  **Perform the "Live Run":**
    If satisfied, edit the script, change `DRY_RUN = True` to `DRY_RUN = False`, and run it again:
    ```bash
    python3 /path/to/your/process_comics.py
    ```
    This will begin the full process, which may take a long time.

### Step 5: Final Kavita Scan

Once the script has completed, your library is ready.

1.  Start your Kavita server.
2.  In the Kavita web UI, **Delete** and **Re-add** your comics library to ensure a clean import.
3.  Let Kavita perform a fresh scan.
4.  Check the `skipped_files.log` file for any comics that need to be fixed manually.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.