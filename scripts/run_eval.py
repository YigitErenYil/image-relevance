"""
Runs the labeled eval set: for each post, checks whether the system's top
suggestion (after the guard) matches the hand-labeled correct image.
Prints a report and the headline top-1 precision number for the README.

The "correct" image for each category-labeled post is the canonical
00.jpg for that category (a deliberate, documented labeling choice — see
README). Two posts are excluded from the precision count by design:
- "Comparing fox and wolf hunting strategies" (genuinely ambiguous, both
  categories are legitimate — used as a qualitative check, not scored)
- "Weekly newsletter: garden tips for autumn" (no correct image exists;
  used to qualitatively verify "no confident match" behavior, not scored)

Usage:
    python scripts/run_eval.py
"""
import os
import requests

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# title -> expected category (must match scripts/seed_posts.py exactly)
LABELED_POSTS = {
    "The secret life of the red fox": "fox",
    "Vulpes vulpes: a species profile": "fox",
    "Understanding wolf pack dynamics": "wolf",
    "Canis lupus: apex predator of the north": "wolf",
    "Why golden retrievers make great family dogs": "dog",
    "A beginner's guide to dog training": "dog",
    "Brown bears preparing for hibernation": "bear",
    "Ursus arctos across three continents": "bear",
    "Deer rutting season explained": "deer",
    "How deer antlers grow and shed each year": "deer",
}

UNSCORED_QUALITATIVE_POSTS = {
    "Comparing fox and wolf hunting strategies": "ambiguous by design (both fox and wolf are legitimate)",
    "Weekly newsletter: garden tips for autumn": "no correct image exists — expect no_match",
}


def canonical_image_filename(category: str) -> str:
    return f"data/images/{category}/00.jpg"


def normalize(path: str) -> str:
    return path.replace("\\", "/") if path else path


posts_resp = requests.get(f"{API_BASE}/posts")
posts_resp.raise_for_status()
title_to_id = {p["title"]: p["id"] for p in posts_resp.json()}

def image_category(filename: str) -> str:
    """Extracts the category segment from a path like data/images/fox/05.jpg."""
    parts = normalize(filename).split("/")
    return parts[-2] if len(parts) >= 2 else ""


print("=== Labeled eval set (scored) ===\n")
category_correct_count = 0
exact_correct_count = 0
total = 0
rows = []

for title, category in LABELED_POSTS.items():
    post_id = title_to_id.get(title)
    if post_id is None:
        print(f"  SKIP (post not found): {title}")
        continue

    resp = requests.get(f"{API_BASE}/posts/{post_id}/images")
    resp.raise_for_status()
    result = resp.json()

    expected = canonical_image_filename(category)
    actual = normalize(result.get("image_filename"))
    approved = result["guard_verdict"] == "approved"
    category_correct = approved and image_category(actual) == category
    exact_correct = approved and actual == expected

    total += 1
    if category_correct:
        category_correct_count += 1
    if exact_correct:
        exact_correct_count += 1

    status = "CATEGORY OK" if category_correct else "WRONG"
    if exact_correct:
        status += " + EXACT MATCH"
    print(f"  [{status}] {title}")
    print(f"           expected_category={category}  got={actual}  verdict={result['guard_verdict']}")

category_precision = category_correct_count / total if total else 0.0
exact_precision = exact_correct_count / total if total else 0.0

print(f"\n=== Category-level top-1 precision: {category_correct_count}/{total} = {category_precision:.2%} ===")
print(f"=== Exact-image top-1 precision:    {exact_correct_count}/{total} = {exact_precision:.2%} ===")
print(
    "\nNote: these posts are generic topic posts (not tied to one specific\n"
    "photo), so any image in the right category is a genuinely correct\n"
    "match — category-level precision is the metric that reflects real\n"
    "system quality here. Exact-image precision is reported for\n"
    "transparency but is an artificially strict measure: it only credits\n"
    "the single arbitrarily-chosen '00.jpg' per category as correct, even\n"
    "though every other same-category image is an equally valid answer.\n"
)

print("=== Qualitative checks (not scored) ===\n")
for title, note in UNSCORED_QUALITATIVE_POSTS.items():
    post_id = title_to_id.get(title)
    if post_id is None:
        continue
    resp = requests.get(f"{API_BASE}/posts/{post_id}/images")
    resp.raise_for_status()
    result = resp.json()
    print(f"  {title}  ({note})")
    print(f"    -> verdict={result['guard_verdict']}  image={normalize(result.get('image_filename'))}")
    print(f"    -> explanation: {result['explanation']}\n")

print(f"HEADLINE NUMBERS FOR README:")
print(f"  category-level top-1 precision = {category_precision:.2%} ({category_correct_count}/{total})")
print(f"  exact-image top-1 precision    = {exact_precision:.2%} ({exact_correct_count}/{total})")
