import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional, List
import json

from ..models.job import Job


def create_job(
    db: Session, 
    job_type: str, 
    paper_id: int, 
    parameters: Optional[dict] = None
) -> Job:
    """Create a new job"""
    job_id = str(uuid.uuid4())
    
    job = Job(
        id=job_id,
        type=job_type,
        paper_id=paper_id,
        parameters=json.dumps(parameters) if parameters else None,
        status="pending",
        progress=0
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: str) -> Optional[Job]:
    """Get a job by ID"""
    return db.query(Job).filter(Job.id == job_id).first()


def get_jobs_by_paper(db: Session, paper_id: int, job_type: Optional[str] = None) -> List[Job]:
    """Get all jobs for a paper, optionally filtered by type"""
    query = db.query(Job).filter(Job.paper_id == paper_id)
    if job_type:
        query = query.filter(Job.type == job_type)
    return query.order_by(Job.created_at.desc()).all()


def update_job_status(
    db: Session, 
    job_id: str, 
    status: str,
    progress: Optional[int] = None,
    progress_message: Optional[str] = None,
    result: Optional[dict] = None,
    error_message: Optional[str] = None
) -> Optional[Job]:
    """Update job status and progress"""
    job = get_job(db, job_id)
    if not job:
        return None
    
    job.status = status
    
    if progress is not None:
        job.progress = progress
        
    if progress_message is not None:
        job.progress_message = progress_message
    
    if result is not None:
        job.result = json.dumps(result)
    
    if error_message is not None:
        job.error_message = error_message
    
    # Set timestamps based on status
    now = datetime.utcnow()
    if status == "processing" and not job.started_at:
        job.started_at = now
    elif status in ["completed", "failed"] and not job.completed_at:
        job.completed_at = now
    
    db.commit()
    db.refresh(job)
    return job


def start_job(db: Session, job_id: str) -> Optional[Job]:
    """Mark job as started"""
    return update_job_status(db, job_id, "processing", progress=0, progress_message="開始中...")


def complete_job(db: Session, job_id: str, result: dict) -> Optional[Job]:
    """Mark job as completed with result"""
    return update_job_status(db, job_id, "completed", progress=100, result=result)


def fail_job(db: Session, job_id: str, error_message: str) -> Optional[Job]:
    """Mark job as failed with error message"""
    return update_job_status(db, job_id, "failed", error_message=error_message)


def get_pending_jobs(db: Session, job_type: Optional[str] = None) -> List[Job]:
    """Get all pending jobs, optionally filtered by type"""
    query = db.query(Job).filter(Job.status == "pending")
    if job_type:
        query = query.filter(Job.type == job_type)
    return query.order_by(Job.created_at).all()


def cleanup_old_jobs(db: Session, days: int = 30) -> int:
    """Delete jobs older than specified days"""
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    deleted_count = db.query(Job).filter(
        Job.created_at < cutoff_date,
        Job.status.in_(["completed", "failed"])
    ).delete()
    
    db.commit()
    return deleted_count