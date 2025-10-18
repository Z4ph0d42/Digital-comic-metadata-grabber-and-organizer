# Automated Comic Archiving and Tagging Workflow for Kavita

Have you ever meticulously organized your digital comic collection into a perfect folder structure, only to import it into a media server like [Kavita](https://www.kavita.zip/) and watch it get dumped onto the digital floor in one giant, unsorted pile?

The problem is usually missing metadata. While powerful tools like [Comic Tagger](https://github.com/comictagger/comictagger) exist, they often require manual intervention to get started. To get reliable results, you have to search for each series by hand—an impossible task when you have thousands of comics.

This project was created to solve that exact problem. I automated it.

This workflow uses the folder structure you *already have* as a guide. It provides two main scripts:
1.  `process_full_library.py`: A powerful, one-time script to convert your entire existing library of unprocessed comics into a perfectly tagged and organized collection.
2.  `process_inbox.py`: A script designed to be run on a schedule, which automatically processes new comics dropped into an "inbox" folder and adds them to your library and Kavita.

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

## The Workflow

The workflow is divided into two parts: a one-time setup for your existing library, and then the ongoing automation for new comics.

### Part 1: Initial Library Conversion

Use the `process_full_library.py` script for this.

1.  **Get Your Comic Vine API Key:**
    *   Sign up for a free account at [comicvine.gamespot.com/api/](https://comicvine.gamespot.com/api/).
    *   Copy the API key provided and save it to a plain text file on your server (e.g., `/home/user/.comic_vine_api_key`).

2.  **Configure the Script:**
    *   Edit the configuration variables at the top of the `process_full_library.py` script to match your system's paths.
    *   **Crucially, leave `DRY_RUN = True` for the first run.**

3.  **Execute the Script:**
    *   Activate the virtual environment: `source ~/comictagger_project/venv/bin/activate`
    *   Run a **Dry Run** to test: `python3 /path/to/your/process_full_library.py`
    *   If the output looks correct, change `DRY_RUN` to `False` in the script and run it again to process your entire library. This will take a long time.

4.  **Final Kavita Scan:**
    *   Once the script finishes, go to your Kavita web UI, **Delete** and **Re-add** your comics library to ensure a clean import.

### Part 2: Ongoing Automation with the Inbox

Use the `process_inbox.py` script for this.

1.  **Create an Inbox Folder** on your server where you will drop new comics (e.g., `/path/to/your/inbox`).

2.  **Get Your Kavita API Key:**
    *   In your Kavita UI, go to **My Profile** and copy your API Key.

3.  **Configure the Script:**
    *   Edit the configuration variables at the top of the `process_inbox.py` script, including your paths and pasting in your Kavita API key.

4.  **Test the Script Manually:**
    *   Drop a new comic folder into your `inbox`.
    *   Activate the virtual environment and run `python3 /path/to/your/process_inbox.py`.
    *   Check if the comic is processed correctly and appears in Kavita.

5.  **Automate with Cron (The Scheduler):**
    *   Open the cron editor: `crontab -e`
    *   Add a line to schedule the script. This example runs it every night at 3:00 AM:
        ```
        0 3 * * * /home/user/comictagger_project/venv/bin/python3 /path/to/your/process_inbox.py >> /home/user/inbox_processing.log 2>&1
        ```
    *   Save and exit. Your automated system is now live.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.