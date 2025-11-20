import os
import shutil
import sys

# --- CONFIGURATION ---
INBOX_DIR = "/path/to/comics/inbox"
QUARANTINE_DIR = "/path/to/comics/quarantine"

def list_quarantine():
    print("\n--- QUARANTINE REPORT ---")
    if not os.path.exists(QUARANTINE_DIR):
        print("Quarantine directory not found.")
        return

    categories = [d for d in os.listdir(QUARANTINE_DIR) if os.path.isdir(os.path.join(QUARANTINE_DIR, d))]
    
    if not categories:
        print("Quarantine is empty.")
        return

    for cat in categories:
        cat_path = os.path.join(QUARANTINE_DIR, cat)
        files = os.listdir(cat_path)
        print(f"\n[{cat.upper()}] - {len(files)} files")

def restore_category(category):
    cat_path = os.path.join(QUARANTINE_DIR, category)
    if not os.path.exists(cat_path):
        print("Category not found.")
        return
    
    files = os.listdir(cat_path)
    print(f"Moving {len(files)} files back to Inbox...")
    for f in files:
        src = os.path.join(cat_path, f)
        dst = os.path.join(INBOX_DIR, f)
        if os.path.exists(dst):
            print(f"Skipping {f} (Exists in Inbox)")
            continue
        shutil.move(src, dst)
    
    # Clean up empty dir
    if not os.listdir(cat_path):
        os.rmdir(cat_path)
    print("Done.")

def main():
    while True:
        list_quarantine()
        print("\nOPTIONS:")
        print("1. Exit")
        print("2. Restore 'Tagging_Failed' to Inbox")
        print("3. Restore 'Untagged_Ambiguous' to Inbox")
        print("4. Restore 'Corrupt_Archive' to Inbox (Only if you fixed them)")
        
        choice = input("\nSelect: ")
        
        if choice == '1': break
        elif choice == '2': restore_category("Tagging_Failed")
        elif choice == '3': restore_category("Untagged_Ambiguous")
        elif choice == '4': restore_category("Corrupt_Archive")
        else: print("Invalid option.")

if __name__ == "__main__":
    main()