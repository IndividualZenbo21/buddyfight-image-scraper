from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from urllib.parse import unquote
from bs4 import BeautifulSoup
import requests
import os
import time
import re
from urllib.parse import urljoin
from time import sleep
from datetime import datetime

# =========================
# CONFIG
# =========================

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

# =========================
# HELPERS
# =========================

def get_full_image_url(img_url):
    img_url = img_url.split("/revision")[0]
    img_url = unquote(img_url)

    if "format=original" not in img_url:
        img_url += "?format=original"

    return img_url


def sanitize_name(text):
    return re.sub(r'[\\/*:<>|"?]', "_", text)

# =========================
# SELENIUM SETUP
# =========================

options = Options()
options.add_argument("--headless=new")  # modern headless mode
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36")
driver = webdriver.Chrome(options=options)

# =========================
# LOAD PRODUCT PAGES
# =========================

print("🔍 Loading product page list...")
success = False
for attempt in range(3):
    try:
        driver.set_page_load_timeout(120)
        driver.get(CATEGORY_URL)
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.category-page__member-link")))
        for y in range(0, 3000, 500):
            driver.execute_script(f"window.scrollTo(0, {y});")
            time.sleep(1)
        success = True
        break
    except Exception as e:
        print(f"  ⚠️ Timeout loading product list (attempt {attempt+1}/3): {e}")
        time.sleep(5)

if not success:
    raise SystemExit("❌ Failed to load product list.")

soup = BeautifulSoup(driver.page_source, "html.parser")
product_links = []
for a in soup.select("a.category-page__member-link"):
    href = a.get("href", "")
    if href.startswith("/wiki/") and "Category:" not in href:
        full_url = urljoin(BASE_URL, href)
        if full_url not in product_links:
            product_links.append(full_url)

print(f"✅ Found {len(product_links)} product pages.")

# =========================
# DVD LISTING HANDLER
# =========================

def download_dvd_listing_images(soup, set_folder_path):
    print("  📀 Detected DVD listing page")

    tables = soup.find_all("table")
    count = 0

    for table in tables:
        rows = table.select("tr")[1:]  # skip header

        for row in rows:
            img_tag = row.find("img")
            if not img_tag:
                continue

            cols = row.select("td")
            if len(cols) < 3:
                continue

            # Volume is usually the last column
            volume_text = cols[-1].get_text(strip=True)
            if not volume_text:
                continue

            volume = sanitize_name(volume_text)

            img_url = img_tag.get("data-src") or img_tag.get("src")
            if not img_url or "static.wikia.nocookie.net" not in img_url:
                continue

            img_url = get_full_image_url(img_url)

            ext = os.path.splitext(img_url)[1].split("?")[0]
            if not ext:
                ext = ".png"

            filename = f"Future Card Buddyfight DVD - {volume}{ext}"
            filepath = os.path.join(set_folder_path, filename)

            if os.path.exists(filepath):
                continue

            try:
                r = requests.get(img_url, headers=SESSION_HEADERS, timeout=60)
                r.raise_for_status()

                with open(filepath, "wb") as f:
                    f.write(r.content)

                print(f"  ✅ {filename}")
                count += 1

            except Exception as e:
                print(f"  ⚠️ Error downloading DVD image: {e}")

    print(f"📥 Downloaded {count} DVD covers.")

# =========================
# CARD PAGE HANDLER
# =========================

failed_urls = []
skip_urls = []
download_summary = {} # stores {set_code: {"name": set_name, "count": num}}

