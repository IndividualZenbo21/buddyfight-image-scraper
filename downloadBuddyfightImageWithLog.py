import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from time import sleep

from config import BASE_URL, CATEGORY_URL, LOG_FILE
from card_handler import download_images_from_page, failed_urls, download_summary
from helpers import get_input_links

def main():
    # =========================
    # SELENIUM SETUP
    # =========================

    options = Options()
    options.add_argument("--headless=new")  # modern headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)

    try: 
        # =========================
        # LOAD PRODUCT PAGES
        # =========================

        input_links = get_input_links()

        if input_links: 
            product_links = input_links
            print(f"🔗 Using {len(product_links)} manually provided links.")
        
        else:
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
        # MAIN LOOP
        # =========================

        for url in product_links:
            for attempt in range(3):
                try:
                    download_images_from_page(driver, url)
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
                    download_images_from_page(driver, url)
                except Exception as e:
                    print(f"  ❌ Final failure for {url}: {e}")

    finally:
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


if __name__ == "__main__":
    main()
