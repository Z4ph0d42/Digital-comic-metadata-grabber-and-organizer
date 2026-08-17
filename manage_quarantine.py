import os
import shutil
import sys

INBOX_DIR = "/srv/comics/inbox"
QUARANTINE_DIR = "/srv/comics/quarantine"

def list_quarantine():
    print("\n--- QUARANTINE REPORT ---")
    if not os.path.exists(QUARANTINE_DIR):
        print(f"Quarantine dir {QUARANTINE_DIR} not found.")
        return

    categories = [d for d in os.listdir(QUARANTINE_DIR) if os.path.isdir(os.path.join(QUARANTINE_DIR, d))]
    
    if not categories:
        print("Quarantine is empty!")
        return

    for cat in categories:
        cat_path = os.path.join(QUARANTINE_DIR, cat)
        files = os.listdir(cat_path)
        print(f"\n[{cat.upper()}] - {len(files)} files:")
        for f in files[:5]:
            print(f"  - {f}")
        if len(files) > 5:
            print(f"  ... and {len(files)-5} more.")

def restore_category(category):
    cat_path = os.path.join(QUARANTINE_DIR, category)
    if not os.path.exists(cat_path):
        print("Category not found.")
        return
    
    files = os.listdir(cat_path)
    print(f"Moving {len(files)} files back to Inbox...")
    for f in files:
        shutil.move(os.path.join(cat_path, f), os.path.join(INBOX_DIR, f))
    print("Done.")

def main():
    while True:
        list_quarantine()
        print("\nOPTIONS: [1] Exit  [2] Retry Tagging_Failed  [3] Retry Untagged_NoMatch  [4] Retry All")
        choice = input("Select: ")
        
        if choice == '1': break
        elif choice == '2': restore_category("Tagging_Failed")
        elif choice == '3': restore_category("Untagged_NoMatch")
        elif choice == '4':
            for cat in os.listdir(QUARANTINE_DIR):
                restore_category(cat)

if __name__ == "__main__":
    main()
