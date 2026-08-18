# Digital Media Organizer & Metadata Automator

An automated Python toolset designed for self-hosted libraries (**Kavita** or **Komga**) running on Debian. It handles two separate pipelines: **Comics** (via ComicVine and ComicTagger) and **Magazines** (via Filename Parsing, Noise-Filtered Folder Matching, and local OCR Gap-Filling).

## Pipelines Overview

### 1. Comic Pipeline (`process_inbox.py`)
*   **Smart Organization:** Routes messy downloads from Inbox to Library using `Publisher/Series vVol/Series #Issue (Year).ext`.
*   **Metadata Engine:** Leverages **ComicTagger** and the ComicVine API for precise comic book tagging.
*   **Duplicate Protection:** Computes SHA256 hashes stored in a local SQLite database (`library.db`).

### 2. Magazine Pipeline (`process_magazines.py`)
*   **Zero-API Design:** Relies completely on local text intelligence rather than fragile external databases.
*   **Canonical Folder Matching:** Intelligently maps naming variations (e.g., mapping "2600 Magazine" to an existing "2600 v40" folder) to keep series unified.
*   **OCR Gap-Filler:** If a filename lacks a month or year, the script spins up **Tesseract OCR** to scan *only* the first page (cover) to extract missing publication dates safely without hallucinations.
*   **Auto-XML Forging:** Dynamically writes and injects a local `ComicInfo.xml` directly into the `.cbz` archive so Kavita instantly reads the correct Series, Volume, and Issue numbers.

## Automation & Cron Scheduling

Both pipelines are fully automated via daily cron jobs to keep server resource usage staggered:
*   **Comics:** Runs on its designated schedule.
*   **Magazines:** Runs daily at **4:00 AM** to prevent overlapping heavy OCR/PDF conversions:
    ```cron
    0 4 * * * /usr/bin/python3 /home/james/scripts/comic-organizer/process_magazines.py >> /home/james/scripts/comic-organizer/cron_magazines.log 2>&1
    ```

## Folder Structure
```text
/srv/
├── comics/
│   ├── inbox
│   └── [Library Folders]
└── magazines/
    ├── inbox           <-- Drop messy PDFs/CBZs here
    ├── quarantine      <-- Failed conversions or duplicates
    └── [Library Folders] <-- Clean, volume-sorted series folders
```
