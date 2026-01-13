import re
from urllib.parse import unquote

def get_full_image_url(img_url):
    img_url = img_url.split("/revision")[0]
    img_url = unquote(img_url)

    if "format=original" not in img_url:
        img_url += "?format=original"

    return img_url


def sanitize_name(text):
    return re.sub(r'[\\/*:<>|"?]', "_", text)
