import os
import shutil
import re
import sys

# --- CONFIGURATION ---
QUARANTINE_DIR = "/path/to/your/quarantine_folder"
INBOX_DIR = "/path/to/your/inbox"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(PROJECT_DIR, "process_inbox.log")
# ---------------------

def find_quarantine_reason(file_path):
    try:
        with open(LOG_FILE, 'r') as f:
            for line in reversed(list(f)):
                if os.path.basename(file_path) in line and "QUARANTINED" in line:
                    return line.strip().split(' | ')[-1] # Return the reason part
    except FileNotFoundError: return "Log file not found."
    return "Reason not found."

def fix_and_requeue(filename):
    original_path=os.path.join(QUARANTINE_DIR,filename); _,ext=os.path.splitext(filename)
    print("\n--- Interactive File Fix ---"); print(f"Fixing: {filename}")
    series=input("  Enter correct Series Title: "); issue=input("  Enter correct Issue Number: "); year=input("  Enter correct Volume Year: ")
    if not all([series, issue, year]): print("\nERROR: All fields are required. Aborting."); return False
    new_filename=f"{series} #{issue} ({year}){ext}"
    if input(f"\nNew filename: '{new_filename}'. Move to inbox? (y/n): ").lower() == 'y':
        try:
            temp_path=os.path.join(QUARANTINE_DIR,new_filename); os.rename(original_path,temp_path)
            shutil.move(temp_path,os.path.join(INBOX_DIR,new_filename)); print("File fixed and moved to inbox.")
            return True
        except Exception as e: print(f"ERROR: {e}"); os.rename(temp_path,original_path) if os.path.exists(temp_path) else None
    else: print("Fix cancelled.")
    return False

def main_menu():
    while True:
        files=sorted([f for f in os.listdir(QUARANTINE_DIR) if os.path.isfile(os.path.join(QUARANTINE_DIR,f))]) if os.path.exists(QUARANTINE_DIR) else []
        os.system('cls' if os.name == 'nt' else 'clear'); print("--- Quarantine Management ---")
        if not files: print("\nQuarantine is empty.")
        else:
            for i,filename in enumerate(files): print(f"  {i+1}) {filename}")
        print("\n--- Options ---\n (E) Empty quarantine\n (q) Quit")
        choice=input("\nSelect a file or option: ").lower()
        if choice=='q':break
        elif choice=='e':
             if input("Permanently delete all files in quarantine? (y/n): ").lower()=='y':
                for f in files: os.remove(os.path.join(QUARANTINE_DIR,f))
        else:
            try:
                idx=int(choice)-1
                if 0<=idx<len(files):
                    while True:
                        file_to_review = files[idx]
                        os.system('cls' if os.name == 'nt' else 'clear');print(f"--- Reviewing: {file_to_review} ---\n  Reason: {find_quarantine_reason(file_to_review)}")
                        print("\nActions:\n (F)ix & Re-queue\n (K)eep (move to inbox)\n (D)elete\n (B)ack")
                        action=input("Choose action: ").lower()
                        if action=='b':break
                        elif action=='f':
                            if fix_and_requeue(file_to_review): break
                        elif action=='k':shutil.move(os.path.join(QUARANTINE_DIR,file_to_review),INBOX_DIR);print("Moved.");break
                        elif action=='d':
                            if input("Permanently delete? (y/n): ").lower()=='y':
                                os.remove(os.path.join(QUARANTINE_DIR,file_to_review));print("Deleted.");break
            except(ValueError,IndexError):print("Invalid selection.")
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    if "/path/to/" in QUARANTINE_DIR: sys.exit("Error: Please update the placeholder paths in the script before running.")
    main_menu()