"""
Sort screenshots from HACKATHON UI SS into data toolkit folders
"""
import os
import shutil
import glob

# Source folder
SOURCE = r"C:\Users\griff\OneDrive - Providence College\Pictures\HACKATHON UI SS"

# Destination base
DEST = os.path.expanduser("~/Downloads/hackathon-data-toolkit/data-toolkit/data")

# Map filename prefixes to folder names
APP_MAP = {
    "airtable": "airtable",
    "asana": "asana",
    "basecamp": "basecamp",
    "clickup": "clickup",
    "jira": "jira",
    "linear": "linear",
    "monday": "monday",
    "monday.com": "monday",
    "notion": "notion",
    "todoist": "todoist",
    "todoistmobile": "todoist",
    "trello": "trello",
}

def get_app_name(filename):
    """Extract app name from filename like 'asana5.png' -> 'asana'"""
    name = os.path.splitext(filename)[0].lower()
    
    # Check exact matches first (for monday.com, todoistmobile)
    for prefix in sorted(APP_MAP.keys(), key=len, reverse=True):
        if name.startswith(prefix):
            return APP_MAP[prefix]
    
    # Strip trailing numbers
    base = name.rstrip('0123456789')
    if base in APP_MAP:
        return APP_MAP[base]
    
    return None

if __name__ == "__main__":
    print(f"📸 Sorting screenshots from: {SOURCE}\n")
    
    if not os.path.exists(SOURCE):
        print(f"❌ Folder not found: {SOURCE}")
        exit(1)
    
    files = [f for f in os.listdir(SOURCE) if os.path.isfile(os.path.join(SOURCE, f))]
    print(f"   Found {len(files)} files\n")
    
    sorted_count = 0
    skipped = []
    
    for filename in sorted(files):
        app = get_app_name(filename)
        
        if app is None:
            skipped.append(filename)
            continue
        
        dest_dir = os.path.join(DEST, app, "screenshots")
        os.makedirs(dest_dir, exist_ok=True)
        
        # Count existing files to number sequentially
        existing = len([f for f in os.listdir(dest_dir) if os.path.isfile(os.path.join(dest_dir, f))])
        ext = os.path.splitext(filename)[1] or ".png"
        new_name = f"{existing + 1:02d}{ext}"
        
        src = os.path.join(SOURCE, filename)
        dst = os.path.join(dest_dir, new_name)
        
        shutil.copy2(src, dst)
        print(f"  ✅ {filename:30s} → data/{app}/screenshots/{new_name}")
        sorted_count += 1
    
    print(f"\n{'='*60}")
    print(f"  Sorted: {sorted_count} files")
    
    if skipped:
        print(f"\n  ⚠️  Couldn't match these ({len(skipped)} files):")
        for f in skipped:
            print(f"     {f}")
    
    # Summary per app
    print(f"\n  Per app:")
    for app in sorted(set(APP_MAP.values())):
        ss_dir = os.path.join(DEST, app, "screenshots")
        if os.path.exists(ss_dir):
            count = len([f for f in os.listdir(ss_dir) if os.path.isfile(os.path.join(ss_dir, f))])
            if count > 0:
                print(f"    {app:15s} {count} screenshots")
    
    print(f"\n🎉 Done!")
