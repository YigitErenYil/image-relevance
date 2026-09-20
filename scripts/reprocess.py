"""
Resets one or more images' processed_at to NULL so the next batch job
picks them up again (e.g. after a prompt fix, to redo bad tags without
touching the other 47 that were already fine).

Usage:
    docker compose exec api python scripts/reprocess.py data/images/dog/08.jpg data/images/deer/03.jpg data/images/deer/09.jpg
"""
import sys
import os

# Running as `python scripts/reprocess.py` puts scripts/ (not /code) on
# sys.path, so the `app` package isn't importable without this — unlike
# seed_images.py, which sits at the repo root and doesn't need it.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Image

if len(sys.argv) < 2:
    raise SystemExit("Usage: python scripts/reprocess.py <filename1> [filename2] ...")

filenames = [f.replace("\\", "/") for f in sys.argv[1:]]

db = SessionLocal()
reset_count = 0

# Compare normalized (forward-slash) forms in Python, since some existing
# DB rows still have Windows-style backslashes saved before that was fixed.
all_images = db.query(Image).all()
by_normalized = {img.filename.replace("\\", "/"): img for img in all_images}

for filename in filenames:
    image = by_normalized.get(filename)
    if image is None:
        print(f"  NOT FOUND: {filename}")
        continue
    image.processed_at = None
    image.subject = None
    image.category = None
    image.attributes = None
    image.caption = None
    image.confidence = None
    image.flagged_low_confidence = False
    reset_count += 1
    print(f"  reset: {filename}")

db.commit()
db.close()

print(f"\nDone. {reset_count} image(s) reset — re-run POST /batch/tag-images to reprocess them.")
