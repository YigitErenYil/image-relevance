import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Post, PostEmbedding, Suggestion, Image
from app.schemas import PostCreate, PostResponse, SuggestionResponse
from app.services.matching import rank_images_for_embedding
from app.services.guard import evaluate_match

router = APIRouter()


@router.post("/posts", response_model=PostResponse, status_code=201)
def create_post(payload: PostCreate, db: Session = Depends(get_db)):
    post = Post(title=payload.title, content=payload.content)
    db.add(post)
    db.commit()
    db.refresh(post)
    return PostResponse(id=post.id, title=post.title, content=post.content)


@router.get("/posts")
def list_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).all()
    return [{"id": p.id, "title": p.title} for p in posts]


@router.get("/posts/{post_id}/images", response_model=SuggestionResponse)
def get_image_suggestion(post_id: uuid.UUID, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    post_embedding = db.query(PostEmbedding).filter(PostEmbedding.post_id == post_id).first()
    if post_embedding is None:
        raise HTTPException(
            status_code=409,
            detail="Post has not been embedded yet — run POST /batch/embed first",
        )

    ranked = rank_images_for_embedding(db, post_embedding.embedding)
    top_image, top_score = ranked[0] if ranked else (None, None)

    result = evaluate_match(post.title, post.content, top_image, top_score)

    suggestion = Suggestion(
        post_id=post.id,
        image_id=top_image.id if (top_image and result["verdict"] == "approved") else None,
        similarity_score=top_score,
        guard_verdict=result["verdict"],
        explanation=result["explanation"],
    )
    db.add(suggestion)
    db.commit()

    return SuggestionResponse(
        post_id=post.id,
        image_id=suggestion.image_id,
        image_filename=top_image.filename if suggestion.image_id else None,
        similarity_score=top_score,
        guard_verdict=result["verdict"],
        explanation=result["explanation"],
    )


@router.post("/posts/{post_id}/images/force-check", response_model=SuggestionResponse)
def force_check_image(post_id: uuid.UUID, image_filename: str, db: Session = Depends(get_db)):
    """Dev/eval utility: force the guard to evaluate a SPECIFIC image against
    a post, bypassing ranking. Used to demonstrate/prove the guard rejects a
    deliberately wrong candidate (e.g. a wolf image forced onto a fox post)
    per the capstone's Probe 3, independent of what would normally rank #1."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    normalized_target = image_filename.replace("\\", "/")
    image = None
    for candidate in db.query(Image).all():
        if candidate.filename.replace("\\", "/") == normalized_target:
            image = candidate
            break
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    from app.models import ImageEmbedding, PostEmbedding as PE
    post_embedding = db.query(PE).filter(PE.post_id == post_id).first()
    image_embedding = db.query(ImageEmbedding).filter(ImageEmbedding.image_id == image.id).first()
    if post_embedding is None or image_embedding is None:
        raise HTTPException(status_code=409, detail="Post or image not embedded yet")

    from app.services.matching import cosine_similarity
    score = cosine_similarity(post_embedding.embedding, image_embedding.embedding)

    result = evaluate_match(post.title, post.content, image, score)

    return SuggestionResponse(
        post_id=post.id,
        image_id=image.id if result["verdict"] == "approved" else None,
        image_filename=image.filename,
        similarity_score=score,
        guard_verdict=result["verdict"],
        explanation=result["explanation"],
    )