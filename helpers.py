import re
import os
from urllib.parse import unquote

def get_full_image_url(img_url):
    img_url = img_url.split("/revision")[0]
    img_url = unquote(img_url)

    if "format=original" not in img_url:
        img_url += "?format=original"

    return img_url


def sanitize_name(text):
    return re.sub(r'[\\/*:<>|"?]', "_", text)

def get_input_links():
    links_input = input(
        "Choose input mode:\n"
        "  1 = Paste links manually\n"
        "  2 = Use links.txt\n"
        "  ENTER = Scrape Category:Product\n"
        "> "
    ).strip()

    if links_input == "1":
        manual = input("Paste links (comma-separated):\n> ").strip()
        if manual:
            return [x.strip() for x in manual.split(",") if x.strip()]
        return []

    if links_input == "2":
        if os.path.exists("links.txt"):
            with open("links.txt", "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        else:
            print("⚠️ links.txt not found. Falling back to normal mode.")
            return []

    return []
