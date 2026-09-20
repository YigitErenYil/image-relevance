from typing import Optional

from app.config import SIMILARITY_THRESHOLD, CATEGORY_KEYWORDS
from app.models import Image


def detect_category(text: str) -> Optional[str]:
    """Simple, transparent keyword match against our fixed 5-category
    domain (see CATEGORY_KEYWORDS) -- includes scientific names so 'Vulpes
    vulpes' in a post matches an image tagged 'fox'. Returns the category
    with the most keyword hits, or None if nothing matches (post/caption
    isn't clearly about one of our known animals)."""
    text_lower = text.lower()
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits:
            scores[category] = hits
    if not scores:
        return None
    return max(scores, key=scores.get)


def evaluate_match(post_title: str, post_content: str, image: Optional[Image], similarity_score: Optional[float]) -> dict:
    """Returns {"verdict": "approved"|"rejected"|"no_match", "explanation": str}.
    Never returns a bare boolean -- always an explained decision, per the
    capstone brief's "mismatch guard" requirement."""
    if image is None or similarity_score is None:
        return {
            "verdict": "no_match",
            "explanation": "No candidate images are tagged and embedded yet.",
        }

    post_text = f"{post_title} {post_content}"
    expected_category = detect_category(post_text)
    image_text = f"{image.subject or ''} {image.caption or ''}"
    image_category = detect_category(image_text)

    # 1. Category/subject check -- this is what catches the fox/wolf
    # near-miss: a wolf photo can score deceptively high on pure caption
    # similarity to a fox post, but the category check catches it outright.
    if expected_category and image_category and expected_category != image_category:
        return {
            "verdict": "rejected",
            "explanation": (
                f"Animal category mismatch: expected {expected_category}, "
                f"detected {image_category} (image subject: {image.subject!r})"
            ),
        }

    # 2. Confidence check -- never trust a similarity match riding on a
    # vision tag the model itself was unsure about.
    if image.flagged_low_confidence:
        return {
            "verdict": "rejected",
            "explanation": (
                f"Image tagging confidence was too low to trust "
                f"(confidence={image.confidence}), even though similarity "
                f"was {similarity_score:.2f}."
            ),
        }

    # 3. Similarity threshold -- set from the eval set in Phase 4.
    if similarity_score < SIMILARITY_THRESHOLD:
        return {
            "verdict": "no_match",
            "explanation": (
                f"No image cleared the similarity threshold "
                f"(best: {similarity_score:.2f}, cutoff: {SIMILARITY_THRESHOLD})."
            ),
        }

    return {
        "verdict": "approved",
        "explanation": (
            f"Category match ({image_category or 'unclassified'}) and "
            f"similarity {similarity_score:.2f} clears the {SIMILARITY_THRESHOLD} threshold."
        ),
    }