def download_images_from_page(url):
    print(f"\n🔍 Scraping: {url}")
    try:
        driver.set_page_load_timeout(120)
        driver.get(url)

        if "<table" not in driver.page_source:
            print(f"  ⏭ No <table> tag found. Skipping page early.")
            skip_urls.append(url)
            return

        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        for y in range(0, 4000, 400):
            driver.execute_script(f"window.scrollTo(0, {y});")
            time.sleep(1)
    except WebDriverException as e:
        print(f"  ❌ Failed to load page: {e}")
        raise

    soup = BeautifulSoup(driver.page_source, "html.parser")
    page_title = soup.select_one("h1").get_text(strip=True)

    set_folder = sanitize_name(page_title)
    set_folder_path = os.path.join(ROOT_FOLDER, set_folder)
    os.makedirs(set_folder_path, exist_ok=True)

    # DVD PAGE
    if "DVD listing" in page_title or "DVD_listing" in url:
        download_dvd_listing_images(soup, set_folder_path)
        return
    
    # CARD PAGE
    if ":" in page_title:
        set_code, set_name = page_title.split(":", 1)
        set_code = set_code.strip()
        set_name = set_name.strip()
    else:
        set_code = page_title.strip()
        set_name = ""

    count = 0
    downloaded_files = []
    tables = soup.find_all("table")

    if not tables:
        print(f"  ❌ No card tables found. Skipping page.")
        skip_urls.append(url)
        return

    for table in tables:
        rows = table.select("tr")[1:]
        for row in rows:
            img_tag = row.find("img")
            if not img_tag:
                continue

            cols = row.select("td")
            card_number = ""
            card_name = ""

            if len(cols) >= 2:
                num_txt = cols[1].get_text(strip=True)
                if num_txt:
                    card_number = sanitize_name(num_txt)

            if len(cols) >= 3:
                name_tag = cols[2].find("a")
                if name_tag:
                    card_name = sanitize_name(name_tag.get("title") or name_tag.text.strip())

            if not card_number or not card_name:
                alt = img_tag.get("alt", "").strip()
                if alt:
                    match = re.match(r"([A-Z]+-[A-Z0-9_/]+)\s*-?\s*(.*)", alt)
                    if match:
                        if not card_number:
                            card_number = sanitize_name(match.group(1))
                        if not card_name:
                            card_name = sanitize_name(match.group(2))

            img_url = img_tag.get("data-src") or img_tag.get("src")
            
            if not img_url or "static.wikia.nocookie.net" not in img_url:
                continue

            img_url = get_full_image_url(img_url)     
            ext = os.path.splitext(img_url)[1].split("?")[0]

            filename = f"{card_number} - {card_name}{ext}"
            filepath = os.path.join(set_folder_path, filename) 
            
            if os.path.exists(filepath): 
                continue

            for attempt in range(3):
                try:
                    r = requests.get(img_url, headers=SESSION_HEADERS, timeout=90)
                    r.raise_for_status()

                    with open(filepath, "wb") as f:
                        f.write(r.content)

                    print(f"  ✅ {filename}")
                    downloaded_files.append(filename)
                    count += 1
                    break

                except Exception as e:
                    print(f"  ⚠️ Error downloading image: {e}")
                    sleep(2)


    if count > 0:
        print(f"📥 Downloaded {count} cards from '{page_title}'.")
        download_summary[set_code] = {"name": set_name, "count": count}
    else:
        print(f"  ❌ No images downloaded. Skipping page.")
        skip_urls.append(url)

# =========================
# MAIN LOOP
# =========================

for url in product_links:
    for attempt in range(3):
        try:
            download_images_from_page(url)
            break
        except Exception as e:
            print(f"  ⚠️ Retry {attempt+1}: {e}")
            sleep(3)
    else:
        failed_urls.append(url)

if failed_urls:
    print("\n🔁 Retrying failed pages after initial run:")
    for url in failed_urls:
        try:
            download_images_from_page(url)
        except Exception as e:
            print(f"  ❌ Final failure for {url}: {e}")

driver.quit()

# =========================
# LOG FILE
# =========================

total_images = sum(info["count"] for info in download_summary.values())

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("Buddyfight Image Scraper - Download Summary\n")
    f.write("=" * 50 + "\n\n")

    for set_code, info in download_summary.items():
        name = f" - {info['name']}" if info["name"] else ""
        f.write(f"{set_code}{name}: {info['count']} images\n")

    f.write("=" * 50 + "\n")
    f.write(f"TOTAL: {total_images} images downloaded\n")


print(f"\n✅ All done! Images saved to 'BuddyfightImages'. Log written to '{LOG_FILE}'.")
