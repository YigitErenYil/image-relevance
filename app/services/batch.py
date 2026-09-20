import uuid
import time
from pathlib import Path
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models import Image, Post, ImageEmbedding, PostEmbedding, ProcessingJob
from app.services.vision import classify_image, is_low_confidence, VisionCallFailed
from app.services.embeddings import embed_text, EmbeddingCallFailed
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


def run_embedding_job(job_id: uuid.UUID):
    """Embeds every tagged-but-not-yet-embedded image (by its caption) and
    every not-yet-embedded post (by title + content). Same pattern as the
    tagging job: own DB session, per-item try/except so one failure doesn't
    stop the batch, job progress tracked throughout."""
    db = SessionLocal()
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if job is None:
            return

        images = (
            db.query(Image)
            .filter(Image.processed_at.isnot(None))
            .filter(~Image.id.in_(db.query(ImageEmbedding.image_id)))
            .all()
        )
        posts = (
            db.query(Post)
            .filter(~Post.id.in_(db.query(PostEmbedding.post_id)))
            .all()
        )

        job.total_items = len(images) + len(posts)
        job.status = "running"
        db.commit()

        for image in images:
            try:
                vector = embed_text(image.caption)
                db.add(ImageEmbedding(image_id=image.id, embedding=vector))
                db.commit()
                cost_service.log_embedding_call(db, image.id)
                job.processed_items += 1
            except EmbeddingCallFailed as e:
                job.failed_items += 1
                print(f"[embedding_job] FAILED image {image.filename}: {e}")
            db.commit()
            time.sleep(VISION_CALL_MIN_INTERVAL_SECONDS)

        for post in posts:
            try:
                vector = embed_text(f"{post.title} {post.content}")
                db.add(PostEmbedding(post_id=post.id, embedding=vector))
                db.commit()
                cost_service.log_embedding_call(db, post.id)
                job.processed_items += 1
            except EmbeddingCallFailed as e:
                job.failed_items += 1
                print(f"[embedding_job] FAILED post {post.title}: {e}")
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
        print(f"[embedding_job] job {job_id} crashed: {e}")
    finally:
        db.close()
