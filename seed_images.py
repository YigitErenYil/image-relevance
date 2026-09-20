"""
Loads data/images/manifest.json (from scripts/fetch_images.py) into the
`images` table so the batch tagging job has something to process.

Usage:
    docker compose exec api python seed_images.py
"""
import json
from pathlib import Path

from app.database import SessionLocal, Base, engine
from app.models import Image

Base.metadata.create_all(bind=engine)

REPO_ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = REPO_ROOT / "data" / "images" / "manifest.json"

if not MANIFEST_PATH.exists():
    raise SystemExit(f"Manifest not found at {MANIFEST_PATH} — run scripts/fetch_images.py first.")

manifest = json.loads(MANIFEST_PATH.read_text())

db = SessionLocal()
inserted = 0
skipped = 0

for entry in manifest:
    existing = db.query(Image).filter(Image.filename == entry["filename"]).first()
    if existing:
        skipped += 1
        continue

    db.add(Image(
        filename=entry["filename"],
        source_category=entry["source_category"],
    ))
    inserted += 1

db.commit()
db.close()

print(f"Seeded. Inserted {inserted} images, skipped {skipped} already-present.")
