import uuid
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProcessingJob
from app.schemas import JobStatusResponse, TriggerJobResponse
from app.services.batch import run_tagging_job, run_embedding_job

router = APIRouter()


@router.post("/batch/tag-images", response_model=TriggerJobResponse, status_code=202)
def trigger_tagging(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = ProcessingJob(job_type="vision_tagging", status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    # Runs off the request path — this endpoint returns immediately, the
    # job progresses in the background. GET /batch/jobs/:id polls status.
    background_tasks.add_task(run_tagging_job, job.id)

    return TriggerJobResponse(job_id=job.id, message="Tagging job started")


@router.post("/batch/embed", response_model=TriggerJobResponse, status_code=202)
def trigger_embedding(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = ProcessingJob(job_type="embedding", status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_embedding_job, job.id)

    return TriggerJobResponse(job_id=job.id, message="Embedding job started")


@router.get("/batch/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        total_items=job.total_items,
        processed_items=job.processed_items,
        failed_items=job.failed_items,
    )
