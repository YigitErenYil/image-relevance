import uuid
import time
from pathlib import Path
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models import Image, ProcessingJob
from app.services.vision import classify_image, is_low_confidence, VisionCallFailed
from app.services import cost as cost_service
from app.config import VISION_CALL_MIN_INTERVAL_SECONDS

REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # .../image-matching-engine


def run_tagging_job(job_id: uuid.UUID):
    """Runs in a background task (see routers/batch.py). Uses its own DB
    session since it outlives the triggering request. Processes every
    untagged image; a per-image failure (after vision.py's own retries are
    exhausted) is logged and counted, but never stops the batch — one bad
    image should not take down the whole job."""
    db = SessionLocal()
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if job is None:
            return

        images = db.query(Image).filter(Image.processed_at.is_(None)).all()
        job.total_items = len(images)
        job.status = "running"
        db.commit()

        for image in images:
            image_path = REPO_ROOT / image.filename.replace("\\", "/")
            try:
                result = classify_image(image_path)

                image.subject = result.subject
                image.category = result.category
                image.attributes = result.attributes
                image.caption = result.caption
                image.confidence = result.confidence
                image.flagged_low_confidence = is_low_confidence(result)
                image.processed_at = datetime.now(timezone.utc)
                db.commit()

                cost_service.log_vision_call(db, image.id)
                job.processed_items += 1

            except VisionCallFailed as e:
                # Leave the image unprocessed (processed_at stays NULL) so
                # it's picked up again on the next batch run. Never write a
                # guessed result.
                job.failed_items += 1
                print(f"[tagging_job] FAILED {image.filename}: {e}")

            db.commit()
            time.sleep(VISION_CALL_MIN_INTERVAL_SECONDS)

        job.status = "completed"
        db.commit()

    except Exception as e:
        db.rollback()
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if job:
            job.status = "failed"
            db.commit()
        print(f"[tagging_job] job {job_id} crashed: {e}")
    finally:
        db.close()
