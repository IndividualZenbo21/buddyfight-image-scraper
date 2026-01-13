import os
import re
import requests
import time
from time import sleep
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException

from helpers import sanitize_name, get_full_image_url
from config import ROOT_FOLDER, SESSION_HEADERS
from dvd_handler import download_dvd_listing_images

failed_urls = []
skip_urls = []
download_summary = {} # stores {set_code: {"name": set_name, "count": num}}

def download_images_from_page(driver, url):
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
        count = download_dvd_listing_images(soup, set_folder_path)

        if count > 0:
            print(f"📥 Downloaded {count} cards from '{page_title}'.")
            download_summary[page_title] = {
                "name": "DVD Listing",
                "count": count
            }
        else:
            print(f"  ❌ No images downloaded. Skipping page.")
            skip_urls.append(url)
            
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