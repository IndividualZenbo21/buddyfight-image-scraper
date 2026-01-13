import os
from datetime import datetime

BASE_URL = "https://buddyfight.fandom.com"
CATEGORY_URL = f"{BASE_URL}/wiki/Category:Product"

ROOT_FOLDER = "./BuddyfightImages"
LOG_FOLDER = "./Download Log"

os.makedirs(ROOT_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)

SESSION_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "image/png,image/jpeg,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://buddyfight.fandom.com/",
}

LOG_FILE = os.path.join(LOG_FOLDER, f"download_log-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt")
