from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Image, CostLogEntry

router = APIRouter()


@router.get("/images")
def list_images(db: Session = Depends(get_db)):
    images = db.query(Image).all()
    return [
        {
            "id": img.id,
            "filename": img.filename,
            "source_category": img.source_category,
            "subject": img.subject,
            "category": img.category,
            "attributes": img.attributes,
            "caption": img.caption,
            "confidence": img.confidence,
            "flagged_low_confidence": img.flagged_low_confidence,
            "processed": img.processed_at is not None,
        }
        for img in images
    ]


@router.get("/costs")
def cost_summary(db: Session = Depends(get_db)):
    rows = db.query(
        CostLogEntry.call_type,
        func.count(CostLogEntry.id),
        func.sum(CostLogEntry.estimated_cost_micros),
    ).group_by(CostLogEntry.call_type).all()

    return {
        "by_call_type": [
            {"call_type": r[0], "call_count": r[1], "total_estimated_cost_micros": r[2]}
            for r in rows
        ],
        "total_estimated_cost_micros": sum(r[2] for r in rows) if rows else 0,
    }
