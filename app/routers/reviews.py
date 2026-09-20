import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Suggestion, Post, Image
from app.schemas import SuggestionReviewRequest, SuggestionDetail

router = APIRouter()


@router.get("/suggestions", response_model=list[SuggestionDetail])
def list_suggestions(db: Session = Depends(get_db)):
    """Inspect every suggestion the system has made, with its guard verdict
    and explanation — the 'inspect why an image was selected or refused'
    half of the review workflow."""
    rows = db.query(Suggestion, Post).join(Post, Post.id == Suggestion.post_id).all()

    results = []
    for suggestion, post in rows:
        image_filename = None
        if suggestion.image_id:
            image = db.query(Image).filter(Image.id == suggestion.image_id).first()
            image_filename = image.filename if image else None

        results.append(SuggestionDetail(
            id=suggestion.id,
            post_id=post.id,
            post_title=post.title,
            image_id=suggestion.image_id,
            image_filename=image_filename,
            similarity_score=suggestion.similarity_score,
            guard_verdict=suggestion.guard_verdict,
            explanation=suggestion.explanation,
            review_status=suggestion.review_status,
        ))
    return results


@router.post("/suggestions/{suggestion_id}/review", response_model=SuggestionDetail)
def review_suggestion(suggestion_id: uuid.UUID, payload: SuggestionReviewRequest, db: Session = Depends(get_db)):
    """The 'approve or reject a suggested pairing' half of the review
    workflow — a human can override the guard's own verdict either way."""
    suggestion = db.query(Suggestion).filter(Suggestion.id == suggestion_id).first()
    if suggestion is None:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    suggestion.review_status = payload.review_status
    db.commit()
    db.refresh(suggestion)

    post = db.query(Post).filter(Post.id == suggestion.post_id).first()
    image_filename = None
    if suggestion.image_id:
        image = db.query(Image).filter(Image.id == suggestion.image_id).first()
        image_filename = image.filename if image else None

    return SuggestionDetail(
        id=suggestion.id,
        post_id=suggestion.post_id,
        post_title=post.title if post else "",
        image_id=suggestion.image_id,
        image_filename=image_filename,
        similarity_score=suggestion.similarity_score,
        guard_verdict=suggestion.guard_verdict,
        explanation=suggestion.explanation,
        review_status=suggestion.review_status,
    )
