import uuid
from sqlalchemy.orm import Session

from app.models import CostLogEntry
from app.config import ESTIMATED_VISION_CALL_COST_MICROS, ESTIMATED_EMBEDDING_CALL_COST_MICROS


def log_vision_call(db: Session, image_id: uuid.UUID):
    db.add(CostLogEntry(
        call_type="vision",
        reference_id=image_id,
        estimated_cost_micros=ESTIMATED_VISION_CALL_COST_MICROS,
    ))
    db.commit()


def log_embedding_call(db: Session, reference_id: uuid.UUID):
    db.add(CostLogEntry(
        call_type="embedding",
        reference_id=reference_id,
        estimated_cost_micros=ESTIMATED_EMBEDDING_CALL_COST_MICROS,
    ))
    db.commit()
