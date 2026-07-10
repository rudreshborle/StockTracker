import re

def extract_product_id(url: str):

    match = re.search(r"/prid/(\d+)", url)

    if match:
        return match.group(1)

    return None
