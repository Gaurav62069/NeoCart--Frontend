import time
import threading
import hashlib
import requests
from .excel_updater import run_seeding

# Google Sheets Excel Export Link
EXCEL_URL = "https://docs.google.com/spreadsheets/d/1J4OprDdBPhB3M8_xmKob6vV5WXLkON3L/export?format=xlsx"

# How often to check for changes (in seconds)
CHECK_INTERVAL = 20   # 🔁 every 20 seconds

# Store last known file hash
_last_hash = None

def get_file_hash():
    """Return MD5 hash of the remote Excel file content."""
    try:
        response = requests.get(EXCEL_URL)
        if response.status_code != 200:
            print(f"⚠️ Failed to fetch sheet (status {response.status_code})")
            return None
        file_hash = hashlib.md5(response.content).hexdigest()
        return file_hash
    except Exception as e:
        print(f"⚠️ Error while fetching file hash: {e}")
        return None


def watch_google_sheet():
    """Continuously check Google Sheet for changes and sync instantly."""
    global _last_hash
    print(f"🕵️ Watching Google Sheet for updates: {EXCEL_URL}")

    while True:
        new_hash = get_file_hash()

        if new_hash and new_hash != _last_hash:
            print("🟢 Change detected in Google Sheet — syncing now...")
            run_seeding()
            _last_hash = new_hash
        else:
            print("🟡 No new change detected.")

        time.sleep(CHECK_INTERVAL)


def start_watcher_in_thread():
    """Starts the watcher thread (daemon)."""
    watcher_thread = threading.Thread(target=watch_google_sheet, daemon=True)
    watcher_thread.start()
    print("✅ Google Sheets watcher started (background mode).")
