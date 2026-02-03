import shutil
import os
import glob

# Source directory (Artifacts)
src_dir = r"C:\Users\mmoza\.gemini\antigravity\brain\af8ecf4f-5482-4e5e-a98d-16486fcaeb05"
# Destination directory (Project)
dst_dir = r"c:\Users\mmoza\Desktop\Study-hub3"

# Map partial names to desired final names
files_to_copy = {
    "01_landing_page": "01_landing_page.png",
    "02_login_page": "02_login_page.png",
    "03_register_page_error": "03_register_failed.png",
    "04_domains_page": "04_domains_page.png"
}

print(f"Copying files from {src_dir} to {dst_dir}...")

for partial_name, final_name in files_to_copy.items():
    # Find the actual file (it has a timestamp suffix)
    pattern = os.path.join(src_dir, f"{partial_name}*.png")
    matches = glob.glob(pattern)
    
    if matches:
        # Sort by usage/time (newest first usually) or just take first
        src_file = matches[0]
        dst_file = os.path.join(dst_dir, final_name)
        
        try:
            shutil.copy2(src_file, dst_file)
            print(f"✅ Copied: {final_name}")
        except Exception as e:
            print(f"❌ Failed to copy {final_name}: {e}")
    else:
        print(f"⚠️  Not found: {partial_name}")

print("Done.")
