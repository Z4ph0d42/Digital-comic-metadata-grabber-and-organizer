import os
import zipfile
import shutil

# --- CONFIGURATION ---
# The root directory of your comic library.
COMIC_ROOT = "/path/to/your/comics"
# --- END CONFIGURATION ---

def is_image_file(filename):
    """Check if a file has a common comic image extension."""
    return filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))

def process_library():
    """
    Walks the comic library and zips any folder containing images into a .cbz archive.
    The original folder is deleted upon successful creation of the .cbz file.
    """
    print("Starting library packing process...")
    
    # Walk through the entire comics directory from the bottom up
    for root, dirs, files in os.walk(COMIC_ROOT, topdown=False):
        # Find all image files directly in the current folder
        image_files = sorted([f for f in files if is_image_file(f)])
        
        # If there are images here, this folder needs to be packed
        if image_files:
            folder_name = os.path.basename(root)
            parent_dir = os.path.dirname(root)
            
            # The CBZ will be named after the folder it's in, and placed in the parent directory
            cbz_path = os.path.join(parent_dir, f"{folder_name}.cbz")
            
            # Avoid re-packing an already packed comic
            if os.path.exists(cbz_path):
                continue

            print(f"  -> Packing folder: '{root}'")
            
            try:
                # Create the new CBZ file
                with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for image in image_files:
                        image_path = os.path.join(root, image)
                        zf.write(image_path, arcname=image)
                
                # After successfully creating the CBZ, remove the original folder
                print(f"  -> Successfully created '{cbz_path}'. Removing original folder.")
                shutil.rmtree(root)

            except Exception as e:
                print(f"  -> ERROR: Failed to pack '{root}': {e}")

    print("\nPacking process complete.")

if __name__ == "__main__":
    process_library()