#!/bin/bash

# 1. Define paths (Using absolute paths for safety)
SCRIPT_DIR="/home/james/scripts/comic-organizer"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"
COMIC_SCRIPT="$SCRIPT_DIR/process_inbox.py"
MAGAZINE_SCRIPT="$SCRIPT_DIR/process_magazines.py"
LOG_FILE="$SCRIPT_DIR/cron_log.txt"

# 2. Go to the directory (Crucial for relative paths to work)
cd "$SCRIPT_DIR"

# 3. Write a start header to the log
echo "---------------------------------" >> "$LOG_FILE"
echo "Starting Daily Organization Job: $(date)" >> "$LOG_FILE"

# 4. Run the COMIC script
echo "--> Processing Comics..." >> "$LOG_FILE"
"$VENV_PYTHON" "$COMIC_SCRIPT" >> "$LOG_FILE" 2>&1

# 5. Run the MAGAZINE script (Added this step)
echo "--> Processing Magazines..." >> "$LOG_FILE"
"$VENV_PYTHON" "$MAGAZINE_SCRIPT" >> "$LOG_FILE" 2>&1

# 6. Trigger Kavita Scan (Optional)
# CURL_CMD="curl -X POST http://localhost:5000/api/Library/scan?force=true -H 'ApiKey: YOUR_KAVITA_API_KEY'"
# $CURL_CMD >> "$LOG_FILE" 2>&1

echo "Job Finished: $(date)" >> "$LOG_FILE"
