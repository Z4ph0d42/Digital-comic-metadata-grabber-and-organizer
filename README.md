Digital Comic Metadata Grabber and Organizer

This project provides a suite of Python scripts to create a powerful, automated pipeline for processing a digital comic book library. It intelligently tags, renames, and organizes new comics, while also detecting duplicates, converting formats, and handling errors safely.

The core of the system is a script that watches an "inbox" directory, processes new files one-by-one, and moves them into a clean, organized library structure suitable for use with media servers like Kavita.

Key Features

Automated Inbox Processing – Simply drop new comic files into the inbox and run the script.

PDF to CBZ Conversion – Automatically converts PDF comics into the standard, metadata-compatible CBZ format.

Advanced Duplicate Detection – Uses a database of file hashes to detect and quarantine 100% identical duplicate issues, saving disk space.

Safe Quarantine System – Instead of deleting files it can't process, the script moves them to a quarantine folder. A separate management script allows for easy review, fixing, or deletion of these files.

Intelligent Metadata Fallback – If the primary metadata tool (comictagger) fails to find a perfect match for a comic, the script falls back to parsing the filename to ensure the comic is still filed correctly in your library.

Database-Driven Library – Maintains a lightweight SQLite database of your collection for fast and efficient duplicate checks.

The Workflow

The system is designed around a simple, multi-stage workflow:

Initial Setup – Install dependencies and run the one-time library scan.

Add New Comics – Place new, unsorted comic files (.cbz, .cbr, .pdf) into the inbox folder.

Process Inbox – Run the main process_inbox.py script. It will automatically convert, tag, check for duplicates, and file everything it can.

Manage Quarantine – For any files the script couldn't handle (e.g., ambiguous names, true duplicates), use the manage_quarantine.py script to easily fix, delete, or re-process them.

Setup and Installation
1. Dependencies

This project relies on a few external tools and Python libraries.

System Tools

You must have unrar installed for .cbr file support.

# On Debian/Ubuntu
```bash
sudo apt-get update && sudo apt-get install unrar
```

Python Environment

It is highly recommended to use a Python virtual environment.
```bash
python3 -m venv venv
source venv/bin/activate
pip install rarfile PyMuPDF
```

ComicTagger

This script uses the command-line version of comictagger.
Follow its installation instructions to install it within your virtual environment.
You will also need to get a free API key from ComicVine and place it in a file.

2. Configuration

Before running, you must edit the configuration variables at the top of each of the three main Python scripts (process_inbox.py, build_library_db.py, manage_quarantine.py).

INBOX_DIR         – The full path to your "new comics" folder.
LIBRARY_DIR       – The full path to your main comic library.
QUARANTINE_DIR    – The full path to a folder where problem comics will be moved.
COMIC_TAGGER_EXE  – The full path to your comictagger executable inside your virtual environment.
API_KEY_FILE      – The full path to the file containing your ComicVine API key.

Usage
Step 1: Perform the Initial Library Scan (One Time Only)

Before you can process new comics, you must build a database of your existing collection.
This allows the script to detect duplicates.
```bash
python3 build_library_db.py
```

Note: This will take a very long time for a large library. Let it finish completely.

Step 2: Process New Comics

Whenever you have new comics, place them in your INBOX_DIR and run the main script.
```bash
python3 process_inbox.py
```

The script will provide detailed output on its actions for each file.

Step 3: Manage Quarantined Files

If the script moves any files to your QUARANTINE_DIR, you can review them with the interactive management tool.
```bash
python3 manage_quarantine.py
```

This tool will allow you to:

(F)ix – Interactively rename a comic with an ambiguous name and send it back to the inbox.

(K)eep – Move a file back to the inbox as-is.

(D)elete – Permanently delete a duplicate or unwanted file.