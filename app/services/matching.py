import math
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.models import Image, ImageEmbedding


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def rank_images_for_embedding(db: Session, post_embedding: List[float]) -> List[Tuple[Image, float]]:
    """Returns every embedded, tagged image ranked by cosine similarity to
    the given post embedding, descending."""
    rows = (
        db.query(Image, ImageEmbedding)
        .join(ImageEmbedding, ImageEmbedding.image_id == Image.id)
        .filter(Image.processed_at.isnot(None))
        .all()
    )
    scored = [(image, cosine_similarity(post_embedding, emb.embedding)) for image, emb in rows]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored
