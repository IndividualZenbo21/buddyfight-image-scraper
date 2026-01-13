import os
import requests
from helpers import sanitize_name, get_full_image_url
from config import SESSION_HEADERS

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

    return count
