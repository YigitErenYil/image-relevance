"""
Fetches the image corpus for the capstone from Unsplash (free license) and
records a manifest with the ground-truth search category for each image.

The manifest's `source_category` is what we SEARCHED for — used later to
sanity-check the vision model's own output and to build the eval set. It is
never fed into the matching pipeline itself.

Usage:
    export UNSPLASH_ACCESS_KEY=your_key   # or set it in .env and load it
    python scripts/fetch_images.py

Requires: requests (pip install requests)
"""
import os
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
if not ACCESS_KEY:
    raise SystemExit("Set UNSPLASH_ACCESS_KEY in your environment or .env file first.")

CATEGORIES = {
    "fox": "red fox animal",
    "wolf": "gray wolf animal",
    "dog": "dog animal portrait",
    "bear": "brown bear animal",
    "deer": "deer animal wild",
}
IMAGES_PER_CATEGORY = 10

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "images"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEARCH_URL = "https://api.unsplash.com/search/photos"
HEADERS = {"Authorization": f"Client-ID {ACCESS_KEY}"}


def fetch_category(category: str, query: str, count: int):
    resp = requests.get(
        SEARCH_URL,
        headers=HEADERS,
        params={"query": query, "per_page": count, "orientation": "landscape"},
    )
    resp.raise_for_status()
    results = resp.json()["results"][:count]

    cat_dir = OUT_DIR / category
    cat_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for i, photo in enumerate(results):
        url = photo["urls"]["regular"]
        filename = f"{i:02d}.jpg"
        filepath = cat_dir / filename

        img_resp = requests.get(url)
        img_resp.raise_for_status()
        filepath.write_bytes(img_resp.content)

        entries.append({
            "filename": str(filepath.relative_to(OUT_DIR.parent.parent)),
            "source_category": category,
            "unsplash_id": photo["id"],
            "unsplash_author": photo["user"]["name"],
            "unsplash_url": photo["links"]["html"],
        })
        print(f"  {category}/{filename} <- {photo['id']}")
        time.sleep(0.5)  # be polite to the free-tier rate limit

    return entries


if __name__ == "__main__":
    manifest = []
    for category, query in CATEGORIES.items():
        print(f"Fetching '{category}' ({query})...")
        manifest.extend(fetch_category(category, query, IMAGES_PER_CATEGORY))

    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"\nDone. {len(manifest)} images across {len(CATEGORIES)} categories.")
    print(f"Manifest: {manifest_path}")
